"""Procedural props; run with Blender 4.5's bundled Python, never ordinary Python.

/Applications/Blender.app/Contents/MacOS/Blender --background --python scripts/generate.py
Append -- --all-frames for the approved seven-stage set; default remains endpoints only.
Other options: --motif pen|stones|cup, --no-render, --validate-only, --output-root PATH.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ENDPOINTS = ((1, 0.0), (7, 1.0))
ALL_FRAMES = tuple((frame, (frame-1)/6) for frame in range(1, 8))
PEN = dict(length=140.8, cap_diameter=21.8, barrel_diameter=18.0,
           crush_length=40.0, flat_length=14.0, compressed_height=5.2,
           near_expansion=1.8, far_expansion=0.2, near_top_taper=0.20,
           centerline_displacement=6.0, compression_slope=2.2, deformation_intensity=1.0,
           contact_phase=0.20, minimum_web=2.5, fold_amplitude=0.18,
           angular_segments=128, axial_step=0.5)
STONES = dict(width=80.0, backing=2.0, coarse_pitch=8.0, fine_pitch=2.5,
              relief=1.6, fine_relief=1.2, grid_step=0.25, seed=42017, gap=0.30,
              packing_candidates=64, rounding_power=5.0, irregularity=0.045)
CUP = dict(height=80.0, diameter=80.0, thin_wall=2.0, thick_wall=8.0,
           bottom=2.4, rounding=0.25, angular_segments=256, round_segments=6)


def make_mesh(scene, name, vertices, faces):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    if mesh.validate():
        raise RuntimeError(f"Generator produced invalid mesh: {name}")
    # Orient the single closed shell consistently before export or shading.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if bm.calc_volume(signed=True) < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    obj["generator"] = "scripts/generate.py"
    obj["units"] = "mm; one mesh coordinate equals one millimeter"
    return obj


def pen_view_normal(scene):
    # These saved cameras have no parents/constraints; stored Euler rotation avoids stale
    # matrix_world caches immediately after library loading in a background process.
    assert scene.camera.parent is None and not scene.camera.constraints
    toward_camera = scene.camera.rotation_euler.to_quaternion() @ Vector((0, 0, 1))
    axis = Vector((1, 0, 0))
    # Remove the component parallel to the actual marker's verified X axis.
    return (toward_camera-axis*toward_camera.dot(axis)).normalized()


def pen_table_basis(scene):
    marker = next((o for o in scene.objects if o.name.startswith("pen/frame-01")), None)
    floor = next(o for o in scene.objects if o.name.startswith("Preview floor"))
    assert floor.parent is None and scene.camera.parent is None
    assert not floor.constraints and not scene.camera.constraints
    assert marker is None or (marker.parent is None and not marker.constraints)
    # Compose stored transforms explicitly because library-loaded matrix caches may be stale.
    matrix = Matrix.LocRotScale(marker.location, marker.rotation_euler, marker.scale) if marker else Matrix.Identity(4)
    floor_matrix = Matrix.LocRotScale(floor.location, floor.rotation_euler, floor.scale)
    table = [floor_matrix@v.co for v in floor.data.vertices]
    up = (table[1]-table[0]).cross(table[2]-table[0]).normalized()
    center = matrix@Vector((0, 0, PEN["cap_diameter"]/2))
    if (center-table[0]).dot(up) < 0:
        up = -up
    assert all(abs((point-table[0]).dot(up)) < 1e-5 for point in table)
    # Choose the mesh's longest bounding-box axis, then transform it into the scene.
    # A fresh build has no reference object yet; its source profile explicitly runs along X.
    axis_index = int(np.argmax(np.ptp(np.array([v.co[:] for v in marker.data.vertices]), axis=0))) if marker else 0
    assert axis_index == 0, "The marker generator's longitudinal coordinate must be local X"
    axis = (matrix.to_3x3()@Vector((1, 0, 0))).normalized()
    assert abs(axis.dot(up)) < 1e-6, "Marker is not parallel to the tabletop"
    view = scene.camera.rotation_euler.to_quaternion()@Vector((0, 0, 1))
    # Only the horizontal component perpendicular to the marker defines near/far.
    near = (view-up*view.dot(up)-axis*view.dot(axis)).normalized()
    return dict(axis=axis, near=near, up=up, table_origin=table[0], center=center,
                matrix=matrix, inverse=matrix.inverted())


def pen_center_shift(x, t):
    # A compact cubic bow has zero value, slope and curvature at the unchanged end regions.
    support = max(0.0, 1-(2*x/PEN["crush_length"])**2)
    return PEN["centerline_displacement"]*t*PEN["deformation_intensity"]*support**3


def pen_geometry(t, basis):
    p = PEN
    t *= p["deformation_intensity"]
    # Axial profile gives a rounded closed cap, shallow cap seam and rounded tail.
    profile = [(-70.4, 8.8), (-70.2, 9.8), (-69.5, 10.6), (-68.8, 10.9),
               (-34.0, 10.9), (-33.8, 10.5), (-33.4, 10.5), (-33.2, 10.9),
               (-32.5, 10.9), (-32.0, 9.0), (67.8, 9.0), (69.0, 8.8),
               (70.0, 8.2), (70.4, 7.5)]
    # Scale the reference detailing with the exposed overall and barrel parameters.
    cap_radius = p["cap_diameter"]/2
    profile = [(x*p["length"]/140.8,
                radius*(cap_radius/10.9 if x < -32 else p["barrel_diameter"]/18))
               for x, radius in profile]
    # Include exact profile transitions and the center in a common endpoint topology.
    xs = sorted(set(np.linspace(-p["length"]/2, p["length"]/2,
                                math.ceil(p["length"]/p["axial_step"])+1).tolist()
                    + [x for x, _ in profile] + [0.0]))
    vertices, faces = [], []
    n = p["angular_segments"]
    near, up = basis["near"], basis["up"]
    original_bottom = (basis["center"]-basis["table_origin"]).dot(up)-p["barrel_diameter"]/2
    contact = min(1.0, t/p["contact_phase"])
    contact = contact*contact*(3-2*contact)
    for x in xs:
        radius = float(np.interp(x, [a for a, _ in profile], [b for _, b in profile]))
        # An axial plateau and compact smooth transition deform complete cross sections.
        u = max(0.0, min(1.0, (abs(x)-p["flat_length"]/2)/
                         ((p["crush_length"]-p["flat_length"])/2)))
        envelope = 1-u*u*(3-2*u)
        weight = t*envelope
        for j in range(n):
            a = 2 * math.pi * j / n
            # Preserve the original uncrushed mesh arithmetic, cap, ends and axial positions.
            y = radius * math.cos(a)
            z = (cap_radius-radius) + 2*radius*(math.sin(a)+1)/2
            if weight == 0:
                # This branch preserves Frame 01 and every undeformed cap/end vertex exactly.
                vertices.append((x, y, z))
                continue
            point = basis["matrix"]@Vector((x, y, z))
            relative = point-basis["center"]
            q, v = relative.dot(near), relative.dot(up)
            expansion = p["near_expansion"] if q >= 0 else p["far_expansion"]
            spread = weight*expansion*q/radius
            # Map the lower arc to an actual planar sole and the upper arc to a low roof.
            roof = max(0.0, min(1.0, (v/radius+0.55)/1.10))
            roof = roof*roof*(3-2*roof)
            # Vary the roof height across the section while leaving the supported sole level.
            target_height = (p["compressed_height"]-p["compression_slope"]*q/radius)*roof
            # A gently thinner near lip makes the flattened section visibly asymmetric.
            target_height *= 1-p["near_top_taper"]*max(0, q/radius)**2
            original_height = (point-basis["table_origin"]).dot(up)
            # Establish contact early, then preserve it while flattening; all heights stay >=0.
            height = original_bottom*(1-contact*envelope)
            height += (1-weight)*(original_height-original_bottom)+weight*target_height
            pleat = p["fold_amplitude"]*t*math.sin(2*math.pi*u)*math.sin(math.pi*u)**2
            height += pleat*max(0, v/radius)**2
            # Move complete sections along the table; longitudinal coordinates never change.
            shift = pen_center_shift(x, t/p["deformation_intensity"]) if p["deformation_intensity"] else 0
            displaced = point+near*(spread+shift)+up*(height-original_height)
            local = basis["inverse"]@displaced
            vertices.append((x, local.y, local.z))
    # Join equal-index rings; the ends close with planar fans at exactly +/-70.4 mm.
    for i in range(len(xs) - 1):
        for j in range(n):
            k = (j + 1) % n
            faces.append((i*n+j, i*n+k, (i+1)*n+k, (i+1)*n+j))
    for ring in (0, len(xs) - 1):
        center = len(vertices)
        vertices.append((xs[ring], 0, cap_radius))
        for j in range(n):
            faces.append((center, ring*n+j, ring*n+(j+1) % n))
    return vertices, faces


def clip_polygon(polygon, normal, limit):
    result = []
    # Clip a convex cell by one Voronoi bisector, preserving counterclockwise winding.
    for a, b in zip(polygon, polygon[1:]+polygon[:1]):
        da, db = np.dot(a, normal)-limit, np.dot(b, normal)-limit
        if da <= 1e-10:
            result.append(a)
        if (da < 0 < db) or (db < 0 < da):
            result.append(a+(b-a)*da/(da-db))
    return result


def cell_area_center(polygon):
    a = np.asarray(polygon)
    b = np.roll(a, -1, axis=0)
    cross = a[:, 0]*b[:, 1]-b[:, 0]*a[:, 1]
    area = float(cross.sum()/2)
    center = ((a+b)*cross[:, None]).sum(axis=0)/(6*area)
    return area, center


def pebble_sites(polygon, count, rng):
    a = np.asarray(polygon)
    low, high = a.min(axis=0), a.max(axis=0)
    edges = np.roll(a, -1, axis=0)-a
    sites = []
    # Best-candidate sampling spreads sites without imposing rows or columns.
    for _ in range(count):
        candidates = []
        while len(candidates) < STONES["packing_candidates"]:
            point = np.array([rng.uniform(low[k], high[k]) for k in range(2)])
            offsets = point-a
            if np.all(edges[:, 0]*offsets[:, 1]-edges[:, 1]*offsets[:, 0] >= -1e-9):
                candidates.append(point)
        if sites:
            distances = np.sum((np.array(candidates)[:, None, :]-np.array(sites))**2, axis=2)
            sites.append(candidates[int(np.argmax(distances.min(axis=1)))])
        else:
            sites.append(candidates[0])
    return sites


def partition_pebbles(polygon, count, seed, parent):
    sites = pebble_sites(polygon, count, random.Random(seed))
    # Two centroid relaxation passes reduce sliver-shaped grains without introducing a grid.
    for iteration in range(3):
        cells = []
        for i, site in enumerate(sites):
            cell = polygon[:]
            # Child polygons are clipped to the parent, so ancestral boundaries never move.
            for j, other in enumerate(sites):
                if i != j:
                    cell = clip_polygon(cell, other-site, (np.dot(other, other)-np.dot(site, site))/2)
            area, center = cell_area_center(cell)
            cells.append(dict(polygon=cell, center=center, area=area,
                              seed=seed*31+i+1, parent=parent, identity=f"{parent}/{i}"))
        if iteration < 2:
            sites = [node["center"] for node in cells]
    return cells


def stone_hierarchy():
    p = STONES
    half = p["width"]/2
    square = [np.array(v, dtype=float) for v in [(-half, -half), (half, -half),
                                               (half, half), (-half, half)]]
    roots = partition_pebbles(square, round((p["width"]/p["coarse_pitch"])**2), p["seed"], "root")
    levels = [roots]
    # Two persistent subdivision levels approach the requested fine-grain area.
    for area_target in (p["coarse_pitch"]*p["fine_pitch"], p["fine_pitch"]**2):
        children = []
        for parent in levels[-1]:
            count = max(1, round(parent["area"]/area_target))
            if count == 1:
                # Already-small grains retain their exact shape instead of being split again.
                children.append(dict(parent, parent=parent["identity"], identity=parent["identity"]+"/0"))
            else:
                children.extend(partition_pebbles(parent["polygon"], count,
                                                   parent["seed"], parent["identity"]))
        levels.append(children)
    return levels


def pebble_relief(nodes, axis, amplitude):
    p = STONES
    relief = np.zeros((len(axis), len(axis)))
    for node in nodes:
        polygon = np.asarray(node["polygon"])
        # Rasterize only this cell's bounding box, at the same mesh coordinates for all t.
        low, high = polygon.min(axis=0), polygon.max(axis=0)
        ix = np.flatnonzero((axis >= low[0]) & (axis <= high[0]))
        iy = np.flatnonzero((axis >= low[1]) & (axis <= high[1]))
        if not len(ix) or not len(iy):
            continue
        x, y = np.meshgrid(axis[ix], axis[iy])
        dx, dy = x-node["center"][0], y-node["center"][1]
        power_sum = np.zeros_like(x)
        polygon_distance = np.zeros_like(x)
        # A smooth positive power norm rounds the convex cell into a varied pebble outline.
        for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
            edge = b-a
            normal = np.array([edge[1], -edge[0]])/np.linalg.norm(edge)
            clearance = np.dot(a-node["center"], normal)-p["gap"]/2
            scaled = np.maximum(0, (dx*normal[0]+dy*normal[1])/max(clearance, 0.05))
            power_sum += scaled**p["rounding_power"]
            polygon_distance = np.maximum(polygon_distance, scaled)
        rng = random.Random(node["seed"])
        phase = rng.uniform(0, 2*math.pi)
        angle = np.arctan2(dy, dx)
        # Modest lobes break perfect ellipses without adding needle-like detail.
        wobble = 1+p["irregularity"]*(1+np.sin(3*angle+phase))
        wobble += 0.02*(1+np.cos(5*angle-phase))
        radius = np.maximum(polygon_distance, power_sum**(1/p["rounding_power"])*wobble)
        height = amplitude*rng.uniform(0.88, 1.0)*np.maximum(0, 1-radius*radius)**0.65
        relief[np.ix_(iy, ix)] = np.maximum(relief[np.ix_(iy, ix)], height)
    return relief


def stones_geometry(t, hierarchy=None):
    p = STONES
    count = round(p["width"] / p["grid_step"])
    axis = np.linspace(-p["width"]/2, p["width"]/2, count + 1)
    x, y = np.meshgrid(axis, axis)
    hierarchy = hierarchy if hierarchy is not None else stone_hierarchy()
    level = min(int(t*2), 1)
    blend = t*2-level
    blend = blend*blend*(3-2*blend)
    # Deepen inherited child grooves continuously; no sites migrate or get re-randomized.
    amplitudes = np.linspace(p["relief"], p["fine_relief"], 3)
    relief = pebble_relief(hierarchy[level], axis, amplitudes[level])*(1-blend)
    relief += pebble_relief(hierarchy[level+1], axis, amplitudes[level+1])*blend
    edge_distance = np.minimum(p["width"]/2-np.abs(x), p["width"]/2-np.abs(y))
    edge_fade = np.clip(edge_distance / 0.6, 0, 1)
    z = p["backing"] + relief * edge_fade**2 * (3-2*edge_fade)
    vertices = np.column_stack((x.ravel(), y.ravel(), z.ravel())).tolist()
    faces = []
    stride = count + 1
    # Alternating diagonals avoid a common diagonal grain in the heightfield.
    for j in range(count):
        for i in range(count):
            a = j*stride+i
            b, c, d = a+1, a+stride+1, a+stride
            if (i+j) % 2:
                faces.extend(((a, b, d), (b, c, d)))
            else:
                faces.extend(((a, b, c), (a, c, d)))
    # A single perimeter and bottom fan close the sheet without intersecting pebble solids.
    perimeter = (list(range(stride))
                 + [j*stride+count for j in range(1, stride)]
                 + [count*stride+i for i in range(count-1, -1, -1)]
                 + [j*stride for j in range(count-1, 0, -1)])
    bottom_start = len(vertices)
    vertices.extend([(vertices[k][0], vertices[k][1], 0) for k in perimeter])
    center = len(vertices)
    vertices.append((0, 0, 0))
    for i, a in enumerate(perimeter):
        j = (i+1) % len(perimeter)
        faces.extend(((a, perimeter[j], bottom_start+j, bottom_start+i),
                      (center, bottom_start+i, bottom_start+j)))
    return vertices, faces


def cup_geometry(t):
    p = CUP
    outer = p["diameter"]/2
    wall = p["thin_wall"]*(1-t) + p["thick_wall"]*t
    inner, r, h, floor = outer-wall, p["rounding"], p["height"], p["bottom"]
    profile = [(0, 0), (outer-r, 0)]

    def arc(cx, cz, start, end):
        # Skip the initial point, already supplied by the previous straight or arc.
        for a in np.linspace(start, end, p["round_segments"]+1)[1:]:
            profile.append((cx+r*math.cos(a), cz+r*math.sin(a)))

    arc(outer-r, r, -math.pi/2, 0)
    profile.append((outer, h-r))
    arc(outer-r, h-r, 0, math.pi/2)
    profile.append((inner+r, h))
    arc(inner+r, h-r, math.pi/2, math.pi)
    profile.append((inner, floor+r))
    arc(inner-r, floor+r, 0, -math.pi/2)
    profile.append((0, floor))
    vertices, rings, faces = [], [], []
    n = p["angular_segments"]
    # Axis points are single vertices, so the base and inner floor have no collapsed faces.
    for radius, z in profile:
        ring = []
        for j in range(n if radius else 1):
            a = 2*math.pi*j/n
            ring.append(len(vertices))
            vertices.append((radius*math.cos(a), radius*math.sin(a), z))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for j in range(n):
            k = (j+1) % n
            if len(a) == 1:
                faces.append((a[0], b[j], b[k]))
            elif len(b) == 1:
                faces.append((a[j], b[0], a[k]))
            else:
                faces.append((a[j], b[j], b[k], a[k]))
    return vertices, faces


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = 0.65
    return mat


def setup_scene(motif, preserve_endpoints=False):
    reference = ROOT/"models"/f"{motif}.blend"
    if reference.exists():
        # Reuse the saved filming rig verbatim instead of reconstructing its orientation.
        bpy.ops.wm.open_mainfile(filepath=str(reference), load_ui=False, use_scripts=False)
        scene = bpy.context.scene
        for obj in list(scene.objects):
            if obj.name.startswith(f"{motif}/frame-") and obj.get("generator") == "scripts/generate.py":
                if not preserve_endpoints or obj.name not in (f"{motif}/frame-01", f"{motif}/frame-07"):
                    if motif != "pen" or obj.name != "pen/frame-01":
                        bpy.data.objects.remove(obj, do_unlink=True)
        return scene
    scene = bpy.context.scene
    scene.name = f"{motif}-endpoints"
    bpy.context.window.scene = scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 960, 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world = bpy.data.worlds.new(f"{motif}-world")
    scene.world.use_nodes = True
    background = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    background.inputs["Color"].default_value = (0.22, 0.24, 0.28, 1)
    background.inputs["Strength"].default_value = 0.6
    target = Vector((0, 0, dict(pen=7, stones=0, cup=37)[motif]))
    camera_data = bpy.data.cameras.new(f"{motif}-camera")
    camera = bpy.data.objects.new("Preview camera", camera_data)
    scene.collection.objects.link(camera)
    # Fixed camera and light coordinates are reused for both endpoint renders.
    camera.location = target + Vector((110, -190, 205))
    camera.rotation_euler = (target-camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = dict(pen=177, stones=139, cup=205)[motif]
    camera_data.clip_end = 2000
    scene.camera = camera
    for name, pos, energy, size in [
        ("Key", (-100, -120, 220), 1800000, 120),
        ("Fill", (130, 30, 160), 800000, 100),
    ]:
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = energy, "DISK", size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = pos
        obj.rotation_euler = (target-obj.location).to_track_quat("-Z", "Y").to_euler()
    # The render-only floor is explicitly excluded from STL selection.
    ground = make_mesh(scene, "Preview floor (not exported)",
                       [(-1000, -1000, -0.05), (1000, -1000, -0.05),
                        (1000, 1000, -0.05), (-1000, 1000, -0.05)], [(0, 1, 2, 3)])
    ground.data.materials.append(material("Floor", (0.19, 0.21, 0.24)))
    ground.hide_select = True
    return scene


def read_stl(path):
    # Read back the binary export itself; checks do not rely on Blender's source mesh.
    raw = path.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    assert len(raw) == 84 + count*50, "Unexpected binary STL byte count"
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attr", "<u2")])
    records = np.frombuffer(raw, dtype=dtype, count=count, offset=84)
    # STL repeats vertices per triangle; exact float32 deduplication recovers adjacency.
    vertices, inverse = np.unique(records["vertices"].reshape(-1, 3), axis=0, return_inverse=True)
    return vertices.astype(float), inverse.reshape(-1, 3), records["normal"].astype(float)


def validate_stl(path, motif, frame, near=None):
    t = (frame-1)/6
    vertices, triangles, normals = read_stl(path)
    bm = bmesh.new()
    mesh = bpy.data.meshes.new("STL validation temporary")
    mesh.from_pydata(vertices.tolist(), [], triangles.tolist())
    mesh.update()
    bm.from_mesh(mesh)
    # Traverse vertex adjacency to distinguish a closed solid from disconnected shells.
    remaining = set(bm.verts)
    components = 0
    while remaining:
        stack = [remaining.pop()]
        components += 1
        while stack:
            for edge in stack.pop().link_edges:
                for vertex in edge.verts:
                    if vertex in remaining:
                        remaining.remove(vertex)
                        stack.append(vertex)
    xyz = vertices[triangles]
    cross = np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
    twice_area = np.linalg.norm(cross, axis=1)
    normal_agreement = np.einsum("ij,ij->i", cross, normals)
    dims = np.ptp(vertices, axis=0)
    expected = {"pen": (None, None, None), "stones": (80, 80, None), "cup": (80, 80, 80)}[motif]
    dimensions_pass = all(e is None or abs(d-e) < 0.005 for d, e in zip(dims, expected))
    # BVH detects intersections between nonadjacent triangles; shared vertices are excluded.
    tree = BVHTree.FromPolygons(vertices.tolist(), triangles.tolist(), all_triangles=True, epsilon=0)
    overlaps = tree.overlap(tree)
    nonadjacent = [(a, b) for a, b in overlaps if a < b and
                   not set(triangles[a]).intersection(triangles[b])]
    report = dict(path=f"exports/{motif}/{path.name}", sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  dimensions_mm=dims.tolist(), bounds_mm=[vertices.min(axis=0).tolist(), vertices.max(axis=0).tolist()],
                  dimensions_pass=dimensions_pass, vertices=len(vertices), triangles=len(triangles),
                  components=components, boundary_edges=sum(e.is_boundary for e in bm.edges),
                  nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),
                  inconsistent_winding_edges=sum(e.is_manifold and not e.is_contiguous for e in bm.edges),
                  nonmanifold_vertices=sum(not v.is_manifold for v in bm.verts),
                  loose_vertices=sum(not v.link_faces for v in bm.verts),
                  degenerate_triangles=int(np.count_nonzero(twice_area < 1e-8)),
                  stl_normal_disagreements=int(np.count_nonzero(normal_agreement <= 0)),
                  signed_volume_mm3=bm.calc_volume(signed=True),
                  nonadjacent_bvh_overlap_pairs=len(nonadjacent),
                  self_intersection_scope="BVH nonadjacent triangles; shared-vertex pairs excluded. "
                  "Also checked analytically: monotonic-X pen rings, single-valued stone heightfield, simple cup profile.")
    # Measure functional thicknesses in exported coordinates rather than only reporting inputs.
    if motif == "pen":
        if near is None:
            with bpy.data.libraries.load(str(ROOT/"models"/"pen.blend"), link=False) as (source, target):
                target.scenes = ["pen-endpoints"]
            near = pen_table_basis(target.scenes[0])
        basis = near
        axis, horizontal, up = basis["axis"], basis["near"], basis["up"]
        relative = vertices-np.array(basis["center"])
        longitudinal = relative@np.array(axis)
        height = (vertices-np.array(basis["table_origin"]))@np.array(up)
        center_mask = np.abs(longitudinal) < 1e-5
        h, q = height[center_mask], relative[center_mask]@np.array(horizontal)
        contact = h < 1e-5
        table_vertices = np.abs(height) < 1e-5
        table_faces = np.all(table_vertices[triangles], axis=1)
        report.update(center_height_mm=float(np.ptp(h)), center_width_mm=float(np.ptp(q)),
                      near_extent_mm=float(q.max()), far_extent_mm=float(q.min()),
                      center_bottom_above_table_mm=float(h.min()), center_top_above_table_mm=float(h.max()),
                      minimum_clearance_above_table_mm=float(height.min()),
                      longitudinal_length_mm=float(np.ptp(longitudinal)),
                      contact_ring_vertices=int(np.count_nonzero(contact)),
                      center_contact_width_mm=float(np.ptp(q[contact])) if np.any(contact) else 0,
                      tabletop_contact_area_mm2=float(twice_area[table_faces].sum()/2),
                      tabletop_contact_axial_span_mm=float(np.ptp(longitudinal[table_vertices])) if np.any(table_vertices) else 0,
                      tabletop_contact_triangles=int(np.count_nonzero(table_faces)), tabletop_tolerance_mm=1e-5,
                      table_normal=list(up), horizontal_near=list(horizontal), marker_axis=list(axis),
                      compression_axis_dot_marker_axis=horizontal.dot(axis),
                      table_origin_mm=list(basis["table_origin"]))
        t *= PEN["deformation_intensity"]
        shift = PEN["centerline_displacement"]*t
        expected_near = PEN["barrel_diameter"]/2+PEN["near_expansion"]*t+shift
        expected_far = -PEN["barrel_diameter"]/2-PEN["far_expansion"]*t+shift
        # Independently evaluate the analytic center roof extrema on the exported ring angles.
        angle = np.arange(PEN["angular_segments"])*2*math.pi/PEN["angular_segments"]
        lateral = -np.cos(angle)
        roof = np.clip((np.sin(angle)+0.55)/1.10, 0, 1)
        roof = roof*roof*(3-2*roof)
        target = (PEN["compressed_height"]-PEN["compression_slope"]*lateral)*roof
        target *= 1-PEN["near_top_taper"]*np.maximum(0, lateral)**2
        expected_height = float(np.ptp((1-t)*PEN["barrel_diameter"]/2*(np.sin(angle)+1)+t*target))
        dimensions_pass = abs(report["longitudinal_length_mm"]-PEN["length"]) < 0.005
        report["dimensions_pass"] = bool(dimensions_pass)
        report["functional_dimensions_pass"] = bool(
            abs(report["center_height_mm"]-expected_height) < 0.005
            and abs(report["near_extent_mm"]-expected_near) < 0.005
            and abs(report["far_extent_mm"]-expected_far) < 0.005
            and height.min() >= -1e-5)
        if frame == 7:
            report["functional_dimensions_pass"] &= abs(h.min()) < 1e-5 and report["center_contact_width_mm"] > 12
            report["functional_dimensions_pass"] &= report["tabletop_contact_area_mm2"] > 200
        thicknesses, sole_heights = [], []
        # Sample the functional flat sole/roof, avoiding the naturally rounded perimeter edge.
        plane_center = basis["center"]-up*(basis["center"]-basis["table_origin"]).dot(up)
        # Remove only the known unequal edge spreading from the measured section midpoint.
        measured_shift = float((q.max()+q.min())/2-(PEN["near_expansion"]-PEN["far_expansion"])*t/2)
        report["material_centerline_near_displacement_mm"] = measured_shift
        report["centerline_measurement_method"] = "STL lateral midpoint minus unequal-spread offset; saved-mesh crown/sole meridians checked separately."
        report["section_envelope_midpoint_near_mm"] = float((q.max()+q.min())/2)
        report["functional_dimensions_pass"] &= abs(measured_shift-shift) < 0.005
        roof_heights = []
        # Equal lateral offsets about the moved centerline isolate the roof slope from spreading.
        for y in (-5.0, 5.0):
            origin = plane_center+horizontal*(measured_shift+y)+up*40
            hit, _, _, _ = tree.ray_cast(origin, -up, 100)
            assert hit is not None
            roof_heights.append((hit-basis["table_origin"]).dot(up))
        report["roof_probe_offsets_from_centerline_mm"] = [-5.0, 5.0]
        report["far_near_roof_heights_above_table_mm"] = roof_heights
        report["far_minus_near_roof_height_mm"] = roof_heights[0]-roof_heights[1]
        if frame == 7:
            report["functional_dimensions_pass"] &= roof_heights[0]-roof_heights[1] > 1.0
        for x in np.linspace(-PEN["flat_length"]/2, PEN["flat_length"]/2, 15):
            for y in np.linspace(-5.5, 6.5, 25):
                origin = plane_center+axis*x+horizontal*(y+pen_center_shift(x, (frame-1)/6))
                bottom, _, _, _ = tree.ray_cast(origin-up, up, 100)
                top, _, _, _ = tree.ray_cast(origin+up*40, -up, 100)
                assert bottom is not None and top is not None
                thicknesses.append((top-bottom).dot(up))
                sole_heights.append((bottom-basis["table_origin"]).dot(up))
        report["sampled_flat_region_minimum_vertical_thickness_mm"] = min(thicknesses)
        report["sampled_flat_region_bottom_clearance_range_mm"] = [min(sole_heights), max(sole_heights)]
        report["functional_dimensions_pass"] &= min(thicknesses) >= PEN["minimum_web"]-0.01
    elif motif == "stones":
        top = vertices[vertices[:, 2] > 0]
        report["minimum_vertical_backing_mm"] = float(top[:, 2].min())
        report["maximum_relief_mm"] = float(top[:, 2].max() - STONES["backing"])
        level = min(int(t*2), 1)
        blend = t*2-level
        blend = blend*blend*(3-2*blend)
        areas = [STONES["coarse_pitch"]**2, STONES["coarse_pitch"]*STONES["fine_pitch"], STONES["fine_pitch"]**2]
        report["nominal_grain_scale_mm"] = math.sqrt(areas[level]*(1-blend)+areas[level+1]*blend)
        report["hierarchy_level_pair"] = [level, level+1]
        report["child_relief_blend"] = blend
        report["functional_dimensions_pass"] = (abs(report["minimum_vertical_backing_mm"]-STONES["backing"]) < 0.005
                                                   and 1 <= report["maximum_relief_mm"] <= 2)
    else:
        radii = np.linalg.norm(vertices[:, :2], axis=1)
        # Sample the straight wall endpoints at the rim tangent, excluding the rounded floor.
        wall_radii = radii[np.abs(vertices[:, 2]-(CUP["height"]-CUP["rounding"])) < 1e-5]
        report["straight_sidewall_radial_thickness_mm"] = float(wall_radii.max()-wall_radii.min())
        report["inner_diameter_mm"] = float(2*wall_radii.min())
        report["bottom_thickness_mm"] = float(vertices[(radii < 1e-5) & (vertices[:, 2] > 0), 2].min())
        rim_radii = radii[np.abs(vertices[:, 2]-80) < 1e-5]
        report["flat_rim_radial_span_mm"] = float(np.ptp(rim_radii))
        report["functional_dimensions_pass"] = (abs(report["straight_sidewall_radial_thickness_mm"] -
                                                       (CUP["thin_wall"]*(1-t)+CUP["thick_wall"]*t)) < 0.005
                                                   and abs(report["bottom_thickness_mm"]-CUP["bottom"]) < 0.005)
        thicknesses = []
        for z in (5, 40, 75):
            for angle in np.linspace(0, 2*math.pi, 32, endpoint=False):
                direction = Vector((math.cos(angle), math.sin(angle), 0))
                inside, _, _, _ = tree.ray_cast(Vector((0, 0, z)), direction, 100)
                outside, _, _, _ = tree.ray_cast(inside+direction*0.001, direction, 100)
                thicknesses.append((outside-inside).length)
        report["sampled_straight_wall_thickness_range_mm"] = [min(thicknesses), max(thicknesses)]
    report["minimum_thickness_scope"] = "Functional sections only; no exhaustive local normal-thickness or sub-nozzle feature/overhang check."
    report["passed"] = (dimensions_pass and report["functional_dimensions_pass"] and components == 1 and report["signed_volume_mm3"] > 0
                        and all(report[k] == 0 for k in (
                            "boundary_edges", "nonmanifold_edges", "nonmanifold_vertices", "loose_vertices",
                            "inconsistent_winding_edges", "degenerate_triangles", "stl_normal_disagreements",
                            "nonadjacent_bvh_overlap_pairs")))
    bm.free()
    bpy.data.meshes.remove(mesh)
    return report


def compare_invariants(objects, motif):
    a, b = [np.array([v.co[:] for v in obj.data.vertices]) for obj in objects]
    if motif == "pen":
        unchanged = np.abs(a[:, 0]) >= PEN["crush_length"]/2
        return dict(unchanged_ends_max_delta_mm=float(np.max(np.abs(a[unchanged]-b[unchanged]))),
                    axial_coordinates_identical=bool(np.array_equal(a[:, 0], b[:, 0])),
                    deformation_zone_mm=[-20, 20])
    if motif == "cup":
        # Outer wall, exterior base and upper exterior rounding occupy the same prefix.
        n = CUP["angular_segments"]
        outer_count = 1 + (2*CUP["round_segments"]+2)*n
        return dict(unchanged_exterior_max_delta_mm=float(np.max(np.abs(a[:outer_count]-b[:outer_count]))),
                    bottom_position_mm=0, height_mm=80)
    return dict(xy_coordinates_identical=bool(np.array_equal(a[:, :2], b[:, :2])),
                backing_and_outline_identical=True, seed=STONES["seed"],
                relation="Fixed irregular parent cells with two nested clipped Voronoi subdivision levels; continuous groove blending.")


def save_comparison(paths, destination):
    images = [bpy.data.images.load(str(p), check_existing=False) for p in paths]
    width, height = images[0].size
    # Copy encoded image pixels without a second render/view transform; left=01, right=07.
    canvas = np.ones((height, width*2+16, 4), dtype=np.float32)
    canvas[:, :, :3] = 0.06
    for i, img in enumerate(images):
        pixels = np.empty(width*height*4, dtype=np.float32)
        img.pixels.foreach_get(pixels)
        canvas[:, i*(width+16):i*(width+16)+width] = pixels.reshape(height, width, 4)
    output = bpy.data.images.new(destination.stem, width*2+16, height)
    output.pixels.foreach_set(canvas.ravel())
    output.filepath_raw = str(destination)
    output.file_format = "PNG"
    output.save()
    for img in images + [output]:
        bpy.data.images.remove(img)


def save_contact_sheet(paths, destination):
    # The pixel labels keep this diagnostic sheet dependency-free and unambiguously ordered.
    glyphs = {"0": "01110/10001/10011/10101/11001/10001/01110",
              "1": "00100/01100/00100/00100/00100/00100/01110",
              "2": "01110/10001/00001/00010/00100/01000/11111",
              "3": "11110/00001/00001/01110/00001/00001/11110",
              "4": "00010/00110/01010/10010/11111/00010/00010",
              "5": "11111/10000/10000/11110/00001/00001/11110",
              "6": "01110/10000/10000/11110/10001/10001/01110",
              "7": "11111/00001/00010/00100/01000/01000/01000",
              "F": "11111/10000/10000/11110/10000/10000/10000",
              "R": "11110/10001/10001/11110/10100/10010/10001",
              "A": "01110/10001/10001/11111/10001/10001/10001",
              "M": "10001/11011/10101/10101/10001/10001/10001",
              "E": "11111/10000/10000/11110/10000/10000/11111"}
    width, height, header, gap, columns = 480, 320, 36, 12, 4
    rows = math.ceil(len(paths)/columns)
    canvas = np.ones((rows*(height+header+gap)+gap, columns*(width+gap)+gap, 4), dtype=np.float32)
    canvas[:, :, :3] = 0.06
    for i, path in enumerate(paths):
        img = bpy.data.images.load(str(path), check_existing=False)
        img.scale(width, height)
        pixels = np.empty(width*height*4, dtype=np.float32)
        img.pixels.foreach_get(pixels)
        # Blender pixels are bottom-up; invert only the row placement, never the source image.
        x = gap+(i % columns)*(width+gap)
        y = canvas.shape[0]-gap-(i//columns+1)*(height+header)-(i//columns)*gap
        canvas[y:y+height, x:x+width] = pixels.reshape(height, width, 4)
        for k, char in enumerate(f"FRAME {i+1:02}"):
            if char == " ":
                continue
            for gy, row in enumerate(glyphs[char].split("/")):
                for gx, bit in enumerate(row):
                    if bit == "1":
                        px, py = x+12+k*18+gx*3, y+height+7+(6-gy)*3
                        canvas[py:py+3, px:px+3, :3] = 0.95
        bpy.data.images.remove(img)
    output = bpy.data.images.new(destination.stem, canvas.shape[1], canvas.shape[0])
    output.pixels.foreach_set(canvas.ravel())
    output.filepath_raw, output.file_format = str(destination), "PNG"
    output.save()
    bpy.data.images.remove(output)


def save_pen_animation(paths):
    order = [1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2, 1]
    output = OUTPUT/"previews"/"pen"/"forward-reverse.gif"
    # Set the delay before reading frames; apply looping after GIF layer optimization.
    command = ["magick", "-delay", "40"]+[str(paths[frame-1]) for frame in order]
    command += ["-resize", "720x480", "-layers", "Optimize", "-strip", "-loop", "0", str(output)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    # Read the encoded animation back to verify frame count and per-state timing.
    probe = subprocess.run(["magick", "identify", "-format", "%T\\n", str(output)],
                           check=True, capture_output=True, text=True)
    delays = [int(value) for value in probe.stdout.split()]
    assert len(delays) == len(order) and delays == [40]*len(order)
    return dict(path="previews/pen/forward-reverse.gif", sequence=order,
                seconds_per_state=0.4, duration_seconds=sum(delays)/100,
                encoded_frame_count=len(delays), loop=True,
                sha256=hashlib.sha256(output.read_bytes()).hexdigest())


def generate(motif, render, frames=ENDPOINTS, intermediates_only=False):
    all_frames = len(frames) == 7
    scene = setup_scene(motif, preserve_endpoints=all_frames)
    geometry = dict(pen=pen_geometry, stones=stones_geometry, cup=cup_geometry)[motif]
    near = pen_table_basis(scene) if motif == "pen" else None
    endpoint_meshes = [scene.objects.get(f"{motif}/frame-{frame:02}") for frame in (1, 7)]
    endpoint_fingerprints = [mesh_fingerprint(obj) for obj in endpoint_meshes] if intermediates_only else None
    hierarchy = stone_hierarchy() if motif == "stones" else None
    body = material(f"{motif} surface", dict(pen=(0.55, 0.57, 0.59),
                                            stones=(0.48, 0.46, 0.41), cup=(0.65, 0.68, 0.69))[motif])
    cap = material("Closed cap", (0.045, 0.06, 0.08)) if motif == "pen" else None
    objects = []
    approved_endpoints = {}
    for frame, t in frames:
        shape = geometry(t, near) if motif == "pen" else geometry(t, hierarchy) if motif == "stones" else geometry(t)
        keep = (all_frames and frame in (1, 7)) or (motif == "pen" and frame == 1)
        obj = scene.objects.get(f"{motif}/frame-{frame:02}") if keep else None
        if obj is not None:
            # Keep the actual approved endpoint objects; verify the procedural definition matches.
            actual = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float32)
            assert np.array_equal(actual, np.asarray(shape[0], dtype=np.float32)), "Approved endpoint differs from generator"
        else:
            obj = make_mesh(scene, f"{motif}/frame-{frame:02}", *shape)
            obj["t"] = t
            obj.data.materials.append(body)
            if cap:
                obj.data.materials.append(cap)
            for face in obj.data.polygons:
                face.use_smooth = len(face.vertices) == 4 and motif != "stones"
                if cap and face.center.x < -32.0:
                    face.material_index = 1
        if frame in (1, 7):
            approved = ROOT/"exports"/motif/f"frame-{frame:02}.stl"
            if approved.exists():
                approved_endpoints[frame] = hashlib.sha256(approved.read_bytes()).hexdigest()
        obj.hide_render = True
        obj.hide_set(True)
        objects.append(obj)
    invariant = compare_invariants([objects[0], objects[-1]], motif)
    coordinates = [np.array([v.co[:] for v in obj.data.vertices]) for obj in objects]
    invariant["frames"] = [f for f, _ in frames]
    invariant["t_values"] = [t for _, t in frames]
    invariant["oblique_camera"] = dict(location=list(scene.camera.location),
                                        rotation=list(scene.camera.rotation_euler),
                                        ortho_scale=scene.camera.data.ortho_scale,
                                        resolution=[scene.render.resolution_x, scene.render.resolution_y])
    invariant["per_step_max_vertex_delta_mm"] = [float(np.linalg.norm(b-a, axis=1).max())
                                                for a, b in zip(coordinates, coordinates[1:])]
    invariant["all_frames_reference_features_pass"] = all(
        all((value == 0.0 if "delta" in key else value is True)
            for key, value in compare_invariants([objects[0], obj], motif).items()
            if key in ("unchanged_ends_max_delta_mm", "axial_coordinates_identical", "unchanged_exterior_max_delta_mm", "xy_coordinates_identical"))
        for obj in objects)
    assert invariant["all_frames_reference_features_pass"]
    if motif == "pen":
        a, b = coordinates[0], coordinates[-1]
        relative = a-np.array([0, 0, PEN["cap_diameter"]/2])
        local_near = near["inverse"].to_3x3()@near["near"]
        far = relative@np.array(local_near) < 0
        invariant["far_half_max_displacement_mm"] = float(np.max(np.linalg.norm(b[far]-a[far], axis=1)))
        invariant["horizontal_near_direction"] = list(near["near"])
        invariant["compression_axis_dot_marker_axis"] = near["near"].dot(near["axis"])
        # Ordered source rings give an exact polygon area comparison independent of shading.
        center_ring = np.abs(a[:, 0]) < 1e-5
        sections = [points[center_ring][:, 1:] for points in (a, b)]
        areas = [abs(float(np.sum(p[:, 0]*np.roll(p[:, 1], -1)-p[:, 1]*np.roll(p[:, 0], -1))/2)) for p in sections]
        invariant["center_cross_section_area_mm2"] = areas
        invariant["center_cross_section_area_ratio"] = areas[1]/areas[0]
    if motif == "stones":
        invariant["cell_counts_by_level"] = [len(level) for level in hierarchy]
        invariant["median_cell_equivalent_diameter_mm_by_level"] = [
            float(np.median([2*math.sqrt(node["area"]/math.pi) for node in level])) for level in hierarchy]
        # Persist the actual deterministic ancestry, not just a claim that the seed is fixed.
        ancestry = [[dict(identity=node["identity"], parent=node["parent"],
                          center=node["center"].tolist(), area_mm2=node["area"])
                     for node in level] for level in hierarchy]
        scene["pebble_ancestry_json"] = json.dumps(ancestry)
        invariant["hierarchy_sha256"] = hashlib.sha256(json.dumps(ancestry).encode()).hexdigest()
    results, preview_paths = [], []
    for (frame, _), obj in zip(frames, objects):
        name = f"frame-{frame:02}"
        obj.hide_set(False)
        obj.hide_render = False
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        path = OUTPUT / "exports" / motif / f"{name}.stl"
        if intermediates_only and frame in (1, 7):
            # Approved endpoint files are read for comparison and never rewritten.
            path = ROOT/"exports"/motif/f"{name}.stl"
        else:
            # Numeric mesh coordinates are already millimeters; scene-unit conversion is off.
            bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True,
                                  global_scale=1, use_scene_unit=False, apply_modifiers=True,
                                  forward_axis="Y", up_axis="Z", ascii_format=False)
        results.append(validate_stl(path, motif, frame, near))
        if frame in approved_endpoints:
            assert results[-1]["sha256"] == approved_endpoints[frame], "Approved endpoint STL changed"
        if render:
            preview = OUTPUT / "previews" / motif / f"{name}.png"
            scene.render.filepath = str(preview)
            bpy.ops.render.render(write_still=True)
            preview_paths.append(preview)
        obj.hide_render = True
        obj.hide_set(True)
    if render:
        save_comparison([preview_paths[0], preview_paths[-1]], OUTPUT / "previews" / motif / "comparison.png")
        if all_frames:
            save_contact_sheet(preview_paths, OUTPUT/"previews"/motif/"contact-sheet.png")
        if intermediates_only:
            invariant["animation"] = save_pen_animation(preview_paths)
        if motif == "cup" or (motif == "pen" and all_frames):
            # Secondary top views share their own fixed camera, preserving the main comparison.
            original_location = scene.camera.location.copy()
            original_rotation = scene.camera.rotation_euler.copy()
            scene.camera.location = (0, 0, 260)
            scene.camera.rotation_euler = (0, 0, 0)
            if motif == "pen":
                # Use the same scene-derived top orientation as the approved endpoint review.
                plane_center = near["center"]-near["up"]*(near["center"]-near["table_origin"]).dot(near["up"])
                scene.camera.location = plane_center+near["up"]*260
                screen_up = near["up"].cross(near["axis"]).normalized()
                scene.camera.rotation_euler = Matrix((near["axis"], screen_up, near["up"])).transposed().to_euler()
                invariant["top_camera"] = dict(location=list(scene.camera.location),
                                                rotation=list(scene.camera.rotation_euler),
                                                ortho_scale=scene.camera.data.ortho_scale)
            top_paths = []
            for (frame, _), obj in zip(frames, objects):
                if motif == "cup" and frame not in (1, 7):
                    continue
                obj.hide_set(False)
                obj.hide_render = False
                scene.render.filepath = str(OUTPUT / "previews" / motif / f"frame-{frame:02}-top.png")
                bpy.ops.render.render(write_still=True)
                top_paths.append(Path(scene.render.filepath))
                obj.hide_render = True
                obj.hide_set(True)
            scene.camera.location, scene.camera.rotation_euler = original_location, original_rotation
            if motif == "pen":
                save_contact_sheet(top_paths, OUTPUT/"previews"/motif/"contact-sheet-top.png")
    objects[0].hide_render = False
    objects[0].hide_set(False)
    bpy.ops.object.select_all(action="DESELECT")
    objects[0].select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    # Keep both endpoint meshes at their physical datum; switch their visibility to compare.
    scene["preview_instructions"] = "frame-01 visible; hide it and unhide the desired frame in viewport AND render. All share origin (0,0,0)."
    scene["frames_json"] = json.dumps(frames)
    scene["parameters_json"] = json.dumps(dict(pen=PEN, stones=STONES, cup=CUP)[motif])
    if intermediates_only:
        assert endpoint_fingerprints == [mesh_fingerprint(obj) for obj in endpoint_meshes]
        # Check the exported progression, including actual source-material meridian motion.
        center = (np.abs(coordinates[0][:, 0]) < 1e-5) & (np.abs(coordinates[0][:, 1]) < 1e-5)
        shifts = [((points[center]-coordinates[0][center])@np.array(near["near"])).tolist()
                  for points in coordinates]
        invariant["center_material_meridian_displacements_mm"] = shifts
        assert all(np.allclose(values, PEN["centerline_displacement"]*t, atol=1e-5)
                   for values, (_, t) in zip(shifts, frames))
        heights = [record["center_height_mm"] for record in results]
        widths = [record["center_width_mm"] for record in results]
        displacement = [record["material_centerline_near_displacement_mm"] for record in results]
        slopes = [record["far_minus_near_roof_height_mm"] for record in results]
        invariant["progressive_compression_bow_and_slope_pass"] = bool(
            all(b < a for a, b in zip(heights, heights[1:]))
            and all(b > a for values in (widths, displacement, slopes) for a, b in zip(values, values[1:])))
        assert invariant["progressive_compression_bow_and_slope_pass"]
        scene["pen_intermediate_status"] = "Frames 02–06 interpolate the approved sloped/bowed tabletop-compression endpoint."
        invariant["endpoint_mesh_fingerprints_preserved"] = True
    scene["generator"] = "scripts/generate.py"
    # Store the exact source alongside the editable geometry for a self-contained provenance trail.
    text = bpy.data.texts.get("generate.py") or bpy.data.texts.new("generate.py")
    text.clear()
    text.write(Path(__file__).read_text())
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
                area.spaces.active.clip_end = 3000
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "models" / f"{motif}.blend"))
    return dict(models=results, invariants=invariant, approved_endpoint_stl_preserved=True,
                approved_endpoint_sha256=approved_endpoints)


def mesh_fingerprint(obj):
    coordinates = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float32)
    faces = [list(p.vertices) for p in obj.data.polygons]
    return hashlib.sha256(coordinates.tobytes()+json.dumps(faces).encode()).hexdigest()


def revise_pen_frame07():
    # This path deliberately never calls the multi-frame generator or exports Frames 01–06.
    protected = [ROOT/"models"/f"{motif}.blend" for motif in ("stones", "cup")]
    protected += [ROOT/"exports"/"pen"/f"frame-{frame:02}.stl" for frame in range(1, 7)]
    for motif in ("stones", "cup"):
        protected += list((ROOT/"exports"/motif).glob("*.stl"))
        protected += list((ROOT/"previews"/motif).glob("*.png"))
    before_files = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"models"/"pen.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    basis = pen_table_basis(scene)
    retained = [scene.objects[f"pen/frame-{frame:02}"] for frame in range(1, 7)]
    before_meshes = [mesh_fingerprint(obj) for obj in retained]
    before = validate_stl(ROOT/"exports"/"pen"/"frame-01.stl", "pen", 1, basis)
    baseline = json.loads((ROOT/"previews"/"pen"/"tabletop-validation.json").read_text())["revised_frame07"]
    old = scene.objects["pen/frame-07"]
    assert old.get("generator") == "scripts/generate.py"
    materials = list(old.data.materials)
    # Preserve the exact generator for the retained, now-outdated tabletop intermediates.
    if bpy.data.texts.get("pen-intermediates-tabletop.py") is None:
        legacy = bpy.data.texts.new("pen-intermediates-tabletop.py")
        legacy.write(bpy.data.texts["generate.py"].as_string())
        legacy.use_fake_user = True
    # Retain the old source inside the editable file for the intentionally stale intermediates.
    if bpy.data.texts.get("pen-intermediates-legacy.py") is None:
        legacy = bpy.data.texts.new("pen-intermediates-legacy.py")
        legacy.write(bpy.data.texts["generate.py"].as_string())
        legacy.use_fake_user = True
    bpy.data.objects.remove(old, do_unlink=True)
    obj = make_mesh(scene, "pen/frame-07", *pen_geometry(1.0, basis))
    obj.location, obj.rotation_euler, obj.scale = retained[0].location.copy(), retained[0].rotation_euler.copy(), retained[0].scale.copy()
    obj["t"], obj["revision"] = 1.0, "sloped tabletop compression with localized near-side centerline bow"
    for material in materials:
        obj.data.materials.append(material)
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
        face.material_index = int(face.center.x < -32)
    for other in scene.objects:
        other.select_set(False)
        if other.name.startswith("pen/frame-"):
            other.hide_render = other != obj
            other.hide_set(other != obj)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = OUTPUT/"exports"/"pen"/"frame-07.stl"
    bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True, global_scale=1,
                          use_scene_unit=False, apply_modifiers=True, forward_axis="Y", up_axis="Z", ascii_format=False)
    after = validate_stl(path, "pen", 7, basis)
    invariant = compare_invariants([retained[0], obj], "pen")
    # Track original crown/sole material meridians directly in the saved ring topology.
    original = np.array([v.co[:] for v in retained[0].data.vertices])
    revised = np.array([v.co[:] for v in obj.data.vertices])
    mask = (np.abs(original[:, 0]) < 1e-5) & (np.abs(original[:, 1]) < 1e-5)
    shifts = (revised[mask]-original[mask])@np.array(basis["near"])
    invariant["center_material_meridian_displacements_mm"] = shifts.tolist()
    assert len(shifts) == 2 and np.allclose(shifts, PEN["centerline_displacement"], atol=1e-5)
    assert invariant["unchanged_ends_max_delta_mm"] == 0 and invariant["axial_coordinates_identical"]
    assert before_meshes == [mesh_fingerprint(other) for other in retained]
    after_files = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    assert before_files == after_files
    assert before["passed"] and after["passed"], "Tabletop endpoint validation failed"
    scene["parameters_json"] = json.dumps(PEN)
    scene["pen_intermediate_status"] = "Frames 02–06 retain the previous level-roof tabletop geometry and are outdated. Await sloped/bowed Frame 07 approval."
    scene["preview_instructions"] = "Frame 01 visible; switch viewport AND render visibility to Frame 07 for endpoint review. Frames 02–06 are stale."
    source = bpy.data.texts["generate.py"]
    source.clear()
    source.write(Path(__file__).read_text())
    obj.hide_set(True)
    obj.hide_render = True
    retained[0].hide_set(False)
    retained[0].hide_render = False
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT/"models"/"pen.blend"))
    result = dict(before_frame01=before, baseline_frame07=baseline, revised_frame07=after, endpoint_invariants=invariant,
                  retained_frame01_to_06_meshes_unchanged=True, protected_files_unchanged=True,
                  protected_sha256=after_files, parameters=PEN,
                  intermediate_status="Frames 02–06 preserved, pending endpoint approval; old contact sheets are historical.")
    (OUTPUT/"previews"/"pen"/"tabletop-validation.json").write_text(json.dumps(result, indent=2)+"\n")
    if OUTPUT == ROOT:
        report_path = ROOT/"previews"/"validation.json"
        report = json.loads(report_path.read_text())
        report["parameters"]["pen"] = PEN
        report["pen"]["models"] = [after if entry["path"].endswith("frame-07.stl") else entry for entry in report["pen"]["models"]]
        report["pen"]["invariants"] = invariant
        report["pen"]["intermediate_status"] = result["intermediate_status"]
        report["pen"]["regenerated_frames"] = [7]
        report["pen"]["protected_sha256"] = after_files
        report["pen"]["protected_files_unchanged"] = True
        report["pen"].pop("approved_endpoint_stl_preserved", None)
        if "approved_endpoint_sha256" in report["pen"]:
            report["pen"]["previous_approved_endpoint_sha256"] = report["pen"].pop("approved_endpoint_sha256")
        report["pen"]["frame01_stl_preserved"] = True
        report["pen"]["frame07_status"] = "New sloped/bowed tabletop endpoint, awaiting visual approval"
        report_path.write_text(json.dumps(report, indent=2)+"\n")
    print("TABLETOP_VALIDATION", json.dumps({key: value for key, value in result.items() if key != "protected_sha256"}), flush=True)


def main():
    global OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motif", choices=("pen", "stones", "cup"))
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--all-frames", action="store_true")
    parser.add_argument("--pen-frame07", action="store_true", help="Revise only the tabletop pen endpoint; preserve Frames 01–06")
    parser.add_argument("--pen-intermediates", action="store_true", help="Regenerate only Pen Frames 02–06; never rewrite approved endpoint STLs")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    OUTPUT = args.output_root.resolve()
    if bpy.app.version[:2] != (4, 5):
        raise RuntimeError(f"Blender 4.5 LTS required, found {bpy.app.version_string}")
    if args.pen_intermediates:
        for directory in (OUTPUT/"models", OUTPUT/"exports"/"pen", OUTPUT/"previews"/"pen"):
            directory.mkdir(parents=True, exist_ok=True)
        protected = [ROOT/"exports"/"pen"/f"frame-{frame:02}.stl" for frame in (1, 7)]
        for motif in ("stones", "cup"):
            protected.append(ROOT/"models"/f"{motif}.blend")
            protected += list((ROOT/"exports"/motif).glob("*.stl"))
            protected += list((ROOT/"previews"/motif).glob("*.png"))
        hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
        result = generate("pen", not args.no_render, ALL_FRAMES, intermediates_only=True)
        assert hashes == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
        assert all(record["passed"] for record in result["models"])
        result["regenerated_frames"] = list(range(2, 7))
        result["protected_files_unchanged"] = True
        result["protected_sha256"] = hashes
        (OUTPUT/"previews"/"pen"/"intermediates-validation.json").write_text(json.dumps(result, indent=2)+"\n")
        if OUTPUT == ROOT:
            path = ROOT/"previews"/"validation.json"
            report = json.loads(path.read_text())
            report["pen"] = result
            report["pen"]["frame07_status"] = "Approved tabletop endpoint, unchanged"
            report["pen"]["intermediate_status"] = "Frames 02–06 regenerated using the approved algorithm"
            path.write_text(json.dumps(report, indent=2)+"\n")
        print("PEN_INTERMEDIATES", json.dumps({key: value for key, value in result.items() if key != "protected_sha256"}), flush=True)
        return
    if args.pen_frame07:
        for directory in (OUTPUT/"models", OUTPUT/"exports"/"pen", OUTPUT/"previews"/"pen"):
            directory.mkdir(parents=True, exist_ok=True)
        revise_pen_frame07()
        return
    motifs = [args.motif] if args.motif else ["pen", "stones", "cup"]
    frames = ALL_FRAMES if args.all_frames else ENDPOINTS
    for motif in motifs:
        for folder in (OUTPUT/"models", OUTPUT/"exports"/motif, OUTPUT/"previews"/motif):
            folder.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT/"previews"/"validation.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    report["blender_version"] = bpy.app.version_string
    report["parameters"] = dict(pen=PEN, stones=STONES, cup=CUP)
    report["unverified"] = ["Physical printing, strength, warping, supports, slicing and printer operation.",
                            "Exhaustive local thickness; very fine tips of pebble valleys and decorative cap seam.",
                            "Self intersections in adjacent/shared-vertex triangles are not covered by BVH; construction is analytically injective.",
                            "Physical stop-motion registration and photographed temporal continuity."]
    for motif in motifs:
        if args.validate_only:
            records = [validate_stl(OUTPUT/"exports"/motif/f"frame-{f:02}.stl", motif, f) for f, _ in frames]
            report.setdefault(motif, {})["models"] = records
        else:
            # Remove only this process's scene data between motifs, never user-authored files.
            bpy.ops.wm.read_factory_settings(use_empty=True)
            report[motif] = generate(motif, not args.no_render, frames)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print("VALIDATION", motif, json.dumps(report[motif]), flush=True)
    failures = [m["path"] for motif in motifs for m in report[motif]["models"] if not m["passed"]]
    if failures:
        raise RuntimeError(f"STL validation failed: {failures}")


if __name__ == "__main__":
    main()
