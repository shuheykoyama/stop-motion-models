"""Generate the eight-pose printable Rolling Wavy Pen sequence with Blender 4.5."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate import make_mesh
from rolling_wavy_pen import (
    FILM_Y_MM, NAMES, ROLL_DEG, centerline, environment, geometry, material, validate,
)

POSES = (
    ("straight", 0.0, 2),
    ("straight-mid", 0.5, 2),
    ("curved", 1.0, 2),
    ("curved-wavy-mid", 1.5, 2),
    ("wavy", 2.0, 2),
    ("wavy-strong-mid", 2.5, 2),
    ("highly-wavy", 3.0, 2),
    ("highly-wavy-hold", 3.0, 4),
)


def interpolate(values, state):
    lower = int(state)
    upper = min(3, lower+1)
    t = state-lower
    return values[lower]*(1-t)+values[upper]*t


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_sheets(preview, names):
    for view, suffix in (("black", "black"), ("neutral", "neutral"), ("top", "top")):
        files = [preview/f"frame-{i:02}-{view}.png" for i in range(1, 9)]
        args = ["magick", "montage", "-background", "#191919", "-fill", "white",
                "-font", "Helvetica", "-pointsize", "18"]
        for name, path in zip(names, files):
            args += ["-label", name.upper(), str(path)]
        args += ["-geometry", "520x350+8+14", "-tile", "2x4", str(preview/f"contact-{suffix}.png")]
        subprocess.run(args, check=True)


def make_gif(preview, exposures):
    args = ["magick"]
    for i, count in enumerate(exposures, 1):
        # GIF stores hundredths of a second; eight centiseconds approximates one 12 fps exposure.
        args += ["-delay", str(count*8), str(preview/f"frame-{i:02}-black.png")]
    args += ["-resize", "800x540", "-loop", "0", str(preview/"sequence.gif")]
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--geometry-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    output = args.output_root.resolve()
    study = "rolling-wavy-pen/sequence-v1"
    exports = output/"exports"/study
    previews = output/"previews"/study
    models = output/"models"
    exports.mkdir(parents=True, exist_ok=True)
    if not args.geometry_only:
        previews.mkdir(parents=True, exist_ok=True)
        models.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    names, reports, objects, fingerprints, placements = [], [], [], [], []
    black = material("solid black marker plastic", (0.014, 0.014, 0.015), 0.30)
    neutral = material("neutral shape review", (0.51, 0.54, 0.58), 0.66)
    for frame, (name, state, exposures) in enumerate(POSES, 1):
        roll = interpolate(ROLL_DEG, state)
        film_y = interpolate(FILM_Y_MM, state)
        vertices, faces, xs = geometry(state, roll)
        obj = make_mesh(scene, f"frame-{frame:02}", vertices, faces)
        obj["generator"] = "scripts/rolling_wavy_pen_sequence.py"
        obj["state"] = name
        obj["centerline_state"] = state
        obj["rolling_angle_degrees"] = roll
        obj["filming_y_mm"] = film_y
        obj.data.materials.append(black)
        obj.data.materials.append(neutral)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        path = exports/f"frame-{frame:02}.stl"
        bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True,
                              use_scene_unit=False, global_scale=1, apply_modifiers=True,
                              forward_axis="Y", up_axis="Z")
        obj.select_set(False)
        report = validate(path, obj, state, xs, pose_name=name)
        report.update(frame=frame, centerline_state=state, roll_degrees=roll,
                      filming_y_mm=film_y, exposure_count=exposures,
                      source_key_shapes=[NAMES[int(state)], NAMES[min(3, int(state)+1)]]
                      if state % 1 else [NAMES[int(state)]])
        if not report["passed"]:
            raise RuntimeError(f"Frame {frame:02} failed validation: {report}")
        reports.append(report)
        obj.location.y = film_y
        objects.append(obj)
        names.append(name)
        fingerprints.append(report["mesh_fingerprint"])
        placements.append([0.0, film_y, 0.0])
        print(f"VALID frame-{frame:02} {name}: {report['dimensions_mm']}", flush=True)
    if not args.geometry_only:
        environment(scene)
        scene.cycles.samples = 10
        scene.render.resolution_x, scene.render.resolution_y = 720, 486
        scene.render.resolution_percentage = 100
        for frame, obj in enumerate(objects, 1):
            for other in objects:
                other.hide_render = other is not obj
            scene.camera = bpy.data.objects["front oblique"]
            for style, material_index in (("black", 0), ("neutral", 1)):
                for polygon in obj.data.polygons:
                    polygon.material_index = material_index
                scene.render.filepath = str(previews/f"frame-{frame:02}-{style}.png")
                bpy.ops.render.render(write_still=True)
            scene.camera = bpy.data.objects["top"]
            scene.render.filepath = str(previews/f"frame-{frame:02}-top.png")
            bpy.ops.render.render(write_still=True)
        for obj in objects:
            obj.hide_render = obj is not objects[0]
        scene.camera = bpy.data.objects["front oblique"]
        scene["motif"] = "Rolling Wavy Pen — eight-pose sequence, review pending"
        scene["reference_length_mm"] = 141.8
        scene["reference_shaft_diameter_mm"] = 11.9
        scene["black_only"] = True
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(models/"rolling-wavy-pen-sequence-v1.blend"))
        make_sheets(previews, names)
        exposures = [entry[2] for entry in POSES]
        make_gif(previews, exposures)
    manifest = dict(
        status="review pending", source="scripts/rolling_wavy_pen_sequence.py",
        playback_fps=12, reference_length_mm=141.8, reference_shaft_diameter_mm=11.9,
        frames=[dict(frame=i, pose_id=name, stl=str(exports/f"frame-{i:02}.stl"),
                     placement_mm=placements[i-1], orientation_roll_degrees=reports[i-1]["roll_degrees"],
                     exposure_count=exposures, mesh_fingerprint=fingerprints[i-1],
                     stl_sha256=reports[i-1]["stl_sha256"], printable=True)
                for i, (name, _, exposures) in enumerate(POSES, 1)],
        unique_mesh_count=len(set(fingerprints)), validation=reports,
        unverified=["exhaustive minimum feature thickness", "slicer overhang/support behavior", "physical printing"])
    manifest_path = (previews if not args.geometry_only else exports)/"manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n")


if __name__ == "__main__":
    main()
