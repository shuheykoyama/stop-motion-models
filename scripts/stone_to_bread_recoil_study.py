"""Create one printable recoil pose from the approved pulling p04 mesh."""
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
REVISION = "recoil-study-v1"
PULL = "pulling-study-v1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t*t*(3-2*t)


def recoil(original):
    """Gather the p04 surface while keeping its former pulled tip flattened."""
    x, y, z = original.T
    result = original.copy()
    # Outer ends contract to 40 mm; the pulled material remains slightly broad.
    tongue = smooth((y-2.0)/22.0)*np.exp(-(x/12.0)**2)
    result[:, 0] = x*(40.0/70.0+0.07*tongue)
    # A monotone near-direction map contracts the long tongue more than the body.
    positive = 0.5*((y-5.0)+np.sqrt((y-5.0)**2+9.0))
    result[:, 1] = 1.28*y-1.03*positive
    # Restore the main height while leaving the old pressure trace near the tip.
    result[:, 2] = np.maximum(z*(1.13-0.33*tongue)-1.0, 0.0)
    # Roll a one-millimeter shoulder into the new support patch, as in the v4 poses.
    low = (result[:, 2] > 0) & (result[:, 2] < 1)
    height = result[low, 2]
    result[low, 2] = 2*height*height-height*height*height
    return result


def montage(items, path, columns=3):
    command = ["magick", "montage", "-background", "#171719", "-fill", "white",
               "-font", "Helvetica", "-pointsize", "16"]
    for label, image in items:
        command += ["-label", label, str(image)]
    command += ["-geometry", "360x270+8+12", "-tile", f"{columns}x", str(path)]
    subprocess.run(command, check=True, capture_output=True)


def gif(items, delays, path):
    command = ["magick"]
    for (_, image), delay in zip(items, delays):
        command += ["-delay", str(delay//10), str(image)]
    command += ["-resize", "720x540", "+remap", "-layers", "Optimize", "-loop", "0", str(path)]
    subprocess.run(command, check=True, capture_output=True)
    actual = [int(x)*10 for x in subprocess.check_output(
        ["magick", "identify", "-format", "%T ", str(path)], text=True).split()]
    assert actual == delays, (actual, delays)
    return dict(path=str(path.relative_to(path.parents[3])), poses=[x[0] for x in items],
                delays_ms=actual, sha256=digest(path))


def append_original(name, scene):
    library = ROOT/"models/stone-to-bread-approved-geometry-recovery.blend"
    with bpy.data.libraries.load(str(library), link=False) as (source, destination):
        assert name in source.objects, name
        destination.objects = [name]
    obj = destination.objects[0]
    scene.collection.objects.link(obj)
    return obj


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
    # Store hashes before opening or writing any scene, including older approved studies.
    protected = {str(p.relative_to(ROOT)): digest(p) for folder in ("models", "exports", "previews")
                 for p in (ROOT/folder).rglob("*") if p.is_file() and p.name != ".DS_Store"
                 and REVISION not in str(p.relative_to(ROOT))}
    (preview/"baseline-hashes.json").write_text(json.dumps(protected, indent=2)+"\n")
    source_report = json.loads((ROOT/"previews/stone-to-bread"/PULL/"manifest.json").read_text())
    p04record = next(p for p in source_report["poses"] if p["id"] == "p04")
    assert digest(ROOT/p04record["stl"]) == p04record["stl_sha256"]
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"models"/f"stone-to-bread-{PULL}.blend"),
                             load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    p04 = scene.objects[f"{PULL}/p04"]
    assert base.mesh_fingerprint(p04) == p04record["mesh_fingerprint"]
    axis, near, up = [Vector(source_report["local_axes_world"][k]) for k in ("X", "Y_near", "Z")]
    basis = np.column_stack((axis, near, up))
    original = np.array([v.co[:] for v in p04.data.vertices], dtype=np.float64)@basis
    local = recoil(original)
    c01 = p04.copy()
    c01.data = p04.data.copy()
    c01.name = f"{REVISION}/c01"
    scene.collection.objects.link(c01)
    c01.data.vertices.foreach_set("co", np.asarray(local@basis.T, dtype=np.float32).ravel())
    c01.data.update()
    c01.location = (0, 0, 0)
    bpy.ops.object.select_all(action="DESELECT")
    c01.select_set(True)
    bpy.context.view_layer.objects.active = c01
    stl = export/"pose-c01.stl"
    bpy.ops.wm.stl_export(filepath=str(stl), export_selected_objects=True, global_scale=1,
                          use_scene_unit=False, apply_modifiers=True, forward_axis="Y", up_axis="Z", ascii_format=False)
    check = base.validate(stl, 1, basis, expected_dimensions=np.ptp(local, axis=0).tolist(),
                          core_dimensions=[30, 15, 20])
    check["path"], check["pose_id"] = str(stl.relative_to(output)), "c01"
    check.pop("frame")
    assert check["passed"], json.dumps(check)
    c01.location = p04.location.copy()
    exported, _, _ = base.read_stl(stl)
    mesh_vertices = np.array([v.co[:] for v in c01.data.vertices], dtype=np.float32)
    order = lambda a: a[np.lexsort(a.T)]
    assert np.array_equal(order(exported.astype(np.float32)), order(mesh_vertices))
    # Sample the former tongue, with the limitation that these are vertical chords.
    tree = BVHTree.FromPolygons(exported.tolist(), base.read_stl(stl)[1].tolist(), all_triangles=True, epsilon=0)
    thickness = []
    for y in np.linspace(5, 16, 6):
        bottom = Vector(basis@np.array([0, y, -1]))
        top = Vector(basis@np.array([0, y, 100]))
        lo, _, _, _ = tree.ray_cast(bottom, Vector(up), 120)
        hi, _, _, _ = tree.ray_cast(top, -Vector(up), 120)
        if lo is not None and hi is not None:
            thickness.append(float((hi-lo).dot(up)))
    assert len(thickness) == 6 and min(thickness) >= base.PARAMETERS["minimum_core"]
    bread = append_original("stone-to-bread/frame-10", scene)
    old = append_original("stone-to-bread/frame-09", scene)
    locked = json.loads((ROOT/"previews/stone-to-bread/sequence-validation.json").read_text())
    assert base.mesh_fingerprint(bread) == locked["mesh_fingerprints"]["10"]
    assert base.mesh_fingerprint(old) == locked["mesh_fingerprints"]["9"]
    bread.name, old.name = f"{REVISION}/b01", f"{REVISION}/reference-old-recoil"
    bread.location = p04.location.copy()
    old.location = p04.location.copy()
    camera_matrix = scene.camera.matrix_world.copy()
    report = dict(status="Recoil study awaiting visual review", source_p04=dict(
        stl=p04record["stl"], sha256=p04record["stl_sha256"],
        mesh_fingerprint=p04record["mesh_fingerprint"]),
        c01=dict(stl=str(stl.relative_to(output)), stl_sha256=digest(stl),
                 mesh_fingerprint=base.mesh_fingerprint(c01), validation=check,
                 placement_world_mm=list(c01.location), sampled_tongue_vertical_mm=thickness,
                 residual_near_extent_mm=float(local[:, 1].max())),
        b01=dict(preview_only=True, mesh_fingerprint=base.mesh_fingerprint(bread),
                 placement_world_mm=list(bread.location), stl=None),
        protected_hashes_verified=len(protected),
        limitations=["BVH intersection check excludes pairs sharing vertices.",
                     "Vertical samples do not prove global minimum wall thickness.",
                     "Slicer behavior and physical stability or printing are unverified."])
    if not args.geometry_only:
        images = {}
        objects = {"p04": p04, "c01": c01, "b01": bread, "old09": old,
                   "p03": scene.objects[f"{PULL}/p03"]}
        all_meshes = [o for o in scene.objects if o.type == "MESH" and o.name != "Tabletop (preview only)"]
        for view in ("front", "top", "side"):
            if view == "top":
                scene.camera.location = near*8+up*260
                scene.camera.rotation_euler = Matrix((axis, up.cross(axis), up)).transposed().to_euler()
            elif view == "side":
                scene.camera.location = -axis*260+near*2+up*11
                scene.camera.rotation_euler = Matrix((near, up, -axis)).transposed().to_euler()
            else:
                scene.camera.matrix_world = camera_matrix
            for name in (("p04", "c01", "b01", "old09") if view != "side" else ("p04", "c01", "old09")):
                for obj in all_meshes:
                    obj.hide_render = obj != objects[name]
                image = preview/f"{name}-{view}.png"
                if name == "c01" or not image.exists():
                    scene.render.filepath = str(image)
                    bpy.ops.render.render(write_still=True)
                images[(name, view)] = image
            comparison = [(name, images[(name, view)]) for name in
                          (("p04", "c01", "b01") if view != "side" else ("p04", "c01"))]
            montage(comparison, preview/f"contact-{view}.png", columns=len(comparison))
        montage([("old Frame 09", images[("old09", "front")]), ("new c01", images[("c01", "front")])],
                preview/"comparison-old09-c01.png", columns=2)
        p03image = ROOT/"previews/stone-to-bread"/PULL/"p03-realistic-front.png"
        quick = [(n, images[(n, "front")]) for n in ("p04", "c01", "b01")]
        context = [("p03", p03image)]+quick
        report["animations"] = dict(
            quick=gif(quick, [420, 80, 750], preview/"transition-quick.gif"),
            deliberate=gif(quick, [420, 250, 750], preview/"transition-deliberate.gif"),
            contextual=gif(context, [250, 420, 80, 750], preview/"transition-context.gif"))
        scene.camera.matrix_world = camera_matrix
        for obj in all_meshes:
            obj.hide_render = obj != p04
            obj.hide_set(obj != p04)
        text = bpy.data.texts.get(Path(__file__).name) or bpy.data.texts.new(Path(__file__).name)
        text.clear()
        text.write(Path(__file__).read_text())
        scene["revision_status"] = report["status"]
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(model))
    assert base.mesh_fingerprint(p04) == p04record["mesh_fingerprint"]
    assert all(digest(ROOT/path) == sha for path, sha in protected.items())
    report["artifacts"] = {str(p.relative_to(output)): digest(p) for p in (export, preview, model.parent)
                           if p.exists() for p in p.rglob("*") if p.is_file() and REVISION in str(p)}
    (preview/("reproduction.json" if args.geometry_only else "manifest.json")).write_text(json.dumps(report, indent=2)+"\n")
    print("RECOIL_COMPLETE", json.dumps(report["c01"]), flush=True)


if __name__ == "__main__":
    main()
