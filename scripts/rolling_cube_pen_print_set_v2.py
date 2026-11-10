"""Study rigid reuse of existing STL props, including explicitly unsupported filming postures."""
import csv
import json
import math
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import bpy
import gpu
import numpy as np
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rolling_cube_pen_print_set_v1 as previous

study = previous.study
ROOT = study.ROOT
OUT = ROOT / 'previews/rolling-cube-pen/print-set-v2'
EXPORT = ROOT / 'exports/rolling-cube-pen/print-set-v2'
MODEL = ROOT / 'models/rolling-cube-pen-print-set-v2.blend'
# Preserve every actual section/groove change, replacing only posture-specific duplicates.
KEEP = ['pose-01'] + [f'pose-{i:02}' for i in range(7, 41)] + ['pose-59', 'pose-60', 'pose-61', 'pose-44']


def errors(a, af, b, bf):
    distances = []
    # Measure both directions on vertices and triangle interiors; this is sampled, not exhaustive Hausdorff distance.
    for vertices, faces, other, other_faces in ((a, af, b, bf), (b, bf, a, af)):
        tree = BVHTree.FromPolygons(other.tolist(), other_faces.tolist(), all_triangles=True)
        for point in np.concatenate((vertices, vertices[faces].mean(axis=1))):
            distances.append(tree.find_nearest(Vector(point))[3])
    distances = np.asarray(distances)
    return dict(max_sampled_surface_mm=float(distances.max()), rms_sampled_surface_mm=float(np.sqrt(np.mean(distances**2))))


def pose_fit(reference, target, angle):
    # Rotate the existing prop about its long axis; never modify vertices or apply a scale.
    rotation = np.asarray(Matrix.Rotation(math.radians(angle), 3, 'X'))
    turned = reference @ rotation.T
    # Most vertices are unaffected by the old sole cut; the median aligns their common body center.
    translation = np.median(target - turned, axis=0)
    # Re-ground the actual rigid prop instead of burying it in the tabletop to hide the discrepancy.
    translation[2] = -turned[:, 2].min()
    return rotation, translation


def main():
    assert bpy.app.version[:2] == (4, 5)
    for path in (OUT, EXPORT, OUT/'frames', OUT/'comparison', OUT/'selected'):
        path.mkdir(parents=True, exist_ok=True)
    old = json.loads((previous.OUT/'manifest.json').read_text())
    source = json.loads((study.OUT/'manifest-v2.json').read_text())
    source_checks = {r['id']: r for r in source['mesh_validation']}
    # Protect tracked assets and all previous cube-pen studies/print outputs, including untracked files.
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    paths = [ROOT/p for p in tracked if p and (ROOT/p).is_file()]
    for folder in (ROOT/'previews/rolling-cube-pen', ROOT/'exports/rolling-cube-pen'):
        paths += [p for p in folder.rglob('*') if p.is_file() and not p.is_relative_to(OUT) and not p.is_relative_to(EXPORT)]
    paths += [p for p in (ROOT/'models').glob('rolling-cube-pen*.blend') if p != MODEL]
    paths += [p for p in (ROOT/'scripts').glob('rolling_cube_pen*.py') if p.name != Path(__file__).name]
    protected = {str(p.relative_to(ROOT)): study.digest(p) for p in paths}
    bpy.ops.wm.open_mainfile(filepath=str(study.MODEL), use_scripts=False)
    scene = bpy.context.scene
    scene.frame_set(1)
    camera = study.camera_signature(scene)
    source_objects = {r['id']: bpy.data.objects[r['id']] for r in source['mesh_validation']}
    raw = {name: previous.mesh_arrays(obj) for name, obj in source_objects.items()}
    original_groups = {g['id']: g for g in old['stls']}
    groups = []
    templates = {}
    checks = []
    for old_id in KEEP:
        original = original_groups[old_id]
        group = dict(id=f'pose-{len(groups)+1:02}', previous_stl_id=old_id,
                     kind=original['kind'], source_v2_mesh=original['source_mesh'])
        path = EXPORT/(group['id']+'.stl')
        shutil.copyfile(ROOT/original['stl'], path)
        assert study.digest(path) == original['stl_sha256']
        vertices, faces, normals = previous.read_stl(path)
        obj = study.base.make_mesh(scene, 'template/'+group['id'], vertices.tolist(), faces.tolist())
        original_obj = source_objects[original['source_mesh']]
        for material in original_obj.data.materials:
            obj.data.materials.append(material)
        for polygon, source_polygon in zip(obj.data.polygons, original_obj.data.polygons):
            polygon.material_index = source_polygon.material_index
            polygon.use_smooth = True
        check = study.validate(obj)
        tri = vertices[faces]
        assert np.all(np.sum(np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])*normals, axis=1) > 0)
        check.update(stl_id=group['id'], normal_disagreements=0)
        checks.append(check)
        group.update(stl=str(path.relative_to(ROOT)), sha256=study.digest(path),
                     dimensions_mm=check['dimensions_mm'], mesh_fingerprint=study.base.mesh_fingerprint(obj),
                     identical_file_bytes_to_print_set_v1=True)
        groups.append(group)
        templates[group['id']] = obj
    by_old = {g['previous_stl_id']: g for g in groups}
    by_id = {g['id']: g for g in groups}
    frames = []
    maximum = Counter()
    usage = Counter()
    warnings = []
    for source_row, old_row in zip(source['frames'], old['frames']):
        counts = Counter()
        parts = []
        for source_part, old_part in zip(source_row['parts'], old_row['parts']):
            target, target_faces = raw[source_part['mesh_id']]
            changed = source_row['phase'] == 1 or source_part['cell_index'] is not None
            if changed:
                cell = source_part['cell_index']
                old_id = 'pose-01' if cell is None else ['pose-59','pose-60','pose-61','pose-44'][min(cell,3)]
                group = by_old[old_id]
                # All cube references are interpreted at the final face-down pose; the plain body is quarter-turn symmetric.
                reference_mesh = source['frames'][0]['parts'][0]['mesh_id'] if cell is None else source['frames'][-1]['parts'][min(cell,3)]['mesh_id']
                reference, _ = raw[reference_mesh]
                angle = source_checks[source_part['mesh_id']]['roll_degrees']
                fit_rotation, fit_translation = pose_fit(reference, target, angle)
                placement = np.asarray(Euler(np.radians(source_part['rotation_degrees']), 'XYZ').to_matrix())
                rotation = placement @ fit_rotation
                translation = placement @ fit_translation + source_part['position_mm']
            else:
                group = by_old[old_part['stl_id']]
                rotation = np.asarray(Euler(np.radians(old_part['rotation_degrees']), 'XYZ').to_matrix())
                translation = np.asarray(old_part['position_mm'])
            stl_id = group['id']
            counts[stl_id] += 1
            vertices, faces = previous.mesh_arrays(templates[stl_id])
            world = vertices @ rotation.T + translation
            ideal_rotation = np.asarray(Euler(np.radians(source_part['rotation_degrees']), 'XYZ').to_matrix())
            ideal = target @ ideal_rotation.T + source_part['position_mm']
            deviation = errors(ideal, target_faces, world, faces) if changed else dict(max_sampled_surface_mm=0, rms_sampled_surface_mm=0)
            volume, com, area, margin = study.support_properties(world, faces)
            stable = bool(area > 1e-6 and margin > 0)
            assert abs(float(world[:,2].min())) < 2e-5 and volume > 0
            part = dict(instance_id=f'{stl_id}-copy-{counts[stl_id]:02}', stl_id=stl_id, stl=group['stl'],
                        source_v2_mesh=source_part['mesh_id'], cell_index=source_part['cell_index'],
                        position_mm=translation.tolist(), rotation_degrees=[math.degrees(a) for a in Matrix(rotation).to_euler('XYZ')],
                        scale=[1,1,1], contact_area_mm2=area, support_margin_mm=margin if math.isfinite(margin) else None,
                        minimum_z_mm=float(world[:,2].min()), self_standing=stable,
                        holding_required=not stable, holding_feasibility='Unverified; no hand or support is simulated.',
                        world_dimensions_mm=np.ptp(world,axis=0).tolist(),
                        height_difference_from_v2_mm=float(world[:,2].max()-ideal[:,2].max()), **deviation)
            parts.append(part)
        # Disjoint actual world-X intervals certify absence of collisions despite the reused soles.
        boxes = []
        for part in parts:
            vertices, _ = previous.mesh_arrays(templates[part['stl_id']])
            rot = np.asarray(Euler(np.radians(part['rotation_degrees']), 'XYZ').to_matrix())
            world = vertices @ rot.T + part['position_mm']
            boxes.append((float(world[:,0].min()), float(world[:,0].max())))
        gaps = [a[0]-b[1] for a,b in zip(boxes,boxes[1:])]
        assert not gaps or min(gaps) > 0
        maximum |= counts
        usage.update(counts)
        if any(p['holding_required'] for p in parts):
            warnings.append(source_row['frame'])
        frames.append(dict(frame=source_row['frame'], phase=source_row['phase'], direction=source_row['direction'],
                           exposure_start=source_row['exposure_start'], exposures_12fps=source_row['exposures_12fps'],
                           parts=parts, projected_X_gaps_mm=gaps))
        print('MAPPED', source_row['frame'], 'holding', sum(p['holding_required'] for p in parts), flush=True)
    instances = {}
    for group in groups:
        group.update(print_copies=maximum[group['id']], object_appearances=usage[group['id']],
                     used_frames=[r['frame'] for r in frames if any(p['stl_id']==group['id'] for p in r['parts'])])
        for count in range(1, group['print_copies']+1):
            name = f"{group['id']}-copy-{count:02}"
            obj = bpy.data.objects.new(name, templates[group['id']].data)
            scene.collection.objects.link(obj)
            obj['stl_id'] = group['id']
            instances[name] = obj
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
                obj.location = active[name]['position_mm']
                obj.rotation_euler = np.radians(active[name]['rotation_degrees'])
                obj.keyframe_insert('location', frame=row['exposure_start'])
                obj.keyframe_insert('rotation_euler', frame=row['exposure_start'])
    for obj in instances.values():
        for curve in obj.animation_data.action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'CONSTANT'
    scene.name = 'Cube pen print-set-v2 - holding feasibility unverified'
    scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(MODEL), compress=True)
    manifest = dict(status='WARNING: reduced-print candidate; finger holding required and unverified',
                    stl_types=len(groups), physical_objects=sum(maximum.values()), poses=61, exposures=74, fps=12,
                    duration_seconds=74/12, round_trips=6, fixed_camera=camera, units='mm',
                    stls=groups, frames=frames, holding_required_poses=warnings, protected_sha256=protected)
    validation = dict(status='WARNING', stl_geometry_passed=all(c['passed'] for c in checks), stls=checks,
                      ground_clearance_passed=True, self_standing_all_poses=False, inter_object_collisions=0,
                      holding_required_poses=warnings, finger_holding_feasibility_verified=False,
                      all_stl_bytes_unchanged_from_v1=True,
                      max_sampled_surface_difference_mm=max(p['max_sampled_surface_mm'] for r in frames for p in r['parts']),
                      max_height_difference_mm=max(abs(p['height_difference_from_v2_mm']) for r in frames for p in r['parts']))
    rows = []
    for row in frames:
        for part in row['parts']:
            rows.append(dict(pose=row['frame'], phase=row['phase'], direction=row['direction'],
                             stl=part['stl'], physical_object=part['instance_id'], cell=part['cell_index'],
                             x_mm=part['position_mm'][0], y_mm=part['position_mm'][1], z_mm=part['position_mm'][2],
                             rotation_x_deg=part['rotation_degrees'][0], rotation_y_deg=part['rotation_degrees'][1],
                             rotation_z_deg=part['rotation_degrees'][2], scale=1, exposures_12fps=row['exposures_12fps'],
                             self_standing=part['self_standing'], finger_holding_required=part['holding_required'],
                             contact_area_mm2=part['contact_area_mm2'], support_margin_mm=part['support_margin_mm'],
                             max_sampled_surface_difference_mm=part['max_sampled_surface_mm'],
                             height_difference_from_v2_mm=part['height_difference_from_v2_mm'],
                             note='Holding feasibility unverified' if part['holding_required'] else 'No external holding required by ideal mesh test'))
    previous.write_csv(OUT/'frame-to-stl.csv', rows)
    previous.write_csv(OUT/'print-inventory.csv', [dict(stl=g['stl'], previous_stl=g['previous_stl_id'], print_copies=g['print_copies'],
                       x_mm=g['dimensions_mm'][0], y_mm=g['dimensions_mm'][1], z_mm=g['dimensions_mm'][2],
                       used_poses=' '.join(map(str,g['used_frames'])), sha256=g['sha256']) for g in groups])
    reductions = []
    for old_id, original in original_groups.items():
        if old_id in by_old:
            replacements = [by_old[old_id]['id']]
            reason = 'Retained approved shape; file bytes unchanged.'
        elif int(old_id.split('-')[1]) <= 6:
            replacements = [by_old['pose-01']['id']]
            reason = 'Reuse one rigid cylinder; rotating sole causes visible height differences and requires finger holding.'
        else:
            replacements = sorted({p['stl_id'] for r, old_row in zip(frames,old['frames']) for p,old_part in zip(r['parts'],old_row['parts']) if old_part['stl_id']==old_id})
            reason = 'Reuse the same 12 cubes with rigid rotations; old pose-dependent soles are not geometrically identical. Holding required in poses 57-60.'
        reductions.append(dict(previous_stl=old_id, replacement_stls=' '.join(replacements), reason=reason))
    previous.write_csv(OUT/'reductions.csv', reductions)
    for name, content in [('manifest.json', manifest), ('validation.json', validation)]:
        (OUT/name).write_text(json.dumps(content,indent=2,allow_nan=False)+'\n')
    images = []
    comparisons = []
    differences = []
    for row in frames:
        scene.frame_set(row['exposure_start'])
        assert study.camera_signature(scene) == camera
        assert all(list(o.scale)==[1,1,1] for o in instances.values())
        path = OUT/'frames'/f"frame-{row['frame']:02}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        assert gpu.platform.vendor_get() == 'AMD Radeon Pro 5600M' and gpu.platform.backend_type_get() == 'METAL'
        baseline = previous.OUT/'frames'/path.name
        combined = OUT/'comparison'/path.name
        subprocess.run(['magick',str(baseline),str(path),'+append',str(combined)],check=True)
        result = subprocess.run(['magick','compare','-metric','RMSE',str(baseline),str(path),'null:'],capture_output=True,text=True)
        assert result.returncode in (0,1)
        differences.append(float(result.stderr.split('(')[-1].split(')')[0]))
        images.append(path)
        comparisons.append(combined)
    previous.assemble_gif(images,frames,OUT/'print-reproduction.gif')
    previous.assemble_gif(comparisons,frames,OUT/'before-vs-after.gif')
    study.montage([(f"{r['frame']:02} / holding: {sum(p['holding_required'] for p in r['parts'])}",p) for r,p in zip(frames,images)],OUT/'contact-sheet.png',6)
    study.montage([(f'{i:02}: v1 | reduced candidate',comparisons[i-1]) for i in (1,3,6,31,55,56,58,61)],OUT/'before-vs-after.png',2)
    # Thumbnail cameras are separate inspection views; saved animation camera is unchanged.
    for obj in instances.values():
        obj.animation_data_clear()
        obj.hide_render = True
    thumbs = []
    for group in groups:
        obj = instances[group['id']+'-copy-01']
        obj.location = (0,0,0)
        obj.rotation_euler = (0,0,0)
        obj.hide_render = False
        scene.camera.data.ortho_scale = 30 if group['kind']=='cube' else 190
        path = OUT/'selected'/(group['id']+'.png')
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        thumbs.append((f"{group['id']} / print x{group['print_copies']}",path))
        obj.hide_render = True
    study.montage(thumbs,OUT/'selected-shapes.png',6)
    assert all(study.digest(ROOT/p)==h for p,h in protected.items())
    validation.update(render_normalized_rmse_by_pose=differences,max_render_normalized_rmse=max(differences),
                      protected_files_unchanged=True, scene_sha256=study.digest(MODEL),generator_sha256=study.digest(Path(__file__)))
    (OUT/'validation.json').write_text(json.dumps(validation,indent=2,allow_nan=False)+'\n')
    print('OPTIMIZED CANDIDATE COMPLETE',len(groups),'types',sum(maximum.values()),'objects; holding poses',warnings,flush=True)


if __name__ == '__main__':
    main()
