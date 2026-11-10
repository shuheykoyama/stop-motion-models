"""50-pose storyboard study with smooth straight-to-arc-to-wave deformation."""
import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate import make_mesh
from rolling_wavy_pen import validate, environment, material

FRAME_COUNT = 60
ROLL_TRAVEL_MM = 2.5
ROLL_ANGLE_DEG = 20.0
LENGTH_MM = 141.8
RADIAL_SEGMENTS = 96
AXIAL_STEP_MM = 0.8
TABLE_CONTACT_TRIM_MM = 0.68
CAP_RADIUS_MM = 6.6
BARREL_RADIUS_MM = 11.9 / 2
PROFILE = [(-70.4, 8.8), (-70.2, 9.8), (-69.5, 10.6), (-68.8, 10.9),
           (-34.0, 10.9), (-33.8, 10.5), (-33.4, 10.5), (-33.2, 10.9),
           (-32.5, 10.9), (-32.0, 9.0), (67.8, 9.0), (69.0, 8.8),
           (70.0, 8.2), (70.4, 7.5)]


def clamp01(value):
    return max(0.0, min(1.0, value))


def smoothstep(value):
    value = clamp01(value)
    return value * value * (3.0 - 2.0 * value)


def curve_parameters(frame):
    if frame <= 12:
        return 0.0, 0.0
    if frame <= 24:
        return smoothstep((frame - 13) / 11.0), 0.0
    return 1.0, clamp01((frame - 25) / 35.0)


def centerline(x, curve_progress, wave_progress):
    """One C2 centerline applies unchanged across cap, seam, barrel, and tip."""
    t = (x + LENGTH_MM / 2) / LENGTH_MM
    bow = math.sin(math.pi * t)
    if wave_progress <= 0:
        return 12.0 * curve_progress * bow

    q = wave_progress
    # Retain the completed arc while the first broad inflection grows from zero.
    base_bow = 12.0 * (1.0 - 0.5 * smoothstep(q)) * bow
    first_wave = 5.0 * smoothstep(q / 0.42) * math.sin(3.0 * math.pi * t)
    second_wave = 4.5 * smoothstep((q - 0.18) / 0.82) * math.sin(5.0 * math.pi * t)
    third_wave = 2.5 * smoothstep((q - 0.48) / 0.52) * math.sin(7.0 * math.pi * t)
    irregular = (3.2 * smoothstep((q - 0.56) / 0.44)
                 * math.sin(math.pi * t) ** 3 * math.sin(4.0 * math.pi * t + 0.45))
    return base_bow + first_wave + second_wave + third_wave + irregular


def geometry(frame, roll_degrees):
    curve_progress, wave_progress = curve_parameters(frame)
    profile_x = [x for x, _ in PROFILE]
    profile_r = [r * (CAP_RADIUS_MM / 10.9 if x < -32 else BARREL_RADIUS_MM / 9.0)
                 for x, r in PROFILE]
    xs = sorted({round(float(x), 5) for x in np.linspace(-LENGTH_MM / 2, LENGTH_MM / 2,
                                                         math.ceil(LENGTH_MM / AXIAL_STEP_MM) + 1)}
                | {round(x, 5) for x in profile_x} | {0.0})
    vertices, faces = [], []
    roll = math.radians(roll_degrees)
    for x in xs:
        radius = float(np.interp(x, profile_x, profile_r))
        clip_axial = smoothstep((x + 65.0) / 4.0) * smoothstep((-37.0 - x) / 4.0)
        offset = centerline(x, curve_progress, wave_progress)
        for j in range(RADIAL_SEGMENTS):
            angle = 2.0 * math.pi * j / RADIAL_SEGMENTS
            clip_angle = math.atan2(math.sin(angle - 2.35), math.cos(angle - 2.35))
            clip = 0.85 * clip_axial * math.exp(-0.5 * (clip_angle / 0.30) ** 4)
            radial = radius + clip
            y = offset + radial * math.cos(angle + roll)
            z = max(0.0, radius + radial * math.sin(angle + roll) - TABLE_CONTACT_TRIM_MM)
            vertices.append((x, y, z))

    for i in range(len(xs) - 1):
        for j in range(RADIAL_SEGMENTS):
            k = (j + 1) % RADIAL_SEGMENTS
            faces.append((i * RADIAL_SEGMENTS + j, i * RADIAL_SEGMENTS + k,
                          (i + 1) * RADIAL_SEGMENTS + k, (i + 1) * RADIAL_SEGMENTS + j))

    for ring in (0, len(xs) - 1):
        x = xs[ring]
        center = len(vertices)
        radius = float(np.interp(x, profile_x, profile_r))
        vertices.append((x, centerline(x, curve_progress, wave_progress), radius))
        for j in range(RADIAL_SEGMENTS):
            faces.append((center, ring * RADIAL_SEGMENTS + j,
                          ring * RADIAL_SEGMENTS + (j + 1) % RADIAL_SEGMENTS))
    return vertices, faces, xs


def rolling_pose(frame):
    if frame <= 12:
        phase_frame = frame - 1
    elif frame <= 24:
        phase_frame = frame - 13
    else:
        phase_frame = frame - 25
    phase_frame %= 12
    if phase_frame <= 5:
        travel = phase_frame / 5.0
        direction = "away"
        y = -ROLL_TRAVEL_MM * travel
        roll = -ROLL_ANGLE_DEG * travel
    else:
        travel = (phase_frame - 5) / 6.0
        direction = "toward"
        y = -ROLL_TRAVEL_MM * (1.0 - travel)
        roll = -ROLL_ANGLE_DEG * (1.0 - travel)
    return direction, y, roll


def phase_for(frame):
    if frame <= 12:
        return "straight"
    if frame <= 24:
        return "single-arc"
    return "wave-development"


def render_one(scene, obj, filepath, black, frame=None):
    scene.camera = bpy.data.objects["front oblique"]
    scene.render.filepath = str(filepath)
    bpy.ops.render.render(write_still=True)


def finish_existing_previews(scene, objects, preview):
    black = bpy.data.materials.get("matte black Mackee-like marker")
    shape_dir = preview / "shape-only"
    shape_dir.mkdir(parents=True, exist_ok=True)
    shape_gif = ["magick"]
    for frame, obj in enumerate(objects, 1):
        scene.frame_set(frame)
        for other in objects:
            other.hide_render = True
        curve_progress, wave_progress = curve_parameters(frame)
        vertices, faces, _ = geometry(frame, 0.0)
        temporary_obj = make_mesh(scene, f"shape-only-{frame:03}", vertices, faces)
        temporary_mesh = temporary_obj.data
        temporary_mesh.materials.append(black)
        temporary_obj.hide_render = False
        temporary_obj.location.y = 0.0
        scene.render.filepath = str(shape_dir / f"frame-{frame:03}.png")
        bpy.ops.render.render(write_still=True)
        shape_gif += ["-delay", "8", str(shape_dir / f"frame-{frame:03}.png")]
        bpy.data.objects.remove(temporary_obj, do_unlink=True)
        bpy.data.meshes.remove(temporary_mesh)

    sequence_gif = ["magick"]
    for frame in range(1, FRAME_COUNT + 1):
        sequence_gif += ["-delay", "8", str(preview / f"frame-{frame:03}.png")]
    subprocess.run(sequence_gif + ["-loop", "0", str(preview / "sequence.gif")], check=True)
    subprocess.run(shape_gif + ["-loop", "0", str(preview / "shape-only.gif")], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--geometry-only", action="store_true")
    parser.add_argument("--finish-previews", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    root = args.output_root.resolve()
    preview = root / "previews/rolling-wavy-pen/storyboard-study-v8"
    model_path = root / "models/rolling-wavy-pen-storyboard-study-v8.blend"
    preview.mkdir(parents=True, exist_ok=True)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    if args.finish_previews:
        bpy.ops.wm.open_mainfile(filepath=str(model_path))
        scene = bpy.context.scene
        objects = sorted((obj for obj in scene.objects if obj.name.startswith("frame-")),
                         key=lambda obj: int(obj.name.rsplit("-", 1)[1]))
        if len(objects) != FRAME_COUNT:
            raise RuntimeError(f"Expected {FRAME_COUNT} saved pose objects, found {len(objects)}")
        finish_existing_previews(scene, objects, preview)
        return
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    environment(scene)
    black = material("matte black Mackee-like marker", (0.014, 0.014, 0.015), 0.34)
    poses, objects = [], []
    x_samples = np.linspace(-LENGTH_MM / 2, LENGTH_MM / 2, 1001)
    previous_curve = None
    max_delta = 0.0
    temp_root = Path(tempfile.mkdtemp(prefix="rolling-wavy-pen-v8-validation-"))

    for frame in range(1, FRAME_COUNT + 1):
        phase = phase_for(frame)
        curve_progress, wave_progress = curve_parameters(frame)
        direction, scene_y, roll = rolling_pose(frame)
        vertices, faces, xs = geometry(frame, roll)
        obj = make_mesh(scene, f"frame-{frame:03}", vertices, faces)
        obj.data.materials.append(black)
        obj.location.y = scene_y
        obj["sequence_frame"] = frame
        obj["phase"] = phase
        obj["shape_curve_progress"] = curve_progress
        obj["shape_wave_progress"] = wave_progress
        obj["rolling_direction"] = direction
        obj["roll_degrees"] = roll
        obj["scene_y_mm"] = scene_y
        objects.append(obj)

        line = np.asarray([centerline(x, curve_progress, wave_progress) for x in x_samples])
        delta = 0.0 if previous_curve is None else float(np.max(np.abs(line - previous_curve)))
        max_delta = max(max_delta, delta)
        previous_curve = line

        stl_path = temp_root / f"frame-{frame:03}.stl"
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.wm.stl_export(filepath=str(stl_path), export_selected_objects=True,
                              use_scene_unit=False, global_scale=1, apply_modifiers=True,
                              forward_axis="Y", up_axis="Z")
        obj.select_set(False)
        report = validate(stl_path, obj, 0, xs, pose_name=f"frame-{frame:03}")
        if not report["passed"]:
            raise RuntimeError(f"Frame {frame:03} failed geometry validation: {report}")
        report["stl"] = "temporary validation export; deleted after checks"
        stl_path.unlink()

        poses.append({
            "frame": frame,
            "phase": phase,
            "curve_progress": curve_progress,
            "wave_progress": wave_progress,
            "rolling_direction": direction,
            "roll_degrees": roll,
            "scene_y_mm": scene_y,
            "dimensions_mm": report["dimensions_mm"],
            "centerline_max_delta_from_previous_mm": delta,
            "cap_uses_same_centerline": True,
            "geometry_validation": report,
            "preview": f"previews/rolling-wavy-pen/storyboard-study-v8/frame-{frame:03}.png",
        })

    temp_root.rmdir()
    # Store frame visibility as discrete step keys so the scene is an editable stop-motion timeline.
    for index, obj in enumerate(objects, 1):
        obj.hide_render = index != 1
        obj.keyframe_insert(data_path="hide_render", frame=1)
        if index != 1:
            obj.hide_render = True
            obj.keyframe_insert(data_path="hide_render", frame=index - 1)
            obj.hide_render = False
            obj.keyframe_insert(data_path="hide_render", frame=index)
        if index < FRAME_COUNT:
            obj.hide_render = True
            obj.keyframe_insert(data_path="hide_render", frame=index + 1)
        if obj.animation_data and obj.animation_data.action:
            for curve in obj.animation_data.action.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = "CONSTANT"

    scene.frame_start, scene.frame_end = 1, FRAME_COUNT
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    scene.render.resolution_x, scene.render.resolution_y = 320, 216
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(model_path))

    phases = [
        {"phase": "straight", "frames": [1, 12], "round_trips": 1,
         "behavior": "perfectly straight mesh; one away-and-toward rolling cycle"},
        {"phase": "single-arc", "frames": [13, 24], "round_trips": 1,
         "behavior": "single-signed-curvature bow grows from zero to 12 mm amplitude"},
        {"phase": "wave-development", "frames": [25, 60], "round_trips": 3,
         "behavior": "the completed bow is retained while 3π, 5π, 7π, and asymmetric terms grow smoothly"},
    ]
    manifest = {
        "status": "animation study; pending visual review; no production STLs",
        "frames": FRAME_COUNT,
        "reference_playback_fps": 12,
        "gif_frame_delay_ms": 80,
        "gif_effective_duration_ms": FRAME_COUNT * 80,
        "reference_duration_ms": FRAME_COUNT * 1000 / 12,
        "round_trips_total": 5,
        "phase_boundaries": phases,
        "camera": {"name": "front oblique", "fixed": True, "orthographic": True,
                   "position_mm": [0, -210, 245], "target_mm": [0, 0, 11]},
        "centerline_method": "one C2-continuous function is sampled for every axial station from cap end through barrel to tip; no cap-specific attenuation or extrapolation",
        "max_consecutive_centerline_delta_mm": max_delta,
        "print_set_status": "deferred until animation review; no production STL files are created",
        "preview_artifacts": {
            "sequence_gif": "previews/rolling-wavy-pen/storyboard-study-v8/sequence.gif",
            "shape_only_gif": "previews/rolling-wavy-pen/storyboard-study-v8/shape-only.gif",
            "contact_sheet": "previews/rolling-wavy-pen/storyboard-study-v8/contact-sequence.png",
            "representative_shapes": "previews/rolling-wavy-pen/storyboard-study-v8/representative-shapes.png",
            "individual_frames": "previews/rolling-wavy-pen/storyboard-study-v8/frame-001.png through frame-060.png",
            "shape_only_frames": "previews/rolling-wavy-pen/storyboard-study-v8/shape-only/frame-001.png through frame-060.png",
            "blender_scene": "models/rolling-wavy-pen-storyboard-study-v8.blend",
        },
        "frames_data": poses,
        "unverified": ["slicer behavior and support requirements", "physical printing", "minimum wall thickness beyond solid geometry checks"],
    }
    (preview / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    if args.geometry_only:
        return

    for frame, obj in enumerate(objects, 1):
        for other in objects:
            other.hide_render = other is not obj
        scene.frame_set(frame)
        render_one(scene, obj, preview / f"frame-{frame:03}.png", black, frame)

    representatives = {"straight": 1, "curved": 24, "wavy": 45, "highly-wavy": 60}
    montage = ["magick", "montage", "-background", "#191919", "-fill", "white",
               "-font", "Helvetica", "-pointsize", "14"]
    for frame in range(1, FRAME_COUNT + 1):
        montage += ["-label", f"{frame:02} | {phase_for(frame)}", str(preview / f"frame-{frame:03}.png")]
    subprocess.run(montage + ["-geometry", "320x216+5+10", "-tile", "5x12",
                              str(preview / "contact-sequence.png")], check=True)

    rep_command = ["magick", "montage", "-background", "#191919", "-fill", "white",
                   "-font", "Helvetica", "-pointsize", "18"]
    for label, frame in representatives.items():
        rep_command += ["-label", f"{label.upper()} | frame {frame:02}",
                        str(preview / f"frame-{frame:03}.png")]
    subprocess.run(rep_command + ["-geometry", "600x405+6+12", "-tile", "2x2",
                                  str(preview / "representative-shapes.png")], check=True)

    gif = ["magick"]
    shape_gif = ["magick"]
    for frame, obj in enumerate(objects, 1):
        image = preview / f"frame-{frame:03}.png"
        gif += ["-delay", "8", str(image)]

        old_data, old_y = obj.data, obj.location.y
        curve_progress, wave_progress = curve_parameters(frame)
        vertices, faces, _ = geometry(frame, 0.0)
        neutral_obj = make_mesh(scene, f"shape-only-{frame:03}", vertices, faces)
        neutral_obj.data.materials.append(black)
        obj.hide_render = False
        obj.location.y = 0.0
        obj.data = neutral_obj.data
        for other in objects:
            other.hide_render = other is not obj
        scene.render.filepath = str(preview / "shape-only" / f"frame-{frame:03}.png")
        (preview / "shape-only").mkdir(parents=True, exist_ok=True)
        bpy.ops.render.render(write_still=True)
        shape_gif += ["-delay", "8", str(preview / "shape-only" / f"frame-{frame:03}.png")]
        obj.data = old_data
        obj.location.y = old_y
        obj.hide_render = True
        neutral_mesh = neutral_obj.data
        bpy.data.objects.remove(neutral_obj, do_unlink=True)
        bpy.data.meshes.remove(neutral_mesh)

    subprocess.run(gif + ["-loop", "0", str(preview / "sequence.gif")], check=True)
    subprocess.run(shape_gif + ["-loop", "0", str(preview / "shape-only.gif")], check=True)


if __name__ == "__main__":
    main()
