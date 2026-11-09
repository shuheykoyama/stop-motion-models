"""Integrate the validated stone study meshes into a discrete 13-pose preview."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stone_to_bread as base

ROOT = base.ROOT
REVISION = "full-sequence-v1"
V4 = "rolling-elongating-study-v4"
PULL = "pulling-study-v1"
RECOIL = "recoil-study-v1"
IDS = [f"r{i:02}" for i in range(1, 8)] + [f"p{i:02}" for i in range(1, 5)] + ["c01", "b01"]
DELIBERATE = [3, 2, 4, 2, 4, 2, 5, 2, 3, 3, 4, 1, 9]
ENERGETIC = [2, 1, 3, 1, 3, 1, 4, 1, 2, 2, 3, 1, 7]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_files():
    # Snapshot every earlier asset and source before writing this separate integration.
    folders = ("models", "exports", "previews", "scripts", "docs")
    paths = [p for folder in folders for p in (ROOT/folder).rglob("*") if p.is_file()]
    paths += [ROOT/"README.md", ROOT/"AGENTS.md"]
    return {str(p.relative_to(ROOT)): digest(p) for p in paths
            if p.name != ".DS_Store" and REVISION not in str(p.relative_to(ROOT))}


def sheet(items, destination, columns=4):
    command = ["magick", "montage", "-background", "#171719", "-fill", "white",
               "-font", "Helvetica", "-pointsize", "16"]
    for name, path in items:
        command += ["-label", name, str(path)]
    command += ["-geometry", "280x210+7+10", "-tile", f"{columns}x", str(destination)]
    subprocess.run(command, check=True, capture_output=True)


def animation(items, exposure, destination):
    # GIF stores centiseconds; rounding cumulative 12-fps time avoids drift.
    boundaries = np.rint(np.cumsum([0]+exposure)*100/12).astype(int)
    delays = np.diff(boundaries).tolist()
    command = ["magick"]
    for (_, path), delay in zip(items, delays):
        command += ["-delay", str(delay), str(path)]
    command += ["-resize", "720x540", "+remap", "-layers", "Optimize", "-loop", "0", str(destination)]
    subprocess.run(command, check=True, capture_output=True)
    actual = [int(v) for v in subprocess.check_output(
        ["magick", "identify", "-format", "%T ", str(destination)], text=True).split()]
    assert actual == delays and len(actual) == len(items)
    assert actual[-2] in (8, 9)
    return dict(path=str(destination.relative_to(ROOT)), exposures=exposure,
                delays_ms=[10*v for v in actual], duration_reference_s=sum(exposure)/12,
                duration_gif_s=sum(actual)/100, sha256=digest(destination))


def projected_bounds(scene, obj):
    bpy.context.view_layer.update()
    points = [world_to_camera_view(scene, scene.camera, obj.matrix_world@vertex.co)
              for vertex in obj.data.vertices]
    return [min(p.x for p in points), max(p.x for p in points),
            min(p.y for p in points), max(p.y for p in points)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    assert bpy.app.version[:2] == (4, 5)
    preview = ROOT/"previews/stone-to-bread"/REVISION
    model = ROOT/"models"/f"stone-to-bread-{REVISION}.blend"
    preview.mkdir(parents=True, exist_ok=True)
    before = protected_files()
    (preview/"baseline-hashes.json").write_text(json.dumps(before, indent=2)+"\n")
    v4 = json.loads((ROOT/"previews/stone-to-bread"/V4/"manifest.json").read_text())
    pull = json.loads((ROOT/"previews/stone-to-bread"/PULL/"manifest.json").read_text())
    recoil = json.loads((ROOT/"previews/stone-to-bread"/RECOIL/"manifest.json").read_text())
    assert v4["local_axes_world"] == pull["local_axes_world"]
    basis = np.column_stack([v4["local_axes_world"][k] for k in ("X", "Y_near", "Z")])
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"models"/f"stone-to-bread-{RECOIL}.blend"),
                             load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    old_reference = scene.objects.get(f"{RECOIL}/reference-old-recoil")
    assert old_reference is not None
    bpy.data.objects.remove(old_reference, do_unlink=True)
    records, objects = [], {}
    source_hashes = {str(ROOT/"models"/f"stone-to-bread-{study}.blend"):
                     digest(ROOT/"models"/f"stone-to-bread-{study}.blend")
                     for study in (V4, PULL, RECOIL)}
    for index, name in enumerate(IDS):
        if name.startswith("r"):
            source, record = V4, next(p for p in v4["poses"] if p["id"] == name)
            expected_place = basis@np.array(record["placement_local_mm"])
            expected_mesh = record["mesh_fingerprint"]
        elif name.startswith("p"):
            source, record = PULL, next(p for p in pull["poses"] if p["id"] == name)
            expected_place = basis@np.array(record["placement_local_mm"])
            expected_mesh = record["mesh_fingerprint"]
        else:
            source, record = RECOIL, recoil[name]
            expected_place = np.array(record["placement_world_mm"])
            expected_mesh = record["mesh_fingerprint"]
        obj = scene.objects[f"{source}/{name}"]
        assert base.mesh_fingerprint(obj) == expected_mesh, name
        assert np.allclose(obj.location[:], expected_place, atol=1e-6), name
        assert np.allclose(obj.scale[:], (1, 1, 1)) and np.allclose(obj.rotation_euler[:], (0, 0, 0)), name
        objects[name] = obj
        item = dict(order=index+1, pose=name, source_study=source,
                    mesh_fingerprint=expected_mesh, placement_world_mm=list(obj.location),
                    placement_local_mm=list(np.array(obj.location)@basis),
                    object_rotation_euler_rad=list(obj.rotation_euler),
                    object_scale=list(obj.scale), printable=name != "b01",
                    exposures=dict(deliberate=DELIBERATE[index], energetic=ENERGETIC[index]),
                    durations_reference_ms=dict(deliberate=round(DELIBERATE[index]*1000/12, 3),
                                                energetic=round(ENERGETIC[index]*1000/12, 3)))
        if name != "b01":
            stl = ROOT/record["stl"]
            assert stl.is_file() and digest(stl) == record["stl_sha256"], name
            # The STL vertex coordinates are the same resting geometry rendered by Blender.
            exported, _, _ = base.read_stl(stl)
            mesh = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float32)
            order_vertices = lambda a: a[np.lexsort(a.T)]
            assert np.array_equal(order_vertices(exported.astype(np.float32)), order_vertices(mesh)), name
            validation = record["validation"]
            assert validation["passed"] and validation["components"] == 1, name
            assert all(validation[k] == 0 for k in ("boundary_edges", "nonmanifold_edges",
                       "nonmanifold_vertices", "inconsistent_winding_edges", "degenerate_faces",
                       "stl_normal_disagreements", "nonadjacent_bvh_intersections")), name
            assert validation["table_contact_area_mm2"] > 0 and validation["support_hull_margin_mm"] > 0, name
            item.update(stl=record["stl"], stl_sha256=record["stl_sha256"],
                        dimensions_mm=validation["local_dimensions_mm"],
                        contact_area_mm2=validation["table_contact_area_mm2"],
                        support_margin_mm=validation["support_hull_margin_mm"],
                        source_geometry_validation_passed=True)
            if name.startswith("r"):
                item["baked_roll_angle_rad"] = record["rotation_baked_local_x_rad"]
            else:
                item["baked_roll_angle_rad"] = v4["poses"][-1]["rotation_baked_local_x_rad"]
        else:
            item.update(stl=None, baked_roll_angle_rad=None, preview_only=True)
        records.append(item)
    assert len(records) == 13 and len({r["stl"] for r in records if r["stl"]}) == 12
    assert not (ROOT/"exports/stone-to-bread/full-sequence-v1").exists()
    # One global orthographic framing change gives p04 extra room at the near edge.
    camera = scene.camera
    original_scale = camera.data.ortho_scale
    assert camera.data.type == "ORTHO"
    camera.data.ortho_scale = 126.0
    front_matrix = camera.matrix_world.copy()
    front_bounds = {name: projected_bounds(scene, obj) for name, obj in objects.items()}
    assert all(min(b[0], b[2], 1-b[1], 1-b[3]) > 0.03 for b in front_bounds.values()), front_bounds
    assert abs(camera.location.x) < 1e-5
    report = dict(status="Integrated study awaiting visual review", revision=REVISION,
                  sequence=IDS, base_fps=12, pose_count=13, printable_pose_count=12,
                  poses=records, source_scene_sha256=source_hashes,
                  source_stl_and_mesh_identical=True,
                  camera=dict(type="ORTHO", elevation_deg=50, original_ortho_scale_mm=original_scale,
                              integrated_ortho_scale_mm=camera.data.ortho_scale,
                              location_world_mm=list(camera.location),
                              rotation_euler_rad=list(camera.rotation_euler),
                              projected_bounds_normalized=front_bounds),
                  geometry_validation="Verified existing per-pose records, STL hashes, mesh fingerprints, and STL/render vertices; no new exhaustive geometry run.",
                  limitations=["Existing BVH tests exclude triangle pairs sharing vertices.",
                               "Existing thickness samples are not a global minimum-thickness proof.",
                               "Slicing, physical printing, friction, handling and real-bread matching are unverified."])
    if not args.validate_only:
        # Every stone retains the source's material-space attribute and uses one unified shader.
        realistic = objects["r07"].data.materials[0]
        neutral = base.material("Integrated geometry neutral", (0.36, 0.36, 0.36))
        original_materials = {name: obj.data.materials[0] for name, obj in objects.items()}
        renderables = [o for o in scene.objects if o.type == "MESH" and o != scene.objects.get("Tabletop (preview only)")]
        images = {}
        for view, style in (("front", "realistic"), ("front", "neutral"),
                            ("top", "realistic"), ("side", "neutral")):
            if view == "top":
                axis, near, up = [Vector(v4["local_axes_world"][k]) for k in ("X", "Y_near", "Z")]
                camera.location = near*8+up*260
                camera.rotation_euler = Matrix((axis, up.cross(axis), up)).transposed().to_euler()
            elif view == "side":
                axis, near, up = [Vector(v4["local_axes_world"][k]) for k in ("X", "Y_near", "Z")]
                camera.location = -axis*260+near*2+up*11
                camera.rotation_euler = Matrix((near, up, -axis)).transposed().to_euler()
            else:
                camera.matrix_world = front_matrix
            for name, obj in objects.items():
                if name != "b01":
                    obj.data.materials[0] = realistic if style == "realistic" else neutral
                else:
                    obj.data.materials[0] = original_materials[name]
            names = IDS if view != "side" else ["r07", "p01", "p02", "p03", "p04", "c01"]
            items = []
            for name in names:
                for obj in renderables:
                    obj.hide_render = obj != objects[name]
                destination = preview/f"{name}-{style}-{view}.png"
                scene.render.filepath = str(destination)
                bpy.ops.render.render(write_still=True)
                images[(name, style, view)] = destination
                items.append((name, destination))
                print("RENDERED", name, style, view, flush=True)
            if view == "front" and style == "realistic":
                sheet(items, preview/"contact-front.png")
            elif view == "top":
                sheet(items, preview/"contact-top.png")
            elif view == "side":
                sheet(items, preview/"contact-side.png", columns=3)
        real = [(name, images[(name, "realistic", "front")]) for name in IDS]
        plain = [(name, images[(name, "neutral", "front")]) for name in IDS]
        report["animations"] = dict(
            realistic_deliberate=animation(real, DELIBERATE, preview/"sequence-realistic-deliberate.gif"),
            realistic_energetic=animation(real, ENERGETIC, preview/"sequence-realistic-energetic.gif"),
            neutral_deliberate=animation(plain, DELIBERATE, preview/"sequence-neutral-deliberate.gif"))
        for name, obj in objects.items():
            obj.data.materials[0] = original_materials[name]
            obj.hide_render = name != "r01"
            obj.hide_set(name != "r01")
        camera.matrix_world = front_matrix
        scene["integration_status"] = report["status"]
        source = bpy.data.texts.get(Path(__file__).name) or bpy.data.texts.new(Path(__file__).name)
        source.clear()
        source.write(Path(__file__).read_text())
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(model))
    assert all(digest(ROOT/path) == sha for path, sha in before.items())
    report["protected_asset_hashes_verified"] = len(before)
    report["artifact_sha256"] = {str(path.relative_to(ROOT)): digest(path)
                                 for path in list(preview.glob("*.png"))+list(preview.glob("*.gif"))+([model] if model.exists() else [])}
    (preview/("validation.json" if args.validate_only else "manifest.json")).write_text(json.dumps(report, indent=2)+"\n")
    print("INTEGRATION_COMPLETE", len(records), report["protected_asset_hashes_verified"], flush=True)


if __name__ == "__main__":
    main()
