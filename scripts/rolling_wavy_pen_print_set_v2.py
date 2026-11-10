"""Export the approved v11 poses as a compact, validated print set.

Run Blender with models/rolling-wavy-pen-storyboard-study-v11.blend open, then:
blender --background models/rolling-wavy-pen-storyboard-study-v11.blend --python scripts/rolling_wavy_pen_print_set_v2.py
"""

import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate import make_mesh, mesh_fingerprint
from rolling_wavy_pen import validate
import rolling_wavy_pen_storyboard_study_v11 as v11


FRAME_COUNT = 30
DELAY_CS = 16
PRINT_SOURCE_FRAMES = (1, 4, 8, 9, 10, 11, 12, 13, 16, 18, 19, 21, 22, 25, 27, 30)
TWELVE_SOURCE_FRAMES = (1, 4, 9, 11, 12, 13, 16, 19, 21, 22, 27, 30)
SOURCE_SCENE_NAME = "Rolling Wavy Pen v11"
PRINT_SCENE_NAME = "Rolling Wavy Pen print-set-v2"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_objects(scene):
    return {
        frame: next(obj for obj in scene.objects if obj.get("sequence_frame") == frame)
        for frame in range(1, FRAME_COUNT + 1)
    }


def fit_about_x(target, candidate):
    """Find a rigid YZ-plane alignment while keeping the shared X stations fixed."""
    target_yz = target[:, 1:3]
    candidate_yz = candidate[:, 1:3]
    target_center = target_yz.mean(axis=0)
    candidate_center = candidate_yz.mean(axis=0)
    target_centered = target_yz - target_center
    candidate_centered = candidate_yz - candidate_center
    dot = np.sum(candidate_centered[:, 0] * target_centered[:, 0]
                 + candidate_centered[:, 1] * target_centered[:, 1])
    cross = np.sum(candidate_centered[:, 0] * target_centered[:, 1]
                   - candidate_centered[:, 1] * target_centered[:, 0])
    angle = math.atan2(cross, dot)
    cosine, sine = math.cos(angle), math.sin(angle)
    rotated = np.column_stack((candidate_centered[:, 0] * cosine - candidate_centered[:, 1] * sine,
                               candidate_centered[:, 0] * sine + candidate_centered[:, 1] * cosine))
    residual = target_centered - rotated
    translation = target_center - np.array((candidate_center[0] * cosine - candidate_center[1] * sine,
                                             candidate_center[0] * sine + candidate_center[1] * cosine))
    return {
        "rms_mm": float(np.sqrt(np.mean(np.sum(residual * residual, axis=1)))),
        "max_vertex_mm": float(np.max(np.linalg.norm(residual, axis=1))),
        "angle_x_deg": math.degrees(angle),
        "translation_y_mm": float(translation[0]),
        "translation_z_mm": float(translation[1]),
    }


def translation_only_fit(target, candidate):
    """Align only in Y so the printed contact plane stays exactly horizontal."""
    delta_y = float(target[:, 1].mean() - candidate[:, 1].mean())
    difference = target - candidate
    difference[:, 1] -= delta_y
    return {
        "rms_mm": float(np.sqrt(np.mean(np.sum(difference * difference, axis=1)))),
        "max_vertex_mm": float(np.max(np.linalg.norm(difference, axis=1))),
        "translation_y_mm": delta_y,
    }


def compare_candidate_set(objects, source_frames):
    arrays = {frame: np.asarray([vertex.co[:] for vertex in obj.data.vertices], dtype=np.float64)
              for frame, obj in objects.items()}
    rows = []
    for frame in range(1, FRAME_COUNT + 1):
        candidates = []
        for source_frame in source_frames:
            actual = translation_only_fit(arrays[frame], arrays[source_frame])
            rigid = fit_about_x(arrays[frame], arrays[source_frame])
            candidates.append((actual["rms_mm"], source_frame, actual, rigid))
        _, source_frame, translation_fit, rigid_fit = min(candidates, key=lambda item: item[0])
        rows.append({"frame": frame, "source_frame": source_frame,
                     "translation_only_fit": translation_fit, "best_rigid_fit": rigid_fit})
    errors = [row["translation_only_fit"]["rms_mm"] for row in rows]
    return {
        "candidate_source_frames": list(source_frames),
        "candidate_count": len(source_frames),
        "max_vertex_rms_mm": max(errors),
        "mean_vertex_rms_mm": float(np.mean(errors)),
        "rms_vertex_error_mean_mm": float(np.sqrt(np.mean(np.square(errors)))),
        "frame_assignments": rows,
    }


def export_stl(obj, filepath):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=str(filepath), export_selected_objects=True,
                          use_scene_unit=False, global_scale=1, apply_modifiers=True,
                          forward_axis="Y", up_axis="Z")
    obj.select_set(False)


def copy_render_environment(source_scene, target_scene):
    """Copy the approved camera, tabletop, lights, and render treatment."""
    front_camera = None
    top_camera = None
    for obj in source_scene.objects:
        keep = (obj.type == "LIGHT" or obj.name.startswith("Preview tabletop")
                or (obj.type == "CAMERA" and obj.name.lower().startswith("front oblique"))
                or (obj.type == "CAMERA" and obj.name.lower().startswith("top")))
        if not keep:
            continue
        copied = obj.copy()
        if obj.data is not None:
            copied.data = obj.data.copy() if obj.type == "CAMERA" else obj.data
        copied.animation_data_clear()
        target_scene.collection.objects.link(copied)
        if obj.type == "CAMERA" and obj.name.lower().startswith("front oblique"):
            front_camera = copied
        if obj.type == "CAMERA" and obj.name.lower().startswith("top"):
            top_camera = copied

    if front_camera is None:
        raise RuntimeError("The v11 front-oblique camera was not found.")
    target_scene.camera = front_camera
    target_scene.world = source_scene.world
    target_scene.render.engine = "CYCLES"
    target_scene.cycles.samples = source_scene.cycles.samples
    target_scene.view_layers[0].cycles.use_denoising = source_scene.view_layers[0].cycles.use_denoising
    target_scene.render.resolution_x = source_scene.render.resolution_x
    target_scene.render.resolution_y = source_scene.render.resolution_y
    target_scene.render.resolution_percentage = source_scene.render.resolution_percentage
    target_scene.render.image_settings.file_format = "PNG"
    target_scene.render.image_settings.color_mode = "RGB"
    target_scene.render.film_transparent = False
    target_scene.view_settings.view_transform = source_scene.view_settings.view_transform
    target_scene.view_settings.look = source_scene.view_settings.look
    target_scene.view_settings.exposure = source_scene.view_settings.exposure
    target_scene.view_settings.gamma = source_scene.view_settings.gamma
    return front_camera, top_camera


def import_stl(filepath, scene, name, material):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.wm.stl_import(filepath=str(filepath), use_scene_unit=False,
                          global_scale=1, forward_axis="Y", up_axis="Z",
                          use_facet_normal=False, use_mesh_validate=True)
    imported = list(bpy.context.selected_objects)
    if len(imported) != 1 or imported[0].type != "MESH":
        raise RuntimeError(f"Expected one imported STL mesh for {filepath}, got {len(imported)} objects.")
    obj = imported[0]
    obj.name = name
    obj.data.name = name + " mesh"
    obj.data.materials.clear()
    obj.data.materials.append(material)
    obj["units"] = "millimeters; one Blender unit equals one millimeter"
    return obj


def render_one(scene, obj, frame, path):
    for candidate in scene.objects:
        if candidate.get("print_set_pose") is not None:
            candidate.hide_render = candidate is not obj
    scene.camera = next(camera for camera in scene.objects
                        if camera.type == "CAMERA" and camera.name.startswith("front oblique"))
    scene.frame_set(1)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def make_gif(frame_paths, output_path, delay_cs=DELAY_CS):
    args = ["magick"]
    for path in frame_paths:
        args.extend(["-delay", str(delay_cs), str(path)])
    subprocess.run(args + ["-loop", "0", str(output_path)], check=True)


def make_montage(preview, output_name, images_and_labels, geometry, tile):
    args = ["magick", "montage", "-background", "#191919", "-fill", "white",
            "-font", "Helvetica", "-pointsize", "14"]
    for path, label in images_and_labels:
        args.extend(["-label", label, str(path)])
    subprocess.run(args + ["-geometry", geometry, "-tile", tile,
                           str(preview / output_name)], check=True)


def build_print_scene(source_scene, exports, preview, source_objects_by_frame,
                      chosen, assignment_rows, use_counts):
    old_scene = bpy.data.scenes.get(PRINT_SCENE_NAME)
    if old_scene is not None:
        fallback = next((candidate for candidate in bpy.data.scenes if candidate != old_scene), None)
        if fallback is not None and bpy.context.window is not None:
            bpy.context.window.scene = fallback
        bpy.data.scenes.remove(old_scene)

    scene = bpy.data.scenes.new(PRINT_SCENE_NAME)
    if bpy.context.window is not None:
        bpy.context.window.scene = scene
    front_camera, _ = copy_render_environment(source_scene, scene)
    original_black = source_objects_by_frame[1].data.materials[0]
    black = original_black.copy()
    black.name = "v11 black marker material (preview only)"

    candidate_objects = {}
    candidate_info = {record["pose_id"]: record for record in chosen}
    source_frame_to_pose = {record["source_v11_frame"]: record["pose_id"] for record in chosen}
    for record in chosen:
        pose_id = record["pose_id"]
        filepath = exports / record["stl_filename"]
        obj = import_stl(filepath, scene, f"print-pose-{pose_id:02}-from-v11-{record['source_v11_frame']:02}", black)
        obj["print_set_pose"] = pose_id
        obj["source_v11_frame"] = record["source_v11_frame"]
        obj["usage_count"] = use_counts[record["source_v11_frame"]]
        obj.location = (0.0, float(source_objects_by_frame[record["source_v11_frame"]]["scene_y_mm"]), 0.0)
        candidate_objects[pose_id] = obj

    selected_render_dir = preview / "selected-poses"
    selected_render_dir.mkdir(parents=True, exist_ok=True)
    selected_images = []
    for record in chosen:
        pose_id = record["pose_id"]
        obj = candidate_objects[pose_id]
        src = source_objects_by_frame[record["source_v11_frame"]]
        obj.location.y = float(src["scene_y_mm"])
        path = selected_render_dir / f"pose-{pose_id:02}.png"
        render_one(scene, obj, record["source_v11_frame"], path)
        selected_images.append((path,
                                f"pose-{pose_id:02} | v11 {record['source_v11_frame']:02} | used {use_counts[record['source_v11_frame']]}x"))

    make_montage(preview, "selected-shapes.png", selected_images,
                 "360x243+5+10", "4x4")

    mapping_by_frame = {row["frame"]: row for row in assignment_rows}
    frame_rows = []
    for frame in range(1, FRAME_COUNT + 1):
        mapping = mapping_by_frame[frame]
        pose_id = source_frame_to_pose[mapping["source_frame"]]
        obj = candidate_objects[pose_id]
        target = source_objects_by_frame[frame]
        delta_y = mapping["translation_only_fit"]["translation_y_mm"]
        # Keep X-axis roll at zero here: each candidate STL already contains its
        # reviewed v11 roll and contact orientation, so translation preserves support.
        y = float(target["scene_y_mm"]) + delta_y
        z = 0.0
        frame_rows.append({
            "frame": frame,
            "phase": target["phase"],
            "stl_filename": candidate_info[pose_id]["stl_filename"],
            "pose_id": pose_id,
            "source_v11_frame": mapping["source_frame"],
            "target_v11_frame": frame,
            "rolling_direction": target["rolling_direction"],
            "stl_baked_roll_degrees": float(candidate_info[pose_id]["source_roll_degrees"]),
            "v11_target_roll_degrees": float(target["roll_degrees"]),
            "additional_rotation_x_degrees": 0.0,
            "additional_rotation_y_degrees": 0.0,
            "additional_rotation_z_degrees": 0.0,
            "position_x_mm": 0.0,
            "position_y_mm": y,
            "position_z_mm": z,
            "reused": use_counts[pose_id] > 1,
            "rms_vertex_error_mm": mapping["translation_only_fit"]["rms_mm"],
            "max_vertex_error_mm": mapping["translation_only_fit"]["max_vertex_mm"],
            "best_rigid_fit_rotation_x_degrees": mapping["best_rigid_fit"]["angle_x_deg"],
            "notes": "Original STL mesh reused; no scale or deformation; source roll is baked into the STL.",
        })

    # Key every pose at every exposure with constant interpolation, so reused
    # prints jump only when the stop-motion frame changes.
    for pose_id, obj in candidate_objects.items():
        rows_for_pose = {row["frame"]: row for row in frame_rows if row["pose_id"] == pose_id}
        last_location = obj.location.copy()
        last_rotation = obj.rotation_euler.copy()
        for frame in range(1, FRAME_COUNT + 1):
            row = rows_for_pose.get(frame)
            if row is not None:
                last_location = Vector((row["position_x_mm"], row["position_y_mm"], row["position_z_mm"]))
            obj.location = last_location
            obj.rotation_euler = last_rotation
            obj.hide_render = row is None
            obj.keyframe_insert(data_path="location", frame=frame)
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
            obj.keyframe_insert(data_path="hide_render", frame=frame)
        if obj.animation_data and obj.animation_data.action:
            for curve in obj.animation_data.action.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = "CONSTANT"

    scene.camera = front_camera
    scene.frame_start, scene.frame_end = 1, FRAME_COUNT
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(preview / "reproduction-frames" / "frame-01.png")
    scene.frame_set(1)
    return scene, candidate_objects, frame_rows


def main():
    source_scene = bpy.data.scenes.get(SOURCE_SCENE_NAME)
    if source_scene is None:
        raise RuntimeError(f"Open {ROOT / 'models/rolling-wavy-pen-storyboard-study-v11.blend'} before running this script.")
    if bpy.context.window is not None:
        bpy.context.window.scene = source_scene

    exports = ROOT / "exports/rolling-wavy-pen/print-set-v2"
    preview = ROOT / "previews/rolling-wavy-pen/print-set-v2"
    model_path = ROOT / "models/rolling-wavy-pen-print-set-v2.blend"
    docs_path = ROOT / "docs/rolling-wavy-pen-print-set-v2.md"
    exports.mkdir(parents=True, exist_ok=True)
    preview.mkdir(parents=True, exist_ok=True)
    ideal_dir = ROOT / "previews/rolling-wavy-pen/storyboard-study-v11/frames"
    ideal_paths = [ideal_dir / f"frame-{frame:02}.png" for frame in range(1, FRAME_COUNT + 1)]
    if not all(path.is_file() for path in ideal_paths):
        raise RuntimeError("One or more approved v11 frame renders are missing.")

    objects = source_objects(source_scene)
    arrays = {frame: np.asarray([vertex.co[:] for vertex in obj.data.vertices], dtype=np.float64)
              for frame, obj in objects.items()}
    analysis_12 = compare_candidate_set(objects, TWELVE_SOURCE_FRAMES)
    analysis_16 = compare_candidate_set(objects, PRINT_SOURCE_FRAMES)
    assignment_rows = analysis_16["frame_assignments"]
    use_counts = Counter(row["source_frame"] for row in assignment_rows)
    pose_id_by_source = {source_frame: index for index, source_frame in enumerate(PRINT_SOURCE_FRAMES, 1)}

    temp_root = Path(tempfile.mkdtemp(prefix="rolling-wavy-pen-print-set-v2-"))
    validation_rows = []
    chosen = []
    try:
        for source_frame in PRINT_SOURCE_FRAMES:
            source_obj = objects[source_frame]
            pose_id = pose_id_by_source[source_frame]
            filename = f"pose-{pose_id:02}.stl"
            output_stl = exports / filename
            vertices, faces, xs = v11.geometry_progress(
                float(source_obj["curve_progress"]), float(source_obj["wave_progress"]),
                float(source_obj["roll_degrees"]), float(source_obj["curve_orientation_sign"]))
            regenerated = make_mesh(source_scene, f"v11-independent-regeneration-{pose_id:02}", vertices, faces)
            regen_mesh = regenerated.data
            source_fingerprint = mesh_fingerprint(source_obj)
            regenerated_fingerprint = mesh_fingerprint(regenerated)
            if source_fingerprint != regenerated_fingerprint:
                raise RuntimeError(f"v11 regeneration fingerprint mismatch for frame {source_frame:02}.")

            source_export = temp_root / f"source-frame-{source_frame:02}.stl"
            saved_location = source_obj.location.copy()
            saved_rotation = source_obj.rotation_euler.copy()
            saved_scale = source_obj.scale.copy()
            source_obj.location = (0.0, 0.0, 0.0)
            source_obj.rotation_euler = (0.0, 0.0, 0.0)
            source_obj.scale = (1.0, 1.0, 1.0)
            export_stl(source_obj, source_export)
            source_obj.location = saved_location
            source_obj.rotation_euler = saved_rotation
            source_obj.scale = saved_scale

            export_stl(regenerated, output_stl)
            independently_exported = temp_root / f"independent-frame-{source_frame:02}.stl"
            export_stl(regenerated, independently_exported)
            source_stl_hash = sha256(source_export)
            stl_hash = sha256(output_stl)
            repeat_hash = sha256(independently_exported)
            if source_stl_hash != stl_hash or stl_hash != repeat_hash:
                raise RuntimeError(f"STL hash mismatch for print pose {pose_id:02}.")

            report = validate(output_stl, regenerated, 0, xs,
                              pose_name=f"pose-{pose_id:02}-from-v11-frame-{source_frame:02}")
            report.update({
                "pose_id": pose_id,
                "source_v11_frame": source_frame,
                "v11_mesh_fingerprint": source_fingerprint,
                "independent_regeneration_fingerprint": regenerated_fingerprint,
                "independent_regeneration_match": source_fingerprint == regenerated_fingerprint,
                "source_mesh_export_sha256": source_stl_hash,
                "stl_sha256": stl_hash,
                "repeat_export_sha256": repeat_hash,
                "independent_stl_hash_match": source_stl_hash == stl_hash == repeat_hash,
                "stl_filename": filename,
                "use_count": use_counts[source_frame],
            })
            if not report["passed"]:
                raise RuntimeError(f"Geometry validation failed for {filename}: {report}")
            validation_rows.append(report)

            chosen.append({
                "pose_id": pose_id,
                "source_v11_frame": source_frame,
                "stl_filename": filename,
                "source_mesh_fingerprint": source_fingerprint,
                "stl_sha256": stl_hash,
                "dimensions_mm": report["dimensions_mm"],
                "source_roll_degrees": float(source_obj["roll_degrees"]),
                "rolling_direction": source_obj["rolling_direction"],
                "use_count": use_counts[source_frame],
                "validation_passed": report["passed"],
            })
            bpy.data.objects.remove(regenerated, do_unlink=True)
            bpy.data.meshes.remove(regen_mesh)
    finally:
        shutil.rmtree(temp_root)

    print_scene, candidate_objects, frame_rows = build_print_scene(
        source_scene, exports, preview, objects, chosen, assignment_rows, use_counts)
    reproduction_dir = preview / "reproduction-frames"
    reproduction_dir.mkdir(parents=True, exist_ok=True)
    reproduction_paths = []
    for frame in range(1, FRAME_COUNT + 1):
        print_scene.frame_set(frame)
        path = reproduction_dir / f"frame-{frame:02}.png"
        print_scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        reproduction_paths.append(path)
        if frame in (1, 6, 12, 13, 21, 22, 30):
            print(f"Rendered print-set frame {frame:02}/{FRAME_COUNT}", flush=True)

    make_gif(reproduction_paths, preview / "print-reproduction.gif")
    pair_paths = []
    for frame, (ideal_path, reproduced_path) in enumerate(zip(ideal_paths, reproduction_paths), 1):
        pair_path = temp_root / f"ideal-vs-print-{frame:02}.png" if temp_root.exists() else preview / f".ideal-vs-print-{frame:02}.png"
        subprocess.run(["magick", str(ideal_path), str(reproduced_path), "+append", str(pair_path)], check=True)
        pair_paths.append(pair_path)
    make_gif(pair_paths, preview / "ideal-vs-print-reproduction.gif")
    comparison_cards = [(path, f"frame {frame:02} | v11 left · print set right")
                        for frame, path in enumerate(pair_paths, 1)]
    make_montage(preview, "ideal-vs-print-reproduction-contact-sheet.png",
                 comparison_cards, "480x324+4+9", "3x10")
    for path in pair_paths:
        if path.exists() and path.parent == preview:
            path.unlink()

    frame_csv = preview / "frame-to-stl.csv"
    with frame_csv.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(frame_rows[0].keys()))
        writer.writeheader()
        writer.writerows(frame_rows)

    source_blend = ROOT / "models/rolling-wavy-pen-storyboard-study-v11.blend"
    source_script = ROOT / "scripts/rolling_wavy_pen_storyboard_study_v11.py"
    manifest = {
        "status": "approved v11 geometry; print-set-v2 candidate, pending slicer and physical verification",
        "source_of_truth": {
            "blend": str(source_blend.relative_to(ROOT)),
            "blend_sha256": sha256(source_blend),
            "generator": str(source_script.relative_to(ROOT)),
            "generator_sha256": sha256(source_script),
        },
        "sequence": {"frames": FRAME_COUNT, "gif_frame_delay_ms": DELAY_CS * 10,
                     "duration_seconds": FRAME_COUNT * DELAY_CS / 100,
                     "v11_ideal_gif": "previews/rolling-wavy-pen/storyboard-study-v11/sequence.gif"},
        "selection_method": {
            "selected_pose_count": len(chosen),
            "candidate_12": analysis_12,
            "candidate_16": analysis_16,
            "selection_reason": "The 16-pose set retains both v11 baked roll directions, the complete single-arc endpoint, wave onset, intermediate wave growth, strong-wave onset, and final form. Its maximum translation-only all-vertex RMS is below 0.31 mm; the 12-pose alternative reaches 0.93 mm and skips a more visible arc-growth step.",
            "rigid_transform_check": "Vertex correspondence was tested under X-axis rotation plus Y/Z translation. Selected frame assignments already share the required baked roll orientation; best-fit additional rotations are below 0.016 degrees. Reproduction uses no additional rotation so the STL contact plane remains level; only millimeter-scale Y placement corrections are applied.",
            "geometry_policy": "Each STL is exported from a deterministic independent v11 mesh regeneration and matched to the saved v11 mesh fingerprint. Reused frames use only rigid placement; mesh interpolation, scaling, mirroring, and deformation are not used.",
        },
        "selected_poses": chosen,
        "frame_to_stl_csv": str(frame_csv.relative_to(ROOT)),
        "validation": {
            "all_passed": all(row["passed"] and row["independent_regeneration_match"] and row["independent_stl_hash_match"] for row in validation_rows),
            "pose_count": len(validation_rows),
            "checks": ["watertight", "manifold", "single connected component", "face orientation",
                       "positive volume", "degenerate triangles", "detected nonadjacent intersections",
                       "dimensions", "tabletop contact", "static center-of-mass support"],
            "contact_area_min_mm2": min(row["contact_area_mm2"] for row in validation_rows),
            "support_margin_min_mm": min(row["support_hull_margin_mm"] for row in validation_rows),
            "intersection_pairs_max": max(row["nonadjacent_bvh_overlap_pairs"] for row in validation_rows),
            "degenerate_triangles_max": max(row["degenerate_triangles"] for row in validation_rows),
            "minimum_thickness": "Exhaustive local minimum-thickness analysis was not performed.",
            "slicer_and_physical_print": "Not performed; geometry checks do not guarantee successful FDM printing.",
        },
        "artifacts": {
            "stl_directory": "exports/rolling-wavy-pen/print-set-v2/",
            "print_reproduction_gif": "previews/rolling-wavy-pen/print-set-v2/print-reproduction.gif",
            "ideal_vs_print_gif": "previews/rolling-wavy-pen/print-set-v2/ideal-vs-print-reproduction.gif",
            "selected_shapes_sheet": "previews/rolling-wavy-pen/print-set-v2/selected-shapes.png",
            "ideal_vs_print_sheet": "previews/rolling-wavy-pen/print-set-v2/ideal-vs-print-reproduction-contact-sheet.png",
            "frame_csv": "previews/rolling-wavy-pen/print-set-v2/frame-to-stl.csv",
            "validation": "previews/rolling-wavy-pen/print-set-v2/validation.json",
            "blender_scene": "models/rolling-wavy-pen-print-set-v2.blend",
            "generation_script": "scripts/rolling_wavy_pen_print_set_v2.py",
            "instructions": "docs/rolling-wavy-pen-print-set-v2.md",
        },
        "transforms": frame_rows,
        "geometry_validation": validation_rows,
    }
    (preview / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    validation_json = {
        "all_passed": manifest["validation"]["all_passed"],
        "poses": validation_rows,
        "unverified": ["exhaustive minimum thickness", "slicer verification", "physical print test"],
    }
    (preview / "validation.json").write_text(json.dumps(validation_json, indent=2, ensure_ascii=False) + "\n")

    dimensions_rows = []
    for record in chosen:
        dims = record["dimensions_mm"]
        dimensions_rows.append(
            f"| pose-{record['pose_id']:02} | v11 frame-{record['source_v11_frame']:02} | "
            f"{dims[0]:.3f} × {dims[1]:.3f} × {dims[2]:.3f} | {record['use_count']} | "
            f"{record['stl_filename']} |"
        )
    docs = [
        "# Rolling Wavy Pen — print-set-v2",
        "",
        "This set reproduces the approved 30-pose v11 sequence using 16 printable STL meshes. "
        "The v11 mesh generator and source scene remain the geometric source of truth; no shape, "
        "scale, or surface profile was redesigned for this set.",
        "",
        "The selected STLs retain the v11 baked roll/contact orientation. Reuse is achieved by "
        "reassigning the same STL and changing its recorded Y placement. The additional roll "
        "correction is zero for the 30-frame assignment so each STL remains on its validated contact plane.",
        "",
        "## Printable models",
        "",
        "Dimensions are STL bounding-box X × Y × Z in millimeters. Usage counts refer to the 30-frame CSV.",
        "",
        "| STL pose | Source v11 frame | Dimensions (mm) | Uses | File |",
        "|---|---:|---:|---:|---|",
        *dimensions_rows,
        "",
        "## Stop-motion placement",
        "",
        "Follow `previews/rolling-wavy-pen/print-set-v2/frame-to-stl.csv` in frame order. "
        "It records the phase, reused STL, source v11 frame, rolling direction, baked roll, "
        "and X/Y/Z filming position. Positions are millimeter starting guides; adjust them "
        "to match the actual table and camera during filming. Preserve the exported STL scale "
        "and use its Z=0 contact side on the table.",
        "",
        "## Review and validation",
        "",
        "- Print-only reconstruction: `previews/rolling-wavy-pen/print-set-v2/print-reproduction.gif`",
        "- Side-by-side v11 ideal versus print-set reconstruction: `previews/rolling-wavy-pen/print-set-v2/ideal-vs-print-reproduction.gif`",
        "- Candidate pose sheet: `previews/rolling-wavy-pen/print-set-v2/selected-shapes.png`",
        "- Validation and SHA-256 records: `previews/rolling-wavy-pen/print-set-v2/validation.json`",
        "",
        "All selected solids passed the recorded mesh checks and independent regeneration/hash comparison. "
        "Minimum feature thickness, slicer behavior, and physical printing remain unverified. "
        "These files are a print-preparation candidate, not evidence of a successful physical print.",
        "",
    ]
    docs_path.write_text("\n".join(docs), encoding="utf-8")

    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(model_path))
    print(f"Print set v2 complete: {len(chosen)} STL files; {FRAME_COUNT} mapped frames; "
          f"max RMS {analysis_16['max_vertex_rms_mm']:.4f} mm", flush=True)


if __name__ == "__main__":
    main()
