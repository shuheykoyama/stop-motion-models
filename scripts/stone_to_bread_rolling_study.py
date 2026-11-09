"""Isolated printable rolling study; Blender 4.5 --background --python this_file -- [--geometry-only]."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stone_to_bread as base

ROOT = base.ROOT
REVISION = "rolling-study-v2"
EXPORT = ROOT / "exports/stone-to-bread" / REVISION
PREVIEW = ROOT / "previews/stone-to-bread" / REVISION
MODEL = ROOT / f"models/stone-to-bread-{REVISION}.blend"
# Negative local-X rotation moves a crown feature toward positive local Y.
POSES = [
    ("r01", "initial", 0.0, 0.0),
    ("r02", "toward, midpoint", -0.45, 4.0),
    ("r03", "toward, turnaround", -0.90, 8.0),
    ("r04", "away, midpoint", -0.20, 1.5),
    ("r05", "away, turnaround", 0.50, -5.0),
    ("r06", "toward again, midpoint", -0.15, 1.0),
    ("r07", "toward again, end", -0.80, 7.0),
]
EXPOSURES = dict(deliberate=[3, 2, 4, 2, 4, 2, 5], energetic=[2, 1, 3, 1, 3, 1, 4])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_files():
    # Every prior model/export/preview and approval file remains a recoverable reference.
    paths = []
    for folder in ("models", "exports", "previews"):
        paths.extend(p for p in (ROOT/folder).rglob("*") if p.is_file()
                     and REVISION not in str(p.relative_to(ROOT)))
    return {str(p.relative_to(ROOT)): digest(p) for p in paths}


def source():
    # Reuse the existing spherical topology; evaluate one persistent uncut pebble surface.
    _, faces, _, _ = base.geometry(1)
    n, m = base.PARAMETERS["angular_segments"], base.PARAMETERS["latitude_segments"]
    points = []
    for i in range(m+1):
        phi = -math.pi/2+math.pi*i/m
        for j in range(1 if i in (0, m) else n):
            theta = 2*math.pi*j/n
            x, y, z = math.cos(phi)*math.cos(theta), math.cos(phi)*math.sin(theta), math.sin(phi)
            # Broad asymmetric shoulders and a shallow hollow are printable orientation landmarks.
            relief = (0.05*math.sin(4*x+2*y+1.1)*math.cos(3*z-0.4)
                      + 0.035*math.cos(5*y-2*z+0.7)+0.03*math.sin(3*x-4*z))
            hollow = 0.055*math.exp(-((x+0.3)**2+(y-0.25)**2+(z-0.75)**2)/0.16)
            points.append(np.array([x, y, z])*(1+relief-hollow))
    points = np.array(points)
    points = (points-points.min(axis=0))/np.ptp(points, axis=0)*[30,25,22]
    points -= [15,12.5,11]
    return points, faces


def pose_geometry(original, angle):
    # Resting orientation is geometry; filming placement is kept outside the STL.
    c, s = math.cos(angle), math.sin(angle)
    rotation = np.array([[1,0,0],[0,c,-s],[0,s,c]])
    points = original @ rotation.T
    points[:, 2] -= points[:, 2].min()+1.4
    points[:, 2] = np.maximum(points[:, 2], 0)
    # A one-millimeter curved shoulder makes the sole transition unobtrusive.
    low = (points[:, 2] > 0) & (points[:, 2] < 1)
    t = points[low, 2]
    points[low, 2] = 2*t*t-t*t*t
    return points


def stone_material():
    mat = base.material("Weathered warm-gray stone", (0.32,0.30,0.27))
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Roughness"].default_value = 0.72
    shader.inputs["Specular IOR Level"].default_value = 0.22
    attribute = nodes.new("ShaderNodeAttribute")
    attribute.attribute_name = "stone_material"
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 9
    noise.inputs["Detail"].default_value = 2
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.17,0.16,0.145,1)
    ramp.color_ramp.elements[1].color = (0.43,0.41,0.37,1)
    links.new(attribute.outputs["Vector"],noise.inputs["Vector"])
    links.new(noise.outputs["Fac"],ramp.inputs[0])
    links.new(ramp.outputs[0],shader.inputs["Base Color"])
    # Only microscopic roughness is shaded; landmarks and silhouette are always geometry.
    fine = nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 120
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.035
    links.new(attribute.outputs["Vector"],fine.inputs["Vector"])
    links.new(fine.outputs["Fac"],bump.inputs["Height"])
    links.new(bump.outputs["Normal"],shader.inputs["Normal"])
    return mat


def timing_gif(paths, exposure_counts, destination):
    # GIF stores centiseconds: round cumulative 12-fps exposure time to prevent drift.
    cumulative = np.rint(np.cumsum([0]+exposure_counts)*100/12).astype(int)
    delays = np.diff(cumulative).tolist()
    command = ["magick"]
    for path, delay in zip(paths, delays):
        command += ["-delay",str(delay),str(path)]
    command += ["-resize","720x540","+remap","-layers","Optimize","-loop","0",str(destination)]
    subprocess.run(command, check=True, capture_output=True)
    actual = subprocess.check_output(["magick","identify","-format","%T ",str(destination)],text=True)
    assert [int(x) for x in actual.split()] == delays
    return dict(path=str(destination.relative_to(ROOT)),exposures=exposure_counts,
                gif_delays_ms=[x*10 for x in delays],sha256=digest(destination))


def pose_contact_sheet(paths, destination):
    command = ["magick","montage","-background","#171719","-fill","white",
               "-font","Helvetica","-pointsize","16"]
    for path, (name,role,_,_) in zip(paths,POSES):
        command += ["-label",f"{name}: {role}",str(path)]
    command += ["-geometry","384x288+8+12","-tile","4x",str(destination)]
    subprocess.run(command,check=True,capture_output=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--geometry-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    assert bpy.app.version[:2] == (4,5)
    EXPORT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    before = protected_files()
    (PREVIEW/"baseline-hashes.json").write_text(json.dumps(before,indent=2)+"\n")
    scene, axis, near, up = base.setup_scene()
    basis = np.column_stack((axis,near,up))
    scene.render.resolution_x, scene.render.resolution_y = 800,600
    scene.cycles.samples = 48
    scene.cycles.seed = 23
    scene.cycles.use_animated_seed = False
    # Keep a full-sequence-sized fixed composition, rather than enlarging individual pebbles.
    target = near*8+up*15
    scene.camera.location = target+near*(260*math.cos(math.radians(50)))+up*(260*math.sin(math.radians(50)))
    scene.camera.rotation_euler = (target-scene.camera.location).to_track_quat("-Z","Y").to_euler()
    scene.camera.data.ortho_scale = 120
    realistic, neutral = stone_material(), base.material("Neutral geometry", (0.36,0.36,0.36))
    original, faces = source()
    objects, records = [], []
    for index, (name, role, angle, y) in enumerate(POSES):
        local = pose_geometry(original, angle)
        obj = base.make_mesh(scene, f"{REVISION}/{name}", (local@basis.T).tolist(), faces)
        for poly in obj.data.polygons:
            poly.use_smooth = True
        obj.data.materials.append(realistic)
        # Material coordinates travel with the source stone and cannot swim between poses.
        attribute = obj.data.attributes.new("stone_material", "FLOAT_VECTOR", "POINT")
        attribute.data.foreach_set("vector", ((original+[15,12.5,11])/[30,25,22]).astype(np.float32).ravel())
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        path = EXPORT/f"pose-{name}.stl"
        bpy.ops.wm.stl_export(filepath=str(path),export_selected_objects=True,use_scene_unit=False,global_scale=1,apply_modifiers=True,forward_axis="Y",up_axis="Z")
        result = base.validate(path,1,basis,expected_dimensions=np.ptp(local,axis=0).tolist(),core_dimensions=[30,25,22])
        result["path"], result["pose_id"] = str(path.relative_to(ROOT)), name
        result.pop("frame")
        assert result["passed"], json.dumps(result)
        # Compare the export with the render mesh before adding scene-only placement.
        verts, _, _ = base.read_stl(path)
        mesh_verts = np.array([v.co[:] for v in obj.data.vertices],dtype=np.float32)
        order = lambda a: a[np.lexsort(a.T)]
        assert np.array_equal(order(verts.astype(np.float32)),order(mesh_verts))
        fingerprint = base.mesh_fingerprint(obj)
        obj.location = near*y
        obj["role"], obj["roll_angle_rad"], obj["placement_near_mm"] = role,angle,y
        objects.append(obj)
        records.append(dict(id=name,role=role,rotation_baked_local_x_rad=angle,
                            placement_local_mm=[0,y,0],dimensions_mm=result["local_dimensions_mm"],
                            stl=str(path.relative_to(ROOT)),stl_sha256=digest(path),mesh_fingerprint=fingerprint,
                            export_render_vertices_identical=True,validation=result,
                            exposures={k:v[index] for k,v in EXPOSURES.items()}))
        print("VALIDATED",name,flush=True)
    report = dict(status="Milestone 1 only; awaiting visual review",revision=REVISION,
                  proposed_total_poses="16–18; rolling 7, then separate pressing/elongation and center pull, one recoil, one bread",
                  base_fps=12,poses=records,local_axes_world=dict(X=list(axis),Y_near=list(near),Z=list(up)),
                  render_rig=base.rig_settings(scene),camera_elevation_deg=50,
                  contact_correction=dict(cap_depth_mm=1.4,shoulder_blend_mm=1.0),
                  notes=["STL includes resting orientation and sole, but no filming Y translation.",
                         "No deformation, recoil or bread poses generated in this milestone.",
                         "No global minimum thickness or adjacent-face intersection proof; no slicer or physical test."],
                  baseline_files_preserved=True)
    if not args.geometry_only:
        original_camera = scene.camera.matrix_world.copy()
        # Inexpensive first render checks framing and shader visibility before the final batch.
        for i,obj in enumerate(objects):
            obj.hide_render = i != 0
        scene.render.resolution_percentage, scene.cycles.samples = 50,8
        scene.render.filepath = str(PREVIEW/"test-front.png")
        bpy.ops.render.render(write_still=True)
        scene.render.resolution_percentage, scene.cycles.samples = 100,48
        report["animations"] = {}
        for style in ("realistic","neutral"):
            for obj in objects:
                obj.data.materials[0] = realistic if style == "realistic" else neutral
            # Both styles use the same mesh objects, rig, placements and fixed scale.
            for view in (("front","top","side") if style == "neutral" else ("front",)):
                if view == "top":
                    scene.camera.location = near*8+up*260
                    scene.camera.rotation_euler = Matrix((axis,up.cross(axis),up)).transposed().to_euler()
                elif view == "side":
                    scene.camera.location = -axis*260+near*2+up*11
                    scene.camera.rotation_euler = Matrix((near,up,-axis)).transposed().to_euler()
                else:
                    scene.camera.matrix_world = original_camera
                images=[]
                for i,obj in enumerate(objects):
                    for other in objects:
                        other.hide_render = other != obj
                    path = PREVIEW/f"{POSES[i][0]}-{style}-{view}.png"
                    scene.render.filepath = str(path)
                    bpy.ops.render.render(write_still=True)
                    images.append(path)
                pose_contact_sheet(images,PREVIEW/f"contact-{style}-{view}.png")
                if view == "front":
                    for timing, exposures in EXPOSURES.items():
                        report["animations"][f"{style}-{timing}"] = timing_gif(images,exposures,PREVIEW/f"rolling-{style}-{timing}.gif")
                scene.camera.matrix_world = original_camera
        for obj,record in zip(objects,records):
            assert base.mesh_fingerprint(obj) == record["mesh_fingerprint"]
            obj.data.materials[0] = realistic
            obj.hide_set(obj != objects[0])
            obj.hide_render = obj != objects[0]
        scene.camera.matrix_world = original_camera
        scene["revision_status"] = report["status"]
        bpy.data.texts.new(Path(__file__).name).write(Path(__file__).read_text())
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(MODEL))
    assert before == protected_files(), "A prior approved asset changed"
    destination = PREVIEW/("reproduction.json" if args.geometry_only else "manifest.json")
    destination.write_text(json.dumps(report,indent=2)+"\n")
    print("MILESTONE_COMPLETE",str(destination),flush=True)


if __name__ == "__main__":
    main()
