"""Generate only the five missing states of the stone-to-bread sequence."""
import hashlib
import json
from pathlib import Path
import subprocess

import bpy
import numpy as np
from mathutils import Matrix, Vector

import stone_to_bread as s


NEW = (2, 3, 5, 6, 7)
LOCKED = (1, 4, 8, 9, 10)


def generate_rolling(output, no_render=False):
    """Replace only Frames 02-04, baking their rolling poses into STL coordinates."""
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(s.ROOT/"models"/f"{s.MOTIF}.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    axes = json.loads(scene["local_axes_world_json"])
    axis, near, up = [Vector(axes[k]) for k in ("X", "Y_near", "Z")]
    basis = np.column_stack((axis, near, up))
    preserved_meshes = {str(i): s.mesh_fingerprint(scene.objects[f"{s.MOTIF}/frame-{i:02}"]) for i in (1,4,5,6,7,8,9,10)}
    protected_paths = [p for motif in ("pen","stones","cup") for folder in ("models","exports","previews") for p in (s.ROOT/folder).rglob("*") if p.is_file() and (motif in p.parts or p.name == motif+".blend")]
    protected_paths += [s.ROOT/"exports"/s.MOTIF/f"frame-{i:02}.stl" for i in (1,5,6,7,8,9)]
    protected_hashes = {str(p.relative_to(s.ROOT)):s.digest(p) for p in protected_paths}
    results, objects = [], {}
    for frame in range(1, 5):
        old = scene.objects[f"{s.MOTIF}/frame-{frame:02}"]
        if frame in (1, 4):
            objects[frame] = old
            if frame == 4:
                # Restore an interrupted earlier export from the retained approved mesh.
                bpy.ops.object.select_all(action="DESELECT")
                old.hide_set(False)
                old.select_set(True)
                bpy.context.view_layer.objects.active = old
                bpy.ops.wm.stl_export(filepath=str(output/"exports"/s.MOTIF/"frame-04.stl"), export_selected_objects=True, global_scale=1, use_scene_unit=False, apply_modifiers=True, forward_axis="Y", up_axis="Z", ascii_format=False)
            continue
        local, faces, directions, settings = s.geometry(frame)
        bpy.data.objects.remove(old, do_unlink=True)
        obj = s.make_mesh(scene, f"{s.MOTIF}/frame-{frame:02}", (local@basis.T).tolist(), faces)
        obj["generator"], obj["preview_only"] = "scripts/stone_to_bread.py", False
        obj["parameters_json"] = json.dumps(settings)
        for mat in scene.objects[f"{s.MOTIF}/frame-01"].data.materials:
            obj.data.materials.append(mat)
        for poly in obj.data.polygons:
            poly.use_smooth = True
            landmark = directions[list(poly.vertices)].mean(axis=0)
            poly.material_index = int(landmark[0]+0.6*landmark[1]-0.5*landmark[2] > 0.70)
        path = output/"exports"/s.MOTIF/f"frame-{frame:02}.stl"
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True, global_scale=1, use_scene_unit=False, apply_modifiers=True, forward_axis="Y", up_axis="Z", ascii_format=False)
        result = s.validate(path, frame, basis)
        assert result["passed"], json.dumps(result)
        results.append(result)
        objects[frame] = obj
    if no_render:
        (output/"previews"/s.MOTIF/"rolling-reproduction.json").write_text(json.dumps(results, indent=2))
        return
    # Fixed frontal-oblique camera: no per-frame recentering; translation remains visible.
    target = near*8+up*15
    cam = scene.camera
    cam.location = target + near*167.12 + up*199.17
    cam.rotation_euler = (target-cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.type, cam.data.ortho_scale = "ORTHO", 155
    paths = []
    for frame in range(1, 5):
        for i in range(1, 5):
            objects[i].hide_render = i != frame
            objects[i].hide_set(i != frame)
        path = output/"previews"/s.MOTIF/f"rolling-{frame:02}-front.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        paths.append(path)
    sheet(paths, range(1,5), output/"previews"/s.MOTIF/"rolling-contact-sheet.png")
    animation(paths, range(1,5), [40]*4, output/"previews"/s.MOTIF/"rolling-revised.gif")
    cam.location = near*8+up*260
    cam.rotation_euler = Matrix((axis, up.cross(axis), up)).transposed().to_euler()
    top=[]
    for frame in range(1,5):
        for i in range(1,5):
            objects[i].hide_render = i != frame
            objects[i].hide_set(i != frame)
        path=output/"previews"/s.MOTIF/f"rolling-{frame:02}-top.png"
        scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        top.append(path)
    sheet(top, range(1,5), output/"previews"/s.MOTIF/"rolling-contact-sheet-top.png")
    for frame in range(1,11):
        obj=scene.objects[f"{s.MOTIF}/frame-{frame:02}"]
        obj.hide_set(frame != 1)
        obj.hide_render=frame != 1
    assert preserved_meshes == {str(i):s.mesh_fingerprint(scene.objects[f"{s.MOTIF}/frame-{i:02}"]) for i in (1,4,5,6,7,8,9,10)}
    assert all(s.digest(s.ROOT/p)==h for p,h in protected_hashes.items())
    cam.location = target + near*167.12 + up*199.17
    cam.rotation_euler = (target-cam.location).to_track_quat("-Z", "Y").to_euler()
    for name in ("stone_to_bread.py","stone_to_bread_sequence.py"):
        block=bpy.data.texts.get(name) or bpy.data.texts.new(name)
        block.clear()
        block.write((s.ROOT/"scripts"/name).read_text())
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(output/"models"/f"{s.MOTIF}.blend"))
    report={"status":"Rolling frames awaiting review","preserved_meshes":preserved_meshes,"protected_sha256":protected_hashes,"frames":results,"angles_rad":{"01":0,"02":0.42,"03":-0.30,"04":0.0},"y_offsets_mm":{"01":0,"02":2,"03":-1.5,"04":0},"gif_delays_ms":[400]*4}
    (output/"previews"/s.MOTIF/"rolling-revision-validation.json").write_text(json.dumps(report,indent=2)+"\n")
    print("ROLLING_REVISION",json.dumps(report),flush=True)


def sheet(paths, frames, destination):
    command = ["magick", "montage", "-background", "#171719", "-fill", "white", "-font", "Helvetica", "-pointsize", "18"]
    for frame, path in zip(frames, paths):
        command += ["-label", f"FRAME {frame:02}", str(path)]
    command += ["-geometry", "384x256+8+12", "-tile", "4x", str(destination)]
    subprocess.run(command, check=True, capture_output=True)


def animation(paths, frames, delays, destination):
    command = ["magick"]
    for path, delay in zip(paths, delays):
        command += ["-delay", str(delay), str(path)]
    command += ["-resize", "720x480", "-dither", "FloydSteinberg", "+remap", "-layers", "Optimize", "-strip", "-loop", "1", str(destination)]
    subprocess.run(command, check=True, capture_output=True)
    result = subprocess.check_output(["magick", "identify", "-format", "%T\\n", str(destination)], text=True)
    assert [int(v) for v in result.split()] == delays
    return dict(frames=list(frames), delays_ms=[v*10 for v in delays], sha256=s.digest(destination))


def generate_intermediates(output, no_render):
    for folder in (output/"models", output/"exports"/s.MOTIF, output/"previews"/s.MOTIF):
        folder.mkdir(parents=True, exist_ok=True)
    # Record every locked export and all assets of the three finalized motifs before editing.
    protected = [s.ROOT/"exports"/s.MOTIF/f"frame-{f:02}.stl" for f in LOCKED if f != 10]
    for motif in ("pen", "stones", "cup"):
        protected.append(s.ROOT/"models"/f"{motif}.blend")
        protected += list((s.ROOT/"exports"/motif).glob("*.stl"))
        protected += [p for p in (s.ROOT/"previews"/motif).iterdir() if p.is_file()]
    hashes = {str(p.relative_to(s.ROOT)): s.digest(p) for p in protected}
    bpy.ops.wm.open_mainfile(filepath=str(s.ROOT/"models"/f"{s.MOTIF}.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    locked = {f: scene.objects[f"{s.MOTIF}/frame-{f:02}"] for f in LOCKED}
    fingerprints = {str(f): s.mesh_fingerprint(o) for f, o in locked.items()}
    stored = json.loads((s.ROOT/"previews"/s.MOTIF/"validation.json").read_text())
    assert all(fingerprints[str(f)] == stored["mesh_fingerprints"][str(f)] for f in LOCKED)
    axes = json.loads(scene["local_axes_world_json"])
    axis, near, up = [Vector(axes[k]) for k in ("X", "Y_near", "Z")]
    basis = np.column_stack((axis, near, up))
    for frame in LOCKED:
        # Existing source must reproduce locked coordinates before it is used for interpolation.
        expected = np.asarray(s.geometry(frame)[0]@basis.T, dtype=np.float32)
        actual = np.array([v.co[:] for v in locked[frame].data.vertices], dtype=np.float32)
        assert np.array_equal(expected, actual), f"Locked frame {frame} source mismatch"
    objects = dict(locked)
    materials = list(locked[1].data.materials)
    results = []
    for frame in NEW:
        existing = scene.objects.get(f"{s.MOTIF}/frame-{frame:02}")
        if existing is not None:
            assert existing.get("generator") == "scripts/stone_to_bread.py"
            bpy.data.objects.remove(existing, do_unlink=True)
        local, faces, directions, settings = s.geometry(frame)
        obj = s.make_mesh(scene, f"{s.MOTIF}/frame-{frame:02}", (local@basis.T).tolist(), faces)
        obj["generator"], obj["preview_only"] = "scripts/stone_to_bread.py", False
        obj["parameters_json"] = json.dumps(settings)
        for mat in materials:
            obj.data.materials.append(mat)
        for face in obj.data.polygons:
            face.use_smooth = True
            landmark = directions[list(face.vertices)].mean(axis=0)
            face.material_index = int(landmark[0]+0.6*landmark[1]-0.5*landmark[2] > 0.70)
        for other in scene.objects:
            other.select_set(False)
        obj.hide_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        path = output/"exports"/s.MOTIF/f"frame-{frame:02}.stl"
        bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True, global_scale=1, use_scene_unit=False, apply_modifiers=True, forward_axis="Y", up_axis="Z", ascii_format=False)
        result = s.validate(path, frame, basis)
        assert result["passed"], json.dumps(result)
        results.append(result)
        objects[frame] = obj
    report = dict(status="Ten-frame sequence awaiting visual approval", new_frames=list(NEW), models=results,
                  locked_mesh_fingerprints=fingerprints, protected_sha256=hashes, camera_axes=axes,
                  unverified=["Adjacent/shared-vertex intersections; global minimum thickness; physical printing, handling and filmed continuity."])
    if not no_render:
        original = (scene.camera.location.copy(), scene.camera.rotation_euler.copy())
        for view_name in ("oblique", "top", "side"):
            if view_name == "top":
                scene.camera.location = Vector((0, -9, 0))+up*260
                scene.camera.rotation_euler = Matrix((axis, up.cross(axis), up)).transposed().to_euler()
            elif view_name == "side":
                scene.camera.location = -axis*260+near*10+up*7.5
                scene.camera.rotation_euler = Matrix((near, up, -axis)).transposed().to_euler()
            frames = tuple(range(4, 10)) if view_name == "side" else tuple(range(1, 11))
            paths = []
            for frame in frames:
                for other in objects.values():
                    other.hide_render = other != objects[frame]
                    other.hide_set(other != objects[frame])
                path = output/"previews"/s.MOTIF/f"frame-{frame:02}-{view_name}.png"
                # Reuse locked renders where the existing camera is identical.
                prior = s.ROOT/"previews"/s.MOTIF/path.name
                if frame in LOCKED and prior.exists():
                    path = prior
                else:
                    scene.render.filepath = str(path)
                    bpy.ops.render.render(write_still=True)
                paths.append(path)
            sheet(paths, frames, output/"previews"/s.MOTIF/f"sequence-{view_name}.png")
            if view_name == "oblique":
                report["full_gif"] = animation(paths, frames, [40]*8+[8,70], output/"previews"/s.MOTIF/"sequence.gif")
                report["rolling_gif"] = animation(paths[:4], frames[:4], [40]*4, output/"previews"/s.MOTIF/"rolling.gif")
                report["stretching_gif"] = animation(paths[3:8], frames[3:8], [40]*5, output/"previews"/s.MOTIF/"stretching.gif")
            scene.camera.location, scene.camera.rotation_euler = original
    assert fingerprints == {str(f): s.mesh_fingerprint(o) for f, o in locked.items()}
    assert hashes == {str(p.relative_to(s.ROOT)): s.digest(p) for p in protected}
    for frame, obj in objects.items():
        obj.hide_set(frame != 1)
        obj.hide_render = frame != 1
    scene["generated_frames"] = json.dumps(list(range(1, 11)))
    scene["sequence_status"] = report["status"]
    for name in ("stone_to_bread.py", "stone_to_bread_sequence.py"):
        text = bpy.data.texts.get(name) or bpy.data.texts.new(name)
        text.clear()
        text.write((s.ROOT/"scripts"/name).read_text())
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output/"models"/f"{s.MOTIF}.blend"))
    (output/"previews"/s.MOTIF/"sequence-validation.json").write_text(json.dumps(report, indent=2)+"\n")
    print("SEQUENCE_VALIDATION", json.dumps(report), flush=True)
