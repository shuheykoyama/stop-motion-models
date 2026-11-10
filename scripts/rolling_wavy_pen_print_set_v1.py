"""Export print candidates sampled from the reviewed v7 animation meshes."""
import argparse
import csv
import hashlib
import json
import shutil
import sys
import subprocess
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate import make_mesh, mesh_fingerprint
from rolling_wavy_pen import validate, environment, material
from rolling_wavy_pen_storyboard_study_v7 import mesh

PICKS = (1, 5, 25, 29, 32, 36, 37, 41, 44, 46, 47, 48)
SOURCE_PREVIEW = ROOT / "previews/rolling-wavy-pen/storyboard-study-v7"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def phase(progress):
    return "early-single-arc" if progress <= 0.30 else "wave-development"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--geometry-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    root = args.output_root.resolve()
    exports = root / "exports/rolling-wavy-pen/print-set-v1"
    previews = root / "previews/rolling-wavy-pen/print-set-v1"
    exports.mkdir(parents=True, exist_ok=True)
    if not args.geometry_only:
        previews.mkdir(parents=True, exist_ok=True)
        (root / "models").mkdir(parents=True, exist_ok=True)
    for stale in exports.glob("pose-*.stl"):
        try:
            if int(stale.stem.removeprefix("pose-")) > len(PICKS):
                stale.unlink()
        except ValueError:
            continue
    if not args.geometry_only:
        for stale in previews.glob("pose-*-source-v7-frame-*.png"):
            stale.unlink()

    source = json.loads((SOURCE_PREVIEW / "manifest.json").read_text())
    states = {row["frame"]: row for row in source["progress"]}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    black = material("black marker", (0.014, 0.014, 0.015), 0.3)
    objects, poses = [], []

    for pose_number, source_frame in enumerate(PICKS, 1):
        state = states[source_frame]
        progress = state["progress"]
        direction_sign = -1 if state["direction"] == "away" else 1
        roll = state["roll_degrees"]
        vertices, faces, xs = mesh(progress, direction_sign, roll)
        pose_id = f"pose-{pose_number:02}"
        obj = make_mesh(scene, pose_id, vertices, faces)
        obj["source_v7_frame"] = source_frame
        obj["shape_progress"] = progress
        obj["rolling_direction"] = state["direction"]
        obj["roll_degrees"] = roll
        obj["filming_y_mm"] = state["scene_y_mm"]
        obj.data.materials.append(black)

        mesh_id = mesh_fingerprint(obj)
        stl_path = exports / f"{pose_id}.stl"
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.wm.stl_export(filepath=str(stl_path), export_selected_objects=True,
                              use_scene_unit=False, global_scale=1, apply_modifiers=True,
                              forward_axis="Y", up_axis="Z")
        obj.select_set(False)
        validation = validate(stl_path, obj, 0, xs, pose_name=pose_id)
        if not validation["passed"]:
            raise RuntimeError(f"{pose_id} failed geometry validation: {validation}")

        obj.location.y = state["scene_y_mm"]
        objects.append(obj)
        duplicate_frames = [row["frame"] for row in source["progress"]
                            if row["progress"] == progress
                            and row["direction"] == state["direction"]
                            and row["roll_degrees"] == roll]
        source_image = SOURCE_PREVIEW / f"anim-{source_frame:02}.png"
        if not source_image.is_file():
            raise FileNotFoundError(source_image)
        copied_image = previews / f"{pose_id}-source-v7-frame-{source_frame:02}.png"
        if not args.geometry_only:
            shutil.copy2(source_image, copied_image)

        poses.append({
            "pose_id": pose_id,
            "source_frame": source_frame,
            "phase": phase(progress),
            "stl": str(stl_path.relative_to(root)),
            "stl_sha256": sha256(stl_path),
            "mesh_fingerprint": mesh_id,
            "preview": str(copied_image.relative_to(root)) if not args.geometry_only else None,
            "source_preview_sha256": sha256(source_image),
            "progress": progress,
            "direction": state["direction"],
            "roll_degrees": roll,
            "scene_y_mm": state["scene_y_mm"],
            "exact_duplicate_v7_frames": duplicate_frames,
            "exact_duplicate_exposure_count": len(duplicate_frames),
            "geometry_validation": validation,
        })

    selected_by_phase_direction = {}
    for pose in poses:
        selected_by_phase_direction.setdefault((pose["phase"], pose["direction"]), []).append(pose)
    source_mapping = []
    for row in source["progress"]:
        pool = selected_by_phase_direction.get((phase(row["progress"]), row["direction"]))
        if not pool:
            pool = [p for p in poses if p["phase"] == phase(row["progress"])]
        assigned = min(pool, key=lambda p: abs(p["progress"] - row["progress"]))
        source_mapping.append({"source_frame": row["frame"], "pose_id": assigned["pose_id"],
                               "stl": assigned["stl"], "direction": row["direction"],
                               "reuse_count": 1})
    mapped_counts = {pose["pose_id"]: sum(m["pose_id"] == pose["pose_id"] for m in source_mapping)
                     for pose in poses}
    for pose in poses:
        pose["recommended_48_frame_mapping_reuse_count"] = mapped_counts[pose["pose_id"]]
    for mapped in source_mapping:
        mapped["reuse_count"] = mapped_counts[mapped["pose_id"]]

    if not args.geometry_only:
        environment(scene)
        scene.render.resolution_x, scene.render.resolution_y = 420, 284
        scene.cycles.samples = 4
        for obj in objects:
            obj.hide_render = True
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(root / "models/rolling-wavy-pen-print-set-v1.blend"))

        montage = ["magick", "montage", "-background", "#191919", "-fill", "white",
                   "-font", "Helvetica", "-pointsize", "15"]
        for pose in poses:
            montage += ["-label", f"v7 F{pose['source_frame']:02} | {pose['pose_id']} | {pose['direction']}",
                        str(root / pose["preview"])]
        subprocess.run(montage + ["-geometry", "420x284+5+10", "-tile", "2x6",
                                  str(previews / "selected-frames.png")], check=True)

        stage_sources = (poses[0], poses[2], next(p for p in poses if p["source_frame"] == 36), poses[-1])
        compare = ["magick", "montage", "-background", "#191919", "-fill", "white",
                   "-font", "Helvetica", "-pointsize", "18"]
        for label, pose in zip(("EARLY ARC", "WAVE ONSET", "MID WAVE", "HIGHLY WAVY"), stage_sources):
            compare += ["-label", f"{label} | v7 F{pose['source_frame']:02}", str(root / pose["preview"])]
        subprocess.run(compare + ["-geometry", "600x406+6+12", "-tile", "2x2",
                                  str(previews / "representative-comparison.png")], check=True)

    mapping_path = previews / "frame-to-stl.csv" if not args.geometry_only else exports / "frame-to-stl.csv"
    with mapping_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=("source_frame", "pose_id", "stl", "direction", "reuse_count"))
        writer.writeheader()
        writer.writerows(source_mapping)

    manifest = {
        "status": "print candidates; awaiting visual review",
        "source_sequence": "previews/rolling-wavy-pen/storyboard-study-v7/manifest.json",
        "selection_note": "Each STL is generated from the v7 mesh function and exact selected frame parameters. Fingerprint comparison found that v7 progress 0.00 through 0.30 uses only two identical early-arc meshes (one per rolling direction); repeated copies were removed. Other source frames map to the nearest selected pose within the same phase and rolling direction.",
        "v7_shape_observation": "The v7 centerline function defines a single bow even at progress 0.00, and the bow remains unchanged through progress 0.30. Therefore this print set does not contain a truly straight state or incremental bow states; this is a limitation of the selected source sequence, not a new shape edit.",
        "recommended_unique_print_shapes": len(poses),
        "poses": poses,
        "source_48_frame_mapping": source_mapping,
        "frame_mapping_csv": str(mapping_path.relative_to(root)),
        "unverified": ["slicer support and print time", "exhaustive minimum feature thickness",
                       "physical printing and filming stability"],
    }
    manifest_path = previews / "manifest.json" if not args.geometry_only else exports / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
