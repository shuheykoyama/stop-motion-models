"""Generate the four printable pulling poses from the saved v4 r07 mesh."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stone_to_bread as base

ROOT = base.ROOT
REVISION = "pulling-study-v1"
V4 = "rolling-elongating-study-v4"
POSES = [("p01", 0.14), ("p02", 0.40), ("p03", 0.70), ("p04", 1.0)]
PARAMETERS = dict(maximum_pull_mm=35.5, maximum_compression=0.36,
                  maximum_widening=0.12, deformation_half_width_mm=13.0)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def smooth(value):
    value = np.clip(value, 0.0, 1.0)
    return value*value*(3.0-2.0*value)


def deform(original, intensity):
    """Map the actual r07 surface continuously in tabletop-local coordinates."""
    points = original.copy()
    x, y = original[:, 0], original[:, 1]
    # The far side remains attached while the near side progressively drags forward.
    q = (y-original[:, 1].min())/np.ptp(original[:, 1])
    across = np.exp(-(x/PARAMETERS["deformation_half_width_mm"])**4)
    near = smooth(q)
    pressure = across*smooth((q-0.20)/0.70)*intensity
    # Widen and compress about the fixed table before moving the same material forward.
    points[:, 0] = x*(1.0+PARAMETERS["maximum_widening"]*pressure)
    points[:, 2] = original[:, 2]*(1.0-PARAMETERS["maximum_compression"]*pressure)
    points[:, 1] = y+PARAMETERS["maximum_pull_mm"]*intensity*across*near
    return points


def contact_sheet(items, destination):
    command = ["magick", "montage", "-background", "#171719", "-fill", "white",
               "-font", "Helvetica", "-pointsize", "16"]
    for name, path in items:
        command += ["-label", name, str(path)]
    command += ["-geometry", "320x240+8+12", "-tile", "5x", str(destination)]
    subprocess.run(command, check=True, capture_output=True)


def gif(items, exposures, destination):
    cumulative = np.rint(np.cumsum([0]+exposures)*100/12).astype(int)
    delays = np.diff(cumulative).tolist()
    command = ["magick"]
    for (_, path), delay in zip(items, delays):
        command += ["-delay", str(delay), str(path)]
    command += ["-resize", "720x540", "+remap", "-layers", "Optimize", "-loop", "0", str(destination)]
    subprocess.run(command, check=True, capture_output=True)
    actual = subprocess.check_output(["magick", "identify", "-format", "%T ", str(destination)], text=True)
    assert [int(x) for x in actual.split()] == delays
    return dict(path=str(destination), poses=[x[0] for x in items], exposures=exposures,
                delays_ms=[10*x for x in delays], sha256=digest(destination))


def extension_samples(path, basis, y_values):
    vertices, triangles, _ = base.read_stl(path)
    tree = BVHTree.FromPolygons(vertices.tolist(), triangles.tolist(), all_triangles=True, epsilon=0)
    result = []
    for y in y_values:
        top = Vector(basis@np.array([0.0, y, 100.0]))
        bottom = Vector(basis@np.array([0.0, y, -1.0]))
        lower, _, _, _ = tree.ray_cast(bottom, Vector(basis[:, 2]), 120)
        upper, _, _, _ = tree.ray_cast(top, -Vector(basis[:, 2]), 120)
        if lower is not None and upper is not None:
            result.append(dict(local_y_mm=y, vertical_thickness_mm=float((upper-lower).dot(Vector(basis[:, 2])))))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--geometry-only", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    assert bpy.app.version[:2] == (4, 5)
    output = args.output_root.resolve()
    export = output/"exports/stone-to-bread"/REVISION
    preview = output/"previews/stone-to-bread"/REVISION
    model = output/"models"/f"stone-to-bread-{REVISION}.blend"
    for folder in (export, preview, model.parent):
        folder.mkdir(parents=True, exist_ok=True)
    # Protect all pre-existing assets, including v4, rather than overwriting them.
    protected = {str(p.relative_to(ROOT)): digest(p) for folder in ("models", "exports", "previews")
                 for p in (ROOT/folder).rglob("*") if p.is_file() and REVISION not in str(p.relative_to(ROOT))}
    (preview/"baseline-hashes.json").write_text(json.dumps(protected, indent=2)+"\n")
    v4report = json.loads((ROOT/"previews/stone-to-bread"/V4/"manifest.json").read_text())
    baseline = next(p for p in v4report["poses"] if p["id"] == "r07")
    assert digest(ROOT/baseline["stl"]) == baseline["stl_sha256"]
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"models"/f"stone-to-bread-{V4}.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    axis, near, up = [Vector(v4report["local_axes_world"][k]) for k in ("X", "Y_near", "Z")]
    basis = np.column_stack((axis, near, up))
    r07 = scene.objects[f"{V4}/r07"]
    assert base.mesh_fingerprint(r07) == baseline["mesh_fingerprint"]
    assert np.allclose(r07.location[:], basis@np.array([0, 7, 0]))
    original = np.array([v.co[:] for v in r07.data.vertices], dtype=np.float64)@basis
    original_near = float(original[:, 1].max())
    objects, records = {"r07": r07}, []
    for name, intensity in POSES:
        local = deform(original, intensity)
        # Copy the exact source topology and material-coordinate attribute; only vertices deform.
        obj = r07.copy()
        obj.data = r07.data.copy()
        obj.name = f"{REVISION}/{name}"
        scene.collection.objects.link(obj)
        obj.data.vertices.foreach_set("co", np.asarray(local@basis.T, dtype=np.float32).ravel())
        obj.data.update()
        obj.hide_set(False)
        obj.hide_render = False
        obj["pull_intensity"] = intensity
        # STL uses the anchored local solid; scene placement is restored immediately after export.
        obj.location = (0, 0, 0)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        path = export/f"pose-{name}.stl"
        bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True, global_scale=1,
                              use_scene_unit=False, apply_modifiers=True, forward_axis="Y", up_axis="Z", ascii_format=False)
        check = base.validate(path, 1, basis, expected_dimensions=np.ptp(local, axis=0).tolist(),
                              core_dimensions=[30, 15, 20])
        check["path"], check["pose_id"] = str(path.relative_to(output)), name
        check.pop("frame")
        assert check["passed"], json.dumps(check)
        exported, _, _ = base.read_stl(path)
        mesh_vertices = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float32)
        order = lambda a: a[np.lexsort(a.T)]
        assert np.array_equal(order(exported.astype(np.float32)), order(mesh_vertices))
        fingerprint = base.mesh_fingerprint(obj)
        obj.location = r07.location.copy()
        near_extent = float(local[:, 1].max())
        # Directional samples are evidence about the tongue, not a global wall-thickness proof.
        samples = extension_samples(path, basis, [float(t) for t in np.linspace(3, max(3, near_extent-4), 6)])
        assert len(samples) == 6 and min(p["vertical_thickness_mm"] for p in samples) >= base.PARAMETERS["minimum_core"]
        records.append(dict(id=name, intensity=intensity, parameters=PARAMETERS,
                            dimensions_mm=check["local_dimensions_mm"], near_extent_mm=near_extent,
                            extension_from_r07_near_boundary_mm=near_extent-original_near,
                            placement_local_mm=[0, 7, 0], stl=str(path.relative_to(output)), stl_sha256=digest(path),
                            mesh_fingerprint=fingerprint, export_render_vertices_identical=True,
                            tongue_vertical_thickness_samples=samples, validation=check))
        objects[name] = obj
        print("VALIDATED", name, json.dumps(records[-1]), flush=True)
    report = dict(status="Pulling study awaiting visual review", revision=REVISION,
                  baseline_r07=baseline, parameters=PARAMETERS, poses=records,
                  local_axes_world=v4report["local_axes_world"], render_rig=v4report["render_rig"],
                  notes=["All pulling poses inherit r07's +7 mm filming placement; STL is exported without it.",
                         "Shared-vertex intersections and global minimum normal thickness are not checked.",
                         "Slicing, supports, friction and physical printing are unverified."])
    if not args.geometry_only:
        camera_matrix = scene.camera.matrix_world.copy()
        realistic = r07.data.materials[0]
        neutral = base.material("Pulling study neutral", (0.36, 0.36, 0.36))
        old = [o for o in scene.objects if o.type == "MESH" and o.name.startswith(V4+"/")]
        names = ["r07"]+[x[0] for x in POSES]
        images = {}
        # Reuse existing v4 stills: they were made with this same fixed scene and rig.
        for style in ("realistic", "neutral"):
            for name in names:
                objects[name].data.materials[0] = realistic if style == "realistic" else neutral
            for view in (("front",) if style == "realistic" else ("front", "top", "side")):
                if view == "top":
                    scene.camera.location = near*8+up*260
                    scene.camera.rotation_euler = Matrix((axis, up.cross(axis), up)).transposed().to_euler()
                elif view == "side":
                    scene.camera.location = -axis*260+near*2+up*11
                    scene.camera.rotation_euler = Matrix((near, up, -axis)).transposed().to_euler()
                else:
                    scene.camera.matrix_world = camera_matrix
                items = []
                for name in names:
                    if name == "r07":
                        path = ROOT/"previews/stone-to-bread"/V4/f"r07-{style}-{view}.png"
                    else:
                        for obj in old+list(objects.values()):
                            obj.hide_render = obj != objects[name]
                        path = preview/f"{name}-{style}-{view}.png"
                        scene.render.filepath = str(path)
                        bpy.ops.render.render(write_still=True)
                    items.append((name, path))
                images[(style, view)] = items
                contact_sheet(items, preview/f"contact-{style}-{view}.png")
                scene.camera.matrix_world = camera_matrix
        prior = [(name, ROOT/"previews/stone-to-bread"/V4/f"{name}-realistic-front.png") for name in ("r05", "r06")]
        transition = prior+images[("realistic", "front")]
        contact_sheet(transition, preview/"contact-rolling-to-pulling.png")
        report["animations"] = {
            "realistic": gif(images[("realistic", "front")], [4, 2, 3, 3, 5], preview/"pull-realistic.gif"),
            "neutral": gif(images[("neutral", "front")], [4, 2, 3, 3, 5], preview/"pull-neutral.gif"),
            "transition": gif(transition, [4, 2, 3, 2, 3, 3, 5], preview/"rolling-to-pulling.gif"),
        }
        for name, obj in objects.items():
            assert name == "r07" or base.mesh_fingerprint(obj) == next(r["mesh_fingerprint"] for r in records if r["id"] == name)
            obj.data.materials[0] = realistic
        for obj in old+list(objects.values()):
            obj.hide_set(obj != r07)
            obj.hide_render = obj != r07
        scene.camera.matrix_world = camera_matrix
        scene["revision_status"] = report["status"]
        text = bpy.data.texts.get(Path(__file__).name) or bpy.data.texts.new(Path(__file__).name)
        text.clear()
        text.write(Path(__file__).read_text())
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(model))
    assert base.mesh_fingerprint(r07) == baseline["mesh_fingerprint"]
    assert all(digest(ROOT/p) == h for p, h in protected.items())
    report["protected_hashes_verified"] = len(protected)
    (preview/("reproduction.json" if args.geometry_only else "manifest.json")).write_text(json.dumps(report, indent=2)+"\n")
    print("PULLING_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
