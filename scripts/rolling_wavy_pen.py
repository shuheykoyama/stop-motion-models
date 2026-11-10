"""Four printable Rolling Wavy Pen study poses; run with Blender 4.5.

blender --background --python scripts/rolling_wavy_pen.py
blender --background --python scripts/rolling_wavy_pen.py -- --output-root /tmp/repro --geometry-only
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
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate import make_mesh, read_stl, mesh_fingerprint


ROOT = Path(__file__).resolve().parents[1]
NAMES = ("straight", "curved", "wavy", "highly-wavy")
ROLL_DEG = (0.0, 18.0, -14.0, 25.0)
FILM_Y_MM = (0.0, 3.0, -2.0, 4.0)
RADIAL_SEGMENTS = 96
AXIAL_STEP_MM = 0.8
TABLE_CONTACT_TRIM_MM = 0.68
LENGTH_SCALE = 141.8/140.8
CAP_RADIUS_MM = 6.6
BARREL_RADIUS_MM = 11.9/2


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def smoothstep(u):
    u = max(0.0, min(1.0, u))
    return u*u*(3-2*u)


def centerline(x, pose):
    # Keep the reviewed wave path while stretching its longitudinal coordinate to the reference length.
    x /= LENGTH_SCALE
    lower = int(math.floor(pose))
    upper = min(3, lower+1)
    fraction = pose-lower

    def blended_curve(position):
        return (1-fraction)*shaft_curve(position, lower)+fraction*shaft_curve(position, upper)

    def shaft_curve(position, state):
        # The existing four endpoint curves remain unchanged at integer states.
        lobes = {
            0: (),
            1: ((22.0, 9.0, 50.0),),
            2: ((1.0, 11.0, 25.0), (37.0, -10.0, 23.0), (68.0, 8.0, 21.0)),
            3: ((-2.0, 11.0, 38.0), (20.0, -7.0, 29.0), (45.0, 9.0, 36.0), (64.0, -8.0, 32.0)),
        }
        envelope = max(0.0, 1-((position-19.2)/51.2)**4)
        return envelope*sum(a*math.exp(-0.5*((position-c)/s)**2) for c, a, s in lobes[state])

    if x >= -32:
        return blended_curve(x)
    # Continue the shaft's seam tangent as a straight rigid cap with no visible kink.
    seam_value = blended_curve(-32.0)
    seam_slope = (blended_curve(-31.98)-blended_curve(-32.02))/0.04
    return seam_value+seam_slope*(x+32.0)


def geometry(pose, roll_deg=None, centerline_fn=None):
    # Scale the reviewed silhouette to the official ultra-fine length and shaft diameter.
    profile = [(-70.4, 8.8), (-70.2, 9.8), (-69.5, 10.6), (-68.8, 10.9),
               (-34.0, 10.9), (-33.8, 10.5), (-33.4, 10.5), (-33.2, 10.9),
               (-32.5, 10.9), (-32.0, 9.0), (67.8, 9.0), (69.0, 8.8),
               (70.0, 8.2), (70.4, 7.5)]
    seam_x = -32.0*LENGTH_SCALE
    xs = sorted({round(float(x), 5) for x in np.linspace(-70.9, 70.9, math.ceil(141.8/AXIAL_STEP_MM)+1)}
                | {round(x*LENGTH_SCALE, 5) for x, _ in profile} | {0.0})
    vertices, faces = [], []
    roll = math.radians(ROLL_DEG[int(pose)] if roll_deg is None else roll_deg)
    for x in xs:
        source_xs = [point[0]*LENGTH_SCALE for point in profile]
        source_radii = [point[1]*(CAP_RADIUS_MM/10.9 if point[0] < -32 else BARREL_RADIUS_MM/9.0) for point in profile]
        radius = float(np.interp(x, source_xs, source_radii))
        # The molded clip rotates with the physical cross section.
        # A broad integral clip relief avoids a fragile separate prong in this first study.
        clip_axial = smoothstep((x+65*LENGTH_SCALE)/4)*smoothstep((-37*LENGTH_SCALE-x)/4)
        shift = centerline_fn(x) if centerline_fn else centerline(x, pose)
        for j in range(RADIAL_SEGMENTS):
            a = 2*math.pi*j/RADIAL_SEGMENTS
            da = math.atan2(math.sin(a-2.35), math.cos(a-2.35))
            clip = 0.85*clip_axial*math.exp(-0.5*(da/0.30)**4)
            radial = radius+clip
            y = radial*math.cos(a+roll)
            z = radial*math.sin(a+roll)
            # The body sits on the same tabletop as the wider cap. The shallow sole
            # leaves a finite contact area for every rolled pose without a support part.
            center_z = radius if seam_x <= x <= 67.8*LENGTH_SCALE else CAP_RADIUS_MM
            if -34*LENGTH_SCALE < x < seam_x:
                center_z = CAP_RADIUS_MM+(radius-CAP_RADIUS_MM)*smoothstep((x+34*LENGTH_SCALE)/(2*LENGTH_SCALE))
            height = max(0.0, center_z+z-TABLE_CONTACT_TRIM_MM)
            vertices.append((x, shift+y, height))
    for i in range(len(xs)-1):
        for j in range(RADIAL_SEGMENTS):
            k = (j+1)%RADIAL_SEGMENTS
            faces.append((i*RADIAL_SEGMENTS+j, i*RADIAL_SEGMENTS+k,
                          (i+1)*RADIAL_SEGMENTS+k, (i+1)*RADIAL_SEGMENTS+j))
    for ring in (0, len(xs)-1):
        center = len(vertices)
        vertices.append((xs[ring], centerline_fn(xs[ring]) if centerline_fn else centerline(xs[ring], pose), CAP_RADIUS_MM))
        for j in range(RADIAL_SEGMENTS):
            faces.append((center, ring*RADIAL_SEGMENTS+j,
                          ring*RADIAL_SEGMENTS+(j+1)%RADIAL_SEGMENTS))
    return vertices, faces, xs


def validate(path, obj, pose, xs, pose_name=None):
    vertices, triangles, normals = read_stl(path)
    xyz = vertices[triangles]
    cross = np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
    area2 = np.linalg.norm(cross, axis=1)
    bm = bmesh.new()
    temporary = bpy.data.meshes.new("STL integrity check")
    temporary.from_pydata(vertices.tolist(), [], triangles.tolist())
    temporary.update()
    bm.from_mesh(temporary)
    remaining, components = set(bm.verts), 0
    while remaining:
        stack = [remaining.pop()]
        components += 1
        while stack:
            for edge in stack.pop().link_edges:
                for vertex in edge.verts:
                    if vertex in remaining:
                        remaining.remove(vertex)
                        stack.append(vertex)
    tree = BVHTree.FromPolygons(vertices.tolist(), triangles.tolist(), all_triangles=True, epsilon=0)
    collisions = sum(a < b and not set(triangles[a]).intersection(triangles[b])
                     for a, b in tree.overlap(tree))
    floor = np.abs(vertices[:, 2]) < 1e-5
    floor_faces = np.all(floor[triangles], axis=1)
    contact_area = float(area2[floor_faces].sum()/2)
    # A convex support polygon encloses the projected center of mass if all signed
    # edge distances are positive. Tetrahedral integration assumes a closed shell.
    from stone_to_bread import hull
    support = hull(vertices[floor, :2])
    volume6 = np.einsum("ij,ij->i", xyz[:, 0], cross)
    com = np.sum(xyz.sum(axis=1)/4*volume6[:, None], axis=0)/volume6.sum()
    edges = np.roll(support, -1, axis=0)-support
    offset = com[:2]-support
    margins = (edges[:, 0]*offset[:, 1]-edges[:, 1]*offset[:, 0])/np.linalg.norm(edges, axis=1)
    dims = np.ptp(vertices, axis=0)
    # The analytic geometry is the design expectation; STL dimensions must agree
    # within float32 quantization, not against an arbitrary broad size tolerance.
    design_dims = np.ptp(np.asarray([v.co[:] for v in obj.data.vertices]), axis=0)
    report = dict(pose=pose_name or NAMES[int(pose)], stl=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                  stl_sha256=digest(path), mesh_fingerprint=mesh_fingerprint(obj),
                  dimensions_mm=dims.tolist(), design_dimensions_mm=design_dims.tolist(),
                  dimension_max_error_mm=float(max(abs(dims-design_dims))),
                  vertices=len(vertices), triangles=len(triangles), components=components,
                  watertight=all(e.is_manifold for e in bm.edges),
                  boundary_edges=sum(e.is_boundary for e in bm.edges),
                  nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),
                  inconsistent_winding_edges=sum(e.is_manifold and not e.is_contiguous for e in bm.edges),
                  degenerate_triangles=int(np.count_nonzero(area2 < 1e-8)),
                  stl_normal_disagreements=int(np.count_nonzero(np.einsum("ij,ij->i", cross, normals) <= 0)),
                  nonadjacent_bvh_overlap_pairs=collisions, signed_volume_mm3=float(volume6.sum()/6),
                  minimum_table_clearance_mm=float(vertices[:, 2].min()),
                  contact_area_mm2=contact_area, support_hull_margin_mm=float(margins.min()),
                  center_of_mass_mm=com.tolist(), contact_span_mm=np.ptp(vertices[floor], axis=0)[:2].tolist(),
                  nominal_body_diameter_mm=11.9, nominal_cap_diameter_mm=13.2,
                  reference_overall_length_mm=141.8,
                  clip_relief_height_mm=0.85,
                  local_thickness_note="Solid mesh; broad clip relief is integral. Exhaustive minimum feature thickness not verified.")
    report["passed"] = bool(report["dimension_max_error_mm"] < 0.005 and components == 1
                            and report["watertight"] and report["inconsistent_winding_edges"] == 0
                            and report["degenerate_triangles"] == 0 and report["stl_normal_disagreements"] == 0
                            and collisions == 0 and report["signed_volume_mm3"] > 0
                            and report["minimum_table_clearance_mm"] >= -1e-5
                            and contact_area > 20 and report["support_hull_margin_mm"] > 1)
    bm.free()
    bpy.data.meshes.remove(temporary)
    return report


def material(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def paint_pose(obj, neutral_style, xs):
    for polygon in obj.data.polygons:
        polygon.material_index = 1 if neutral_style else 0


def environment(scene):
    floor = material("matte warm-gray tabletop", (0.24, 0.23, 0.22), 0.86)
    bpy.ops.mesh.primitive_plane_add(size=500, location=(0, 0, -0.08))
    bpy.context.object.name = "Preview tabletop"
    bpy.context.object.data.materials.append(floor)
    bpy.context.object.hide_render = False
    world = bpy.data.worlds.new("neutral studio world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.55, 0.55, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    scene.world = world
    for name, location, power, size in (("soft key", (-65, -90, 135), 1700, 110),
                                        ("soft fill", (85, 35, 90), 1050, 90)):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = power, "DISK", size
        lamp = bpy.data.objects.new(name, data)
        scene.collection.objects.link(lamp)
        lamp.location = location
        lamp.rotation_euler = (Vector((0, 0, 0))-lamp.location).to_track_quat("-Z", "Y").to_euler()
    for name, location, target, scale in (("front oblique", (0, -210, 245), (0, 0, 11), 185),
                                          ("top", (0, 0, 270), (0, 0, 0), 185)):
        data = bpy.data.cameras.new(name)
        data.type = "ORTHO"
        data.ortho_scale = scale
        cam = bpy.data.objects.new(name, data)
        scene.collection.objects.link(cam)
        cam.location = location
        cam.rotation_euler = (Vector(target)-cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 20
    scene.render.resolution_x, scene.render.resolution_y = 800, 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.camera = bpy.data.objects["front oblique"]


def assemble(preview):
    front = [preview/f"{name}-mackee-front.png" for name in NAMES]
    neutral = [preview/f"{name}-neutral-front.png" for name in NAMES]
    top = [preview/f"{name}-neutral-top.png" for name in NAMES]
    for files, target in ((front, "contact-front.png"), (neutral, "contact-neutral-front.png"),
                          (top, "contact-top.png")):
        command = ["magick", "montage", "-background", "#191919", "-fill", "white",
                   "-font", "Helvetica", "-pointsize", "21"]
        for name, path in zip(NAMES, files):
            command.extend(["-label", name.upper(), str(path)])
        command.extend(["-geometry", "600x405+8+16", "-tile", "2x2", str(preview/target)])
        subprocess.run(command, check=True)
    command = ["magick"]
    for path, delay in zip(front, (33, 33, 33, 58)):
        command.extend(["-delay", str(delay), str(path)])
    command.extend(["-resize", "800x540", "-loop", "0", str(preview/"sequence.gif")])
    subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--geometry-only", action="store_true")
    parser.add_argument("--front-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    output = args.output_root.resolve()
    export = output/"exports"/"rolling-wavy-pen"
    preview = output/"previews"/"rolling-wavy-pen"
    export.mkdir(parents=True, exist_ok=True)
    if not args.geometry_only:
        preview.mkdir(parents=True, exist_ok=True)
        (output/"models").mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    objects, reports, sections = [], [], []
    black = material("solid black marker plastic", (0.014, 0.014, 0.015), 0.30)
    neutral = material("neutral shape review", (0.51, 0.54, 0.58), 0.66)
    for pose, name in enumerate(NAMES):
        vertices, faces, xs = geometry(pose)
        obj = make_mesh(scene, name, vertices, faces)
        obj["generator"] = "scripts/rolling_wavy_pen.py"
        obj["rolling_angle_degrees"] = ROLL_DEG[pose]
        obj["filming_y_mm"] = FILM_Y_MM[pose]
        for mat in (black, neutral):
            obj.data.materials.append(mat)
        paint_pose(obj, False, xs)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        for other in bpy.context.selected_objects:
            if other != obj:
                other.select_set(False)
        path = export/f"{name}.stl"
        bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True,
                              use_scene_unit=False, global_scale=1, apply_modifiers=True,
                              forward_axis="Y", up_axis="Z")
        obj.select_set(False)
        report = validate(path, obj, pose, xs)
        if not report["passed"]:
            raise RuntimeError(f"{name} failed validation: {report}")
        reports.append(report)
        obj.location.y = FILM_Y_MM[pose]
        objects.append(obj)
        sections.append(xs)
        print(f"VALID {name}: {report['dimensions_mm']} contact {report['contact_area_mm2']:.1f} margin {report['support_hull_margin_mm']:.2f}", flush=True)
    if not args.geometry_only:
        environment(scene)
        for pose, obj in enumerate(objects):
            for other in objects:
                other.hide_render = other is not obj
            styles = (("mackee", "mackee-front"),) if args.front_only else (("mackee", "mackee-front"), ("neutral", "neutral-front"))
            for style, suffix in styles:
                paint_pose(obj, style == "neutral", sections[pose])
                scene.camera = bpy.data.objects["front oblique"]
                scene.render.filepath = str(preview/f"{NAMES[pose]}-{suffix}.png")
                bpy.ops.render.render(write_still=True)
            if not args.front_only:
                paint_pose(obj, True, sections[pose])
                scene.camera = bpy.data.objects["top"]
                scene.render.filepath = str(preview/f"{NAMES[pose]}-neutral-top.png")
                bpy.ops.render.render(write_still=True)
        for pose, obj in enumerate(objects):
            obj.hide_render = obj is not objects[0]
            paint_pose(obj, False, sections[pose])
        scene.camera = bpy.data.objects["front oblique"]
        scene["motif"] = "Rolling Wavy Pen — four-shape study, pending visual review"
        scene["generator"] = "scripts/rolling_wavy_pen.py"
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(output/"models"/"rolling-wavy-pen.blend"))
        assemble(preview)
    manifest = dict(status="pending visual review", blender=bpy.app.version_string,
                    source="scripts/rolling_wavy_pen.py", poses=reports,
                    reference_product="Zebra Mackee Gokuhoso", reference_length_mm=141.8,
                    reference_shaft_diameter_mm=11.9, render_colors="black only; no label, text, or logo",
                    rolling_angle_degrees=list(ROLL_DEG), filming_y_mm=list(FILM_Y_MM),
                    film_placement_separate_from_stl=True,
                    validation_scope="STL topology, normals, degenerate triangles, BVH nonadjacent overlap, finite contact and COM support",
                    unverified=["exhaustive minimum feature thickness", "slicer behavior", "support requirements", "physical print"])
    manifest_path = (preview if not args.geometry_only else export)/"validation.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n")


if __name__ == "__main__":
    main()
