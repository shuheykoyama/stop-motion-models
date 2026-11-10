"""Export and reconstruct approved cube-pen v2 using rigid, grounded STL props."""
import csv
import json
import math
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import bpy
import gpu
import numpy as np
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rolling_cube_pen_v2 as study
from generate import read_stl
from stone_to_fireworks_print_set_v1 import surface_hash as raw_surface_hash

ROOT = study.ROOT
OUT = ROOT / 'previews/rolling-cube-pen/print-set-v1'
EXPORT = ROOT / 'exports/rolling-cube-pen/print-set-v1'
MODEL = ROOT / 'models/rolling-cube-pen-print-set-v1.blend'
TOLERANCE = 2e-5  # Millimeter tolerance for float32 mesh coordinates, not a design approximation.


def surface_hash(vertices, faces):
    # IEEE negative zero and positive zero have equal coordinates but different bytes.
    normalized = np.asarray(vertices, dtype=np.float32).copy()
    normalized[normalized == 0] = 0
    return raw_surface_hash(normalized, faces)


def mesh_arrays(obj):
    return (np.array([v.co[:] for v in obj.data.vertices]),
            np.array([p.vertices[:] for p in obj.data.polygons]))


def surface_samples(vertices, faces):
    # Include triangle interiors and edges so coincident vertex sets alone cannot imply equality.
    triangles = vertices[faces]
    return np.concatenate((vertices, triangles.mean(axis=1),
                           (triangles[:, 0] + triangles[:, 1]) / 2,
                           (triangles[:, 1] + triangles[:, 2]) / 2,
                           (triangles[:, 2] + triangles[:, 0]) / 2))


def surface_distance(a, af, b, bf):
    # Bidirectional sampled surface distance also detects differing triangle diagonals on bends.
    worst = 0.0
    for vertices, faces, other, other_faces in ((a, af, b, bf), (b, bf, a, af)):
        tree = BVHTree.FromPolygons(other.tolist(), other_faces.tolist(), all_triangles=True)
        for point in surface_samples(vertices, faces):
            distance = tree.find_nearest(Vector(point))[3]
            worst = max(worst, distance)
            if worst > TOLERANCE:
                return worst
    return worst


def rigid_match(target, candidate):
    a, af = target['vertices'], target['faces']
    b, bf = candidate['vertices'], candidate['faces']
    rotations = []
    if a.shape == b.shape:
        # Kabsch fitting tests rotations, never scale or reflection, with original vertex correspondence.
        u, _, vt = np.linalg.svd((b - b.mean(0)).T @ (a - a.mean(0)))
        rotation = vt.T @ u.T
        if np.linalg.det(rotation) > 0:
            rotations.append(rotation)
    for angle in (0, 90, 180, 270):
        # Cube symmetry can permute radial vertices; test upright rigid yaw independently of indices.
        t = math.radians(angle)
        rotations.append(np.array([[math.cos(t), -math.sin(t), 0],
                                   [math.sin(t), math.cos(t), 0], [0, 0, 1]]))
    tree = KDTree(len(a))
    for i, point in enumerate(a):
        tree.insert(Vector(point), i)
    tree.balance()
    for rotation in rotations:
        translation = a.mean(0) - b.mean(0) @ rotation.T
        transformed = b @ rotation.T + translation
        # Quickly reject differing resting soles before the more expensive surface test.
        error = max(tree.find(Vector(point))[2] for point in transformed)
        if error > TOLERANCE:
            continue
        error = surface_distance(a, af, transformed, bf)
        if error <= TOLERANCE:
            return dict(rotation=rotation.tolist(), translation=translation.tolist(),
                        max_sampled_surface_error_mm=error)
    return None


def export_source(obj, path):
    # Export a temporary identity-transform copy so filming translation/rotation is not applied twice.
    copied = obj.copy()
    copied.data = obj.data.copy()
    copied.animation_data_clear()
    bpy.context.scene.collection.objects.link(copied)
    copied.matrix_world = Matrix.Identity(4)
    copied.hide_render = False
    copied.hide_viewport = False
    bpy.ops.object.select_all(action='DESELECT')
    copied.select_set(True)
    bpy.context.view_layer.objects.active = copied
    bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True,
                          global_scale=1, use_scene_unit=False, forward_axis='Y', up_axis='Z')
    bpy.data.objects.remove(copied, do_unlink=True)


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def assemble_gif(images, records, path):
    command = ['magick']
    previous = 0
    for image, record in zip(images, records):
        cumulative = round((record['exposure_start'] - 1 + record['exposures_12fps']) * 100 / 12)
        command += ['-delay', str(cumulative - previous), str(image)]
        previous = cumulative
    subprocess.run(command + ['-loop', '0', str(path)], check=True)


def main():
    assert bpy.app.version[:2] == (4, 5)
    OUT.mkdir(parents=True, exist_ok=True)
    EXPORT.mkdir(parents=True, exist_ok=True)
    (OUT / 'frames').mkdir(exist_ok=True)
    (OUT / 'selected').mkdir(exist_ok=True)
    (OUT / 'comparison').mkdir(exist_ok=True)
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    paths = [ROOT / p for p in tracked if p and (ROOT / p).is_file()]
    paths += [p for p in study.OUT.rglob('*') if p.is_file()]
    paths += [study.MODEL, ROOT / 'scripts/rolling_cube_pen_v2.py', ROOT / 'scripts/rolling_cube_pen.py',
              ROOT / 'models/rolling-cube-pen.blend']
    protected = {str(p.relative_to(ROOT)): study.digest(p) for p in paths}
    source = json.loads((study.OUT / 'manifest-v2.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(study.MODEL), use_scripts=False)
    scene = bpy.context.scene
    scene.frame_set(1)
    camera = study.camera_signature(scene)
    source_objects = {r['id']: bpy.data.objects[r['id']] for r in source['mesh_validation']}
    data = {}
    groups = []
    assignments = {}
    for row in source['mesh_validation']:
        obj = source_objects[row['id']]
        assert study.base.mesh_fingerprint(obj) == row['mesh_fingerprint']
        vertices, faces = mesh_arrays(obj)
        data[row['id']] = dict(vertices=vertices, faces=faces, row=row,
                               materials=list(obj.data.materials),
                               face_materials=[p.material_index for p in obj.data.polygons])
        target = data[row['id']]
        fit = None
        for group in groups:
            other = data[group['source_mesh']]
            if (row['cell_index'] is None) != (other['row']['cell_index'] is None):
                continue
            if abs(row['volume_mm3'] - other['row']['volume_mm3']) > .01:
                continue
            fit = rigid_match(target, other)
            if fit is not None:
                break
        if fit is None:
            group = dict(id=f'pose-{len(groups)+1:02}', source_mesh=row['id'],
                         kind='whole-pen' if row['cell_index'] is None else 'cube')
            groups.append(group)
            fit = dict(rotation=np.eye(3).tolist(), translation=[0, 0, 0], max_sampled_surface_error_mm=0)
        assignments[row['id']] = dict(stl_id=group['id'], **fit)
    print('SELECTED', len(groups), 'STL types from', len(data), 'source meshes', flush=True)

    templates = {}
    validations = []
    for group in groups:
        original = data[group['source_mesh']]
        destination = EXPORT / (group['id'] + '.stl')
        export_source(source_objects[group['source_mesh']], destination)
        # Repeat export into a temporary directory to verify serialization determinism.
        with tempfile.TemporaryDirectory(prefix='cube-pen-stl-') as directory:
            repeated = Path(directory) / destination.name
            export_source(source_objects[group['source_mesh']], repeated)
            assert study.digest(destination) == study.digest(repeated)
        vertices, faces, normals = read_stl(destination)
        assert np.isfinite(vertices).all() and np.isfinite(normals).all()
        assert surface_hash(vertices, faces) == surface_hash(original['vertices'], original['faces'])
        assert len(faces) == len(original['face_materials'])
        obj = study.base.make_mesh(scene, 'STL-template/' + group['id'], vertices.tolist(), faces.tolist())
        for material in original['materials']:
            obj.data.materials.append(material)
        for polygon, index in zip(obj.data.polygons, original['face_materials']):
            polygon.use_smooth = True
            polygon.material_index = index
        checked = study.validate(obj)
        tri = vertices[faces]
        geometric = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        assert np.all(np.sum(geometric * normals, axis=1) > 0)
        source_frame = next(r['frame'] for r in source['frames']
                            if any(p['mesh_id'] == group['source_mesh'] for p in r['parts']))
        group.update(stl=str(destination.relative_to(ROOT)), source_v2_frame=source_frame,
                     source_cell_index=original['row']['cell_index'],
                     source_roll_degrees=original['row']['roll_degrees'],
                     source_mesh_fingerprint=original['row']['mesh_fingerprint'],
                     stl_sha256=study.digest(destination), stl_surface_sha256=surface_hash(vertices, faces),
                     render_mesh_fingerprint=study.base.mesh_fingerprint(obj),
                     dimensions_mm=checked['dimensions_mm'], source_surface_identical=True,
                     repeated_export_sha256_match=True)
        checked.update(stl_id=group['id'], stl=group['stl'], normal_disagreements=0)
        validations.append(checked)
        templates[group['id']] = obj
        print('VALIDATED', group['id'], group['kind'], flush=True)

    frames = []
    maximum = Counter()
    usage = Counter()
    phase_usage = {phase: Counter() for phase in (1, 2, 3)}
    for row in source['frames']:
        parts = []
        occurrences = Counter()
        for source_part in row['parts']:
            match = assignments[source_part['mesh_id']]
            stl_id = match['stl_id']
            occurrences[stl_id] += 1
            # Compose reuse fitting with approved filming placement; scale remains exactly one.
            placement = np.asarray(Euler(np.radians(source_part['rotation_degrees']), 'XYZ').to_matrix())
            rotation = placement @ np.asarray(match['rotation'])
            translation = placement @ np.asarray(match['translation']) + source_part['position_mm']
            angles = [math.degrees(a) for a in Matrix(rotation).to_euler('XYZ')]
            template = templates[stl_id]
            vertices, faces = mesh_arrays(template)
            world = vertices @ rotation.T + translation
            approved = data[source_part['mesh_id']]
            ideal = approved['vertices'] @ placement.T + source_part['position_mm']
            error = surface_distance(ideal, approved['faces'], world, faces)
            assert error <= TOLERANCE
            volume, center, area, margin = study.support_properties(world, faces)
            assert abs(float(world[:, 2].min())) < TOLERANCE and margin > 0 and area > 0
            parts.append(dict(instance_id=f'{stl_id}-copy-{occurrences[stl_id]:02}', stl_id=stl_id,
                              stl=str((EXPORT / (stl_id + '.stl')).relative_to(ROOT)),
                              source_v2_mesh=source_part['mesh_id'], cell_index=source_part['cell_index'],
                              position_mm=translation.tolist(), rotation_degrees=angles, scale=[1, 1, 1],
                              world_dimensions_mm=np.ptp(world, axis=0).tolist(),
                              minimum_world_z_mm=float(world[:, 2].min()), contact_area_mm2=area,
                              support_margin_mm=margin, sampled_surface_error_mm=error))
        # Positive disjoint world-X intervals rule out collisions between separated solids.
        if len(parts) > 1:
            boxes = []
            for part in parts:
                vertices, _ = mesh_arrays(templates[part['stl_id']])
                rotation = np.asarray(Euler(np.radians(part['rotation_degrees']), 'XYZ').to_matrix())
                world = vertices @ rotation.T + part['position_mm']
                boxes.append((float(world[:, 0].min()), float(world[:, 0].max())))
            gaps = [a[0] - b[1] for a, b in zip(boxes, boxes[1:])]
            assert min(gaps) > 0
            assert np.allclose(gaps, row['projected_X_gaps_mm'], atol=4e-5)
        maximum |= occurrences
        usage.update(occurrences)
        phase_usage[row['phase']].update(occurrences)
        frames.append(dict(frame=row['frame'], phase=row['phase'], direction=row['direction'],
                           stroke_in_phase=row['stroke_in_phase'], exposure_start=row['exposure_start'],
                           exposures_12fps=row['exposures_12fps'], parts=parts,
                           changes_from_v2='None; rigid reuse within float32 tolerance only.'))

    instances = {}
    for group in groups:
        stl_id = group['id']
        group.update(required_print_copies=maximum[stl_id], object_appearances=usage[stl_id],
                     used_frames=[r['frame'] for r in frames if any(p['stl_id'] == stl_id for p in r['parts'])],
                     used_phases=[phase for phase, counts in phase_usage.items() if counts[stl_id]])
        for copy in range(1, maximum[stl_id] + 1):
            name = f'{stl_id}-copy-{copy:02}'
            obj = bpy.data.objects.new(name, templates[stl_id].data)
            scene.collection.objects.link(obj)
            obj['stl_id'] = stl_id
            obj['stl_path'] = group['stl']
            instances[name] = obj
    # Render instances contain only re-read STL meshes; discard all original and temporary objects.
    for obj in list(source_objects.values()) + list(templates.values()):
        bpy.data.objects.remove(obj, do_unlink=True)
    for row in frames:
        active = {p['instance_id']: p for p in row['parts']}
        for name, obj in instances.items():
            obj.hide_render = name not in active
            obj.hide_viewport = name not in active
            obj.keyframe_insert('hide_render', frame=row['exposure_start'])
            obj.keyframe_insert('hide_viewport', frame=row['exposure_start'])
            if name in active:
                part = active[name]
                obj.location = part['position_mm']
                obj.rotation_euler = np.radians(part['rotation_degrees'])
                obj.keyframe_insert('location', frame=row['exposure_start'])
                obj.keyframe_insert('rotation_euler', frame=row['exposure_start'])
    for obj in instances.values():
        for curve in obj.animation_data.action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'CONSTANT'
    scene.name = 'Rolling Cube Pen print-set-v1'
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = .001
    scene.unit_settings.length_unit = 'MILLIMETERS'
    scene.frame_set(1)
    assert scene.frame_end == 74 and study.camera_signature(scene) == camera
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(MODEL), compress=True)

    manifest = dict(status='Print-set candidate awaiting visual review; not Final QA',
                    source_scene=str(study.MODEL.relative_to(ROOT)), source_scene_sha256=study.digest(study.MODEL),
                    source_manifest_sha256=study.digest(study.OUT / 'manifest-v2.json'),
                    units='mm; STL is unitless and must be imported as millimeters',
                    fixed_camera=camera, poses=61, exposures=74, fps=12, duration_seconds=74/12,
                    round_trips=6, phase_ranges=source['phase_ranges'],
                    stl_types=len(groups), required_physical_objects=sum(maximum.values()),
                    selection='Exact source shapes; Kabsch and upright quarter-turn rigid symmetry tests, no decimation.',
                    tolerance_mm=TOLERANCE, stls=groups, source_mesh_assignments=assignments, frames=frames,
                    protected_sha256=protected,
                    limitations=['Pose-dependent resting soles require multiple props even in the cylindrical phase.',
                                 '0.05 mm initial separation is retained; manual placement tolerance is not established.',
                                 'Global minimum thickness, slicer, supports, print time and physical tests are unverified.'])
    csv_rows = []
    inventory = []
    group_by_id = {g['id']: g for g in groups}
    for row in frames:
        for part in row['parts']:
            group = group_by_id[part['stl_id']]
            csv_rows.append(dict(pose=row['frame'], phase=row['phase'], direction=row['direction'],
                                 source_v2_frame=row['frame'], source_mesh=part['source_v2_mesh'],
                                 stl=part['stl'], physical_object_id=part['instance_id'],
                                 cell_index_from_cap=part['cell_index'],
                                 copies_of_this_stl_required=group['required_print_copies'],
                                 objects_in_this_pose=len(row['parts']),
                                 x_mm=part['position_mm'][0], y_mm=part['position_mm'][1], z_mm=part['position_mm'][2],
                                 rotation_x_deg=part['rotation_degrees'][0], rotation_y_deg=part['rotation_degrees'][1],
                                 rotation_z_deg=part['rotation_degrees'][2], scale_x=1, scale_y=1, scale_z=1,
                                 dimensions_x_mm=group['dimensions_mm'][0], dimensions_y_mm=group['dimensions_mm'][1],
                                 dimensions_z_mm=group['dimensions_mm'][2], baked_source_roll_deg=group['source_roll_degrees'],
                                 exposure_start=row['exposure_start'], exposures_12fps=row['exposures_12fps'],
                                 changes_from_v2=row['changes_from_v2'],
                                 note='Place on Z=0. Roll posture is baked into STL; apply only listed extra rotations.'))
    for group in groups:
        checked = next(r for r in validations if r['stl_id'] == group['id'])
        inventory.append(dict(stl=group['stl'], kind=group['kind'], print_copies=group['required_print_copies'],
                              source_v2_frame=group['source_v2_frame'], source_cell=group['source_cell_index'],
                              used_poses=' '.join(map(str, group['used_frames'])),
                              object_appearances=group['object_appearances'],
                              x_mm=group['dimensions_mm'][0], y_mm=group['dimensions_mm'][1], z_mm=group['dimensions_mm'][2],
                              volume_mm3=checked['volume_mm3'], sha256=group['stl_sha256']))
    write_csv(OUT / 'frame-to-stl.csv', csv_rows)
    write_csv(OUT / 'print-inventory.csv', inventory)
    # Save metadata before rendering so a rendering failure cannot lose the printable plan.
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    validation = dict(passed=all(r['passed'] for r in validations), stls=validations,
                      all_poses_grounded_and_supported=True, inter_object_collisions=0,
                      source_shapes_unchanged=True, design_approximation=False,
                      max_sampled_surface_error_mm=max(p['sampled_surface_error_mm'] for r in frames for p in r['parts']))
    (OUT / 'validation.json').write_text(json.dumps(validation, indent=2, allow_nan=False) + '\n')

    images = []
    comparisons = []
    raster_errors = []
    for row in frames:
        scene.frame_set(row['exposure_start'])
        assert study.camera_signature(scene) == camera
        assert all(list(o.scale) == [1, 1, 1] for o in instances.values())
        assert sum(not o.hide_render for o in instances.values()) == len(row['parts'])
        path = OUT / 'frames' / f"frame-{row['frame']:02}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        assert gpu.platform.vendor_get() == 'AMD Radeon Pro 5600M'
        assert gpu.platform.backend_type_get() == 'METAL'
        ideal = study.OUT / 'frames' / path.name
        combined = OUT / 'comparison' / path.name
        subprocess.run(['magick', str(ideal), str(path), '+append', str(combined)], check=True)
        difference = subprocess.run(['magick', 'compare', '-metric', 'RMSE', str(ideal), str(path), 'null:'],
                                    text=True, capture_output=True)
        assert difference.returncode in (0, 1), difference.stderr
        values = re.findall(r'\(([^)]+)\)', difference.stderr)
        raster_errors.append(float(values[-1]))
        images.append(path)
        comparisons.append(combined)
    assemble_gif(images, frames, OUT / 'print-reproduction.gif')
    assemble_gif(comparisons, frames, OUT / 'v2-vs-print-set.gif')
    study.montage([(f"{r['frame']:02} / P{r['phase']} / {len(r['parts'])} objects", p)
                   for r, p in zip(frames, images)], OUT / 'contact-sheet.png', 6)
    study.montage([(f'{f:02}: approved v2 | STL reproduction', comparisons[f-1])
                   for f in (1, 26, 31, 41, 46, 51, 56, 61)], OUT / 'v2-vs-print-set.png', 2)
    # Selected shape thumbnails use an explicit detail scale; animation camera remains saved unchanged.
    for obj in instances.values():
        obj.animation_data_clear()
        obj.hide_render = True
        obj.hide_viewport = True
    thumbnails = []
    for group in groups:
        obj = instances[group['id'] + '-copy-01']
        obj.hide_render = False
        obj.hide_viewport = False
        obj.location = (0, 0, 0)
        obj.rotation_euler = (0, 0, 0)
        scene.camera.data.ortho_scale = 30 if group['kind'] == 'cube' else 190
        path = OUT / 'selected' / (group['id'] + '.png')
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        label = f"{group['id']} / {group['kind']} / print x{group['required_print_copies']}"
        thumbnails.append((label, path))
        obj.hide_render = True
        obj.hide_viewport = True
    study.montage(thumbnails, OUT / 'selected-shapes.png', 6)
    assert all(study.digest(ROOT / p) == digest for p, digest in protected.items())
    manifest['protected_assets_unchanged'] = True
    manifest['rendering'] = dict(engine=scene.render.engine, gpu=gpu.platform.vendor_get(), backend='METAL')
    validation.update(protected_assets_unchanged=True, rendering_normalized_rmse_by_pose=raster_errors,
                      max_render_normalized_rmse=max(raster_errors), scene_sha256=study.digest(MODEL),
                      generator_sha256=study.digest(Path(__file__)))
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    (OUT / 'validation.json').write_text(json.dumps(validation, indent=2, allow_nan=False) + '\n')
    print('PRINT SET COMPLETE:', len(groups), 'STL types;', sum(maximum.values()), 'physical objects;',
          'max sampled shape error', validation['max_sampled_surface_error_mm'], flush=True)


if __name__ == '__main__':
    main()
