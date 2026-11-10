"""28-pose stop-motion timing study based on the reviewed v8 pen geometry."""

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
        return "straight", 0.0, 0.0, frame - 1, 6
    if frame <= 14:
        i = frame - 7
        curve_progress = (0.02, 0.07, 0.15, 0.28, 0.45, 0.63, 0.82, 1.0)[i]
        return "single-arc", curve_progress, 0.0, i, 8
    i = frame - 15
    # Three short roll cycles give the long wave phase visible reversals without
    # making the sequence feel like a continuously interpolated CG move.
    cycle_specs = ((0, 6), (6, 5), (11, 5))
    cycle_start, cycle_length = next((s, n) for s, n in cycle_specs if s <= i < s + n)
    local_index = i - cycle_start
    local_count = cycle_length
    progress_by_frame = (
        0.0, 0.035, 0.095, 0.17, 0.255, 0.35,
        0.43, 0.51, 0.59, 0.67, 0.74,
        0.80, 0.86, 0.92, 0.97, 1.0,
    )
    return "wave-development", 1.0, progress_by_frame[i], local_index, local_count


def motion_for_phase(local_index, local_count):
    if local_count == 8:
        travel_values = (0.0, 0.25, 0.50, 0.75, 1.0, 0.67, 0.33, 0.0)
    elif local_count == 6:
        # Map six discrete exposures over an away-and-return arc. The far endpoint
        # occurs once; the final exposure starts the return so there is no dead hold.
        travel_values = (0.0, 0.5, 1.0, 2.0 / 3.0, 1.0 / 3.0, 0.0)
    else:
        travel_values = (0.0, 0.5, 1.0, 0.5, 0.0)
    travel = travel_values[local_index]
    if local_index == 0:
        direction = "start"
    else:
        previous = travel_values[local_index - 1]
        direction = "away" if travel > previous else "toward" if travel < previous else "hold"
    scene_y = -ROLL_TRAVEL_MM * travel
    roll = -ROLL_ANGLE_DEG * travel
    return direction, scene_y, roll


def shape_parameters(frame):
    phase, curve, wave, local_index, local_count = phase_spec(frame)
    direction, scene_y, roll = motion_for_phase(local_index, local_count)
    return phase, curve, wave, direction, scene_y, roll


def geometry_progress(curve_progress, wave_progress, roll_degrees):
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
        offset = v8.centerline(x, curve_progress, wave_progress)
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
        vertices.append((x, v8.centerline(x, curve_progress, wave_progress),
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
    preview = root / "previews/rolling-wavy-pen/storyboard-study-v9"
    model_path = root / "models/rolling-wavy-pen-storyboard-study-v9.blend"
    preview.mkdir(parents=True, exist_ok=True)
    frame_dir = preview / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    # Replace only a failed or repeated v9 build, leaving every unrelated scene intact.
    previous_v9 = bpy.data.scenes.get("Rolling Wavy Pen v9")
    if previous_v9 is not None:
        fallback = next((candidate for candidate in bpy.data.scenes if candidate != previous_v9), None)
        if fallback is not None and bpy.context.window is not None:
            bpy.context.window.scene = fallback
        bpy.data.scenes.remove(previous_v9)
    for old_object in list(bpy.data.objects):
        if old_object.name.startswith("pose-") and old_object.get("sequence_frame") is not None:
            old_mesh = old_object.data if old_object.type == "MESH" else None
            bpy.data.objects.remove(old_object, do_unlink=True)
            if old_mesh is not None and old_mesh.users == 0:
                bpy.data.meshes.remove(old_mesh)
    # Create a dedicated scene so using the live Blender session never clears
    # unrelated work already present in its current scene.
    scene = bpy.data.scenes.new("Rolling Wavy Pen v9")
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
    temp_root = Path(tempfile.mkdtemp(prefix="rolling-wavy-pen-v9-check-"))
    centerline_samples = np.linspace(-LENGTH_MM / 2, LENGTH_MM / 2, 1001)
    previous_line = None
    max_centerline_step = 0.0

    for frame in range(1, FRAME_COUNT + 1):
        phase, curve, wave, direction, scene_y, roll = shape_parameters(frame)
        vertices, faces, xs = geometry_progress(curve, wave, roll)
        obj = make_mesh(scene, f"pose-{frame:02}", vertices, faces)
        obj.data.materials.append(black)
        obj.location.y = scene_y
        obj["sequence_frame"] = frame
        obj["phase"] = phase
        obj["curve_progress"] = curve
        obj["wave_progress"] = wave
        obj["rolling_direction"] = direction
        obj["scene_y_mm"] = scene_y
        obj["roll_degrees"] = roll
        objects.append(obj)

        line = np.asarray([v8.centerline(x, curve, wave) for x in centerline_samples])
        line_step = 0.0 if previous_line is None else float(np.max(np.abs(line - previous_line)))
        max_centerline_step = max(max_centerline_step, line_step)
        previous_line = line

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
            "centerline_max_delta_from_previous_mm": line_step,
            "dimensions_mm": report["dimensions_mm"],
            "mesh_fingerprint": report["mesh_fingerprint"],
            "validation_passed": report["passed"],
            "preview": f"previews/rolling-wavy-pen/storyboard-study-v9/frames/frame-{frame:02}.png",
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
        if frame in (1, 7, 14, 15, 20, 25, 30):
            print(f"Rendered checkpoint frame {frame:02}/{FRAME_COUNT}", flush=True)

    gif_args = ["magick"]
    for frame in range(1, FRAME_COUNT + 1):
        gif_args.extend(["-delay", str(DELAY_CS), str(frame_dir / f"frame-{frame:02}.png")])
    subprocess.run(gif_args + ["-loop", "0", str(preview / "sequence.gif")], check=True)

    make_montage(preview, "contact-sheet.png", list(range(1, FRAME_COUNT + 1)),
                 [f"{i:02} · {rows[i-1]['phase']}" for i in range(1, FRAME_COUNT + 1)], "5x6")
    representatives = [1, 6, 10, 14, 22, 30]
    make_montage(preview, "representative-shapes.png", representatives,
                 [f"{i:02} · {rows[i-1]['phase']} · c={rows[i-1]['curve_progress']:.2f} w={rows[i-1]['wave_progress']:.2f}"
                  for i in representatives], "2x3")

    phase_counts = {name: sum(row["phase"] == name for row in rows)
                    for name in ("straight", "single-arc", "wave-development")}
    manifest = {
        "status": "review preview; pending visual approval; no final print set selected",
        "source": "storyboard-study-v8 centerline and geometry definition, with a reduced 30-pose exposure plan",
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
            {"phase": "single-arc", "frames": [7, 14], "round_trips": 1,
             "shape": "one same-sign arc grows in eight discrete steps"},
            {"phase": "wave-development", "frames": [15, 30], "round_trips": 3,
             "shape": "arc retained while broad and then tighter undulations grow"},
        ],
        "camera": {"name": "front oblique", "fixed": True, "position_mm": [0, -210, 245],
                   "target_mm": [0, 0, 11], "orthographic_scale_mm": 185},
        "change_from_v8": [
            "60 poses reduced to 30; GIF hold is 160 ms per pose for 4.8 seconds total.",
            "One away-and-return roll remains in straight and single-arc phases; three shorter cycles carry wave growth.",
            "Phase transitions are explicitly sampled; the first wave exposure starts at zero wave progress so no new lobe appears as a one-frame jump.",
            "No geometric smoothing was added between exposures; each pose remains a discrete mesh.",
        ],
        "max_consecutive_centerline_delta_mm": max_centerline_step,
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
            "Visual judgment is still needed on whether the 160 ms exposure has enough stop-motion cadence without feeling slow.",
            "The arc-to-first-wave transition and final amplitude growth should be reviewed in the contact sheet and GIF.",
        ],
        "artifacts": {
            "sequence_gif": "previews/rolling-wavy-pen/storyboard-study-v9/sequence.gif",
            "contact_sheet": "previews/rolling-wavy-pen/storyboard-study-v9/contact-sheet.png",
            "representative_shapes": "previews/rolling-wavy-pen/storyboard-study-v9/representative-shapes.png",
            "blender_scene": "models/rolling-wavy-pen-storyboard-study-v9.blend",
            "generator": "scripts/rolling_wavy_pen_storyboard_study_v9.py",
            "frame_renders": "previews/rolling-wavy-pen/storyboard-study-v9/frames/frame-01.png through frame-30.png",
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
