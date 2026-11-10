"""30-pose study with full-length waves added over a constant arc baseline."""

import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

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
    # Use one normalized coordinate for the complete soft rod, independent of
    # the later cap, barrel, clip, and tip profile.
    t = (x + LENGTH_MM / 2) / LENGTH_MM
    arc = 12.0 * curve_progress * math.sin(math.pi * t)
    if wave_progress <= 0:
        return sign * arc

    # A whole-length envelope closes the wave smoothly at both physical ends.
    # Its gentle global asymmetry gives the final silhouette a less regular rhythm.
    envelope = math.sin(math.pi * t) ** 1.5 * (1.0 + 0.10 * math.sin(2.0 * math.pi * t))
    q = wave_progress
    broad = 5.0 * smoothstep(q / 0.48) * math.sin(5.0 * math.pi * t)
    medium = 3.0 * smoothstep((q - 0.16) / 0.84) * math.sin(7.0 * math.pi * t)
    tight = 4.0 * smoothstep((q - 0.46) / 0.54) * math.sin(9.0 * math.pi * t)
    irregular = 2.0 * smoothstep((q - 0.72) / 0.28) * math.sin(11.0 * math.pi * t)
    return sign * (arc + envelope * (broad + medium + tight + irregular))


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


def rod_mesh(curve_progress, wave_progress, radius=BARREL_RADIUS_MM):
    # Sweep a constant circular section along the same unadorned centerline.
    xs = np.linspace(-LENGTH_MM / 2, LENGTH_MM / 2, 721)
    ys = np.asarray([centerline(x, curve_progress, wave_progress, 1) for x in xs])
    slopes = np.gradient(ys, xs)
    vertices, faces = [], []
    sides = 64
    for x, y, slope in zip(xs, ys, slopes):
        length = math.sqrt(1.0 + float(slope) ** 2)
        normal_x, normal_y = -float(slope) / length, 1.0 / length
        for side in range(sides):
            angle = 2.0 * math.pi * side / sides
            across = radius * math.cos(angle)
            height = max(0.0, radius + radius * math.sin(angle) - 0.3)
            vertices.append((float(x) + normal_x * across,
                             float(y) + normal_y * across, height))
    for row in range(len(xs) - 1):
        for side in range(sides):
            nxt = (side + 1) % sides
            faces.append((row * sides + side, row * sides + nxt,
                          (row + 1) * sides + nxt, (row + 1) * sides + side))
    for row in (0, len(xs) - 1):
        center = len(vertices)
        vertices.append((float(xs[row]), float(ys[row]), radius))
        for side in range(sides):
            faces.append((center, row * sides + side, row * sides + (side + 1) % sides))
    return vertices, faces


def write_plot(preview, filename, title, series, y_label):
    width, height = 1200, 620
    left, right, top, bottom = 85, 1140, 80, 530
    values = [value for _, points, _ in series for value in points]
    ymin, ymax = min(values), max(values)
    padding = max((ymax - ymin) * 0.12, 0.5 if y_label == "centerline Y (mm)" else 0.005)
    ymin, ymax = ymin - padding, ymax + padding

    def px(index, count):
        return left + index * (right - left) / (count - 1)

    def py(value):
        return bottom - (value - ymin) * (bottom - top) / (ymax - ymin)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#f4f2ed"/>',
             f'<text x="{left}" y="42" font-family="Arial" font-size="25" font-weight="bold" fill="#202126">{title}</text>']
    for tick in range(5):
        value = ymin + (ymax - ymin) * tick / 4
        y = py(value)
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="#d3d0c8" stroke-width="1"/>')
        parts.append(f'<text x="{left-12}" y="{y+5:.2f}" text-anchor="end" font-family="Arial" font-size="15" fill="#555">{value:.2f}</text>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#333"/>')
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#333"/>')
    for index, (label, points, color) in enumerate(series):
        coords = " ".join(f"{px(i, len(points)):.2f},{py(value):.2f}" for i, value in enumerate(points))
        path_data = "M " + coords.replace(" ", " L ")
        parts.append(f'<path d="{path_data}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
        legend_x = left + index * 240
        parts.append(f'<line x1="{legend_x}" y1="{height-35}" x2="{legend_x+30}" y2="{height-35}" stroke="{color}" stroke-width="4"/>')
        parts.append(f'<text x="{legend_x+40}" y="{height-29}" font-family="Arial" font-size="15" fill="#333">{label}</text>')
    parts.append(f'<text x="{(left+right)/2}" y="{height-4}" text-anchor="middle" font-family="Arial" font-size="16" fill="#333">position along full 141.8 mm centerline (mm)</text>')
    parts.append(f'<text x="22" y="{(top+bottom)/2}" transform="rotate(-90 22 {(top+bottom)/2})" text-anchor="middle" font-family="Arial" font-size="16" fill="#333">{y_label}</text>')
    parts.append('</svg>')
    svg_path = preview / filename.replace(".png", ".svg")
    svg_path.write_text("\n".join(parts))
    subprocess.run(["rsvg-convert", "-o", str(preview / filename), str(svg_path)], check=True)


def v10_centerline(x, curve_progress, wave_progress, sign=1):
    # Reproduce v10's centerline exactly for a direct shape-only comparison.
    t = (x + LENGTH_MM / 2) / LENGTH_MM
    bow = math.sin(math.pi * t)
    q = wave_progress
    arc = 12.0 * (1.0 - 0.5 * smoothstep(q)) * bow
    first = 5.0 * smoothstep(q / 0.42) * math.sin(3.0 * math.pi * t)
    second = 4.5 * smoothstep((q - 0.18) / 0.82) * math.sin(5.0 * math.pi * t)
    third = 2.5 * smoothstep((q - 0.48) / 0.52) * math.sin(7.0 * math.pi * t)
    irregular = 3.2 * smoothstep((q - 0.56) / 0.44) * math.sin(math.pi * t) ** 3 * math.sin(4.0 * math.pi * t + 0.45)
    return sign * (12.0 * curve_progress * bow if q <= 0 else arc + first + second + third + irregular)


def curvature_profile(xs, ys):
    slope = np.gradient(ys, xs)
    second = np.gradient(slope, xs)
    return second / np.power(1.0 + slope * slope, 1.5)


def render_analytical_comparisons(preview):
    xs = np.linspace(-LENGTH_MM / 2, LENGTH_MM / 2, 601)
    stages = [
        ("Straight", 0.0, 0.0, "#4f6475"),
        ("Single Arc", 1.0, 0.0, "#d17b32"),
        ("Arc + Waves", 1.0, 0.40, "#208c88"),
        ("Arc + Stronger Waves", 1.0, 1.0, "#b2465d"),
    ]
    centerline_series = []
    curvature_series = []
    distribution = {}
    for name, curve, wave, color in stages:
        ys = np.asarray([centerline(x, curve, wave, 1) for x in xs])
        centerline_series.append((name, ys.tolist(), color))
        curvature = curvature_profile(xs, ys)
        curvature_series.append((name, curvature.tolist(), color))
        third_metrics = []
        for third in range(3):
            lo = int(third * len(xs) / 3)
            hi = int((third + 1) * len(xs) / 3)
            segment = curvature[lo:hi]
            third_metrics.append({
                "rms_curvature_per_mm": float(np.sqrt(np.mean(segment * segment))),
                "max_abs_curvature_per_mm": float(np.max(np.abs(segment))),
            })
        distribution[name] = third_metrics
    write_plot(preview, "centerline-overlay.png", "Centerline stages — one full-length rod",
               centerline_series, "centerline Y (mm)")
    write_plot(preview, "curvature-distribution.png", "Signed curvature along the full centerline",
               curvature_series, "curvature (1/mm)")

    v10 = np.asarray([v10_centerline(x, 1.0, 1.0) for x in xs])
    v11 = np.asarray([centerline(x, 1.0, 1.0, 1) for x in xs])
    arc = np.asarray([12.0 * math.sin(math.pi * (x + LENGTH_MM / 2) / LENGTH_MM) for x in xs])
    write_plot(preview, "v10-v11-centerline.png", "Final centerline comparison — v10 and v11",
               [("v10", v10.tolist(), "#b2465d"),
                ("v11", v11.tolist(), "#208c88"),
                ("v11 arc baseline", arc.tolist(), "#30343b")], "centerline Y (mm)")
    return {
        "curvature_rms_by_equal_length_third": distribution,
        "final_centerline_midpoint_y_mm": float(centerline(0.0, 1.0, 1.0, 1)),
        "final_arc_baseline_amplitude_mm": 12.0,
        "wave_generation_domain": "normalized full-length coordinate t from 0 at cap end to 1 at tip; no component boundary input or end-local mask",
    }


def render_rod_comparison(scene, preview, neutral, shape_parameters_list):
    rod_dir = preview / "plain-rods"
    rod_dir.mkdir(parents=True, exist_ok=True)
    rods = []
    for name, curve, wave in shape_parameters_list:
        vertices, faces = rod_mesh(curve, wave)
        obj = make_mesh(scene, f"plain-rod-{name}", vertices, faces)
        obj.data.materials.append(neutral)
        obj.hide_render = True
        rods.append((name, obj))
    for index, (name, rod) in enumerate(rods):
        for obj in scene.objects:
            obj.hide_render = True
        rod.hide_render = False
        scene.camera = next(obj for obj in scene.objects if obj.type == "CAMERA" and obj.name.startswith("front oblique"))
        scene.render.filepath = str(rod_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    cmd = ["magick", "montage", "-background", "#191919", "-fill", "white",
           "-font", "Helvetica", "-pointsize", "18"]
    for name, _ in rods:
        cmd.extend(["-label", name, str(rod_dir / f"{name}.png")])
    subprocess.run(cmd + ["-geometry", "540x365+8+14", "-tile", "2x2",
                          str(preview / "plain-rods-four-stages.png")], check=True)
    for _, rod in rods:
        rod.hide_render = True
    return rods


def render_static_comparisons(scene, objects, preview, black, neutral, representative_frames):
    neutral_dir, top_dir = preview / "neutral", preview / "top"
    neutral_dir.mkdir(parents=True, exist_ok=True)
    top_dir.mkdir(parents=True, exist_ok=True)
    camera_front = next(obj for obj in scene.objects if obj.type == "CAMERA" and obj.name.startswith("front oblique"))
    camera_top = next(obj for obj in scene.objects if obj.type == "CAMERA" and obj.name.startswith("top"))
    for frame in representative_frames:
        obj = objects[frame - 1]
        scene.frame_set(frame)
        for other in objects:
            other.hide_render = other is not obj
        obj.data.materials[0] = neutral
        scene.camera = camera_front
        scene.render.filepath = str(neutral_dir / f"frame-{frame:02}.png")
        bpy.ops.render.render(write_still=True)
        scene.camera = camera_top
        scene.render.filepath = str(top_dir / f"frame-{frame:02}.png")
        bpy.ops.render.render(write_still=True)
        obj.data.materials[0] = black
    for dirname, subdir in (("representative-neutral.png", neutral_dir), ("representative-top.png", top_dir)):
        args = ["magick", "montage", "-background", "#191919", "-fill", "white",
                "-font", "Helvetica", "-pointsize", "15"]
        for frame in representative_frames:
            args.extend(["-label", f"frame {frame:02}", str(subdir / f"frame-{frame:02}.png")])
        subprocess.run(args + ["-geometry", "320x216+5+9", "-tile", "3x2",
                              str(preview / dirname)], check=True)


def render_cap_boundary(scene, objects, preview, frames):
    close_dir = preview / "cap-boundary"
    close_dir.mkdir(parents=True, exist_ok=True)
    camera = bpy.data.cameras.new("cap boundary close-up camera")
    camera.type = "ORTHO"
    camera.ortho_scale = 48
    cam = bpy.data.objects.new("cap boundary close-up", camera)
    scene.collection.objects.link(cam)
    target_x = -32.0
    for frame in frames:
        obj = objects[frame - 1]
        scene.frame_set(frame)
        y = centerline(target_x, obj["curve_progress"], obj["wave_progress"], obj["curve_orientation_sign"])
        target = np.array((target_x, y + obj.location.y, 6.0))
        cam.location = (target[0], target[1] - 78.0, target[2] + 90.0)
        cam.rotation_euler = (Vector(target.tolist()) - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = cam
        for other in objects:
            other.hide_render = other is not obj
        scene.render.filepath = str(close_dir / f"frame-{frame:02}.png")
        bpy.ops.render.render(write_still=True)
    cmd = ["magick", "montage", "-background", "#191919", "-fill", "white",
           "-font", "Helvetica", "-pointsize", "16"]
    for frame in frames:
        cmd.extend(["-label", f"frame {frame:02}", str(close_dir / f"frame-{frame:02}.png")])
    subprocess.run(cmd + ["-geometry", "640x432+8+12", "-tile", "2x1",
                          str(preview / "cap-boundary-closeup.png")], check=True)


def main():
    root = ROOT
    preview = root / "previews/rolling-wavy-pen/storyboard-study-v11"
    model_path = root / "models/rolling-wavy-pen-storyboard-study-v11.blend"
    preview.mkdir(parents=True, exist_ok=True)
    frame_dir = preview / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    # Replace only a repeated v11 build, leaving every unrelated scene intact.
    previous_scene = bpy.data.scenes.get("Rolling Wavy Pen v11")
    if previous_scene is not None:
        fallback = next((candidate for candidate in bpy.data.scenes if candidate != previous_scene), None)
        if fallback is not None and bpy.context.window is not None:
            bpy.context.window.scene = fallback
        bpy.data.scenes.remove(previous_scene)
    for old_object in list(bpy.data.objects):
        if old_object.name.startswith("pose-v11-") and old_object.get("sequence_frame") is not None:
            old_mesh = old_object.data if old_object.type == "MESH" else None
            bpy.data.objects.remove(old_object, do_unlink=True)
            if old_mesh is not None and old_mesh.users == 0:
                bpy.data.meshes.remove(old_mesh)
    # Create a dedicated scene so using the live Blender session never clears
    # unrelated work already present in its current scene.
    scene = bpy.data.scenes.new("Rolling Wavy Pen v11")
    if bpy.context.window is not None:
        bpy.context.window.scene = scene
    environment(scene)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 8
    scene.view_layers[0].cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 320, 216
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    black = material("matte black Mackee-like marker", (0.014, 0.014, 0.015), 0.34)
    scene.camera = next(obj for obj in scene.objects if obj.type == "CAMERA" and obj.name.startswith("front oblique"))
    scene.render.filepath = str(frame_dir / "frame-01.png")
    objects, rows, validation = [], [], []
    temp_root = Path(tempfile.mkdtemp(prefix="rolling-wavy-pen-v11-check-"))
    centerline_samples = np.linspace(-LENGTH_MM / 2, LENGTH_MM / 2, 1001)
    previous_shape_line = None
    previous_view_line = None
    max_shape_step = 0.0
    max_view_step = 0.0

    for frame in range(1, FRAME_COUNT + 1):
        phase, curve, wave, direction, sign, scene_y, roll = shape_parameters(frame)
        vertices, faces, xs = geometry_progress(curve, wave, roll, sign)
        obj = make_mesh(scene, f"pose-v11-{frame:02}", vertices, faces)
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
            "preview": f"previews/rolling-wavy-pen/storyboard-study-v11/frames/frame-{frame:02}.png",
        })

    for temporary_file in temp_root.iterdir():
        temporary_file.unlink()
    temp_root.rmdir()

    neutral = material("neutral shape-check marker", (0.48, 0.52, 0.57), 0.66)
    rod_stages = [("straight", 0.0, 0.0), ("single-arc", 1.0, 0.0),
                  ("arc-plus-waves", 1.0, 0.40), ("arc-plus-stronger-waves", 1.0, 1.0)]
    render_rod_comparison(scene, preview, neutral, rod_stages)

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
    representatives = [1, 12, 21, 30]
    make_montage(preview, "representative-shapes.png", representatives,
                 [f"{i:02} · {rows[i-1]['phase']} · c={rows[i-1]['curve_progress']:.2f} w={rows[i-1]['wave_progress']:.2f}"
                  for i in representatives], "2x2")

    render_static_comparisons(scene, objects, preview, black, neutral, representatives)
    render_cap_boundary(scene, objects, preview, [12, 30])
    distribution_analysis = render_analytical_comparisons(preview)

    for obj in objects:
        obj.hide_render = True
    objects[0].hide_render = False
    for obj in scene.objects:
        if obj.name.startswith("plain-rod-"):
            obj.hide_render = True
    scene.camera = next(obj for obj in scene.objects if obj.type == "CAMERA" and obj.name.startswith("front oblique"))
    scene.frame_set(1)

    phase_counts = {name: sum(row["phase"] == name for row in rows)
                    for name in ("straight", "single-arc", "arc+waves", "arc+stronger-waves")}
    manifest = {
        "status": "review preview; pending visual approval; no final print set selected",
        "source": "v8 pen profile and v6 alternating roll presentation; v11 uses one whole-length warped Fourier centerline and the full arc baseline",
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
        "centerline_design": {
            "definition": "sign * (12*c*sin(pi*t) + sin(pi*t)^1.5*(1+0.10*sin(2*pi*t))*sum(A_n*sin(n*pi*t), n=5,7,9,11))",
            "normalized_domain": "t=(x+70.9)/141.8 from cap end to tip; the function does not receive or branch on the cap seam",
            "wave_harmonics_and_max_amplitudes_mm": {"5pi": 5.0, "7pi": 3.0, "9pi": 4.0, "11pi": 2.0},
            "wave_envelope": "sin(pi*t)^1.5 closes added waves smoothly at both ends; a gentle full-length modulation creates restrained irregularity",
            "arc_baseline": "12 mm amplitude is not reduced when waves grow",
            "surface_profile_applied_after_centerline": True,
        },
        "motion_and_timing": [
            "The v6 movement convention is used: each six-pose cycle presents away/toward orientations with opposite centerline sign, ±20 degree roll and ±2.5 mm Y placement.",
            "The 30-pose sequence retains five round trips: one straight, one single-arc, and three with growing waves.",
            "GIF hold is 160 ms per pose for 4.8 seconds; no continuous interpolation is rendered between the discrete meshes.",
        ],
        "max_base_shape_centerline_delta_mm": max_shape_step,
        "max_oriented_view_centerline_delta_mm": max_view_step,
        "wave_distribution_analysis": distribution_analysis,
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
            "Review whether the v6-style sign reversal reads as rolling in physical stop motion.",
            "Review that the full-length wave distribution remains visually balanced in the bare-rod and marker comparisons.",
        ],
        "artifacts": {
            "sequence_gif": "previews/rolling-wavy-pen/storyboard-study-v11/sequence.gif",
            "contact_sheet": "previews/rolling-wavy-pen/storyboard-study-v11/contact-sheet.png",
            "representative_shapes": "previews/rolling-wavy-pen/storyboard-study-v11/representative-shapes.png",
            "plain_rod_comparison": "previews/rolling-wavy-pen/storyboard-study-v11/plain-rods-four-stages.png",
            "centerline_overlay": "previews/rolling-wavy-pen/storyboard-study-v11/centerline-overlay.png",
            "curvature_distribution": "previews/rolling-wavy-pen/storyboard-study-v11/curvature-distribution.png",
            "v10_v11_centerline": "previews/rolling-wavy-pen/storyboard-study-v11/v10-v11-centerline.png",
            "neutral_comparison": "previews/rolling-wavy-pen/storyboard-study-v11/representative-neutral.png",
            "top_comparison": "previews/rolling-wavy-pen/storyboard-study-v11/representative-top.png",
            "cap_boundary_closeup": "previews/rolling-wavy-pen/storyboard-study-v11/cap-boundary-closeup.png",
            "blender_scene": "models/rolling-wavy-pen-storyboard-study-v11.blend",
            "generator": "scripts/rolling_wavy_pen_storyboard_study_v11.py",
            "frame_renders": "previews/rolling-wavy-pen/storyboard-study-v11/frames/frame-01.png through frame-30.png",
        },
        "frames_data": rows,
    }
    (preview / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    validation_json = {"all_passed": manifest["validation_summary"]["all_passed"],
                       "pose_count": len(validation), "poses": validation,
                       "unverified": ["exhaustive minimum feature thickness", "slicer verification",
                                      "physical print test"]}
    (preview / "validation.json").write_text(json.dumps(validation_json, indent=2) + "\n")
    bpy.ops.wm.save_as_mainfile(filepath=str(model_path))


if __name__ == "__main__":
    main()
