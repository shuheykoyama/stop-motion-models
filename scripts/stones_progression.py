"""Resample the existing Stones hierarchy without changing its shapes or frozen motifs.

Blender --background --threads 8 --python-exit-code 1 --python scripts/stones_progression.py
Append -- --no-render --output-root /absolute/path for isolated reproduction.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate as g
from review_previews import animation, rig_settings


ROOT = Path(__file__).resolve().parents[1]
CHANGED = (2, 3, 5, 6)
CHILD_BLENDS = (0.0, 0.35, 0.70, 1.0)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shape_time(frame):
    # Keep all three exact hierarchy landmarks, including the approved endpoints, fixed.
    if frame in (1, 4, 7):
        return (frame-1)/6
    level, fraction = divmod(frame-1, 3)
    target = CHILD_BLENDS[fraction]
    low, high = 0.0, 1.0
    # Invert the unchanged easing; slightly shorter last blends balance fine-groove visibility.
    for _ in range(60):
        middle = (low+high)/2
        if middle*middle*(3-2*middle) < target:
            low = middle
        else:
            high = middle
    return (level+(low+high)/2)/2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    output = args.output_root.resolve()
    assert bpy.app.version[:2] == (4, 5), "Blender 4.5 LTS required"
    for folder in (output/"models", output/"exports"/"stones", output/"previews"/"stones"):
        folder.mkdir(parents=True, exist_ok=True)
    protected = [ROOT/"scripts"/name for name in ("generate.py", "pen_previews.py")]
    for motif in ("pen", "cup"):
        protected.append(ROOT/"models"/f"{motif}.blend")
        protected += sorted((ROOT/"exports"/motif).glob("*.stl"))
        protected += sorted(p for p in (ROOT/"previews"/motif).iterdir() if p.is_file())
    protected += [ROOT/"exports"/"stones"/f"frame-{f:02}.stl" for f in (1, 4, 7)]
    before = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    combined = json.loads((ROOT/"previews"/"validation.json").read_text())
    prior = combined["stones"]
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"models"/"stones.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    objects = [scene.objects[f"stones/frame-{f:02}"] for f in range(1, 8)]
    preserved = {f: g.mesh_fingerprint(objects[f-1]) for f in (1, 4, 7)}
    old_coordinates = [np.array([v.co[:] for v in obj.data.vertices]) for obj in objects]
    hierarchy = g.stone_hierarchy()
    ancestry = [[dict(identity=n["identity"], parent=n["parent"], center=n["center"].tolist(), area_mm2=n["area"])
                 for n in level] for level in hierarchy]
    hierarchy_hash = hashlib.sha256(json.dumps(ancestry).encode()).hexdigest()
    assert hierarchy_hash == prior["invariants"]["hierarchy_sha256"]
    records = []
    for frame, old in enumerate(objects, 1):
        t = shape_time(frame)
        path = ROOT/"exports"/"stones"/f"frame-{frame:02}.stl"
        if frame in CHANGED:
            materials = list(old.data.materials)
            transform = (old.location.copy(), old.rotation_euler.copy(), old.scale.copy())
            bpy.data.objects.remove(old, do_unlink=True)
            obj = g.make_mesh(scene, f"stones/frame-{frame:02}", *g.stones_geometry(t, hierarchy))
            obj.location, obj.rotation_euler, obj.scale = transform
            for material in materials:
                obj.data.materials.append(material)
            obj["t"], obj["sampler"] = t, "scripts/stones_progression.py"
            objects[frame-1] = obj
            for other in scene.objects:
                other.select_set(False)
            obj.hide_set(False)
            obj.hide_render = False
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            path = output/"exports"/"stones"/f"frame-{frame:02}.stl"
            bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True, global_scale=1,
                                  use_scene_unit=False, apply_modifiers=True,
                                  forward_axis="Y", up_axis="Z", ascii_format=False)
            record = g.validate_stl(path, "stones", frame)
        else:
            # Reuse the existing passing validation only after checking its exact STL digest.
            record = dict(prior["models"][frame-1])
            assert record["passed"] and record["sha256"] == digest(path)
        level = min(int(t*2), 1)
        u = t*2-level
        blend = u*u*(3-2*u)
        areas = [g.STONES["coarse_pitch"]**2, g.STONES["coarse_pitch"]*g.STONES["fine_pitch"], g.STONES["fine_pitch"]**2]
        # The validator's shape checks are t-independent; replace its uniform-sampling labels.
        record.update(shape_t=t, hierarchy_level_pair=[level, level+1], child_relief_blend=blend,
                      nominal_grain_scale_mm=math.sqrt(areas[level]*(1-blend)+areas[level+1]*blend),
                      geometry_validation="rerun" if frame in CHANGED else "existing passing record; SHA-256 verified")
        assert record["passed"]
        records.append(record)
    coordinates = [np.array([v.co[:] for v in obj.data.vertices]) for obj in objects]
    assert all(np.array_equal(points[:, :2], coordinates[0][:, :2]) for points in coordinates)
    assert preserved == {f: g.mesh_fingerprint(objects[f-1]) for f in preserved}
    steps = lambda values: [float(np.abs(b[:, 2]-a[:, 2]).max()) for a, b in zip(values, values[1:])]
    report = dict(status="Awaiting revised Stones visual review; not finally approved", models=records,
                  modified_frames=list(CHANGED), unchanged_frames=[1, 4, 7],
                  child_blend_landmarks=CHILD_BLENDS,
                  t_values=[shape_time(f) for f in range(1, 8)],
                  invariants=dict(xy_coordinates_identical=True, backing_and_outline_identical=True,
                                  hierarchy_sha256=hierarchy_hash, cell_counts_by_level=[len(level) for level in hierarchy],
                                  retained_mesh_fingerprints=preserved,
                                  before_per_step_max_height_delta_mm=steps(old_coordinates),
                                  initial_uniform_per_step_max_height_delta_mm=prior["invariants"].get(
                                      "initial_uniform_per_step_max_height_delta_mm",
                                      prior["invariants"].get("before_per_step_max_height_delta_mm", steps(old_coordinates))),
                                  per_step_max_height_delta_mm=steps(coordinates)))
    if not args.no_render:
        original_location, original_rotation = scene.camera.location.copy(), scene.camera.rotation_euler.copy()
        for view in ("oblique", "top"):
            if view == "top":
                scene.camera.location, scene.camera.rotation_euler = (0, 0, 260), (0, 0, 0)
            fixed = rig_settings(scene)
            paths = []
            for frame, obj in enumerate(objects, 1):
                for other in objects:
                    other.hide_render = other != obj
                    other.hide_set(other != obj)
                assert rig_settings(scene) == fixed
                suffix = "-top" if view == "top" else ""
                path = ROOT/"previews"/"stones"/f"frame-{frame:02}{suffix}.png"
                if frame in CHANGED:
                    path = output/"previews"/"stones"/path.name
                    scene.render.filepath = str(path)
                    bpy.ops.render.render(write_still=True)
                paths.append(path)
            sheet = output/"previews"/"stones"/("contact-sheet-top.png" if view == "top" else "contact-sheet.png")
            g.save_contact_sheet(paths, sheet)
            report[f"{view}_rig"] = fixed
            if view == "oblique":
                report["animation"] = animation(paths, output/"previews"/"stones"/"forward-reverse.gif")
            scene.camera.location, scene.camera.rotation_euler = original_location, original_rotation
    for frame, obj in enumerate(objects, 1):
        obj.hide_set(frame != 1)
        obj.hide_render = frame != 1
    scene["frames_json"] = json.dumps([(f, shape_time(f)) for f in range(1, 8)])
    scene["stones_progression_status"] = report["status"]
    scene["stones_sampling"] = "Inverse smoothstep at 35% and 70% child blends per hierarchy stage"
    text = bpy.data.texts.get("stones_progression.py") or bpy.data.texts.new("stones_progression.py")
    text.clear()
    text.write(Path(__file__).read_text())
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output/"models"/"stones.blend"))
    assert before == {str(p.relative_to(ROOT)): digest(p) for p in protected}
    report["protected_files_unchanged"] = True
    report["protected_sha256"] = before
    (output/"previews"/"stones"/"progression-validation.json").write_text(json.dumps(report, indent=2)+"\n")
    if output == ROOT:
        combined["stones"] = report
        (ROOT/"previews"/"validation.json").write_text(json.dumps(combined, indent=2)+"\n")
    print("Stones sampling refined; changed Frames 02, 03, 05, 06 only; validation passed.")


if __name__ == "__main__":
    main()
