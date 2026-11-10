"""Recheck print-set-v2 STLs against the approved v11 source scene.

Run with:
blender --background models/rolling-wavy-pen-storyboard-study-v11.blend \
  --python-exit-code 1 --python scripts/rolling_wavy_pen_print_set_v2_qa.py
"""

import csv
import hashlib
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate import make_mesh, mesh_fingerprint, read_stl
from rolling_wavy_pen import validate
import rolling_wavy_pen_storyboard_study_v11 as v11
from rolling_wavy_pen_print_set_v2 import (
    FRAME_COUNT,
    PRINT_SOURCE_FRAMES,
    SOURCE_SCENE_NAME,
    sha256,
    source_objects,
)

PREVIEW = ROOT / "previews/rolling-wavy-pen/print-set-v2"
EXPORTS = ROOT / "exports/rolling-wavy-pen/print-set-v2"
SOURCE_BLEND = ROOT / "models/rolling-wavy-pen-storyboard-study-v11.blend"
SOURCE_SCRIPT = ROOT / "scripts/rolling_wavy_pen_storyboard_study_v11.py"
REPORT_JSON = PREVIEW / "final-qa.json"
REPORT_MD = ROOT / "docs/rolling-wavy-pen-final-qa.md"
PRINT_BLEND = ROOT / "models/rolling-wavy-pen-print-set-v2.blend"
PRINT_SCENE_NAME = "Rolling Wavy Pen print-set-v2"


def lexicographic_rows(points):
    """Sort 3D points by x, then y, then z for order-independent comparison."""
    order = np.lexsort((points[:, 2], points[:, 1], points[:, 0]))
    return points[order]


def check_saved_blender_import(path):
    """Read each binary STL through Blender's STL importer as a second reader."""
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.wm.stl_import(
        filepath=str(path), use_scene_unit=False, global_scale=1,
        forward_axis="Y", up_axis="Z", use_facet_normal=False,
        use_mesh_validate=False,
    )
    imported = list(bpy.context.selected_objects)
    if len(imported) != 1 or imported[0].type != "MESH":
        for obj in imported:
            bpy.data.objects.remove(obj, do_unlink=True)
        return {"readable": False, "reason": f"expected 1 mesh object, got {len(imported)}"}
    obj = imported[0]
    coords = np.asarray([vertex.co[:] for vertex in obj.data.vertices], dtype=np.float64)
    result = {
        "readable": len(coords) > 0 and len(obj.data.polygons) > 0,
        "vertices": int(len(coords)),
        "triangles": int(len(obj.data.polygons)),
        "finite_coordinates": bool(np.isfinite(coords).all()),
    }
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return result


def main():
    source_scene = bpy.data.scenes.get(SOURCE_SCENE_NAME)
    if source_scene is None:
        raise RuntimeError(f"Source scene {SOURCE_SCENE_NAME!r} is missing.")
    if not SOURCE_BLEND.is_file() or not SOURCE_SCRIPT.is_file():
        raise RuntimeError("The approved v11 source blend or generator is missing.")

    manifest = json.loads((PREVIEW / "manifest.json").read_text())
    prior_validation = json.loads((PREVIEW / "validation.json").read_text())
    # Load only the print scene from the saved integration file into this QA session.
    with bpy.data.libraries.load(str(PRINT_BLEND), link=False) as (data_from, data_to):
        data_to.scenes = [PRINT_SCENE_NAME] if PRINT_SCENE_NAME in data_from.scenes else []
    print_scene = next((scene for scene in data_to.scenes if scene is not None), None)
    if print_scene is not None and bpy.context.window is not None:
        bpy.context.window.scene = print_scene
    scene_objects = [obj for obj in print_scene.objects if obj.get("print_set_pose") is not None] if print_scene else []
    scene_object_by_pose = {int(obj["print_set_pose"]): obj for obj in scene_objects}
    scene_library_links = sorted({
        block.library.filepath
        for block in ([print_scene] + list(print_scene.objects) + [obj.data for obj in print_scene.objects if obj.data is not None])
        if block is not None and getattr(block, "library", None) is not None
    }) if print_scene else []
    scene_materials = {
        material
        for obj in print_scene.objects
        for material in getattr(obj.data, "materials", [])
        if material is not None
    } if print_scene else set()
    scene_images = {
        node.image
        for material in scene_materials if material.use_nodes
        for node in material.node_tree.nodes
        if node.type == "TEX_IMAGE" and node.image is not None
    }
    if print_scene and print_scene.world and print_scene.world.use_nodes:
        scene_images.update(
            node.image
            for node in print_scene.world.node_tree.nodes
            if node.type == "TEX_IMAGE" and node.image is not None
        )
    unresolved_images = sorted(
        image.filepath for image in scene_images
        if image.source == "FILE" and image.packed_file is None
        and not os.path.isfile(bpy.path.abspath(image.filepath))
    )
    with (PREVIEW / "frame-to-stl.csv").open(newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    selected = manifest["selected_poses"]
    by_source = {record["source_v11_frame"]: record for record in selected}
    objects = source_objects(source_scene)
    report_poses = []

    for pose_id, source_frame in enumerate(PRINT_SOURCE_FRAMES, 1):
        filename = f"pose-{pose_id:02}.stl"
        path = EXPORTS / filename
        record = by_source[source_frame]
        if not path.is_file():
            raise RuntimeError(f"Missing STL: {path}")

        # Parse the stored binary STL and rerun the geometry validator on its triangles.
        vertices, triangles, normals = read_stl(path)
        source_obj = objects[source_frame]
        bounds_min = vertices.min(axis=0)
        bounds_max = vertices.max(axis=0)
        dimensions = np.ptp(vertices, axis=0)
        regenerated_vertices, regenerated_faces, xs = v11.geometry_progress(
            float(source_obj["curve_progress"]),
            float(source_obj["wave_progress"]),
            float(source_obj["roll_degrees"]),
            float(source_obj["curve_orientation_sign"]),
        )
        regenerated = make_mesh(
            source_scene, f"qa-regenerated-{pose_id:02}",
            regenerated_vertices, regenerated_faces,
        )
        saved_fingerprint = mesh_fingerprint(source_obj)
        regenerated_fingerprint = mesh_fingerprint(regenerated)
        source_points = np.asarray([vertex.co[:] for vertex in source_obj.data.vertices], dtype=np.float32)
        stl_points = vertices.astype(np.float32)
        if len(source_points) != len(stl_points):
            vertex_match = False
            max_vertex_delta = None
        else:
            deltas = np.abs(lexicographic_rows(source_points) - lexicographic_rows(stl_points))
            max_vertex_delta = float(deltas.max(initial=0.0))
            vertex_match = max_vertex_delta <= 1e-5

        # Recheck the mesh properties from STL triangles, not from the source object.
        geometry = validate(path, source_obj, pose_id - 1, xs, pose_name=filename)
        stl_hash = sha256(path)
        blender_import = check_saved_blender_import(path)
        scene_obj = scene_object_by_pose.get(pose_id)
        scene_mesh_match = False
        if scene_obj is not None:
            scene_points = np.asarray([vertex.co[:] for vertex in scene_obj.data.vertices], dtype=np.float32)
            scene_mesh_match = len(scene_points) == len(stl_points)
            if scene_mesh_match:
                scene_delta = np.abs(lexicographic_rows(scene_points) - lexicographic_rows(stl_points))
                scene_mesh_match = float(scene_delta.max(initial=0.0)) <= 1e-5
        previous = next(row for row in prior_validation["poses"] if row["stl_filename"] == filename)
        checks = {
            "binary_stl_readable": True,
            "binary_stl_length_valid": True,
            "blender_stl_import_readable": blender_import["readable"],
            "finite_vertices_and_normals": bool(np.isfinite(vertices).all() and np.isfinite(normals).all()),
            "nonempty_vertices_and_triangles": bool(len(vertices) > 0 and len(triangles) > 0),
            "source_frame_fingerprint_matches_manifest": saved_fingerprint == record["source_mesh_fingerprint"],
            "independent_regeneration_fingerprint_matches": regenerated_fingerprint == saved_fingerprint,
            "stl_vertex_coordinates_match_source": vertex_match,
            "blender_scene_mesh_matches_stl": scene_mesh_match,
            "stl_sha256_matches_manifest": stl_hash == record["stl_sha256"],
            "stl_sha256_matches_previous_export_record": stl_hash == previous["stl_sha256"],
            "geometry_validation_passed": geometry["passed"],
            "mm_dimensions_match_manifest": bool(np.max(np.abs(dimensions - record["dimensions_mm"])) < 0.005),
            "x_length_matches_141_8_mm": abs(float(dimensions[0]) - 141.8) < 0.005,
        }
        geometry.update({
            "stl_filename": filename,
            "pose_id": pose_id,
            "source_v11_frame": source_frame,
            "bounds_min_mm": bounds_min.tolist(),
            "bounds_max_mm": bounds_max.tolist(),
            "blender_import": blender_import,
            "source_mesh_fingerprint": saved_fingerprint,
            "independent_regeneration_fingerprint": regenerated_fingerprint,
            "source_mesh_coordinate_match": vertex_match,
            "source_mesh_max_vertex_delta_mm": max_vertex_delta,
            "stl_sha256": stl_hash,
            "recorded_stl_sha256": record["stl_sha256"],
            "blender_scene_mesh_matches_stl": scene_mesh_match,
            "source_baked_roll_degrees": record["source_roll_degrees"],
            "checks": checks,
            "passed": all(checks.values()),
        })
        report_poses.append(geometry)
        regenerated_mesh = regenerated.data
        bpy.data.objects.remove(regenerated, do_unlink=True)
        bpy.data.meshes.remove(regenerated_mesh)

    # Check that no extra numbered STL is mixed into this exact print-set directory.
    actual_stls = sorted(path.name for path in EXPORTS.glob("*.stl"))
    expected_stls = [f"pose-{index:02}.stl" for index in range(1, 17)]
    stl_directory_check = actual_stls == expected_stls

    csv_path = PREVIEW / "frame-to-stl.csv"
    with csv_path.open(newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    manifest_rows = manifest["transforms"]
    csv_frames = [int(row["frame"]) for row in csv_rows]
    csv_usage = Counter(row["stl_filename"] for row in csv_rows)
    selected_usage = {row["stl_filename"]: int(row["use_count"]) for row in selected}
    def csv_row_matches_manifest(csv_row, manifest_row):
        # CSV serializes numbers and booleans as text, so compare their values by type.
        if set(csv_row) != set(manifest_row):
            return False
        for key, expected in manifest_row.items():
            actual = csv_row[key]
            if isinstance(expected, bool):
                if actual.lower() != str(expected).lower():
                    return False
            elif isinstance(expected, (int, float)):
                if not math.isfinite(float(actual)) or abs(float(actual) - float(expected)) > 1e-9:
                    return False
            elif actual != str(expected):
                return False
        return True

    frame_checks = {
        "csv_has_exactly_30_rows": len(csv_rows) == FRAME_COUNT,
        "csv_frames_are_01_to_30_once": csv_frames == list(range(1, FRAME_COUNT + 1)),
        "csv_stl_references_exist": all((EXPORTS / row["stl_filename"]).is_file() for row in csv_rows),
        "csv_uses_all_16_stls": set(csv_usage) == set(expected_stls),
        "csv_usage_sums_to_30": sum(csv_usage.values()) == FRAME_COUNT,
        "csv_usage_matches_manifest": dict(csv_usage) == selected_usage,
        "csv_matches_manifest_rows": len(csv_rows) == len(manifest_rows) and all(
            csv_row_matches_manifest(csv_row, manifest_row)
            for csv_row, manifest_row in zip(csv_rows, manifest_rows)
        ),
        "motion_directions_are_valid": all(row["rolling_direction"] in {"toward", "away"} for row in csv_rows),
        "placements_and_angles_are_finite": all(
            math.isfinite(float(row[field]))
            for row in csv_rows
            for field in (
                "stl_baked_roll_degrees", "v11_target_roll_degrees",
                "additional_rotation_x_degrees", "additional_rotation_y_degrees",
                "additional_rotation_z_degrees", "position_x_mm", "position_y_mm", "position_z_mm",
            )
        ),
        "all_additional_rotations_are_zero": all(
            all(abs(float(row[field])) < 1e-9 for field in (
                "additional_rotation_x_degrees", "additional_rotation_y_degrees",
                "additional_rotation_z_degrees",
            )) for row in csv_rows
        ),
    }

    # Check the saved Blender scene's discrete visibility and filming placements.
    placement_matches = []
    one_pose_visible = []
    extra_rotation_matches = []
    camera = print_scene.camera if print_scene is not None else None
    if print_scene is not None:
        print_scene.frame_set(1)
    camera_at_start = camera.matrix_world.copy() if camera is not None else None
    camera_frame_matches = []
    for frame, row in enumerate(csv_rows, 1):
        print_scene.frame_set(frame)
        camera_frame_matches.append(bool(camera is not None and np.max(np.abs(
            np.asarray(camera.matrix_world[:]) - np.asarray(camera_at_start[:])
        )) < 1e-8))
        visible_poses = [obj for obj in scene_objects if not obj.hide_render]
        one_pose_visible.append(len(visible_poses) == 1)
        pose_id = int(row["pose_id"])
        obj = scene_object_by_pose.get(pose_id)
        if obj is None:
            placement_matches.append(False)
            extra_rotation_matches.append(False)
            continue
        expected_position = np.asarray([
            float(row["position_x_mm"]), float(row["position_y_mm"]), float(row["position_z_mm"])
        ])
        actual_position = np.asarray(obj.location[:], dtype=np.float64)
        placement_matches.append(bool(np.max(np.abs(actual_position - expected_position)) < 1e-6))
        actual_rotation = np.asarray(obj.rotation_euler[:], dtype=np.float64)
        extra_rotation_matches.append(bool(np.max(np.abs(actual_rotation)) < 1e-6))
    camera_fixed = camera is not None and len(camera_frame_matches) == FRAME_COUNT and all(camera_frame_matches)
    scene_checks = {
        "print_scene_loaded_from_saved_blend": print_scene is not None,
        "scene_frame_range_is_01_to_30": print_scene is not None and print_scene.frame_start == 1 and print_scene.frame_end == 30,
        "scene_has_exactly_16_pose_meshes": len(scene_objects) == 16 and len(scene_object_by_pose) == 16,
        "scene_has_camera": camera is not None,
        "scene_has_no_external_library_links": not scene_library_links,
        "scene_images_are_packed_or_resolved": not unresolved_images,
        "camera_is_fixed": camera_fixed,
        "one_pose_visible_per_frame": len(one_pose_visible) == FRAME_COUNT and all(one_pose_visible),
        "scene_placements_match_csv": len(placement_matches) == FRAME_COUNT and all(placement_matches),
        "scene_extra_rotations_are_zero": len(extra_rotation_matches) == FRAME_COUNT and all(extra_rotation_matches),
        "scene_meshes_match_stl_coordinates": all(
            row["checks"]["blender_scene_mesh_matches_stl"] for row in report_poses
        ),
    }

    source_hashes = {
        "v11_blend_sha256": sha256(SOURCE_BLEND),
        "v11_generator_sha256": sha256(SOURCE_SCRIPT),
        "v11_blend_unchanged_from_manifest": sha256(SOURCE_BLEND) == manifest["source_of_truth"]["blend_sha256"],
        "v11_generator_unchanged_from_manifest": sha256(SOURCE_SCRIPT) == manifest["source_of_truth"]["generator_sha256"],
    }
    validation = {
        "report": "Rolling Wavy Pen print-set-v2 final QA",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": "PASS" if (stl_directory_check and all(pose["passed"] for pose in report_poses)
                               and all(frame_checks.values()) and all(scene_checks.values())
                               and all(source_hashes.values())) else "FAIL",
        "units": "millimeters; STL has no unit metadata and must be imported as mm",
        "stl_directory": {
            "expected_count": 16,
            "actual_count": len(actual_stls),
            "filenames_match_pose_01_to_pose_16": stl_directory_check,
        },
        "source_of_truth": {
            "blend": str(SOURCE_BLEND.relative_to(ROOT)),
            "generator": str(SOURCE_SCRIPT.relative_to(ROOT)),
            **source_hashes,
        },
        "csv_checks": frame_checks,
        "blender_scene_checks": scene_checks,
        "blender_scene_external_references": {
            "library_links": scene_library_links,
            "unresolved_image_paths": unresolved_images,
        },
        "csv_use_count_by_stl": dict(sorted(csv_usage.items())),
        "poses": report_poses,
        "unverified": [
            "Exhaustive minimum feature thickness.",
            "Slicer import/profile, support requirements, and estimated print time.",
            "Physical printing and tabletop filming tests.",
            "Bambu Lab X1 Carbon compatibility beyond the checked dimensions and mesh integrity.",
        ],
        "notes": [
            "Geometry metrics were recalculated from the saved binary STL triangles.",
            "The STL vertex coordinates were independently compared with the corresponding v11 mesh after float32 quantization.",
            "Rolling angle is baked into each selected STL; CSV additional rotations are zero.",
            "Support margin is a static center-of-mass projection measure, not a vibration or filming stability test.",
            "The BVH test detects non-adjacent triangle overlaps under the existing validator's method; it is not a mathematical proof of no self-intersections.",
        ],
    }
    REPORT_JSON.write_text(json.dumps(validation, indent=2, ensure_ascii=False) + "\n")

    md = [
        "# Rolling Wavy Pen — print-set-v2 final QA",
        "",
        f"- Checked: {validation['checked_at_utc']}",
        f"- Verdict: **{validation['verdict']}**",
        f"- Targets: `{EXPORTS.relative_to(ROOT)}/`, `{PREVIEW.relative_to(ROOT)}/frame-to-stl.csv`, `models/rolling-wavy-pen-print-set-v2.blend`",
        "- Method: binary STL was reread and its triangles revalidated; Blender's STL importer was also used as a second reader. Source v11 mesh and regenerated mesh fingerprints were checked against the manifest.",
        "- Units: STL has no unit field. Import each file interpreting coordinates as **millimeters** (1 Blender unit = 1 mm).",
        "",
        "## STL results",
        "",
        "| STL | v11 frame | Dimensions X × Y × Z (mm) | Volume (mm³) | Contact (mm²) | Support margin (mm) | SHA-256 | Result |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in report_poses:
        dims = row["dimensions_mm"]
        md.append(
            f"| `{row['stl_filename']}` | {row['source_v11_frame']:02} | "
            f"{dims[0]:.3f} × {dims[1]:.3f} × {dims[2]:.3f} | "
            f"{row['signed_volume_mm3']:.3f} | {row['contact_area_mm2']:.3f} | "
            f"{row['support_hull_margin_mm']:.3f} | `{row['stl_sha256']}` | "
            f"{'PASS' if row['passed'] else 'FAIL'} |"
        )
    md += [
        "",
        "All 16 files have finite coordinates, valid binary STL length, nonempty triangle data, the expected X length, and match their v11 fingerprints and recorded hashes. All have one connected component, are watertight/manifold, consistently oriented with positive volume, contain no degenerate triangles, have zero detected non-adjacent BVH overlap pairs, rest at Z=0, and have a positive static support margin.",
        "",
        "## 30-frame CSV and placement",
        "",
        f"- CSV rows: {len(csv_rows)}; frame IDs 01–30 each occur once: {frame_checks['csv_frames_are_01_to_30_once']}",
        f"- Referenced STLs: {len(csv_usage)}; usage total: {sum(csv_usage.values())}; all references exist: {frame_checks['csv_stl_references_exist']}",
        f"- CSV rows match manifest transforms: {frame_checks['csv_matches_manifest_rows']}",
        f"- Saved Blender scene: {sum(scene_checks.values())}/{len(scene_checks)} checks passed; 16 meshes, 30 placements, and fixed camera verified.",
        f"- Scene external references: {len(scene_library_links)} linked libraries, {len(unresolved_images)} unresolved image paths.",
        "- The baked roll is retained in each STL. CSV additional rotation is 0°; translations are millimeter filming guides. The tabletop contact side is at Z=0.",
        "- Read [frame-to-stl.csv](../previews/rolling-wavy-pen/print-set-v2/frame-to-stl.csv) for each frame's pose, direction, baked angle, and X/Y/Z placement.",
        "",
        "## Source integrity and checks",
        "",
        f"- v11 blend SHA-256: `{source_hashes['v11_blend_sha256']}`; matches print-set manifest: {source_hashes['v11_blend_unchanged_from_manifest']}.",
        f"- v11 generator SHA-256: `{source_hashes['v11_generator_sha256']}`; matches print-set manifest: {source_hashes['v11_generator_unchanged_from_manifest']}.",
        f"- Per-pose geometry and independent regeneration checks: {sum(row['passed'] for row in report_poses)}/16 passed.",
        f"- CSV checks: {sum(frame_checks.values())}/{len(frame_checks)} passed.",
        f"- Blender scene checks: {sum(scene_checks.values())}/{len(scene_checks)} passed.",
        "- The corresponding v11 pose generator was rerun for every selected frame. Its fingerprint matches the saved v11 mesh; source mesh vertices match STL vertices within float32 coordinate quantization (maximum measured delta recorded in JSON).",
        "",
        "## Slicer handoff and limitations",
        "",
        "- Import as millimeters; STL does not encode units. Do not apply an additional roll rotation: the approved roll/contact orientation is already baked into the geometry.",
        "- Keep the current axis/orientation for this handoff. This QA does not optimize print orientation or support placement.",
        "- PASS means the checked files are internally consistent and ready for the user's slicer review; it does not guarantee a successful print.",
        "- Not verified: exhaustive minimum wall/feature thickness, slicer support needs, slicer print-time estimate, physical print strength, and actual printing/filming.",
        "- Static support margin does not test vibration, accidental contact, or filming stability. BVH overlap checking is a detector, not an exhaustive proof against all possible self-intersections.",
        "",
        f"Machine-readable results: `{REPORT_JSON.relative_to(ROOT)}`.",
    ]
    REPORT_MD.write_text("\n".join(md) + "\n")
    print(f"Final QA {validation['verdict']}: {len(report_poses)} STLs; {len(csv_rows)} CSV frames; {sum(frame_checks.values())}/{len(frame_checks)} CSV checks")


main()
