"""Render existing Stones/Cup meshes for review; never generate or save geometry.

Blender --background --threads 8 --python-exit-code 1 --python scripts/review_previews.py
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate import save_contact_sheet


ROOT = Path(__file__).resolve().parents[1]
ORDER = [1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2, 1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def camera_settings(scene):
    camera = scene.camera
    return dict(location=list(camera.location), rotation=list(camera.rotation_euler),
                type=camera.data.type, scale=camera.data.ortho_scale,
                resolution=[scene.render.resolution_x, scene.render.resolution_y],
                percentage=scene.render.resolution_percentage)


def rig_settings(scene):
    # Store every fixed light and the world nodes without relying on localized node names.
    lights = [dict(name=o.name, location=list(o.location), rotation=list(o.rotation_euler),
                   energy=o.data.energy, color=list(o.data.color), size=o.data.size)
              for o in scene.objects if o.type == "LIGHT"]
    backgrounds = [dict(color=list(n.inputs[0].default_value), strength=n.inputs[1].default_value)
                   for n in scene.world.node_tree.nodes if n.type == "BACKGROUND"]
    return dict(camera=camera_settings(scene), lights=lights, world=backgrounds,
                engine=scene.render.engine, samples=scene.cycles.samples,
                view_transform=scene.view_settings.view_transform,
                exposure=scene.view_settings.exposure, gamma=scene.view_settings.gamma)


def surface_settings(obj):
    settings = []
    for material in obj.data.materials:
        shader = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        settings.append(dict(color=list(shader.inputs["Base Color"].default_value),
                             roughness=shader.inputs["Roughness"].default_value))
    return settings


def animation(paths, destination):
    # Only repeat the supplied still images; resizing/palette encoding adds no time samples.
    command = ["magick", "-delay", "40"]+[str(paths[f-1]) for f in ORDER]
    # One palette across all states avoids palette changes being mistaken for shape flicker.
    command += ["-resize", "720x480", "-dither", "FloydSteinberg", "+remap",
                "-layers", "Optimize", "-strip", "-loop", "0", str(destination)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    delays = subprocess.check_output(["magick", "identify", "-format", "%T\\n", str(destination)], text=True)
    assert [int(value) for value in delays.split()] == [40]*13
    # Decode composited GIF frames and compare them against the seven forward states.
    raw = subprocess.check_output(["magick", str(destination), "-coalesce", "-resize", "180x120!",
                                   "-depth", "8", "RGB:-"])
    decoded = np.frombuffer(raw, dtype=np.uint8).reshape(13, 120, 180, 3).astype(np.int16)
    nearest = [int(np.argmin(np.abs(decoded[:7]-frame).mean(axis=(1, 2, 3))))+1 for frame in decoded]
    assert nearest == ORDER, "Decoded GIF does not match the requested source-state order"
    # The Netscape application extension explicitly encodes an infinite loop count of zero.
    assert b"NETSCAPE2.0\x03\x01\x00\x00" in destination.read_bytes()
    return dict(path=str(destination.relative_to(ROOT)), sha256=digest(destination),
                sequence=ORDER, decoded_sequence=nearest, frames=13,
                milliseconds_per_frame=400, duration_seconds=5.2, continuous_loop=True,
                canvas=[720, 480], interpolation=False, shared_palette=True,
                dithering="FloydSteinberg")


def main():
    assert bpy.app.version[:2] == (4, 5), "Blender 4.5 LTS required"
    protected = sorted((ROOT/"models").glob("*.blend"))+sorted((ROOT/"exports").glob("*/*.stl"))
    protected += sorted(p for p in (ROOT/"previews"/"pen").iterdir() if p.is_file())
    protected += [ROOT/"scripts"/name for name in ("generate.py", "pen_previews.py")]
    # Existing oblique images and contact sheets are reused byte-for-byte.
    for motif in ("stones", "cup"):
        protected += [ROOT/"previews"/motif/f"frame-{f:02}.png" for f in range(1, 8)]
        protected.append(ROOT/"previews"/motif/"contact-sheet.png")
    before = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    report = dict(status="Awaiting final visual review; neither Stones nor Cup is finally approved",
                  blender=bpy.app.version_string, geometry_regenerated=False, motifs={})
    for motif in ("stones", "cup"):
        bpy.ops.wm.open_mainfile(filepath=str(ROOT/"models"/f"{motif}.blend"), load_ui=False, use_scripts=False)
        scene = bpy.context.scene
        objects = [scene.objects[f"{motif}/frame-{f:02}"] for f in range(1, 8)]
        assert all(surface_settings(obj) == surface_settings(objects[0]) for obj in objects)
        assert all(obj.matrix_basis == objects[0].matrix_basis for obj in objects)
        entry = dict(oblique=rig_settings(scene), shared_surface=surface_settings(objects[0]),
                     oblique_sources_reused=True, contact_sheet=f"previews/{motif}/contact-sheet.png")
        paths = [ROOT/"previews"/motif/f"frame-{f:02}.png" for f in range(1, 8)]
        entry["oblique_animation"] = animation(paths, ROOT/"previews"/motif/"forward-reverse.gif")
        # Match the existing cup endpoint top camera; this temporary change is never saved.
        scene.camera.location = (0, 0, 260)
        scene.camera.rotation_euler = (0, 0, 0)
        fixed = rig_settings(scene)
        top_paths = []
        for frame, obj in enumerate(objects, 1):
            for other in objects:
                other.hide_render = other != obj
                other.hide_set(other != obj)
            assert rig_settings(scene) == fixed
            path = ROOT/"previews"/motif/f"frame-{frame:02}-top.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            top_paths.append(path)
        sheet = ROOT/"previews"/motif/"contact-sheet-top.png"
        save_contact_sheet(top_paths, sheet)
        entry["top"] = fixed
        entry["top_contact_sheet"] = str(sheet.relative_to(ROOT))
        entry["top_source_sha256"] = {p.name: digest(p) for p in top_paths}
        if motif == "cup":
            entry["top_animation"] = animation(top_paths, ROOT/"previews"/motif/"forward-reverse-top.gif")
        report["motifs"][motif] = entry
    after = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    assert before == after, "Protected geometry, Pen asset or existing oblique preview changed"
    report["protected_assets_unchanged"] = True
    report["protected_sha256"] = after
    (ROOT/"previews"/"review-validation.json").write_text(json.dumps(report, indent=2)+"\n")
    print("Stones/Cup previews complete; all protected assets unchanged; awaiting visual review.")


if __name__ == "__main__":
    main()
