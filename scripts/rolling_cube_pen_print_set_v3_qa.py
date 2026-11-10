"""Final data QA, retaining known non-self-standing finger-held postures."""
import csv
import datetime
import json
import math
import shutil
import subprocess
import sys
import tempfile
from collections import Counter,defaultdict
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0,str(Path(__file__).resolve().parent))
import rolling_cube_pen_print_set_v3 as job


def main():
    m=json.loads((job.OUT/'manifest.json').read_text())
    assert job.shared.study.digest(job.REVIEW)==m['source_review_sha256']
    build=json.loads((job.OUT/'validation.json').read_text())
    frames,inputs=job.selection()
    assert len(inputs)==43 and len(list(job.EXPORT.glob('*.stl')))==43
    groups={g['id']:g for g in m['stls']}
    assert list(groups)==[f'pose-{i:02}' for i in range(1,44)]
    assert len({g['sha256'] for g in groups.values()})==43
    assert sum(g['print_copies'] for g in groups.values())==59
    # Independently assemble the source selection without using the generated STL files as inputs.
    with tempfile.TemporaryDirectory(prefix='cube-v3-independent-assembly-') as directory:
        for index,path in enumerate(inputs,1):
            copied=Path(directory)/f'pose-{index:02}.stl'
            shutil.copyfile(job.ROOT/path,copied)
            assert job.shared.study.digest(copied)==groups[f'pose-{index:02}']['sha256']
    bpy.ops.wm.open_mainfile(filepath=str(job.MODEL),use_scripts=False)
    scene=bpy.context.scene
    objects={o.name:o for o in scene.objects if o.get('stl_id')}
    assert len(objects)==59
    file_checks=[]
    for group in groups.values():
        path=job.ROOT/group['stl']
        assert job.shared.study.digest(path)==job.shared.study.digest(job.ROOT/group['source_stl'])==group['sha256']
        a,f,normals=job.shared.previous.read_stl(path)
        assert np.isfinite(a).all() and np.isfinite(normals).all()
        assert np.allclose(np.ptp(a,axis=0),group['dimensions_mm'])
        # Disable the optional importer correction step; QA must not repair an input mesh.
        before=set(bpy.data.objects)
        bpy.ops.wm.stl_import(filepath=str(path),global_scale=1,use_scene_unit=False,
                              forward_axis='Y',up_axis='Z',use_mesh_validate=False)
        imported=list(set(bpy.data.objects)-before)
        assert len(imported)==1
        obj=imported[0]
        va,fa=job.shared.previous.mesh_arrays(obj)
        assert job.shared.previous.surface_hash(va,fa)==group['surface_sha256']
        check=job.shared.study.validate(obj)
        bm=bmesh.new();bm.from_mesh(obj.data)
        bad_vertices=sum(not v.is_manifold for v in bm.verts);bm.free()
        assert bad_vertices==0
        tri=a[f]
        assert np.all(np.sum(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])*normals,axis=1)>0)
        check.update(id=group['id'],stl=group['stl'],source_stl=group['source_stl'],sha256=group['sha256'],
                     source_sha256_match=True,independent_reader_match=True,independent_set_assembly_sha_match=True,
                     nonmanifold_vertices=bad_vertices,normal_disagreements=0,
                     bbox_min_mm=a.min(0).tolist(),bbox_max_mm=a.max(0).tolist(),
                     solid_volume_bbox_ratio=check['volume_mm3']/float(np.prod(np.ptp(a,axis=0))),
                     global_minimum_wall_thickness='Not exhaustively measured')
        file_checks.append(check)
        bpy.data.objects.remove(obj,do_unlink=True)
        print('FINAL QA STL',group['id'],flush=True)
    for obj in objects.values():
        a,f=job.shared.previous.mesh_arrays(obj);group=groups[obj['stl_id']]
        assert job.shared.previous.surface_hash(a,f)==group['surface_sha256']
        assert job.shared.study.base.mesh_fingerprint(obj)==group['mesh_fingerprint']
        assert obj.data.shape_keys is None and not obj.modifiers and obj.parent is None
        assert all(c.data_path!='scale' for c in obj.animation_data.action.fcurves)
        assert all(k.interpolation=='CONSTANT' for c in obj.animation_data.action.fcurves for k in c.keyframe_points)
    floor=[o for o in scene.objects if o.type=='MESH' and not o.get('stl_id')]
    assert len(floor)==1 and all(abs((floor[0].matrix_world@v.co).z)<1e-7 for v in floor[0].data.vertices)
    assert not bpy.data.libraries and not any(i.filepath for i in bpy.data.images)
    with (job.OUT/'frame-to-stl.csv').open() as stream:csv_rows=list(csv.DictReader(stream))
    by_pose=defaultdict(list)
    for row in csv_rows:by_pose[int(row['pose'])].append(row)
    assert sorted(by_pose)==list(range(1,62)) and len(csv_rows)==127
    assert sum(int(r[0]['exposures_12fps']) for r in by_pose.values())==74
    with (job.OUT/'print-inventory.csv').open() as stream:inventory=list(csv.DictReader(stream))
    assert len(inventory)==43 and sum(int(r['print_copies']) for r in inventory)==59
    checks=[];unsupported=[];maximum=Counter()
    for row,reference in zip(m['frames'],frames):
        scene.frame_set(row['exposure_start'])
        assert job.shared.study.camera_signature(scene)==m['fixed_camera']
        expected={p['instance_id'] for p in row['parts']}
        assert {n for n,o in objects.items() if not o.hide_render}==expected
        assert {n for n,o in objects.items() if not o.hide_viewport}==expected
        counts=Counter();boxes=[]
        for p,source,csv_row in zip(row['parts'],reference['parts'],by_pose[row['frame']]):
            assert p['source_stl']==source['stl']
            assert np.allclose(p['position_mm'],source['position_mm'],atol=1e-10)
            assert np.allclose(p['rotation_degrees'],source['rotation_degrees'],atol=1e-10)
            obj=objects[p['instance_id']]
            assert csv_row['physical_object_id']==p['instance_id'] and csv_row['stl']==p['stl']
            assert np.allclose([float(csv_row[k]) for k in ('x_mm','y_mm','z_mm')],obj.location[:],atol=2e-5)
            assert np.allclose(obj.rotation_euler[:],np.radians(p['rotation_degrees']),atol=1e-6)
            assert list(obj.scale)==[1,1,1]
            a,f=job.shared.previous.mesh_arrays(obj);matrix=np.asarray(obj.matrix_world)
            world=a@matrix[:3,:3].T+matrix[:3,3]
            volume,com,area,margin=job.shared.study.support_properties(world,f)
            stable=bool(area>1e-6 and margin>0)
            assert abs(float(world[:,2].min()))<2e-5
            if p['cell_index'] is not None:assert stable
            if not stable:unsupported.append(row['frame'])
            projected=[world_to_camera_view(scene,scene.camera,obj.matrix_world@Vector(c)) for c in obj.bound_box]
            assert all(.01<q.x<.99 and .01<q.y<.99 for q in projected)
            boxes.append((float(world[:,0].min()),float(world[:,0].max())))
            checks.append(dict(pose=row['frame'],instance=p['instance_id'],stl=p['stl'],cell=p['cell_index'],
                               clearance_mm=float(world[:,2].min()),contact_area_mm2=area,
                               support_margin_mm=margin if math.isfinite(margin) else None,self_standing=stable))
            counts[p['stl_id']]+=1
        assert all(a[0]>b[1] for a,b in zip(boxes,boxes[1:]))
        maximum|=counts
    for group in groups.values():assert group['print_copies']==maximum[group['id']]
    for exposure in range(1,75):
        row=next(r for r in m['frames'] if r['exposure_start']<=exposure<r['exposure_start']+r['exposures_12fps'])
        scene.frame_set(exposure)
        assert job.shared.study.camera_signature(scene)==m['fixed_camera']
        assert {n for n,o in objects.items() if not o.hide_render}=={p['instance_id'] for p in row['parts']}
        for p in row['parts']:
            obj=objects[p['instance_id']]
            assert list(obj.scale)==[1,1,1]
            assert np.allclose(obj.location[:],p['position_mm'],atol=2e-5)
            assert np.allclose(obj.rotation_euler[:],np.radians(p['rotation_degrees']),atol=1e-6)
    for name in ('print-reproduction.gif','v2-vs-print-set.gif'):
        delays=list(map(int,subprocess.check_output(['magick','identify','-format','%T ',str(job.OUT/name)],text=True).split()))
        assert len(delays)==61 and sum(delays)==617
    comparison=[]
    for frame in range(56,62):
        for view in ('front','top'):
            actual=job.OUT/('frames/frame-'+str(frame)+'.png' if view=='front' else f'top-{frame}.png')
            adopted=job.shared.OUT/'review/images'/f'hybrid59-{frame}-{view}.png'
            result=subprocess.run(['magick','compare','-metric','RMSE',str(actual),str(adopted),'null:'],capture_output=True,text=True)
            assert result.returncode in (0,1)
            error=float(result.stderr.split('(')[-1].split(')')[0])
            comparison.append(dict(pose=frame,view=view,normalized_rmse_against_adopted_still=error))
            assert error<.001
    assert sorted(set(unsupported))==[2,3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,19,20]
    metadata_changes=[p for p,h in m['protected_sha256'].items() if Path(p).name=='.DS_Store' and (job.ROOT/p).is_file() and job.shared.study.digest(job.ROOT/p)!=h]
    # Historical preservation snapshots can contain local-only studies, not required reproduction inputs.
    archive={p:h for p,h in m['protected_sha256'].items() if p.startswith(('models/rolling-cube-pen','exports/rolling-cube-pen/','previews/rolling-cube-pen/')) and Path(p).name!='.DS_Store'}
    absent_archive=[p for p in archive if not (job.ROOT/p).is_file()]
    assert all(job.shared.study.digest(job.ROOT/p)==h for p,h in archive.items() if (job.ROOT/p).is_file())
    cubes=[r for r in checks if r['cell'] is not None]
    qa=dict(status='WARNING',checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            reason='Data integrity passed. Phase 1 has 18 non-self-standing poses requiring unverified finger holding.',
            stl_count=43,required_print_objects=59,poses=61,exposures=74,duration_seconds=74/12,gif_duration_seconds=6.17,
            stl_geometry_passed=True,stls=file_checks,placements=checks,unsupported_phase1_poses=sorted(set(unsupported)),
            all_cube_placements_self_standing=True,min_cube_support_margin_mm=min(r['support_margin_mm'] for r in cubes),
            csv_manifest_scene_match=True,all_74_exposures_checked=True,inventory_peak_counts_match=True,
            fixed_camera_scale_verified=True,inter_object_collisions=0,adopted_hybrid_placements_match=True,
            adopted_hybrid_render_comparisons=comparison,previous_assets_unchanged=True,
            volatile_finder_metadata_changes=metadata_changes,
            unbundled_historical_snapshot_paths=absent_archive,
            source_stl_sha256_all_match=True,independent_stl_reader_all_match=True,independent_set_assembly_sha_all_match=True,
            procedural_shape_regeneration='Not rerun; existing validated meshes copied unchanged.',
            scene_sha256=job.shared.study.digest(job.MODEL),qa_script_sha256=job.shared.study.digest(Path(__file__)),
            unverified=['Phase 1 finger holding','Dynamic rolling stability','0.05 mm initial gap placement accuracy',
                        'Exhaustive minimum thickness','Slicer result','Support need','Print success','Physical filming'])
    (job.OUT/'final-qa.json').write_text(json.dumps(qa,indent=2,allow_nan=False)+'\n')
    build.update(final_qa_status='WARNING',final_qa_json='final-qa.json')
    (job.OUT/'validation.json').write_text(json.dumps(build,indent=2,allow_nan=False)+'\n')
    m.update(status='Adopted final print set; Final QA WARNING: finger holding unverified',
             final_qa_status='WARNING',final_qa_json='final-qa.json')
    (job.OUT/'manifest.json').write_text(json.dumps(m,indent=2,allow_nan=False)+'\n')
    report=['# Rolling Cube Pen - Final QA','',f"Decision: WARNING. Checked at {qa['checked_at_utc']}.",'',
            'Data integrity passes for 43 STL types, 59 props, 61 poses and 74 exposures.',
            'All 72 separated-cube placements pass static support. Phase 1 requires finger holding in 18 poses.',
            'This is not a claim that filming or printing has been physically tested.','',
            '## Executed checks','',
            '- All saved STL files: binary reader and independent Blender importer, with automatic correction disabled.',
            '- Watertightness, manifold edges and vertices, one component, positive volume, consistent winding and STL normals.',
            '- No degenerate triangles, non-finite vertices or detected non-adjacent BVH intersections.',
            '- Dimensions, bounds, volume and gross volume/bounding-box ratio recorded below and in JSON.',
            '- All source SHA-256 hashes match. Independent assembly into a temporary directory also matches.',
            '- Saved scene reopened separately: surfaces, transforms, CSV, manifest and 59 persistent prop IDs checked.',
            '- All 61 poses and 74 exposures: contact, framing, fixed camera, unit scale, constant keys and no part collisions.',
            '- Adopted review placements match exactly; front/top renders compared to the adopted reference stills.','',
            'Finder .DS_Store metadata is excluded from immutable model-asset hashes; any observed metadata changes are recorded in JSON.','',
            '## Support and accepted differences','',
            f"Minimum cube support margin: {qa['min_cube_support_margin_mm']:.6f} mm.",
            'Pose 57 roll changes from -84 to -90 degrees; pose 60 changes from -6 to 0 degrees.',
            'The adopted separation-section maximum sampled surface difference is about 0.657 mm.',
            'This is not the maximum over the whole animation: inherited Phase 1 reuse has a known difference up to 1.899 mm.',
            'Unsupported Phase 1 poses: '+', '.join(map(str,qa['unsupported_phase1_poses']))+'.','',
            '## Files','', '| STL | X x Y x Z (mm) | Volume (mm3) | SHA-256 |','|---|---|---:|---|']
    for r in file_checks:
        report.append(f"| {r['id']} | {' x '.join(f'{d:.3f}' for d in r['dimensions_mm'])} | {r['volume_mm3']:.3f} | {r['sha256']} |")
    report += ['', '## Limited feature assessment and unverified work','',
               'Closed solid geometry and overall proportions were checked; exhaustive local wall thickness was not measured.',
               'Existing design details include about 0.25 mm clip relief, 0.22 mm end treatment and narrow grooves.',
               'These are design parameters, not measured minimum wall thicknesses. Their slicer reproduction is unverified.',
               'No repair, reinforcement or rescaling was applied. STL is unitless: import as millimeters at 100% scale.',
               'Filming contact orientation is not necessarily the best printing orientation.',
               'Finger holding, dynamic stability, tiny-gap placement, slicing, supports, print success and physical filming remain unverified.','',
               '[Filming and printing guide](rolling-cube-pen-print-set-v3.md)',
               '[Machine-readable QA](../previews/rolling-cube-pen/print-set-v3/final-qa.json)','']
    report += ['STL importer API reference: [Blender 4.5 documentation](https://docs.blender.org/api/4.5/bpy.ops.wm.html#bpy.ops.wm.stl_import).','']
    (job.ROOT/'docs/rolling-cube-pen-final-qa.md').write_text('\n'.join(report))
    print('FINAL QA WARNING: integrity passed, 43 STLs / 59 objects; 18 inherited finger-held poses',flush=True)


if __name__=='__main__':main()
