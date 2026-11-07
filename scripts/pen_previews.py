"""Render the saved pen endpoints without regenerating or saving any model.

Blender --background --threads 8 --python-exit-code 1 --python scripts/pen_previews.py
"""

import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate import pen_table_basis, save_comparison


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/"previews"/"pen"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def camera_settings(scene):
    camera = scene.camera
    return dict(location=list(camera.location), rotation=list(camera.rotation_euler),
                type=camera.data.type, ortho_scale=camera.data.ortho_scale,
                resolution=[scene.render.resolution_x, scene.render.resolution_y],
                percentage=scene.render.resolution_percentage)


def section_points(obj):
    # The procedural mesh contains an exact ordered ring at X=0, so no cutting is needed.
    assert not obj.modifiers
    points = [tuple(v.co) for v in obj.data.vertices if abs(v.co.x) < 1e-6]
    assert len(points) == 128, "Expected one complete source ring at the center"
    return points


def emission(name, color):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    shader = nodes.new("ShaderNodeEmission")
    shader.inputs[0].default_value = (*color, 1)
    output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(shader.outputs[0], output.inputs[0])
    return material


def line(scene, name, yz, material, radius=0.055, closed=False, layer=0):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(yz)-1)
    for point, (y, z) in zip(spline.points, yz):
        point.co = (layer, y, z+10.9, 1)
    spline.use_cyclic_u = closed
    obj = bpy.data.objects.new(name, curve)
    scene.collection.objects.link(obj)
    curve.materials.append(material)


def label(scene, body, y, z, material, size=1.05):
    curve = bpy.data.curves.new(body, "FONT")
    curve.body, curve.size = body, size
    obj = bpy.data.objects.new(body, curve)
    scene.collection.objects.link(obj)
    # Local text X/Y becomes world Y/Z; its face points toward the +X inspection camera.
    obj.rotation_euler = Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0))).to_euler()
    obj.location = (0.3, y, z+10.9)
    curve.materials.append(material)


def top_centerlines(scene, objects, basis):
    blue = emission("Original centerline", (0.025, 0.20, 0.65))
    orange = emission("Displaced centerline", (0.85, 0.13, 0.025))
    up, axis, near = basis["up"], basis["axis"], basis["near"]
    screen_up = up.cross(axis).normalized()
    origin = basis["center"]+up*30

    def stroke(name, points, material):
        curve = bpy.data.curves.new(name, "CURVE")
        curve.dimensions, curve.bevel_depth = "3D", 0.16
        spline = curve.splines.new("POLY")
        spline.points.add(len(points)-1)
        for point, position in zip(spline.points, points):
            point.co = (*position, 1)
        obj = bpy.data.objects.new(name, curve)
        scene.collection.objects.link(obj)
        curve.materials.append(material)
        return obj

    def text(body, x, y, material):
        curve = bpy.data.curves.new(body, "FONT")
        curve.body, curve.size = body, 2.3
        obj = bpy.data.objects.new(body, curve)
        scene.collection.objects.link(obj)
        obj.rotation_euler = Matrix((axis, screen_up, up)).transposed().to_euler()
        obj.location = origin+axis*x+screen_up*y
        curve.materials.append(material)
        return obj

    # Extract material centerlines from matching original crown/sole meridians of every ring.
    paths = []
    for obj in objects:
        points = []
        for index in range(0, len(obj.data.vertices)-2, 128):
            pair = [basis["matrix"]@obj.data.vertices[index+j].co for j in (32, 96)]
            center = (pair[0]+pair[1])/2
            delta = center-basis["center"]
            points.append(origin+axis*delta.dot(axis)+near*delta.dot(near))
        paths.append(points)
    overlays = [stroke("Original centerline", paths[0], blue),
                text("BLUE: original centerline", -65, 29, blue)]
    displacement = max((p-origin).dot(near) for p in paths[1])
    revised = [stroke("Revised material centerline", [p for p in paths[1]
                if abs((p-origin).dot(axis)) <= 20], orange),
               text(f"ORANGE: revised centerline (+{displacement:.1f} mm at center)", -65, 23, orange)]
    overlays += revised
    # An explicit near arrow follows the camera-derived tabletop direction, not a world axis.
    tip = origin+axis*45+near*34
    overlays.append(stroke("Near direction", [tip-near*10, tip, tip-near*2-axis, tip,
                                               tip-near*2+axis], blue))
    overlays.append(text("NEAR", 49, -30, blue))
    return overlays, revised


def cross_section(sections, basis):
    scene = bpy.data.scenes.new("Pen section overlay (preview only)")
    bpy.context.window.scene = scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    scene.render.resolution_x, scene.render.resolution_y = 1500, 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world = bpy.data.worlds.new("Diagram background")
    scene.world.use_nodes = True
    background = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    background.inputs[0].default_value = (1, 1, 1, 1)
    background.inputs[1].default_value = 1
    blue = emission("Frame 01 outline", (0.025, 0.20, 0.65))
    orange = emission("Frame 07 outline", (0.85, 0.13, 0.025))
    ink = emission("Diagram text", (0.015, 0.02, 0.03))
    grid = emission("5 mm grid", (0.64, 0.67, 0.70))
    for value in range(-10, 21, 5):
        line(scene, "Grid", [(value, -12), (value, 12)], grid, 0.014, layer=-0.2)
        line(scene, "Grid", [(-12, value), (21, value)], grid, 0.014, layer=-0.2)
    center_height = (basis["center"]-basis["table_origin"]).dot(basis["up"])
    measurements = []
    for frame, points, material in ((1, sections[0], blue), (7, sections[1], orange)):
        # Use true saved vertex positions, with one common datum and no independent alignment.
        world = [basis["matrix"]@Vector(p) for p in points]
        q = [(p-basis["center"]).dot(basis["near"]) for p in world]
        h = [(p-basis["table_origin"]).dot(basis["up"]) for p in world]
        measurements.append(dict(height=max(h)-min(h), width=max(q)-min(q), near=max(q), far=min(q)))
        line(scene, f"Frame {frame:02} center outline", list(zip(q, [z-center_height for z in h])),
             material, 0.075, closed=True, layer=0 if frame == 1 else 0.1)
    line(scene, "Origin", [(-0.5, 0), (0.5, 0)], ink, 0.025, layer=0.2)
    line(scene, "Origin", [(0, -0.5), (0, 0.5)], ink, 0.025, layer=0.2)
    # In this conceptual section, +Y is horizontal toward the viewer and +Z is tabletop up.
    line(scene, "Horizontal far to near spreading", [(-12, 14.5), (21, 14.5)], ink, 0.085)
    for sign in (-1, 1):
        line(scene, "Horizontal arrow head", [(19.5, 14.5+sign*0.65), (21, 14.5)], ink, 0.085)
    label(scene, "FAR SIDE", -12, 16, ink)
    label(scene, "NEAR SIDE", 15, 16, ink)
    label(scene, "Spreading along tabletop", -12, 12.3, ink, 0.95)
    line(scene, "Downward pressure", [(-16, 9), (-16, -8)], ink, 0.085)
    line(scene, "Downward arrow head", [(-16.6, -6.5), (-16, -8), (-15.4, -6.5)], ink, 0.085)
    label(scene, "DOWN", -21, 2, ink)
    line(scene, "Actual tabletop reference", [(-13, -center_height), (22, -center_height)], ink, 0.07)
    label(scene, "TABLETOP  h = 0", -13, -center_height-2, ink)
    label(scene, "CENTER CROSS SECTION", -22, 22, ink, 1.65)
    label(scene, "X = 0 mm | along marker axis | same origin and scale", -22, 19.6, ink)
    label(scene, "Frame 01 - original", 25, 0, blue, 1.2)
    label(scene, "Frame 07 - sloped + bowed", 25, -2.5, orange, 1.2)
    a, b = measurements
    label(scene, f"Height: {a['height']:.1f} -> {b['height']:.1f} mm", 25, -6, ink)
    label(scene, f"Width: {a['width']:.1f} -> {b['width']:.1f} mm", 25, -8, ink)
    label(scene, f"Near: +{a['near']:.1f} -> +{b['near']:.1f} mm", 25, -10, ink)
    label(scene, f"Far: {a['far']:.1f} -> {b['far']:.1f} mm", 25, -12, ink)
    meridians = [basis["matrix"]@Vector(sections[1][index]) for index in (32, 96)]
    displacement = sum((p-basis["center"]).dot(basis["near"]) for p in meridians)/2
    label(scene, f"Material centerline: +{displacement:.1f} mm", 25, -14, ink)
    label(scene, "Blue and orange outlines overlay directly.", -22, -17, ink)
    label(scene, "Grid: 5 mm | +Y = near, +Z = up | cross = original center", -22, -19, ink, 0.9)
    label(scene, "Outlines extracted from saved meshes. No geometry changed.", -22, -21, ink, 0.95)
    data = bpy.data.cameras.new("Section inspection camera")
    camera = bpy.data.objects.new("Section inspection camera", data)
    scene.collection.objects.link(camera)
    camera.location = (100, 12, 10.9)
    camera.rotation_euler = Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0))).to_euler()
    data.type, data.ortho_scale = "ORTHO", 85
    scene.camera = camera
    scene.render.filepath = str(OUTPUT/"comparison-section.png")
    bpy.ops.render.render(write_still=True)
    return camera_settings(scene)


def main():
    assert bpy.app.version[:2] == (4, 5), "Blender 4.5 LTS required"
    protected = sorted((ROOT/"models").glob("*.blend")) + sorted((ROOT/"exports").glob("*/*.stl"))
    protected += sorted((ROOT/"previews"/"stones").glob("*.png"))
    protected += sorted((ROOT/"previews"/"cup").glob("*.png"))
    before = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/"models"/"pen.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    objects = [next(o for o in scene.objects if o.name == f"pen/frame-{f:02}") for f in (1, 7)]
    sections = [section_points(o) for o in objects]
    basis = pen_table_basis(scene)
    metadata = dict(blender=bpy.app.version_string, horizontal_near=list(basis["near"]),
                    tabletop_normal=list(basis["up"]), tabletop_origin=list(basis["table_origin"]),
                    cross_section_plane="Marker X=0; horizontal +Y toward viewer; vertical +Z tabletop up", views={})
    top_overlays, revised_overlays = [], []
    for view in ("oblique", "top", "side"):
        if view == "top":
            # Directly above the common datum: X runs horizontally across both top renders.
            plane_center = basis["center"]-basis["up"]*(basis["center"]-basis["table_origin"]).dot(basis["up"])
            scene.camera.location = plane_center+basis["up"]*260
            screen_up = basis["up"].cross(basis["axis"]).normalized()
            scene.camera.rotation_euler = Matrix((basis["axis"], screen_up, basis["up"])).transposed().to_euler()
            scene.camera.data.ortho_scale = 177
            top_overlays, revised_overlays = top_centerlines(scene, objects, basis)
        elif view == "side":
            for overlay in top_overlays:
                overlay.hide_render = True
            scene.camera.location = basis["center"]+basis["near"]*260
            scene.camera.rotation_euler = Matrix((basis["axis"], basis["up"], basis["near"])).transposed().to_euler()
        settings = camera_settings(scene)
        paths = []
        for frame, obj in zip((1, 7), objects):
            if view == "top":
                for overlay in revised_overlays:
                    overlay.hide_render = frame != 7
            for other in scene.objects:
                if other.name.startswith("pen/frame-"):
                    other.hide_render = other != obj
                    other.hide_set(other != obj)
            assert camera_settings(scene) == settings
            path = OUTPUT/f"frame-{frame:02}-{view}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            paths.append(path)
        save_comparison(paths, OUTPUT/f"comparison-{view}.png")
        if view == "oblique":
            save_comparison(paths, OUTPUT/"comparison.png")
            (OUTPUT/"frame-07.png").write_bytes(paths[-1].read_bytes())
        metadata["views"][view] = dict(camera=settings, left="frame-01", right="frame-07")
    metadata["views"]["section"] = dict(camera=cross_section(sections, basis),
                                          original_outline="blue", compressed_outline="orange",
                                          shared_origin=True, shared_scale=True)
    after = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    assert before == after, "Protected model/export/other-motif assets changed"
    metadata["protected_assets_unchanged"] = True
    metadata["protected_asset_sha256"] = after
    (OUTPUT/"view-settings.json").write_text(json.dumps(metadata, indent=2)+"\n")
    print("Preview-only run complete; all model, STL, stones and cup hashes unchanged.")


if __name__ == "__main__":
    main()
