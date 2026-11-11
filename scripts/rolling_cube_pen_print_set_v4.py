"""Build and validate a reduced, reusable print set from the approved v3 solids."""
import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rolling_cube_pen_print_set_v3 as v3

ROOT = v3.ROOT
OUT = ROOT / 'previews/rolling-cube-pen/print-set-v4'
EXPORT = ROOT / 'exports/rolling-cube-pen/print-set-v4'
MODEL = ROOT / 'models/rolling-cube-pen-print-set-v4.blend'
SOURCES = {
    f'pose-{new:02}': f'pose-{old:02}'
    for new, old in enumerate((1, 6, 11, 16, 21, 25, 30, 35, 36, 37, 38, 39), 1)
}
WHOLE_FRAMES = {
    **{frame: 'pose-01' for frame in range(1, 26)},
    **{frame: 'pose-02' for frame in range(26, 31)},
    **{frame: 'pose-03' for frame in range(31, 36)},
    **{frame: 'pose-04' for frame in range(36, 41)},
    **{frame: 'pose-05' for frame in range(41, 45)},
    **{frame: 'pose-06' for frame in range(45, 49)},
    **{frame: 'pose-07' for frame in range(49, 52)},
    **{frame: 'pose-08' for frame in range(52, 56)},
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path, rows):
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def rotation_matrix(degrees):
    return np.asarray(Euler(np.radians(degrees), 'XYZ').to_matrix())


def transformed(vertices, degrees, translation):
    return vertices @ rotation_matrix(degrees).T + np.asarray(translation)


def world_metrics(vertices, faces):
    volume, center, area, margin = v3.shared.study.support_properties(vertices, faces)
    return dict(volume_mm3=float(volume), center_of_mass_mm=center.tolist(),
                contact_area_mm2=float(area),
                support_margin_mm=float(margin) if math.isfinite(margin) else None,
                self_standing=bool(area > 1e-6 and margin > 0),
                minimum_z_mm=float(vertices[:, 2].min()))


def save_stl_geometry(scene, source_group, target_id, source_objects):
    source_path = ROOT / source_group['stl']
    target_path = EXPORT / f'{target_id}.stl'
    shutil.copyfile(source_path, target_path)
    assert digest(source_path) == digest(target_path) == source_group['sha256']
    vertices, faces, normals = v3.shared.previous.read_stl(target_path)
    assert len(vertices) > 0 and len(faces) > 0
    assert np.isfinite(vertices).all() and np.isfinite(normals).all()
    obj = v3.shared.study.base.make_mesh(scene, 'template/' + target_id,
                                         vertices.tolist(), faces.tolist())
    reference = source_objects[source_group['id'] + '-copy-01']
    assert len(obj.data.polygons) == len(reference.data.polygons)
    for material in reference.data.materials:
        obj.data.materials.append(material)
    for polygon, source_polygon in zip(obj.data.polygons, reference.data.polygons):
        polygon.material_index = source_polygon.material_index
        polygon.use_smooth = True
    check = v3.shared.study.validate(obj)
    tri = vertices[faces]
    assert np.all(np.sum(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]) * normals, axis=1) > 0)
    check.update(id=target_id, dimensions_mm=np.ptp(vertices, axis=0).tolist(),
                 stl=str(target_path.relative_to(ROOT)), sha256=digest(target_path), source_stl=source_group['stl'],
                 source_v3_stl_id=source_group['id'], source_mesh_fingerprint=check['mesh_fingerprint'],
                 kind=source_group['kind'],
                 copied_without_geometry_change=True, independent_binary_stl_read=True,
                 normals_agree=True)
    return obj, vertices, faces, check


def cube_reuse_id(cell_index):
    return f'pose-{9 + cell_index:02}' if cell_index < 3 else 'pose-12'


def render_selected_only():
    bpy.ops.wm.open_mainfile(filepath=str(MODEL), use_scripts=False)
    scene = bpy.context.scene
    manifest = json.loads((OUT / 'manifest.json').read_text())
    objects = {obj.name: obj for obj in scene.objects if obj.get('stl_id')}
    for obj in objects.values():
        obj.animation_data_clear()
        obj.hide_render = True
        obj.hide_viewport = True
    for group in manifest['stls']:
        group_id = group['id']
        if int(group_id[-2:]) >= 9:
            cell = next(i for i in range(12) if cube_reuse_id(i) == group_id)
            obj = objects[f'cube-{cell:02}']
        else:
            obj = objects[group_id + '-copy-01']
        obj.location = (0, 0, 0)
        obj.rotation_euler = (0, 0, 0)
        obj.hide_render = False
        obj.hide_viewport = False
        scene.camera.location = (0, 210, 250)
        scene.camera.rotation_euler = (scene.camera.location * -1).to_track_quat('-Z', 'Y').to_euler()
        scene.camera.data.ortho_scale = 190 if int(group_id[-2:]) < 9 else 30
        path = OUT / 'selected' / f'{group_id}.png'
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        obj.hide_render = True
        obj.hide_viewport = True
    v3.shared.study.montage([(f"{g['id']} / {g['source_v3_stl_id']} x{g['print_copies']}",
                              OUT / 'selected' / f"{g['id']}.png") for g in manifest['stls']],
                            OUT / 'selected-shapes.png', 4)
    print('SELECTED SHAPES PREVIEW COMPLETE', flush=True)


def plan_rows(source_manifest, source_groups, templates):
    copies = Counter()
    appearances = Counter()
    placements = []
    for source_frame in source_manifest['frames']:
        frame = source_frame['frame']
        parts = []
        if frame < 56:
            selected_id = WHOLE_FRAMES[frame]
            source_part = source_frame['parts'][0]
            physical_id = selected_id + '-copy-01'
            vertices, faces = templates[selected_id][1:3]
            matrix = rotation_matrix(source_part['rotation_degrees'])
            rotated = vertices @ matrix.T
            translation = np.asarray(source_part['position_mm'], dtype=float).copy()
            translation[2] = -float(rotated[:, 2].min())
            world = rotated + translation
            metrics = world_metrics(world, faces)
            part = dict(stl_id=selected_id, instance_id=physical_id, cell_index=None,
                        source_v3_stl_id=source_part['stl_id'],
                        source_v2_mesh=source_groups[source_part['stl_id']]['source_v2_mesh'],
                        position_mm=translation.tolist(), rotation_degrees=list(source_part['rotation_degrees']),
                        scale=[1, 1, 1], source_position_mm=source_part['position_mm'],
                        source_rotation_degrees=source_part['rotation_degrees'],
                        grounded_by_translation_mm=float(translation[2] - source_part['position_mm'][2]),
                        shape_mapping='reuse representative solid; no mesh interpolation', **metrics)
            parts.append(part)
            copies[selected_id] = max(copies[selected_id], 1)
            appearances[selected_id] += 1
        else:
            cube_parts = sorted(source_frame['parts'], key=lambda part: part['cell_index'])
            pending = []
            for source_part in cube_parts:
                cell = int(source_part['cell_index'])
                selected_id = cube_reuse_id(cell)
                physical_id = f'cube-{cell:02}'
                vertices, faces = templates[selected_id][1:3]
                matrix = rotation_matrix(source_part['rotation_degrees'])
                rotated = vertices @ matrix.T
                translation = np.asarray(source_part['position_mm'], dtype=float).copy()
                translation[2] = -float(rotated[:, 2].min())
                pending.append(dict(stl_id=selected_id, instance_id=physical_id, cell_index=cell,
                                    source_v3_stl_id=source_part['stl_id'],
                                    source_v2_mesh=source_groups[source_part['stl_id']]['source_v2_mesh'],
                                    position_mm=translation.tolist(), rotation_degrees=list(source_part['rotation_degrees']),
                                    scale=[1, 1, 1], source_position_mm=source_part['position_mm'],
                                    source_rotation_degrees=source_part['rotation_degrees'],
                                    grounded_by_translation_mm=float(translation[2] - source_part['position_mm'][2]),
                                    shape_mapping='reuse one of the persistent 12 physical cubes'))
            # Preserve cell order and the existing gaps; only separate boxes if a reused solid extends into its neighbor.
            for index, part in enumerate(pending):
                vertices = templates[part['stl_id']][1]
                world = transformed(vertices, part['rotation_degrees'], part['position_mm'])
                if index:
                    previous_part = pending[index - 1]
                    previous_world = transformed(templates[previous_part['stl_id']][1],
                                                  previous_part['rotation_degrees'], previous_part['position_mm'])
                    clearance = float(previous_world[:, 0].min() - world[:, 0].max())
                    if clearance < 0.10:
                        delta = 0.10 - clearance
                        part['position_mm'][0] -= delta
                        part['x_clearance_adjustment_mm'] = -delta
                        world[:, 0] -= delta
                    else:
                        part['x_clearance_adjustment_mm'] = 0.0
                else:
                    part['x_clearance_adjustment_mm'] = 0.0
                part.update(world_metrics(world, templates[part['stl_id']][2]))
                assert abs(part['minimum_z_mm']) < 2e-5
                parts.append(part)
                copies[part['stl_id']] = max(copies[part['stl_id']], sum(p['stl_id'] == part['stl_id'] for p in pending))
                appearances[part['stl_id']] += 1
            boxes = []
            for part in parts:
                world = transformed(templates[part['stl_id']][1], part['rotation_degrees'], part['position_mm'])
                boxes.append((float(world[:, 0].min()), float(world[:, 0].max())))
            assert all(left[0] > right[1] for left, right in zip(boxes, boxes[1:])), (frame, boxes)
        placements.append(dict(frame=frame, phase=source_frame['phase'], direction=source_frame['direction'],
                               exposure_start=source_frame['exposure_start'],
                               exposures_12fps=source_frame['exposures_12fps'], parts=parts))
    return placements, copies, appearances


def main():
    parser = __import__('argparse').ArgumentParser()
    parser.add_argument('--no-render', action='store_true')
    parser.add_argument('--selected-only', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    assert bpy.app.version[:2] == (4, 5)
    if args.selected_only:
        render_selected_only()
        return
    OUT.mkdir(parents=True, exist_ok=True)
    EXPORT.mkdir(parents=True, exist_ok=True)
    (OUT / 'frames').mkdir(exist_ok=True)
    (OUT / 'comparison').mkdir(exist_ok=True)
    (OUT / 'selected').mkdir(exist_ok=True)
    source_manifest = json.loads((OUT.parent / 'print-set-v3/manifest.json').read_text())
    source_groups = {group['id']: group for group in source_manifest['stls']}
    bpy.ops.wm.open_mainfile(filepath=str(v3.MODEL), use_scripts=False)
    scene = bpy.context.scene
    scene.frame_set(1)
    camera = v3.shared.study.camera_signature(scene)
    source_objects = {obj.name: obj for obj in scene.objects if obj.get('stl_id')}
    templates = {}
    records = []
    for new_id, old_id in SOURCES.items():
        obj, vertices, faces, check = save_stl_geometry(scene, source_groups[old_id], new_id, source_objects)
        templates[new_id] = (obj, vertices, faces)
        records.append(check)
        print('VALIDATED', new_id, 'from', old_id, flush=True)
    frames, copies, appearances = plan_rows(source_manifest, source_groups, templates)
    assert len(frames) == 61 and sum(row['exposures_12fps'] for row in frames) == 74
    assert len(records) == 12 and sum(copies.values()) == 20
    # Remove v3 scene instances before creating v4 props so Blender cannot suffix duplicate object names.
    for obj in source_objects.values():
        bpy.data.objects.remove(obj, do_unlink=True)
    instances = {}
    for group_id, count in copies.items():
        for index in range(1, count + 1):
            name = f'{group_id}-copy-{index:02}' if group_id not in ('pose-09', 'pose-10', 'pose-11', 'pose-12') else None
            if group_id.startswith('pose-') and int(group_id[-2:]) >= 9:
                cell_ids = [cell for cell in range(12) if cube_reuse_id(cell) == group_id]
                name = f'cube-{cell_ids[index - 1]:02}'
            instance = bpy.data.objects.new(name, templates[group_id][0].data)
            scene.collection.objects.link(instance)
            instance['stl_id'] = group_id
            instance['source_stl'] = str((EXPORT / f'{group_id}.stl').relative_to(ROOT))
            instances[name] = instance
    for template, _, _ in templates.values():
        bpy.data.objects.remove(template, do_unlink=True)
    for frame in frames:
        active = {part['instance_id']: part for part in frame['parts']}
        for name, obj in instances.items():
            visible = name in active
            obj.hide_render = not visible
            obj.hide_viewport = not visible
            obj.keyframe_insert('hide_render', frame=frame['exposure_start'])
            obj.keyframe_insert('hide_viewport', frame=frame['exposure_start'])
            if visible:
                part = active[name]
                obj.location = part['position_mm']
                obj.rotation_euler = np.radians(part['rotation_degrees'])
                obj.keyframe_insert('location', frame=frame['exposure_start'])
                obj.keyframe_insert('rotation_euler', frame=frame['exposure_start'])
        scene.frame_set(frame['exposure_start'])
        assert all(abs(part['minimum_z_mm']) < 2e-5 for part in frame['parts'])
        if frame['frame'] >= 56:
            assert all(part['self_standing'] for part in frame['parts']), frame['frame']
        frame['component_count'] = len(frame['parts'])
        frame['replacement_from_v3'] = [part['source_v3_stl_id'] for part in frame['parts']]
        frame['shape_difference_note'] = 'Discrete representative STL replacement; no mesh morph, scale or camera change.'
    for obj in instances.values():
        for curve in obj.animation_data.action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'CONSTANT'
    scene.name = 'Rolling Cube Pen - reduced print-set-v4 candidate'
    scene.frame_end = 74
    scene.frame_set(1)
    assert v3.shared.study.camera_signature(scene) == camera
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(MODEL), compress=True)

    for group in records:
        group['print_copies'] = int(copies[group['id']])
        group['appearances'] = int(appearances[group['id']])
        group['selected_for_frames'] = [row['frame'] for row in frames
                                        if any(part['stl_id'] == group['id'] for part in row['parts'])]
        group['estimated_material_volume_mm3'] = group['volume_mm3'] * group['print_copies']
    cube_checks = [part for frame in frames if frame['frame'] >= 56 for part in frame['parts']]
    manifest = dict(status='Approved official print-set-v4; 12 STL types / 20 physical props',
                    source_print_set='print-set-v3', source_animation='rolling-cube-pen/v2',
                    stl_types=len(records), print_objects=sum(copies.values()), poses=61, exposures=74,
                    fps=12, duration_seconds=74 / 12, phases=[
                        dict(name='cylinder', frames=[1, 21], round_trips=2),
                        dict(name='cylinder-to-square', frames=[22, 41], round_trips=2),
                        dict(name='square-to-cubes', frames=[42, 61], round_trips=2)],
                    fixed_camera=camera, source_stl_selection=SOURCES,
                    cube_policy='Twelve physical pieces reused for every separated pose; cap-derived cells 0-2 retain their own three STL shapes and cells 3-11 share one body STL.',
                    v3_total_cad_volume_mm3=sum(float(row['volume_mm3']) * int(row['print_copies'])
                                                for row in csv.DictReader((OUT.parent / 'print-set-v3/print-inventory.csv').open())),
                    v4_total_cad_volume_mm3=sum(group['estimated_material_volume_mm3'] for group in records),
                    scene_scale_changes=False, mesh_interpolation=False, camera_changes=False,
                    stls=records, frames=frames,
                    limitations=['Finger holding is required for rolling poses that do not self-stand; physical feasibility is untested.',
                                  'FDM minimum wall thickness, slicer supports, print time and physical printing are unverified.',
                                  'The approved reduced set intentionally uses discrete representative shapes from v2.',
                                  'All cube placements are static support checked; dynamic handling and friction are untested.'])
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    write_csv(OUT / 'print-inventory.csv', [dict(stl=str((EXPORT / f"{g['id']}.stl").relative_to(ROOT)),
                      print_copies=g['print_copies'], type=g['kind'] if 'kind' in g else ('cube' if g['id'] in ('pose-09','pose-10','pose-11','pose-12') else 'whole-pen'),
                      source_v3_stl=g['source_stl'], x_mm=g['dimensions_mm'][0], y_mm=g['dimensions_mm'][1],
                      z_mm=g['dimensions_mm'][2], volume_mm3=g['volume_mm3'],
                      total_material_volume_mm3=g['estimated_material_volume_mm3'],
                      appearances=g['appearances'], sha256=g['sha256']) for g in records])
    write_csv(OUT / 'frame-to-stl.csv', [dict(frame=row['frame'], phase=row['phase'], direction=row['direction'],
                      exposures_12fps=row['exposures_12fps'], exposure_start=row['exposure_start'],
                      object_index=index, stl=str((EXPORT / f"{part['stl_id']}.stl").relative_to(ROOT)),
                      physical_object_id=part['instance_id'], source_v3_stl_id=part['source_v3_stl_id'],
                      cell_index=part['cell_index'], x_mm=part['position_mm'][0], y_mm=part['position_mm'][1],
                      z_mm=part['position_mm'][2], rotation_x_deg=part['rotation_degrees'][0],
                      rotation_y_deg=part['rotation_degrees'][1], rotation_z_deg=part['rotation_degrees'][2],
                      scale_x=1, scale_y=1, scale_z=1, contact_area_mm2=part['contact_area_mm2'],
                      support_margin_mm=part['support_margin_mm'], self_standing=part['self_standing'],
                      holding_required=not part['self_standing'], x_clearance_adjustment_mm=part.get('x_clearance_adjustment_mm', 0),
                      replacement=part['shape_mapping']) for row in frames for index, part in enumerate(row['parts'], 1)])
    selected_sources = set(SOURCES.values())
    v3_groups = {group['id']: group for group in source_manifest['stls']}
    source_to_v4 = {}
    source_frames = {}
    for source_frame in source_manifest['frames']:
        frame_index = source_frame['frame']
        for source_part in source_frame['parts']:
            old_id = source_part['stl_id']
            new_id = WHOLE_FRAMES[frame_index] if frame_index < 56 else cube_reuse_id(source_part['cell_index'])
            source_to_v4.setdefault(old_id, set()).add(new_id)
            source_frames.setdefault(old_id, set()).add(frame_index)
    write_csv(OUT / 'reduced-models.csv', [dict(v3_stl=old_id,
                      v4_stl=' '.join(sorted(source_to_v4.get(old_id, set()))),
                      source_frames=' '.join(map(str, sorted(source_frames.get(old_id, set())))),
                      decision='Retained representative' if old_id in selected_sources else 'Replaced by the named staged representative',
                      source_sha256=v3_groups[old_id]['sha256']) for old_id in v3_groups])
    validation_passed = (all(row['passed'] for row in records)
                         and all(abs(p['minimum_z_mm']) < 2e-5 for f in frames for p in f['parts'])
                         and all(p['self_standing'] for p in cube_checks))
    validation = dict(status='PASS' if validation_passed else 'WARNING',
                      stl_types=len(records), print_objects=sum(copies.values()), poses=len(frames),
                      exposures=sum(row['exposures_12fps'] for row in frames), geometry=records,
                      all_shapes_reused_from_v3=True, source_hashes_match=True,
                      all_poses_grounded=all(abs(p['minimum_z_mm']) < 2e-5 for f in frames for p in f['parts']),
                      all_final_cube_placements_self_standing=all(p['self_standing'] for p in cube_checks),
                      phase1_nonselfstanding_poses=sorted({f['frame'] for f in frames if f['frame'] <= 21 and any(not p['self_standing'] for p in f['parts'])}),
                      min_final_cube_support_margin_mm=min(p['support_margin_mm'] for p in cube_checks),
                      camera_fixed=True, scale_fixed=True, mesh_interpolation=False,
                      minimum_wall_thickness='Not exhaustively measured', slicer_or_print='Not tested')
    (OUT / 'validation.json').write_text(json.dumps(validation, indent=2, allow_nan=False) + '\n')
    if not args.no_render:
        images = []
        for frame in frames:
            scene.frame_set(frame['exposure_start'])
            assert v3.shared.study.camera_signature(scene) == camera
            path = OUT / 'frames' / f"frame-{frame['frame']:02}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            images.append(path)
            print('RENDERED', frame['frame'], flush=True)
        ideal_frames = [ROOT / 'previews/rolling-cube-pen/v2/frames' / f'frame-{i:02}.png' for i in range(1, 62)]
        assert all(path.is_file() for path in ideal_frames)
        comparisons = []
        for frame, ideal, actual in zip(frames, ideal_frames, images):
            paired = OUT / 'comparison' / f"frame-{frame['frame']:02}.png"
            subprocess.run(['magick', str(ideal), str(actual), '+append', str(paired)], check=True)
            comparisons.append(paired)
        v3.shared.previous.assemble_gif(images, frames, OUT / 'print-reproduction.gif')
        v3.shared.previous.assemble_gif(comparisons, frames, OUT / 'v2-vs-print-set.gif')
        v3.shared.study.montage([(f"{row['frame']:02} / P{row['phase']}", path)
                                for row, path in zip(frames, images)], OUT / 'contact-sheet.png', 6)
        thumbnails = []
        original_scale = scene.camera.data.ortho_scale
        original_location = scene.camera.location.copy()
        original_rotation = scene.camera.rotation_euler.copy()
        for candidate in instances.values():
            candidate.animation_data_clear()
            candidate.hide_render = True
            candidate.hide_viewport = True
        for group in records:
            obj = instances.get(group['id'] + '-copy-01')
            if obj is None:
                cell = next(i for i in range(12) if cube_reuse_id(i) == group['id'])
                obj = instances[f'cube-{cell:02}']
            obj.hide_render = False
            obj.hide_viewport = False
            obj.location = (0, 0, 0)
            obj.rotation_euler = (0, 0, 0)
            scene.camera.location = (0, 210, 250)
            scene.camera.rotation_euler = (scene.camera.location * -1).to_track_quat('-Z', 'Y').to_euler()
            scene.camera.data.ortho_scale = 190 if group['id'] not in ('pose-09','pose-10','pose-11','pose-12') else 30
            path = OUT / 'selected' / f"{group['id']}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            thumbnails.append((f"{group['id']} / {group['source_v3_stl_id']} x{group['print_copies']}", path))
            obj.hide_render = True
        scene.camera.location = original_location
        scene.camera.rotation_euler = original_rotation
        scene.camera.data.ortho_scale = original_scale
        v3.shared.study.montage(thumbnails, OUT / 'selected-shapes.png', 4)
    print('PRINT SET V4 COMPLETE', len(records), 'types', sum(copies.values()), 'physical items', flush=True)


if __name__ == '__main__':
    main()
