"""Storyboard four-stage Rolling Wavy Pen study, with paired resting roll poses."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate import make_mesh, mesh_fingerprint
from rolling_wavy_pen import LENGTH_SCALE, environment, geometry, material, validate

STAGES = ("straight", "curved", "wavy", "highly-wavy")
ROLLS = ((0.0, 180.0), (16.0, 196.0), (22.0, 202.0), (26.0, 206.0))
FILM_Y = ((0.0, 1.2), (0.0, 1.2), (0.0, 1.2), (0.0, 1.2))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shape(x, stage, sign):
    # Normalize the flexible shaft separately from the cap, so its four stages
    # describe material-space locations rather than independent random curves.
    seam = -32.0 * LENGTH_SCALE
    tip = 70.4 * LENGTH_SCALE

    def shaft(px):
        t = (px - seam) / (tip - seam)
        envelope = math.sin(math.pi * t)
        if stage == 0:
            return 0.0
        if stage == 1:
            # A parabola has one curvature sign: this stage is a bow, never an S.
            return sign * 6.4 * 4.0 * t * (1.0 - t)
        if stage == 2:
            # Two broad cycles introduce the first alternating bends.
            return sign * 5.0 * envelope * math.sin(4.0 * math.pi * t)
        # Unequal frequencies and amplitudes break the final stage's rhythm.
        return sign * envelope * (8.0 * math.sin(3.3 * math.pi * t)
                                  + 2.6 * math.sin(6.1 * math.pi * t + 0.55))

    if x >= seam:
        return shaft(min(x, tip))
    # Continue the shaft tangent through the cap as one rigid straight section.
    at_seam = shaft(seam)
    slope = (shaft(seam + 0.02) - at_seam) / 0.02
    return at_seam + slope * (x - seam)


def export_stl(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True,
                          use_scene_unit=False, global_scale=1,
                          apply_modifiers=True, forward_axis="Y", up_axis="Z")
    obj.select_set(False)


def render(scene, obj, path, camera):
    for candidate in scene.objects:
        if candidate.get("storyboard_pose"):
            candidate.hide_render = candidate is not obj
    scene.camera = bpy.data.objects[camera]
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def assemble(preview):
    for camera, target in (("front", "contact-front.png"), ("top", "contact-top.png")):
        files = [preview / f"{name}-main-{camera}.png" for name in STAGES]
        command = ["magick", "montage", "-background", "#191919", "-fill", "white",
                   "-font", "Helvetica", "-pointsize", "20"]
        for name, path in zip(STAGES, files):
            command += ["-label", name.upper(), str(path)]
        command += ["-geometry", "600x405+8+16", "-tile", "2x2", str(preview / target)]
        subprocess.run(command, check=True)
    command = ["magick", "montage", "-background", "#191919", "-fill", "white",
               "-font", "Helvetica", "-pointsize", "18"]
    for name in STAGES:
        for side in ("main", "opposite"):
            command += ["-label", f"{name.upper()} {side.upper()}",
                        str(preview / f"{name}-{side}-front.png")]
    command += ["-geometry", "540x365+8+14", "-tile", "2x4",
                str(preview / "contact-roll-direction.png")]
    subprocess.run(command, check=True)
    command = ["magick"]
    for name in STAGES:
        command += ["-delay", "42", str(preview / f"{name}-main-front.png")]
    command += ["-loop", "0", str(preview / "four-stages.gif")]
    subprocess.run(command, check=True)
    command = ["magick"]
    for name in STAGES:
        for side in ("main", "opposite"):
            command += ["-delay", "28", str(preview / f"{name}-{side}-front.png")]
    command += ["-loop", "0", str(preview / "rolling-views.gif")]
    subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--geometry-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    output = args.output_root.resolve()
    export = output / "exports/rolling-wavy-pen/storyboard-study-v1"
    preview = output / "previews/rolling-wavy-pen/storyboard-study-v1"
    export.mkdir(parents=True, exist_ok=True)
    if not args.geometry_only:
        preview.mkdir(parents=True, exist_ok=True)
        (output / "models").mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    black = material("solid black marker plastic", (0.014, 0.014, 0.015), 0.30)
    objects, reports = {}, []
    for stage, name in enumerate(STAGES):
        for side_index, side in enumerate(("main", "opposite")):
            sign = 1 if side_index == 0 else -1
            roll = ROLLS[stage][side_index]
            vertices, faces, xs = geometry(stage, roll, lambda x, s=stage, g=sign: shape(x, s, g))
            obj = make_mesh(scene, f"{name}-{side}", vertices, faces)
            obj["storyboard_pose"] = True
            obj["stage"] = name
            obj["side"] = side
            obj["roll_degrees"] = roll
            obj["filming_y_mm"] = FILM_Y[stage][side_index]
            obj.data.materials.append(black)
            path = export / f"{name}-{side}.stl"
            export_stl(obj, path)
            report = validate(path, obj, stage, xs, pose_name=f"{name}-{side}")
            report.update(stage=name, side=side, roll_degrees=roll,
                          filming_y_mm=FILM_Y[stage][side_index])
            if not report["passed"]:
                raise RuntimeError(f"{name}-{side} validation failed: {report}")
            reports.append(report)
            obj.location.y = FILM_Y[stage][side_index]
            objects[name, side] = obj
            print(f"VALID {name}-{side}: {report['dimensions_mm']}", flush=True)
    if not args.geometry_only:
        environment(scene)
        scene.cycles.samples = 12
        scene.render.resolution_x, scene.render.resolution_y = 720, 486
        for name in STAGES:
            for side in ("main", "opposite"):
                render(scene, objects[name, side], preview / f"{name}-{side}-front.png", "front oblique")
            render(scene, objects[name, "main"], preview / f"{name}-main-top.png", "top")
        render(scene, objects["straight", "main"], preview / "straight-main-front.png", "front oblique")
        scene["motif"] = "Rolling Wavy Pen storyboard study; pending visual review"
        scene["generator"] = "scripts/rolling_wavy_pen_storyboard_study.py"
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(output / "models/rolling-wavy-pen-storyboard-study-v1.blend"))
        assemble(preview)
    manifest = dict(status="pending visual review", source="scripts/rolling_wavy_pen_storyboard_study.py",
                    blender=bpy.app.version_string, stages=list(STAGES), reports=reports,
                    render_mesh_is_stl_mesh=True,
                    unverified=["exhaustive minimum wall thickness", "slicer support behavior", "physical print"])
    (preview if not args.geometry_only else export).joinpath("validation.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
