"""Five representative states only; run with Blender 4.5's bundled Python.

Blender --background --threads 8 --python-exit-code 1 --python scripts/stone_to_bread.py
Append -- --no-render --output-root /absolute/path for isolated reproduction.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate import make_mesh, material, mesh_fingerprint, read_stl
from review_previews import rig_settings


ROOT = Path(__file__).resolve().parents[1]
MOTIF = "stone-to-bread"
FRAMES = (1, 4, 8, 9, 10)
PARAMETERS = dict(stone_dimensions=[30, 25, 20], rod_dimensions=[70, 20, 18],
                  stretched_dimensions=[70, 55, 15], recoil_dimensions=[40, 30, 18],
                  bread_dimensions=[80, 60, 50], pull=35.0, pull_width=8.5,
                  recoil_pull=6.0, rolling_radians=2.2, floor_cut=-0.88,
                  tongue_compression=0.30, tongue_widening=0.18,
                  press_start_y=-3.0, press_full_y=10.0,
                  recoil_compression=0.28, recoil_widening=0.12,
                  recoil_press_start_y=5.0, recoil_press_full_y=13.0,
                  angular_segments=256, latitude_segments=128, minimum_core=2.4)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state(frame):
    p = PARAMETERS
    # Three short rolling strokes alternate toward/away/toward before the final rod pose.
    if frame == 1:
        rolling = 0.0
        offset = 0.0
    elif frame == 2:
        rolling = 0.42
        offset = 2.0
    elif frame == 3:
        rolling = -0.30
        offset = -1.5
    elif frame == 4:
        rolling = PARAMETERS["rolling_radians"]
        offset = 0.0
    else:
        rolling = PARAMETERS["rolling_radians"]
        offset = 0.0
    # Keep a continuous stone definition available without generating unrequested frames.
    if frame <= 4:
        # Retain a pebble silhouette through the two opposing rolls; elongation arrives at 04.
        progress = {1: 0.0, 2: 0.16, 3: 0.38, 4: 1.0}[frame]
        s = progress*progress*(3-2*progress)
        dims = np.array(PARAMETERS["stone_dimensions"])*(1-s)+np.array(PARAMETERS["rod_dimensions"])*s
        return dict(dimensions=dims.tolist(), roll=rolling,
                    displacement_y=offset, pull=0.0,
                    pull_width=PARAMETERS["pull_width"], tension=0.0, roll_phase=rolling if frame in (2, 3) else 0.0, roll_offset=offset)
    if frame <= 8:
        s = (frame-4)/4
        s = s*s*(3-2*s)
        dims = np.array(p["rod_dimensions"])*(1-s)+np.array(p["stretched_dimensions"])*s
        dims[1] = p["rod_dimensions"][1]
        return dict(dimensions=dims.tolist(), roll=PARAMETERS["rolling_radians"], displacement_y=0.0,
                    pull=PARAMETERS["pull"]*s, pull_width=PARAMETERS["pull_width"], tension=0.0)
    # Recoil is a separate state; the preview performs no in-between morph into bread.
    dims = list(p["recoil_dimensions"])
    dims[1] -= p["recoil_pull"]
    return dict(dimensions=dims, roll=PARAMETERS["rolling_radians"],
                pull=PARAMETERS["recoil_pull"], pull_width=7.5, tension=0.025)


def geometry(frame, apply_press=True):
    p = PARAMETERS
    bread = frame == 10
    settings = dict(dimensions=p["bread_dimensions"], roll=0, pull=0, pull_width=1, tension=0) if bread else state(frame)
    n, m = p["angular_segments"], p["latitude_segments"]
    vertices, directions, rings = [], [], []
    for i in range(m+1):
        phi = -math.pi/2+math.pi*i/m
        ring = []
        for j in range(1 if i in (0, m) else n):
            angle = 2*math.pi*j/n
            direction = np.array([math.cos(phi)*math.cos(angle), math.cos(phi)*math.sin(angle), math.sin(phi)])
            x, y, z = direction
            # Rotate material coordinates around the future rod axis before evaluating relief.
            ry = y*math.cos(settings["roll"])-z*math.sin(settings["roll"])
            rz = y*math.sin(settings["roll"])+z*math.cos(settings["roll"])
            character = (0.030*math.sin(4*x+2*ry+1.1)*math.cos(3*rz-0.4)
                         +0.022*math.cos(5*ry-2*rz+0.7)+0.018*math.sin(3*x-4*rz))
            if bread:
                # Three curved, broad seams are real depressions in a softly puffed roll.
                character = 0.012*math.sin(3*x+2*y)*math.cos(4*z)
                for seam in (-0.48, 0.0, 0.48):
                    character -= 0.040*math.exp(-((x-seam-0.13*y*y)/0.055)**2)*max(0, z)**0.5
            else:
                character += settings["tension"]*math.cos(9*x+2*ry)*math.exp(-8*x*x)
            point = direction*(1+character)
            # Truncate only the lowermost spherical cap, retaining a broad planar footprint.
            point[2] = max(0, point[2]-p["floor_cut"])
            ring.append(len(vertices))
            vertices.append(point)
            directions.append((x, ry, rz))
        rings.append(ring)
    points = np.array(vertices)
    low, high = points.min(axis=0), points.max(axis=0)
    # Normalize the source stone/roll dimensions before the actual tabletop-plane pull.
    points = (points-low)/(high-low)*np.array(settings["dimensions"])
    points[:, :2] -= np.array(settings["dimensions"][:2])/2
    # Bake the alternating rolling poses into the printable mesh before export.
    angle = settings.get("roll_phase", 0.0)
    if angle:
        c, sn = math.cos(angle), math.sin(angle)
        y, z = points[:, 1].copy(), points[:, 2].copy()
        points[:, 1] = c*y-sn*z
        points[:, 2] = sn*y+c*z
        # Trim only a shallow lower cap after rotation to create a finite, table-aligned sole.
        patch_depth = 1.25
        points[:, 2] = np.maximum(points[:, 2]-points[:, 2].min()-patch_depth, 0.0)
        # Keep the intended Y datum independent of rotation around the old origin.
        points[:, 1] -= (points[:, 1].min()+points[:, 1].max())/2
    if settings.get("displacement_y", 0.0):
        points[:, 1] += settings["displacement_y"]
    if settings["pull"]:
        q = np.clip((points[:, 1]+settings["dimensions"][1]/2)/settings["dimensions"][1], 0, 1)
        near_weight = q*q*(3-2*q)
        envelope = np.exp(-(points[:, 0]/settings["pull_width"])**4)
        # This monotone Y map stretches one existing solid; no branch is unioned onto it.
        points[:, 1] += settings["pull"]*envelope*near_weight
    if apply_press and 4 < frame <= 8:
        # Press the nearward tongue progressively, keeping the far rim and lateral rod ends.
        intensity = (frame-4)/4
        intensity = intensity*intensity*(3-2*intensity)
        along = np.clip((points[:, 1]-p["press_start_y"])/(p["press_full_y"]-p["press_start_y"]), 0, 1)
        along = along*along*(3-2*along)
        across = np.clip((np.abs(points[:, 0])-12)/10, 0, 1)
        across = 1-across*across*(3-2*across)
        pressure = along*across*intensity
        # Scale upward from the fixed table, rather than shifting any lower face below it.
        points[:, 2] *= 1-p["tongue_compression"]*pressure
        points[:, 0] *= 1+p["tongue_widening"]*pressure
    if apply_press and frame == 9:
        # Let the compact body recover its height while the forward remnant stays pressed.
        along = np.clip((points[:, 1]-p["recoil_press_start_y"])/
                        (p["recoil_press_full_y"]-p["recoil_press_start_y"]), 0, 1)
        along = along*along*(3-2*along)
        across = np.clip((np.abs(points[:, 0])-7)/9, 0, 1)
        across = 1-across*across*(3-2*across)
        pressure = along*across
        # The existing 6 mm residual pull is retained; no separate stem is added.
        points[:, 2] *= 1-p["recoil_compression"]*pressure
        points[:, 0] *= 1+p["recoil_widening"]*pressure
    faces = []
    for a, b in zip(rings, rings[1:]):
        for j in range(n):
            k = (j+1) % n
            if len(a) == 1:
                faces.append((a[0], b[j], b[k]))
            elif len(b) == 1:
                faces.append((a[j], b[0], a[k]))
            else:
                # Explicit triangles make export topology and geometric validation comparable.
                faces.extend(((a[j], b[j], b[k]), (a[j], b[k], a[k])))
    return points, faces, np.array(directions), settings


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = MOTIF
    scene.unit_settings.system, scene.unit_settings.scale_length = "METRIC", 0.001
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.render.engine = "CYCLES"
    scene.cycles.device, scene.cycles.samples = "CPU", 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 960, 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world = bpy.data.worlds.new("Tabletop studio")
    scene.world.use_nodes = True
    background = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    background.inputs[0].default_value, background.inputs[1].default_value = (0.22, 0.24, 0.28, 1), 0.6
    target = Vector((0, -9, 17))
    camera_data = bpy.data.cameras.new("Comparison camera")
    camera = bpy.data.objects.new("Comparison camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (100, -180, 175)
    camera.rotation_euler = (target-camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type, camera_data.ortho_scale, camera_data.clip_end = "ORTHO", 155, 2000
    scene.camera = camera
    for name, position, energy, size in (("Key", (-100, -120, 220), 1800000, 120),
                                          ("Fill", (130, 30, 160), 800000, 100)):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = energy, "DISK", size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = position
        obj.rotation_euler = (target-obj.location).to_track_quat("-Z", "Y").to_euler()
    floor = make_mesh(scene, "Tabletop (preview only)",
                      [(-1000, -1000, 0), (1000, -1000, 0), (1000, 1000, 0), (-1000, 1000, 0)], [(0, 1, 2, 3)])
    floor.data.materials.append(material("Neutral tabletop", (0.19, 0.21, 0.24)))
    # Derive normal and near from actual floor geometry, marker-axis choice and camera rotation.
    a, b, c = [v.co for v in floor.data.vertices[:3]]
    up = (b-a).cross(c-a).normalized()
    axis = Vector((1, 0, 0))
    view = camera.rotation_euler.to_quaternion()@Vector((0, 0, 1))
    near = (view-up*view.dot(up)-axis*view.dot(axis)).normalized()
    return scene, axis, near, up


def bread_material():
    mat = material("Golden butter roll (preview only)", (0.64, 0.27, 0.065))
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Roughness"].default_value = 0.42
    coords = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value, noise.inputs["Detail"].default_value = 3.5, 2
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.22, (0.24, 0.065, 0.012, 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.80, (0.83, 0.43, 0.12, 1)
    links.new(coords.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs[0])
    links.new(ramp.outputs[0], shader.inputs["Base Color"])
    return mat


def hull(points):
    points = sorted(set(map(tuple, points)))
    cross = lambda o, a, b: (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    halves = []
    for order in (points, list(reversed(points))):
        half = []
        for p in order:
            while len(half) >= 2 and cross(half[-2], half[-1], p) <= 0:
                half.pop()
            half.append(p)
        halves.append(half[:-1])
    return np.array(halves[0]+halves[1])


def validate(path, frame, basis, expected_dimensions=None, core_dimensions=None):
    vertices, triangles, normals = read_stl(path)
    xyz = vertices[triangles]
    cross = np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
    area2 = np.linalg.norm(cross, axis=1)
    bm = bmesh.new()
    mesh = bpy.data.meshes.new("Export validation")
    mesh.from_pydata(vertices.tolist(), [], triangles.tolist())
    mesh.update()
    bm.from_mesh(mesh)
    remaining, components = set(bm.verts), 0
    while remaining:
        stack = [remaining.pop()]
        components += 1
        while stack:
            for edge in stack.pop().link_edges:
                for v in edge.verts:
                    if v in remaining:
                        remaining.remove(v)
                        stack.append(v)
    tree = BVHTree.FromPolygons(vertices.tolist(), triangles.tolist(), all_triangles=True, epsilon=0)
    intersections = sum(a < b and not set(triangles[a]).intersection(triangles[b]) for a, b in tree.overlap(tree))
    local = vertices@basis
    on_table = np.abs(local[:, 2]) < 1e-5
    contact_faces = np.all(on_table[triangles], axis=1)
    # Tetrahedral integration measures the solid's uniform-density center of mass.
    volumes = np.einsum("ij,ij->i", xyz[:, 0], np.cross(xyz[:, 1], xyz[:, 2]))/6
    center = np.sum(xyz.sum(axis=1)/4*volumes[:, None], axis=0)/volumes.sum()
    center_local = center@basis
    support = hull(local[on_table, :2])
    edges = np.roll(support, -1, axis=0)-support
    offsets = center_local[:2]-support
    margins = (edges[:, 0]*offsets[:, 1]-edges[:, 1]*offsets[:, 0])/np.linalg.norm(edges, axis=1)
    dims = np.ptp(local, axis=0)
    expected = {1: PARAMETERS["stone_dimensions"], 4: PARAMETERS["rod_dimensions"],
                8: PARAMETERS["stretched_dimensions"], 9: PARAMETERS["recoil_dimensions"]}.get(frame)
    if expected is None:
        expected = np.ptp(geometry(frame)[0], axis=0).tolist()
    if expected_dimensions is not None:
        expected = expected_dimensions
    report = dict(frame=frame, path=f"exports/{MOTIF}/{path.name}", sha256=digest(path),
                  local_dimensions_mm=dims.tolist(), local_bounds_mm=[local.min(axis=0).tolist(), local.max(axis=0).tolist()],
                  target_dimensions_mm=expected, dimension_tolerance_mm=0.1,
                  vertices=len(vertices), triangles=len(triangles), components=components,
                  boundary_edges=sum(e.is_boundary for e in bm.edges), nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),
                  nonmanifold_vertices=sum(not v.is_manifold for v in bm.verts),
                  inconsistent_winding_edges=sum(e.is_manifold and not e.is_contiguous for e in bm.edges),
                  degenerate_faces=int(np.count_nonzero(area2 < 1e-8)),
                  stl_normal_disagreements=int(np.count_nonzero(np.einsum("ij,ij->i", cross, normals) <= 0)),
                  nonadjacent_bvh_intersections=intersections, signed_volume_mm3=float(volumes.sum()),
                  table_contact_area_mm2=float(area2[contact_faces].sum()/2),
                  minimum_table_clearance_mm=float(local[:, 2].min()), center_of_mass_local_mm=center_local.tolist(),
                  support_hull_margin_mm=float(margins.min()))
    thicknesses = []
    settings = state(frame)
    if core_dimensions is not None:
        settings = dict(dimensions=core_dimensions, pull=0.0)
    # Sample a core along the crossbar and along the pulled tongue, avoiding tapered edges.
    sites = [(x, 0) for x in np.linspace(-0.3*settings["dimensions"][0], 0.3*settings["dimensions"][0], 9)]
    sites += [(x, y) for x in (-2, 0, 2) for y in np.linspace(0, settings["dimensions"][1]/2+settings["pull"]-4, 10)]
    for x, y in sites:
        base = Vector(basis@np.array([x, y, -1.0]))
        top = Vector(basis@np.array([x, y, 100.0]))
        lower, _, _, _ = tree.ray_cast(base, Vector(basis[:, 2]), 120)
        upper, _, _, _ = tree.ray_cast(top, -Vector(basis[:, 2]), 120)
        if lower is not None and upper is not None:
            thicknesses.append((upper-lower).dot(Vector(basis[:, 2])))
    report["core_thickness_samples"] = len(thicknesses)
    report["sampled_minimum_vertical_core_mm"] = min(thicknesses)
    dimensions_pass = np.max(np.abs(dims-expected)) < 0.1
    if frame == 8:
        # Local pressing lowers the overall roof; preserve the original width/depth envelope.
        height_range = [expected[2]*(1-PARAMETERS["tongue_compression"]), expected[2]]
        dimensions_pass = np.max(np.abs(dims[:2]-expected[:2])) < 0.1 and height_range[0] <= dims[2] <= height_range[1]+1e-5
        report["pressed_height_allowed_range_mm"] = height_range
    report["dimensions_pass"] = bool(dimensions_pass)
    report["passed"] = bool(dimensions_pass and components == 1 and volumes.sum() > 0
                            and local[:, 2].min() >= -1e-5 and report["table_contact_area_mm2"] > 20
                            and margins.min() > 1 and len(thicknesses) == len(sites)
                            and min(thicknesses) >= PARAMETERS["minimum_core"]
                            and all(report[k] == 0 for k in ("boundary_edges", "nonmanifold_edges", "nonmanifold_vertices",
                                "inconsistent_winding_edges", "degenerate_faces", "stl_normal_disagreements", "nonadjacent_bvh_intersections")))
    bm.free()
    bpy.data.meshes.remove(mesh)
    return report


def contact_sheet(paths, destination):
    command = ["magick", "montage", "-background", "#171719", "-fill", "white", "-font", "Helvetica", "-pointsize", "18"]
    for frame, path in zip(FRAMES, paths):
        command += ["-label", f"FRAME {frame:02}"+(" - PREVIEW BREAD" if frame == 10 else ""), str(path)]
    command += ["-geometry", "384x256+8+12", "-tile", "3x2", str(destination)]
    subprocess.run(command, check=True, capture_output=True, text=True)


def gif(paths, destination, delays, frame_ids=FRAMES):
    assert len(paths) == len(delays) == len(frame_ids)
    command = ["magick"]
    for path, delay in zip(paths, delays):
        command += ["-delay", str(delay), str(path)]
    command += ["-resize", "720x480", "-dither", "FloydSteinberg", "+remap", "-layers", "Optimize", "-strip", "-loop", "0", str(destination)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    actual = subprocess.check_output(["magick", "identify", "-format", "%T\\n", str(destination)], text=True)
    assert [int(t) for t in actual.split()] == delays
    assert b"NETSCAPE2.0\x03\x01\x00\x00" in destination.read_bytes()
    return dict(path=destination.name, frames=list(frame_ids), milliseconds=[10*t for t in delays],
                duration_seconds=sum(delays)/100, infinite_loop=True, abrupt_bread_replacement=True, sha256=digest(destination))


def tongue_sections(vertices, triangles, basis, near_planes=(12, 20, 28, 36, 41)):
    local = vertices@basis
    result = []
    # Intersect the exported triangles with fixed nearward planes, beyond the crossbar rim.
    for y in near_planes:
        points = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            first, second = local[triangles[:, a]], local[triangles[:, b]]
            d1, d2 = first[:, 1]-y, second[:, 1]-y
            mask = d1*d2 < 0
            t = d1[mask]/(d1[mask]-d2[mask])
            points.extend(first[mask]+(second[mask]-first[mask])*t[:, None])
        points.extend(local[np.abs(local[:, 1]-y) < 1e-7])
        points = np.array(points)
        assert len(points)
        result.append(dict(near_y_mm=y, width_mm=float(np.ptp(points[:, 0])),
                           height_mm=float(np.ptp(points[:, 2])), bottom_mm=float(points[:, 2].min())))
    return result


def pair_preview(paths, labels, destination):
    command = ["magick", "montage", "-background", "#171719", "-fill", "white", "-font", "Helvetica", "-pointsize", "18"]
    for path, label in zip(paths, labels):
        command += ["-label", label, str(path)]
    command += ["-geometry", "480x320+8+12", "-tile", "2x1", str(destination)]
    subprocess.run(command, check=True, capture_output=True, text=True)


def revise_frame08(output, no_render):
    for folder in (output/"models", output/"exports"/MOTIF, output/"previews"/MOTIF):
        folder.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    protected = [ROOT/name for name in tracked if name and name != "README.md"]
    for frame in (1, 4, 9, 10):
        if frame != 10:
            protected.append(ROOT/"exports"/MOTIF/f"frame-{frame:02}.stl")
        protected += list((ROOT/"previews"/MOTIF).glob(f"frame-{frame:02}-*.png"))
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    previous = json.loads((ROOT/"previews"/MOTIF/"validation.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"models"/f"{MOTIF}.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    retained = [scene.objects[f"{MOTIF}/frame-{f:02}"] for f in (1, 4, 9, 10)]
    fingerprints = [mesh_fingerprint(obj) for obj in retained]
    floor = scene.objects["Tabletop (preview only)"]
    a, b, c = [floor.matrix_world@v.co for v in floor.data.vertices[:3]]
    up = (b-a).cross(c-a).normalized()
    axis = Vector((1, 0, 0))
    assert abs(up.dot(axis)) < 1e-6
    view = scene.camera.rotation_euler.to_quaternion()@Vector((0, 0, 1))
    near = (view-up*view.dot(up)-axis*view.dot(axis)).normalized()
    basis = np.column_stack((axis, near, up))
    old = scene.objects[f"{MOTIF}/frame-08"]
    assert old.matrix_basis == Matrix.Identity(4)
    materials = list(old.data.materials)
    indices = [p.material_index for p in old.data.polygons]
    baseline_hash = old.get("baseline_mesh_fingerprint", mesh_fingerprint(old))
    if bpy.data.texts.get("stone_to_bread-pre-press.py") is None:
        text = bpy.data.texts.new("stone_to_bread-pre-press.py")
        text.write(bpy.data.texts["stone_to_bread.py"].as_string())
        text.use_fake_user = True
    bpy.data.objects.remove(old, do_unlink=True)
    objects = []
    for apply_press, name in ((False, "frame-08-before"), (True, "frame-08")):
        local, faces, _, settings = geometry(8, apply_press=apply_press)
        obj = make_mesh(scene, f"{MOTIF}/{name}", (local@basis.T).tolist(), faces)
        for mat in materials:
            obj.data.materials.append(mat)
        for polygon, index in zip(obj.data.polygons, indices):
            polygon.material_index, polygon.use_smooth = index, True
        obj["generator"], obj["preview_only"] = "scripts/stone_to_bread.py", False
        obj["parameters_json"] = json.dumps(settings)
        objects.append(obj)
    baseline, revised = objects
    assert mesh_fingerprint(baseline) == baseline_hash, "Unpressed source differs from original Frame 08"
    revised["baseline_mesh_fingerprint"] = baseline_hash
    revised["frame08_revision"] = "Localized pressure and spreading along the pulled tongue"
    before_vertices = np.array([v.co[:] for v in baseline.data.vertices])
    before_triangles = np.array([p.vertices[:] for p in baseline.data.polygons])
    for obj in scene.objects:
        obj.select_set(False)
    revised.hide_set(False)
    revised.select_set(True)
    bpy.context.view_layer.objects.active = revised
    path = output/"exports"/MOTIF/"frame-08.stl"
    bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True, global_scale=1,
                          use_scene_unit=False, apply_modifiers=True, forward_axis="Y", up_axis="Z", ascii_format=False)
    result = validate(path, 8, basis)
    assert result["passed"], json.dumps(result)
    after_vertices, after_triangles, _ = read_stl(path)
    before_sections = tongue_sections(before_vertices, before_triangles, basis)
    after_sections = tongue_sections(after_vertices, after_triangles, basis)
    comparisons = [dict(near_y_mm=a["near_y_mm"], before=a, after=b,
                        height_ratio=b["height_mm"]/a["height_mm"], width_ratio=b["width_mm"]/a["width_mm"])
                   for a, b in zip(before_sections, after_sections)]
    assert all(0.65 <= c["height_ratio"] <= 0.80 and 1.10 <= c["width_ratio"] <= 1.25 for c in comparisons)
    old_local = before_vertices@basis
    new_coordinates = np.array([v.co[:] for v in revised.data.vertices])
    unchanged = (np.abs(old_local[:, 0]) >= 22) | (old_local[:, 1] <= PARAMETERS["press_start_y"])
    assert np.array_equal(before_vertices[unchanged], new_coordinates[unchanged])
    assert np.array_equal((before_vertices@basis)[:, 1], (new_coordinates@basis)[:, 1])
    report = dict(status="Revised Frame 08 awaiting visual review; Frame 09 unchanged",
                  revised_frame08=result, sections=comparisons, baseline_mesh_fingerprint=baseline_hash,
                  revised_mesh_fingerprint=mesh_fingerprint(revised), retained_frame_mesh_fingerprints=dict(zip((1, 4, 9, 10), fingerprints)),
                  unchanged_far_rim_and_lateral_ends=True, near_coordinates_identical=True,
                  parameters=PARAMETERS, local_axes_world=dict(X=list(axis), Y_near=list(near), Z=list(up)))
    if not no_render:
        original = (scene.camera.location.copy(), scene.camera.rotation_euler.copy())
        all_objects = retained+objects
        for view_name in ("oblique", "top", "side"):
            if view_name == "top":
                scene.camera.location = Vector((0, -9, 0))+up*260
                scene.camera.rotation_euler = Matrix((axis, up.cross(axis), up)).transposed().to_euler()
            elif view_name == "side":
                # Along X, the image shows tongue depth horizontally and vertical compression.
                scene.camera.location = -axis*260+near*10+up*7.5
                scene.camera.rotation_euler = Matrix((near, up, -axis)).transposed().to_euler()
            fixed = rig_settings(scene)
            paths = []
            for obj, stem in ((baseline, "frame-08-before"), (revised, "frame-08")):
                for other in all_objects:
                    other.hide_render = other != obj
                    other.hide_set(other != obj)
                assert rig_settings(scene) == fixed
                image = output/"previews"/MOTIF/f"{stem}-{view_name}.png"
                scene.render.filepath = str(image)
                bpy.ops.render.render(write_still=True)
                paths.append(image)
            reference = ROOT/"previews"/MOTIF/f"frame-04-{view_name}.png"
            if view_name == "side":
                for other in all_objects:
                    other.hide_render = other != retained[1]
                reference = output/"previews"/MOTIF/"frame-04-side.png"
                scene.render.filepath = str(reference)
                bpy.ops.render.render(write_still=True)
            pair_preview(paths, ["FRAME 08 - BEFORE", "FRAME 08 - PRESSED"], output/"previews"/MOTIF/f"comparison-08-before-after-{view_name}.png")
            pair_preview([reference, paths[1]], ["FRAME 04", "FRAME 08 - PRESSED"], output/"previews"/MOTIF/f"comparison-04-08-{view_name}.png")
            report[f"{view_name}_rig"] = fixed
            scene.camera.location, scene.camera.rotation_euler = original
        # Replace only the Frame 08 image in the existing five-state comparisons and timing.
        for view_name in ("oblique", "top"):
            paths = [(output if f == 8 else ROOT)/"previews"/MOTIF/f"frame-{f:02}-{view_name}.png" for f in FRAMES]
            contact_sheet(paths, output/"previews"/MOTIF/("contact-sheet.png" if view_name == "oblique" else "contact-sheet-top.png"))
            if view_name == "oblique":
                report["exploratory_gif"] = gif(paths, output/"previews"/MOTIF/"keyframes.gif", [60]*5)
                report["quick_release_gif"] = gif(paths, output/"previews"/MOTIF/"quick-release.gif", [60, 60, 80, 8, 100])
    bpy.data.objects.remove(baseline, do_unlink=True)
    assert fingerprints == [mesh_fingerprint(obj) for obj in retained]
    for obj in retained+[revised]:
        obj.hide_set(obj != retained[0])
        obj.hide_render = obj != retained[0]
    bpy.context.view_layer.objects.active = retained[0]
    text = bpy.data.texts["stone_to_bread.py"]
    text.clear()
    text.write(Path(__file__).read_text())
    scene["parameters_json"] = json.dumps(PARAMETERS)
    scene["frame08_press_status"] = report["status"]
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output/"models"/f"{MOTIF}.blend"))
    assert hashes == {str(p.relative_to(ROOT)): digest(p) for p in protected}
    report["protected_assets_unchanged"] = True
    report["protected_sha256"] = hashes
    (output/"previews"/MOTIF/"frame-08-press-validation.json").write_text(json.dumps(report, indent=2)+"\n")
    if output == ROOT:
        previous["models"] = [result if r["frame"] == 8 else r for r in previous["models"]]
        previous["mesh_fingerprints"]["8"] = mesh_fingerprint(revised)
        previous["parameters"] = PARAMETERS
        previous["frame08_revision"] = report["status"]
        if "reproducibility" in previous:
            previous["initial_prototype_reproducibility"] = previous.pop("reproducibility")
        for key in ("exploratory_gif", "quick_release_gif"):
            if key in report:
                previous[key] = report[key]
        (output/"previews"/MOTIF/"validation.json").write_text(json.dumps(previous, indent=2)+"\n")
    print("FRAME08_PRESS", json.dumps({k: v for k, v in report.items() if k != "protected_sha256"}))


def revise_frame09(output, no_render):
    for folder in (output/"models", output/"exports"/MOTIF, output/"previews"/MOTIF):
        folder.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    protected = [ROOT/name for name in tracked if name and name != "README.md"]
    for frame in (1, 4, 8, 10):
        if frame != 10:
            protected.append(ROOT/"exports"/MOTIF/f"frame-{frame:02}.stl")
        protected += list((ROOT/"previews"/MOTIF).glob(f"frame-{frame:02}*.png"))
    protected += list((ROOT/"previews"/MOTIF).glob("comparison-04-08*.png"))
    protected += list((ROOT/"previews"/MOTIF).glob("comparison-08-before-after*.png"))
    protected.append(ROOT/"previews"/MOTIF/"frame-08-press-validation.json")
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    previous = json.loads((ROOT/"previews"/MOTIF/"validation.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"models"/f"{MOTIF}.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    retained_ids = (1, 4, 8, 10)
    retained = [scene.objects[f"{MOTIF}/frame-{f:02}"] for f in retained_ids]
    fingerprints = dict(zip(retained_ids, [mesh_fingerprint(o) for o in retained]))
    floor = scene.objects["Tabletop (preview only)"]
    a, b, c = [floor.matrix_world@v.co for v in floor.data.vertices[:3]]
    up = (b-a).cross(c-a).normalized()
    axis = Vector((1, 0, 0))
    view = scene.camera.rotation_euler.to_quaternion()@Vector((0, 0, 1))
    near = (view-up*view.dot(up)-axis*view.dot(axis)).normalized()
    basis = np.column_stack((axis, near, up))
    # Verify that changing the shared definition leaves all retained source coordinates exact.
    for frame, obj in zip(retained_ids, retained):
        expected = np.asarray(geometry(frame)[0]@basis.T, dtype=np.float32)
        actual = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float32)
        assert np.array_equal(expected, actual), f"Approved Frame {frame:02} source changed"
    old = scene.objects[f"{MOTIF}/frame-09"]
    assert old.matrix_basis == Matrix.Identity(4)
    materials = list(old.data.materials)
    indices = [p.material_index for p in old.data.polygons]
    baseline_hash = old.get("recoil_baseline_mesh_fingerprint", mesh_fingerprint(old))
    if bpy.data.texts.get("stone_to_bread-pre-recoil.py") is None:
        text = bpy.data.texts.new("stone_to_bread-pre-recoil.py")
        text.write(bpy.data.texts["stone_to_bread.py"].as_string())
        text.use_fake_user = True
    bpy.data.objects.remove(old, do_unlink=True)
    objects = []
    for apply_press, name in ((False, "frame-09-before"), (True, "frame-09")):
        local, faces, _, settings = geometry(9, apply_press=apply_press)
        obj = make_mesh(scene, f"{MOTIF}/{name}", (local@basis.T).tolist(), faces)
        for mat in materials:
            obj.data.materials.append(mat)
        for polygon, index in zip(obj.data.polygons, indices):
            polygon.material_index, polygon.use_smooth = index, True
        obj["generator"], obj["preview_only"] = "scripts/stone_to_bread.py", False
        obj["parameters_json"] = json.dumps(settings)
        objects.append(obj)
    baseline, revised = objects
    assert mesh_fingerprint(baseline) == baseline_hash
    revised["recoil_baseline_mesh_fingerprint"] = baseline_hash
    revised["frame09_revision"] = "Compact recoil with a short flattened nearward remnant"
    before_vertices = np.array([v.co[:] for v in baseline.data.vertices])
    before_triangles = np.array([p.vertices[:] for p in baseline.data.polygons])
    for obj in scene.objects:
        obj.select_set(False)
    revised.hide_set(False)
    revised.select_set(True)
    bpy.context.view_layer.objects.active = revised
    path = output/"exports"/MOTIF/"frame-09.stl"
    bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True, global_scale=1,
                          use_scene_unit=False, apply_modifiers=True, forward_axis="Y", up_axis="Z", ascii_format=False)
    result = validate(path, 9, basis)
    assert result["passed"], json.dumps(result)
    vertices, triangles, _ = read_stl(path)
    planes = (8, 12, 15, 17)
    before_sections = tongue_sections(before_vertices, before_triangles, basis, planes)
    after_sections = tongue_sections(vertices, triangles, basis, planes)
    comparisons = [dict(near_y_mm=a["near_y_mm"], before=a, after=b,
                        height_ratio=b["height_mm"]/a["height_mm"], width_ratio=b["width_mm"]/a["width_mm"])
                   for a, b in zip(before_sections, after_sections)]
    assert all(c["height_ratio"] < 1 and c["width_ratio"] > 1 for c in comparisons)
    report = dict(status="Frame 09 revised; awaiting visual review, not finally approved",
                  approved_frame08_preserved=True, revised_frame09=result, sections=comparisons,
                  baseline_mesh_fingerprint=baseline_hash, revised_mesh_fingerprint=mesh_fingerprint(revised),
                  retained_frame_mesh_fingerprints=fingerprints, retained_source_coordinates_identical=True,
                  parameters=PARAMETERS, local_axes_world=dict(X=list(axis), Y_near=list(near), Z=list(up)))
    if not no_render:
        original = (scene.camera.location.copy(), scene.camera.rotation_euler.copy())
        all_objects = retained+objects
        for view_name in ("oblique", "top", "side"):
            if view_name == "top":
                scene.camera.location = Vector((0, -9, 0))+up*260
                scene.camera.rotation_euler = Matrix((axis, up.cross(axis), up)).transposed().to_euler()
            elif view_name == "side":
                scene.camera.location = -axis*260+near*10+up*7.5
                scene.camera.rotation_euler = Matrix((near, up, -axis)).transposed().to_euler()
            fixed = rig_settings(scene)
            paths = []
            for obj, stem in ((baseline, "frame-09-before"), (revised, "frame-09")):
                for other in all_objects:
                    other.hide_render = other != obj
                    other.hide_set(other != obj)
                assert rig_settings(scene) == fixed
                path = output/"previews"/MOTIF/f"{stem}-{view_name}.png"
                scene.render.filepath = str(path)
                bpy.ops.render.render(write_still=True)
                paths.append(path)
            reference = ROOT/"previews"/MOTIF/f"frame-08-{view_name}.png"
            pair_preview(paths, ["FRAME 09 - BEFORE", "FRAME 09 - RECOIL"], output/"previews"/MOTIF/f"comparison-09-before-after-{view_name}.png")
            pair_preview([reference, paths[1]], ["FRAME 08 - APPROVED", "FRAME 09 - RECOIL"], output/"previews"/MOTIF/f"comparison-08-09-{view_name}.png")
            report[f"{view_name}_rig"] = fixed
            scene.camera.location, scene.camera.rotation_euler = original
        # Keep all sequence previews current by replacing only the Frame 09 still image.
        for view_name in ("oblique", "top"):
            paths = [(output if f == 9 else ROOT)/"previews"/MOTIF/f"frame-{f:02}-{view_name}.png" for f in FRAMES]
            contact_sheet(paths, output/"previews"/MOTIF/("contact-sheet.png" if view_name == "oblique" else "contact-sheet-top.png"))
            if view_name == "oblique":
                report["exploratory_gif"] = gif(paths, output/"previews"/MOTIF/"keyframes.gif", [60]*5)
                report["quick_release_gif"] = gif(paths, output/"previews"/MOTIF/"quick-release.gif", [60, 60, 80, 8, 100])
                transition = [paths[2], paths[3], paths[4]]
                report["transition_standard"] = gif(transition, output/"previews"/MOTIF/"transition-08-09-10-standard.gif", [50, 25, 70], (8, 9, 10))
                report["transition_quick"] = gif(transition, output/"previews"/MOTIF/"transition-08-09-10-quick.gif", [50, 8, 70], (8, 9, 10))
    bpy.data.objects.remove(baseline, do_unlink=True)
    assert fingerprints == dict(zip(retained_ids, [mesh_fingerprint(o) for o in retained]))
    for obj in retained+[revised]:
        obj.hide_set(obj != retained[0])
        obj.hide_render = obj != retained[0]
    bpy.context.view_layer.objects.active = retained[0]
    text = bpy.data.texts["stone_to_bread.py"]
    text.clear()
    text.write(Path(__file__).read_text())
    scene["parameters_json"] = json.dumps(PARAMETERS)
    scene["frame08_press_status"] = "Visually approved; pressed geometry preserved"
    scene["frame09_recoil_status"] = report["status"]
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output/"models"/f"{MOTIF}.blend"))
    assert hashes == {str(p.relative_to(ROOT)): digest(p) for p in protected}
    report["protected_assets_unchanged"] = True
    report["protected_sha256"] = hashes
    (output/"previews"/MOTIF/"frame-09-recoil-validation.json").write_text(json.dumps(report, indent=2)+"\n")
    if output == ROOT:
        previous["models"] = [result if r["frame"] == 9 else r for r in previous["models"]]
        previous["mesh_fingerprints"]["9"] = mesh_fingerprint(revised)
        previous["parameters"] = PARAMETERS
        previous["frame08_approval"] = dict(status="Visually approved", mesh_fingerprint=fingerprints[8])
        previous["frame09_revision"] = report["status"]
        if "reproducibility" in previous:
            previous["prior_frame08_reproducibility"] = previous.pop("reproducibility")
        for key in ("exploratory_gif", "quick_release_gif", "transition_standard", "transition_quick"):
            if key in report:
                previous[key] = report[key]
        (output/"previews"/MOTIF/"validation.json").write_text(json.dumps(previous, indent=2)+"\n")
    print("FRAME09_RECOIL", json.dumps({k: v for k, v in report.items() if k != "protected_sha256"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--frame08-only", action="store_true")
    parser.add_argument("--frame09-only", action="store_true")
    parser.add_argument("--intermediates-only", action="store_true")
    parser.add_argument("--rolling-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    output = args.output_root.resolve()
    assert bpy.app.version[:2] == (4, 5)
    if args.intermediates_only:
        from stone_to_bread_sequence import generate_intermediates
        generate_intermediates(output, args.no_render)
        return
    if args.rolling_only:
        from stone_to_bread_sequence import generate_rolling
        generate_rolling(output)
        return
    if args.frame09_only:
        revise_frame09(output, args.no_render)
        return
    if args.frame08_only:
        revise_frame08(output, args.no_render)
        return
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    protected = {name: digest(ROOT/name) for name in tracked if name and name != "README.md"}
    for folder in (output/"models", output/"exports"/MOTIF, output/"previews"/MOTIF):
        folder.mkdir(parents=True, exist_ok=True)
    scene, axis, near, up = setup_scene()
    basis = np.column_stack((axis, near, up))
    assert abs(np.linalg.det(basis)) > 0.999
    stone = material("Stone - shared across all physical states", (0.27, 0.29, 0.265))
    patch = material("Subtle stone mineral patch", (0.235, 0.25, 0.225))
    for mat in (stone, patch):
        next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Roughness"].default_value = 0.85
    bread = bread_material()
    objects, results = [], []
    for frame in FRAMES:
        local, faces, directions, settings = geometry(frame)
        obj = make_mesh(scene, f"{MOTIF}/frame-{frame:02}", (local@basis.T).tolist(), faces)
        obj["generator"], obj["preview_only"] = "scripts/stone_to_bread.py", frame == 10
        obj["parameters_json"] = json.dumps(settings)
        obj.data.materials.append(bread if frame == 10 else stone)
        if frame != 10:
            obj.data.materials.append(patch)
        for face in obj.data.polygons:
            face.use_smooth = True
            if frame != 10:
                # A broad material landmark rotates with the same material coordinates as relief.
                landmark = directions[list(face.vertices)].mean(axis=0)
                face.material_index = int(landmark[0]+0.6*landmark[1]-0.5*landmark[2] > 0.70)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        if frame != 10:
            path = output/"exports"/MOTIF/f"frame-{frame:02}.stl"
            bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True, global_scale=1,
                                  use_scene_unit=False, apply_modifiers=True, forward_axis="Y", up_axis="Z", ascii_format=False)
            result = validate(path, frame, basis)
            results.append(result)
            assert result["passed"], json.dumps(result)
        obj.hide_set(True)
        obj.hide_render = True
        objects.append(obj)
    report = dict(status="Initial prototype; awaiting visual approval", blender=bpy.app.version_string,
                  generated_frames=list(FRAMES), printable_frames=[1, 4, 8, 9], bread_exported=False,
                  parameters=PARAMETERS, models=results, local_axes_world=dict(X=list(axis), Y_near=list(near), Z=list(up)),
                  mesh_fingerprints={str(f): mesh_fingerprint(obj) for f, obj in zip(FRAMES, objects)},
                  tabletop_world_z_mm=0, bread_local_dimensions_mm=np.ptp(geometry(10)[0], axis=0).tolist(),
                  unverified=["Self intersections involving shared-vertex/adjacent triangles are excluded from BVH checks.",
                              "Vertical core samples are not a global local-normal minimum-feature-thickness check.",
                              "Static uniform-density support checks do not verify friction, handling or physical stability.",
                              "Slicing, supports, nozzle/layer suitability, strength, warping and physical printing.",
                              "Perceptual rolling/interpolation across ungenerated frames and matching the real bread.",
                              "No volume conservation, elasticity or physical deformation simulation."])
    if not args.no_render:
        original = (scene.camera.location.copy(), scene.camera.rotation_euler.copy())
        for view in ("oblique", "top"):
            if view == "top":
                center = Vector((0, -9, 0))
                scene.camera.location = center+up*260
                scene.camera.rotation_euler = Matrix((axis, up.cross(axis), up)).transposed().to_euler()
            fixed = rig_settings(scene)
            paths = []
            for frame, obj in zip(FRAMES, objects):
                for other in objects:
                    other.hide_render = other != obj
                    other.hide_set(other != obj)
                assert rig_settings(scene) == fixed
                path = output/"previews"/MOTIF/f"frame-{frame:02}-{view}.png"
                scene.render.filepath = str(path)
                bpy.ops.render.render(write_still=True)
                paths.append(path)
            contact_sheet(paths, output/"previews"/MOTIF/("contact-sheet.png" if view == "oblique" else "contact-sheet-top.png"))
            report[f"{view}_rig"] = fixed
            if view == "oblique":
                report["exploratory_gif"] = gif(paths, output/"previews"/MOTIF/"keyframes.gif", [60]*5)
                report["quick_release_gif"] = gif(paths, output/"previews"/MOTIF/"quick-release.gif", [60, 60, 80, 8, 100])
            scene.camera.location, scene.camera.rotation_euler = original
    for obj in objects:
        obj.hide_set(obj != objects[0])
        obj.hide_render = obj != objects[0]
    bpy.context.view_layer.objects.active = objects[0]
    scene["local_axes_world_json"] = json.dumps(report["local_axes_world"])
    scene["parameters_json"] = json.dumps(PARAMETERS)
    scene["generated_frames"] = json.dumps(FRAMES)
    scene["preview_only_frame"] = 10
    text = bpy.data.texts.new("stone_to_bread.py")
    text.write(Path(__file__).read_text())
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output/"models"/f"{MOTIF}.blend"))
    assert protected == {name: digest(ROOT/name) for name in protected}, "Existing approved assets changed"
    assert sorted(p.name for p in (output/"exports"/MOTIF).glob("*.stl")) == [f"frame-{f:02}.stl" for f in FRAMES if f != 10]
    report["existing_tracked_files_unchanged"] = True
    report["protected_sha256"] = protected
    (output/"previews"/MOTIF/"validation.json").write_text(json.dumps(report, indent=2)+"\n")
    print("STONE_TO_BREAD", json.dumps({k: v for k, v in report.items() if k != "protected_sha256"}))


if __name__ == "__main__":
    main()
