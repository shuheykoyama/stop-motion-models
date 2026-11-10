"""30-pose stop-motion study with an arc baseline retained beneath growing waves."""

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
import rolling_wavy_pen_storyboard_study_v8 as v8

FRAME_COUNT = 30
DELAY_CS = 16
ROLL_TRAVEL_MM = v8.ROLL_TRAVEL_MM
ROLL_ANGLE_DEG = v8.ROLL_ANGLE_DEG
LENGTH_MM = v8.LENGTH_MM
RADIAL_SEGMENTS = v8.RADIAL_SEGMENTS
AXIAL_STEP_MM = v8.AXIAL_STEP_MM
TABLE_CONTACT_TRIM_MM = v8.TABLE_CONTACT_TRIM_MM
CAP_RADIUS_MM = v8.CAP_RADIUS_MM
BARREL_RADIUS_MM = v8.BARREL_RADIUS_MM
PROFILE = v8.PROFILE


def smoothstep(value):
    return v8.smoothstep(value)


def phase_spec(frame):
    if frame <= 6:
        return "straight", 0.0, 0.0, frame - 1
    if frame <= 12:
        i = frame - 7
        curve_progress = (0.0, 0.12, 0.34, 0.58, 0.82, 1.0)[i]
        return "single-arc", curve_progress, 0.0, i
    i = frame - 13
    wave_progress = (0.0, 0.02, 0.05, 0.09, 0.14, 0.20,
                     0.26, 0.33, 0.40, 0.47, 0.54, 0.61,
                     0.68, 0.75, 0.82, 0.89, 0.95, 1.0)[i]
    phase = "arc+waves" if wave_progress <= 0.40 else "arc+stronger-waves"
    return phase, 1.0, wave_progress, i % 6


def motion_for_cycle(local_index):
    # Retain v6's alternating paired poses: the same bend faces away and then
    # toward the camera as the marker rocks through each tabletop roll.
    direction_sign = -1 if local_index < 3 else 1
    direction = "away" if direction_sign < 0 else "toward"
    scene_y = direction_sign * ROLL_TRAVEL_MM
    roll = direction_sign * ROLL_ANGLE_DEG
    return direction, direction_sign, scene_y, roll


def shape_parameters(frame):
    phase, curve, wave, local_index = phase_spec(frame)
    direction, sign, scene_y, roll = motion_for_cycle(local_index)
    return phase, curve, wave, direction, sign, scene_y, roll


def centerline(x, curve_progress, wave_progress, sign):
    t = (x + LENGTH_MM / 2) / LENGTH_MM
    bow = math.sin(math.pi * t)
    arc = 12.0 * curve_progress * bow
    if wave_progress <= 0:
        return sign * arc
    q = wave_progress
    first_wave = 5.0 * smoothstep(q / 0.42) * math.sin(3.0 * math.pi * t)
    second_wave = 4.5 * smoothstep((q - 0.18) / 0.82) * math.sin(5.0 * math.pi * t)
    third_wave = 2.5 * smoothstep((q - 0.48) / 0.52) * math.sin(7.0 * math.pi * t)
    irregular = (3.2 * smoothstep((q - 0.56) / 0.44)
                 * math.sin(math.pi * t) ** 3 * math.sin(4.0 * math.pi * t + 0.45))
    return sign * (arc + first_wave + second_wave + third_wave + irregular)


def geometry_progress(curve_progress, wave_progress, roll_degrees, sign):
    profile_x = [x for x, _ in PROFILE]
    profile_r = [r * (CAP_RADIUS_MM / 10.9 if x < -32 else BARREL_RADIUS_MM / 9.0)
                 for x, r in PROFILE]
    xs = sorted({round(float(x), 5) for x in np.linspace(
        -LENGTH_MM / 2, LENGTH_MM / 2,
        math.ceil(LENGTH_MM / AXIAL_STEP_MM) + 1)}
        | {round(x, 5) for x in profile_x} | {0.0})
    vertices, faces = [], []
    roll = math.radians(roll_degrees)
    for x in xs:
        radius = float(np.interp(x, profile_x, profile_r))
        clip_axial = smoothstep((x + 65.0) / 4.0) * smoothstep((-37.0 - x) / 4.0)
        offset = centerline(x, curve_progress, wave_progress, sign)
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
        vertices.append((x, centerline(x, curve_progress, wave_progress, sign),
                         float(np.interp(x, profile_x, profile_r))))
        for j in range(RADIAL_SEGMENTS):
            faces.append((center, ring * RADIAL_SEGMENTS + j,
                          ring * RADIAL_SEGMENTS + (j + 1) % RADIAL_SEGMENTS))
    return vertices, faces, xs


def save_stl(obj, filepath):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=str(filepath), export_selected_objects=True,
                          use_scene_unit=False, global_scale=1, apply_modifiers=True,
                          forward_axis="Y", up_axis="Z")
    obj.select_set(False)


def set_visibility(scene, objects, visible_index):
    for idx, obj in enumerate(objects):
        obj.hide_render = idx != visible_index
    scene.view_layers[0].update()


def make_montage(preview, name, frames, labels, tile):
    args = ["magick", "montage", "-background", "#191919", "-fill", "white",
            "-font", "Helvetica", "-pointsize", "16"]
    for frame, label in zip(frames, labels):
        args.extend(["-label", label, str(preview / "frames" / f"frame-{frame:02}.png")])
    args.extend(["-geometry", "320x216+5+9", "-tile", tile, str(preview / name)])
    subprocess.run(args, check=True)


def main():
    root = ROOT
    preview = root / "previews/rolling-wavy-pen/storyboard-study-v10"
    model_path = root / "models/rolling-wavy-pen-storyboard-study-v10.blend"
    preview.mkdir(parents=True, exist_ok=True)
    frame_dir = preview / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    # Replace only a failed or repeated v10 build, leaving every unrelated scene intact.
    previous_scene = bpy.data.scenes.get("Rolling Wavy Pen v10")
    if previous_scene is not None:
        fallback = next((candidate for candidate in bpy.data.scenes if candidate != previous_scene), None)
        if fallback is not None and bpy.context.window is not None:
            bpy.context.window.scene = fallback
        bpy.data.scenes.remove(previous_scene)
    for old_object in list(bpy.data.objects):
        if old_object.name.startswith("pose-v10-") and old_object.get("sequence_frame") is not None:
            old_mesh = old_object.data if old_object.type == "MESH" else None
            bpy.data.objects.remove(old_object, do_unlink=True)
            if old_mesh is not None and old_mesh.users == 0:
                bpy.data.meshes.remove(old_mesh)
    # Create a dedicated scene so using the live Blender session never clears
    # unrelated work already present in its current scene.
    scene = bpy.data.scenes.new("Rolling Wavy Pen v10")
    if bpy.context.window is not None:
        bpy.context.window.scene = scene
    environment(scene)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    scene.render.resolution_x, scene.render.resolution_y = 320, 216
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    black = material("matte black Mackee-like marker", (0.014, 0.014, 0.015), 0.34)
    scene.camera = bpy.data.objects["front oblique"]
    scene.render.filepath = str(frame_dir / "frame-01.png")
    objects, rows, validation = [], [], []
    temp_root = Path(tempfile.mkdtemp(prefix="rolling-wavy-pen-v10-check-"))
    centerline_samples = np.linspace(-LENGTH_MM / 2, LENGTH_MM / 2, 1001)
    previous_shape_line = None
    previous_view_line = None
    max_shape_step = 0.0
    max_view_step = 0.0

    for frame in range(1, FRAME_COUNT + 1):
        phase, curve, wave, direction, sign, scene_y, roll = shape_parameters(frame)
        vertices, faces, xs = geometry_progress(curve, wave, roll, sign)
        obj = make_mesh(scene, f"pose-v10-{frame:02}", vertices, faces)
        obj.data.materials.append(black)
        obj.location.y = scene_y
        obj["sequence_frame"] = frame
        obj["phase"] = phase
        obj["curve_progress"] = curve
        obj["wave_progress"] = wave
        obj["rolling_direction"] = direction
        obj["curve_orientation_sign"] = sign
        obj["scene_y_mm"] = scene_y
        obj["roll_degrees"] = roll
        objects.append(obj)

        shape_line = np.asarray([centerline(x, curve, wave, 1) for x in centerline_samples])
        view_line = sign * shape_line
        shape_step = (0.0 if previous_shape_line is None else
                      float(np.max(np.abs(shape_line - previous_shape_line))))
        view_step = (0.0 if previous_view_line is None else
                     float(np.max(np.abs(view_line - previous_view_line))))
        max_shape_step = max(max_shape_step, shape_step)
        max_view_step = max(max_view_step, view_step)
        previous_shape_line = shape_line
        previous_view_line = view_line

        # Validate each discrete preview mesh through the established STL checks.
        old_y = obj.location.y
        obj.location.y = 0.0
        stl = temp_root / f"pose-{frame:02}.stl"
        save_stl(obj, stl)
        report = validate(stl, obj, 0, xs, pose_name=f"pose-{frame:02}")
        obj.location.y = old_y
        if not report["passed"]:
            raise RuntimeError(f"Pose {frame:02} geometry validation failed: {report}")
        validation.append(report)

        rows.append({
            "frame": frame,
            "phase": phase,
            "curve_progress": curve,
            "wave_progress": wave,
            "rolling_direction": direction,
            "scene_y_mm": scene_y,
            "roll_degrees": roll,
            "base_shape_max_delta_from_previous_mm": shape_step,
            "oriented_view_centerline_delta_mm": view_step,
            "dimensions_mm": report["dimensions_mm"],
            "mesh_fingerprint": report["mesh_fingerprint"],
            "validation_passed": report["passed"],
            "curve_orientation_sign": sign,
            "preview": f"previews/rolling-wavy-pen/storyboard-study-v10/frames/frame-{frame:02}.png",
        })

    for temporary_file in temp_root.iterdir():
        temporary_file.unlink()
    temp_root.rmdir()
    for idx, obj in enumerate(objects):
        for keyframe in range(1, FRAME_COUNT + 1):
            obj.hide_render = keyframe != idx + 1
            obj.keyframe_insert(data_path="hide_render", frame=keyframe)
        if obj.animation_data and obj.animation_data.action:
            for curve in obj.animation_data.action.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = "CONSTANT"
    scene.frame_start, scene.frame_end = 1, FRAME_COUNT
    scene.render.image_settings.color_mode = "RGB"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(model_path))

    for frame, obj in enumerate(objects, 1):
        set_visibility(scene, objects, frame - 1)
        scene.frame_set(frame)
        scene.render.filepath = str(frame_dir / f"frame-{frame:02}.png")
        bpy.ops.render.render(write_still=True)
        if frame in (1, 7, 12, 13, 18, 21, 22, 30):
            print(f"Rendered checkpoint frame {frame:02}/{FRAME_COUNT}", flush=True)

    gif_args = ["magick"]
    for frame in range(1, FRAME_COUNT + 1):
        gif_args.extend(["-delay", str(DELAY_CS), str(frame_dir / f"frame-{frame:02}.png")])
    subprocess.run(gif_args + ["-loop", "0", str(preview / "sequence.gif")], check=True)

    make_montage(preview, "contact-sheet.png", list(range(1, FRAME_COUNT + 1)),
                 [f"{i:02} · {rows[i-1]['phase']}" for i in range(1, FRAME_COUNT + 1)], "5x6")
    representatives = [1, 12, 18, 21, 30]
    make_montage(preview, "representative-shapes.png", representatives,
                 [f"{i:02} · {rows[i-1]['phase']} · c={rows[i-1]['curve_progress']:.2f} w={rows[i-1]['wave_progress']:.2f}"
                  for i in representatives], "2x3")

    phase_counts = {name: sum(row["phase"] == name for row in rows)
                    for name in ("straight", "single-arc", "arc+waves", "arc+stronger-waves")}
    manifest = {
        "status": "review preview; pending visual approval; no final print set selected",
        "source": "v8 profile and smooth wave terms with a constant arc baseline, combined with v6 alternating roll presentation",
        "frame_count": FRAME_COUNT,
        "gif_frame_delay_ms": DELAY_CS * 10,
        "effective_duration_seconds": FRAME_COUNT * DELAY_CS / 100,
        "reference_playback_fps": 12,
        "reference_exposure_frames_per_pose": 2,
        "reference_duration_seconds_at_12fps": FRAME_COUNT * 2 / 12,
        "gif_preview_rate_fps_equivalent": 100 / DELAY_CS,
        "phase_frame_counts": phase_counts,
        "phase_boundaries": [
            {"phase": "straight", "frames": [1, 6], "round_trips": 1,
             "shape": "exactly straight; roll/placement only"},
            {"phase": "single-arc", "frames": [7, 12], "round_trips": 1,
             "shape": "one full-length arc grows, including the cap, with the v6-style view reversal"},
            {"phase": "arc+waves", "frames": [13, 21], "round_trips": 1.5,
             "shape": "the 12 mm arc baseline remains constant while broad waves are added"},
            {"phase": "arc+stronger-waves", "frames": [22, 30], "round_trips": 1.5,
             "shape": "the same arc remains beneath stronger, tighter and irregular wave terms"},
        ],
        "camera": {"name": "front oblique", "fixed": True, "position_mm": [0, -210, 245],
                   "target_mm": [0, 0, 11], "orthographic_scale_mm": 185},
        "change_from_v8": [
            "The bow term stays at full 12 mm amplitude throughout wave growth; wave terms are added without tapering the arc.",
            "The v6 movement convention is used: each six-pose cycle presents away/toward orientations with opposite centerline sign, ±20 degree roll and ±2.5 mm Y placement.",
            "The 30-pose sequence retains five round trips: one straight, one single-arc, and three with growing waves.",
            "GIF hold is 160 ms per pose for 4.8 seconds; no continuous interpolation is rendered between the discrete meshes.",
        ],
        "max_base_shape_centerline_delta_mm": max_shape_step,
        "max_oriented_view_centerline_delta_mm": max_view_step,
        "validation_summary": {
            "poses_checked": len(validation),
            "all_passed": all(report["passed"] for report in validation),
            "checks": ["watertight", "manifold", "single component", "face orientation",
                       "degenerate faces", "nonadjacent face intersections", "tabletop clearance",
                       "finite-area contact", "static support margin", "dimensions"],
            "minimum_thickness": "exhaustive minimum feature thickness not verified",
            "slicer_and_physical_print": "not performed",
        },
        "unresolved_review_points": [
            "The v6-style sign reversal intentionally flips the curve/wave silhouette at each rolling reversal; review whether the discrete flip reads as a roll rather than a pose swap.",
            "Review that the arc remains visually dominant as irregular wave terms grow toward the final pose.",
        ],
        "artifacts": {
            "sequence_gif": "previews/rolling-wavy-pen/storyboard-study-v10/sequence.gif",
            "contact_sheet": "previews/rolling-wavy-pen/storyboard-study-v10/contact-sheet.png",
            "representative_shapes": "previews/rolling-wavy-pen/storyboard-study-v10/representative-shapes.png",
            "blender_scene": "models/rolling-wavy-pen-storyboard-study-v10.blend",
            "generator": "scripts/rolling_wavy_pen_storyboard_study_v10.py",
            "frame_renders": "previews/rolling-wavy-pen/storyboard-study-v10/frames/frame-01.png through frame-30.png",
        },
        "frames_data": rows,
    }
    (preview / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    validation_json = {"all_passed": manifest["validation_summary"]["all_passed"],
                       "pose_count": len(validation), "poses": validation,
                       "unverified": ["exhaustive minimum feature thickness", "slicer verification",
                                      "physical print test"]}
    (preview / "validation.json").write_text(json.dumps(validation_json, indent=2) + "\n")


if __name__ == "__main__":
    main()
