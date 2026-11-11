"""Independently reload and check the reduced Rolling Cube Pen candidate."""
import csv
import datetime
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import bpy
import bmesh
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rolling_cube_pen_print_set_v4 as job


def main():
    manifest = json.loads((job.OUT / 'manifest.json').read_text())
    generated = json.loads((job.OUT / 'validation.json').read_text())
    source = json.loads((job.OUT.parent / 'print-set-v3/manifest.json').read_text())
    phase1_holding = generated.get('phase1_nonselfstanding_poses')
    if phase1_holding is None:
        phase1_holding = sorted({row['frame'] for row in generated.get('placements', [])
                                 if row['frame'] <= 21 and not row['self_standing']})
    if phase1_holding is None:
        phase1_holding = [frame['frame'] for frame in manifest['frames'] if frame['frame'] <= 21
                          and any(not part['self_standing'] for part in frame['parts'])]
    source_groups = {group['id']: group for group in source['stls']}
    assert len(manifest['stls']) == 12
    assert sum(int(group['print_copies']) for group in manifest['stls']) == 20
    assert len(manifest['frames']) == 61
    assert sum(int(row['exposures_12fps']) for row in manifest['frames']) == 74

    file_checks = []
    temporary_meshes = []
    for group in manifest['stls']:
        path = job.ROOT / group['stl']
        source_group = source_groups[group['source_v3_stl_id']]
        assert path.is_file()
        assert job.digest(path) == group['sha256'] == source_group['sha256']
        vertices, faces, normals = job.v3.shared.previous.read_stl(path)
        assert vertices.shape[0] > 0 and faces.shape[0] > 0
        assert np.isfinite(vertices).all() and np.isfinite(normals).all()
        assert np.allclose(np.ptp(vertices, axis=0), group['dimensions_mm'], atol=2e-5)
        triangles = vertices[faces]
        assert np.all(np.sum(np.cross(triangles[:, 1] - triangles[:, 0],
                                     triangles[:, 2] - triangles[:, 0]) * normals, axis=1) > 0)

        before = set(bpy.data.objects)
        bpy.ops.wm.stl_import(filepath=str(path), global_scale=1, use_scene_unit=False,
                              forward_axis='Y', up_axis='Z', use_mesh_validate=False)
        imported = list(set(bpy.data.objects) - before)
        assert len(imported) == 1
        obj = imported[0]
        check = job.v3.shared.study.validate(obj)
        assert check['passed']
        fingerprint = job.v3.shared.study.base.mesh_fingerprint(obj)
        assert np.allclose(check['dimensions_mm'], group['dimensions_mm'], atol=2e-5)
        assert abs(check['volume_mm3'] - group['volume_mm3']) < max(1e-4, group['volume_mm3'] * 1e-6)
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        nonmanifold_vertices = sum(not vertex.is_manifold for vertex in bm.verts)
        bm.free()
        assert nonmanifold_vertices == 0
        check.update(stl=group['stl'], sha256=job.digest(path), source_v3_sha256_match=True,
                     dimensions_mm=np.ptp(vertices, axis=0).tolist(), nonmanifold_vertices=nonmanifold_vertices,
                     normal_disagreements=0, independent_stl_importer=True,
                     imported_mesh_fingerprint=fingerprint, imported_dimensions_and_volume_match=True,
                     print_copies=group['print_copies'])
        file_checks.append(check)
        temporary_meshes.append(obj)
        print('QA STL', group['id'], flush=True)
    for obj in temporary_meshes:
        bpy.data.objects.remove(obj, do_unlink=True)

    bpy.ops.wm.open_mainfile(filepath=str(job.MODEL), use_scripts=False)
    scene = bpy.context.scene
    objects = {obj.name: obj for obj in scene.objects if obj.get('stl_id')}
    assert len(objects) == 20
    assert scene.render.fps == 12 and scene.frame_end == 74
    assert job.v3.shared.study.camera_signature(scene) == manifest['fixed_camera']
    floors = [obj for obj in scene.objects if obj.type == 'MESH' and not obj.get('stl_id')]
    assert len(floors) == 1 and all(abs((floors[0].matrix_world @ vertex.co).z) < 1e-7
                                    for vertex in floors[0].data.vertices)
    stl_records = {group['id']: group for group in manifest['stls']}
    for obj in objects.values():
        assert obj.data.shape_keys is None and not obj.modifiers and obj.parent is None
        assert list(obj.scale) == [1, 1, 1]
        assert all(curve.data_path != 'scale' for curve in obj.animation_data.action.fcurves)
        assert all(key.interpolation == 'CONSTANT' for curve in obj.animation_data.action.fcurves
                   for key in curve.keyframe_points)
        record = stl_records[obj['stl_id']]
        assert job.v3.shared.study.base.mesh_fingerprint(obj) == record['source_mesh_fingerprint']

    with (job.OUT / 'frame-to-stl.csv').open(newline='') as stream:
        csv_rows = list(csv.DictReader(stream))
    by_frame = defaultdict(list)
    for row in csv_rows:
        by_frame[int(row['frame'])].append(row)
        assert (job.ROOT / row['stl']).is_file()
        assert np.isfinite([float(row[k]) for k in ('x_mm', 'y_mm', 'z_mm',
                             'rotation_x_deg', 'rotation_y_deg', 'rotation_z_deg')]).all()
        assert [float(row[k]) for k in ('scale_x', 'scale_y', 'scale_z')] == [1, 1, 1]
    assert sorted(by_frame) == list(range(1, 62)) and len(csv_rows) == 127
    assert all(len(rows) == (1 if frame < 56 else 12) for frame, rows in by_frame.items())
    assert all(len({int(row['exposures_12fps']) for row in rows}) == 1 for rows in by_frame.values())
    assert sum(int(rows[0]['exposures_12fps']) for rows in by_frame.values()) == 74
    inventory = list(csv.DictReader((job.OUT / 'print-inventory.csv').open(newline='')))
    assert len(inventory) == 12 and sum(int(row['print_copies']) for row in inventory) == 20
    assert len({row['stl'] for row in inventory}) == 12

    placement_checks = []
    for frame in manifest['frames']:
        scene.frame_set(frame['exposure_start'])
        expected_names = {part['instance_id'] for part in frame['parts']}
        assert {name for name, obj in objects.items() if not obj.hide_render} == expected_names
        assert {name for name, obj in objects.items() if not obj.hide_viewport} == expected_names
        boxes = []
        for part in frame['parts']:
            obj = objects[part['instance_id']]
            assert obj['stl_id'] == part['stl_id']
            assert np.allclose(obj.location[:], part['position_mm'], atol=2e-5)
            assert np.allclose(obj.rotation_euler[:], np.radians(part['rotation_degrees']), atol=1e-6)
            vertices, faces = job.v3.shared.previous.mesh_arrays(obj)
            matrix = np.asarray(obj.matrix_world)
            world = vertices @ matrix[:3, :3].T + matrix[:3, 3]
            volume, center, area, margin = job.v3.shared.study.support_properties(world, faces)
            assert volume > 0 and abs(float(world[:, 2].min())) < 2e-5
            stable = bool(area > 1e-6 and margin > 0)
            if frame['frame'] >= 56:
                assert stable
            boxes.append((float(world[:, 0].min()), float(world[:, 0].max())))
            placement_checks.append(dict(frame=frame['frame'], instance=part['instance_id'],
                                         minimum_z_mm=float(world[:, 2].min()), contact_area_mm2=float(area),
                                         support_margin_mm=float(margin) if math.isfinite(margin) else None,
                                         self_standing=stable))
        if frame['frame'] >= 56:
            assert all(left[0] > right[1] for left, right in zip(boxes, boxes[1:]))

    gif_checks = {}
    for name in ('print-reproduction.gif', 'v2-vs-print-set.gif'):
        path = job.OUT / name
        delays = list(map(int, subprocess.check_output(
            ['magick', 'identify', '-format', '%T ', str(path)], text=True).split()))
        assert len(delays) == 61 and sum(delays) == 617
        gif_checks[name] = dict(frames=len(delays), duration_centiseconds=sum(delays))
    expected_images = [job.OUT / 'contact-sheet.png', job.OUT / 'selected-shapes.png']
    assert all(path.is_file() and path.stat().st_size > 0 for path in expected_images)

    result = dict(status=generated['status'], checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  stl_types=12, print_objects=20, poses=61, exposures=74, duration_seconds=74 / 12,
                  stl_geometry=file_checks, blender_scene_reopened=True, scene_object_count=len(objects),
                  scene_mesh_fingerprints_match=True, camera_fixed=True, scale_fixed=True,
                  csv_rows=len(csv_rows), csv_inventory_rows=len(inventory), placements=placement_checks,
                  all_poses_touching_table=True, all_separated_cube_poses_self_standing=True,
                  phase1_holding_required_poses=phase1_holding,
                  gif_checks=gif_checks, unverified=['Exhaustive minimum wall thickness', 'Slicer material/time estimate',
                      'Slicer supports and print success', 'Dynamic finger-held rolling stability',
                      'Physical model-swap registration and tiny cube-gap placement', 'Physical placement and filming conditions'])
    (job.OUT / 'validation.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print('V4 QA PASS', len(file_checks), 'STLs / 20 props / 61 poses / 74 exposures', flush=True)


if __name__ == '__main__':
    main()
