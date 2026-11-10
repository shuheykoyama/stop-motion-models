"""Read-only final asset checks; writes only the requested final QA report and JSON."""
import csv,json,sys,tempfile,subprocess,hashlib
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import bpy,numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
import stone_to_fireworks_print_set_v1 as assembly
import stone_to_fireworks_v3 as v3
base=assembly.base
ROOT=base.ROOT
OUT=assembly.OUT
REPORT=OUT/'final-qa.json'
DOC=ROOT/'docs/stone-to-fireworks-final-qa.md'
sha=assembly.shared.sha

def mesh_arrays(obj):
    return np.array([v.co[:] for v in obj.data.vertices]),np.array([p.vertices[:] for p in obj.data.polygons])

def native_read(path):
    """Blender's native reader is independent of the project's binary STL parser."""
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.stl_import(filepath=str(path),global_scale=1,use_scene_unit=False,forward_axis='Y',up_axis='Z',use_facet_normal=False,use_mesh_validate=False)
    imported=list(bpy.context.selected_objects)
    assert len(imported)==1
    obj=imported[0];vertices,faces=mesh_arrays(obj)
    result=dict(vertices=len(vertices),triangles=len(faces),finite=bool(np.isfinite(vertices).all()),surface_sha256=assembly.surface_hash(vertices,faces))
    mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
    return result

def main():
    assert bpy.app.version[:2]==(4,5)
    manifest=json.loads((OUT/'manifest.json').read_text());prior=json.loads((OUT/'validation.json').read_text())
    source_validation=json.loads((ROOT/'previews/stone-to-fireworks/v3/validation-v3.json').read_text())
    source_by_name={p['id']:p for p in source_validation['poses']}
    # Snapshot existing stone-to-fireworks assets, excluding these two QA outputs.
    protected=[p for folder in ('exports/stone-to-fireworks','previews/stone-to-fireworks') for p in (ROOT/folder).rglob('*') if p.is_file() and p!=REPORT]
    protected+=list((ROOT/'models').glob('stone-to-fireworks*.blend'))
    protected+=list((ROOT/'scripts').glob('stone_to_fireworks*.py'))
    protected+=[p for p in (ROOT/'docs').glob('stone-to-fireworks*.md') if p!=DOC]
    baseline={str(p.relative_to(ROOT)):sha(p) for p in protected}
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/stone-to-fireworks-v3.blend'),use_scripts=False)
    source_meshes={name:dict(fingerprint=base.mesh_fingerprint(bpy.data.objects[name]),surface=assembly.surface_hash(*mesh_arrays(bpy.data.objects[name])),vertices=len(bpy.data.objects[name].data.vertices),triangles=len(bpy.data.objects[name].data.polygons)) for name in source_by_name}
    source,source_faces,_=base.read_stl(ROOT/'exports/stone-to-fireworks/rest.stl')
    assert sha(ROOT/'exports/stone-to-fireworks/rest.stl')==source_validation['source_sha256']
    regenerated_base=v3.stone_base(source)
    poses=[];geometry={}
    expected=[f'pose-{i:02}.stl' for i in range(1,15)]
    directory_check=sorted(p.name for p in assembly.EXPORT.glob('*.stl'))==expected
    with tempfile.TemporaryDirectory(prefix='fireworks-final-qa-') as tmp:
        for p in manifest['poses']:
            path=ROOT/p['stl'];vertices,faces,normals=base.read_stl(path)
            dimensions=np.ptp(vertices,axis=0);name=p['v3_pose'];original=source_by_name[name]
            fresh=base.validate(path,1,np.eye(3),expected_dimensions=p['dimensions_mm'],core_dimensions=[8*float(vertices[:,2].max())/20,8,float(vertices[:,2].max())])
            # The generic bread-study pass threshold is not a miniature print specification.
            # Evaluate the explicit requested integrity, finite contact and support requirements.
            integrity=('boundary_edges','nonmanifold_edges','nonmanifold_vertices','inconsistent_winding_edges','degenerate_faces','stl_normal_disagreements','nonadjacent_bvh_intersections')
            fresh['bread_study_absolute_thresholds_passed']=fresh.pop('passed')
            fresh['path']=p['stl']
            canonical=assembly.surface_hash(vertices,faces)
            native=native_read(path)
            spec=v3.SPECS[p['source_v3_frame']-1]
            coords=v3.shape(regenerated_base,spec)
            regenerated_path=Path(tmp)/(p['id']+'.stl')
            regenerated=v3.export(bpy.context.scene,'qa-independent-'+p['id'],coords,source_faces,regenerated_path)
            regenerated_hash=sha(regenerated_path);regenerated_fingerprint=base.mesh_fingerprint(regenerated)
            mesh=regenerated.data;bpy.data.objects.remove(regenerated,do_unlink=True);bpy.data.meshes.remove(mesh)
            checks=dict(binary_reader_nonempty=len(vertices)>0 and len(faces)>0,finite_vertices_and_normals=bool(np.isfinite(vertices).all() and np.isfinite(normals).all()),native_reader_matches=native['finite'] and native['surface_sha256']==canonical and native['vertices']==len(vertices) and native['triangles']==len(faces),geometry_integrity=all(fresh[k]==0 for k in integrity),single_component=fresh['components']==1,positive_volume=fresh['signed_volume_mm3']>0,dimensions_match_manifest=bool(np.max(np.abs(dimensions-p['dimensions_mm']))<.005),dimensions_match_v3=bool(np.max(np.abs(dimensions-original['local_dimensions_mm']))<.005),finite_local_contact=fresh['table_contact_area_mm2']>0,positive_static_support=fresh['support_hull_margin_mm']>0,no_table_penetration=fresh['minimum_table_clearance_mm']>=-1e-5,stl_hash_matches_manifest=sha(path)==p['stl_sha256'],stl_hash_matches_prior_qa=sha(path)==next(c['stl_sha256'] for c in prior['poses'] if c['id']==p['id']),stl_bytes_match_v3=sha(path)==sha(ROOT/p['source_stl'])==original['sha256'],source_scene_fingerprint_matches=source_meshes[name]['fingerprint']==p['source_mesh_fingerprint']==original['mesh_fingerprint'],source_surface_matches=canonical==source_meshes[name]['surface']==p['canonical_surface_sha256'],independent_regeneration_hash_matches=regenerated_hash==sha(path),independent_regeneration_fingerprint_matches=regenerated_fingerprint==source_meshes[name]['fingerprint'])
            # Edge and triangle sizes describe actual file resolution, not printer resolution.
            xyz=vertices[faces];edges=np.linalg.norm(xyz-np.roll(xyz,1,axis=1),axis=2)
            area=np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1)/2
            pose=dict(id=p['id'],stl=p['stl'],source_v3_frame=p['source_v3_frame'],v3_pose=name,sha256=sha(path),size_bytes=path.stat().st_size,dimensions_mm=dimensions.tolist(),geometry=fresh,native_reader=native,canonical_surface_sha256=canonical,source_scene_mesh=source_meshes[name],independent_regeneration_sha256=regenerated_hash,checks=checks,passed=all(checks.values()),resolution=dict(vertices=len(vertices),triangles=len(faces),minimum_triangle_area_mm2=float(area.min()),edge_length_percentiles_mm=np.percentile(edges,[0,50,95,100]).tolist()),thickness_limit='Vertical core samples only; global normal thickness and minimum feature size are unverified.')
            poses.append(pose);geometry[p['id']]=(vertices,faces);print('QA',p['id'],pose['passed'],flush=True)
    # Compare the three stored miniatures against scaled source rest coordinates.
    rest=base.read_stl(ROOT/manifest['poses'][0]['stl'])[0]
    sort=lambda a:a[np.lexsort(a.T)]
    miniature_checks=[]
    for pose_id,size in [('pose-12',.65),('pose-13',.4),('pose-14',.25)]:
        vertices,_=geometry[pose_id]
        expected_points=rest*size
        # Float32 scaling can collapse near-equal X coordinates into ties and change
        # lexicographic order. Use a bijective nearest-vertex match in both directions.
        distances=[];bijections=[]
        for left,right in ((vertices,expected_points),(expected_points,vertices)):
            tree=KDTree(len(right))
            for index,point in enumerate(right):tree.insert(point,index)
            tree.balance()
            matches=[tree.find(point) for point in left]
            distances.extend(float(match[2]) for match in matches)
            bijections.append(len({match[1] for match in matches})==len(right)==len(left))
        delta=max(distances)
        miniature_checks.append(dict(id=pose_id,physical_scale=size,max_coordinate_delta_from_scaled_rest_mm=delta,bidirectional_bijective_vertex_match=all(bijections),comparison_method='Bidirectional bijective nearest vertices; tolerance unchanged at 0.000002 mm.',geometry_preserved=delta<2e-6 and all(bijections),detail_note='Shallow relief scales with the whole solid and may not resolve in FDM. No detached appendage or zero-area triangle was detected.'))
    # Verify actual saved scene coordinates against its actual tabletop plane.
    bpy.ops.wm.open_mainfile(filepath=str(assembly.MODEL),use_scripts=False)
    scene=bpy.context.scene
    objects={p['id']:bpy.data.objects['print-set-v1/'+p['id']] for p in manifest['poses']}
    for p in poses:
        p['checks']['saved_scene_mesh_matches']=base.mesh_fingerprint(objects[p['id']])==next(row['render_mesh_fingerprint'] for row in manifest['poses'] if row['id']==p['id']) and assembly.surface_hash(*mesh_arrays(objects[p['id']]))==p['canonical_surface_sha256']
        p['passed']=all(p['checks'].values())
    floor=bpy.data.objects['Tabletop (preview only)']
    a,b,c=[floor.matrix_world@v.co for v in floor.data.vertices[:3]]
    normal=(b-a).cross(c-a).normalized();u=(b-a).normalized();v=normal.cross(u)
    basis=np.column_stack((u,v,normal));plane=float(normal.dot(a))
    camera=scene.camera.matrix_world.copy();lens=scene.camera.data.lens
    exposure_checks=[]
    for exposure in range(1,41):
        row=manifest['frames'][(exposure-1)//2];scene.frame_set(exposure);obj=objects[row['pose_id']]
        vertices,faces=geometry[row['pose_id']];matrix=np.asarray(obj.matrix_world)
        world=vertices@matrix[:3,:3].T+matrix[:3,3]
        distances=world@np.array(normal)-plane
        table=np.abs(distances)<1e-5;contact=np.all(table[faces],axis=1)
        triangle=world[faces];areas=np.linalg.norm(np.cross(triangle[:,1]-triangle[:,0],triangle[:,2]-triangle[:,0]),axis=1)/2
        center=np.array(next(p['geometry']['center_of_mass_local_mm'] for p in poses if p['id']==row['pose_id']))@matrix[:3,:3].T+matrix[:3,3]
        projected=world@basis;support=base.hull(projected[table,:2]);edge=np.roll(support,-1,axis=0)-support;offset=(center@basis)[:2]-support
        margin=(edge[:,0]*offset[:,1]-edge[:,1]*offset[:,0])/np.linalg.norm(edge,axis=1)
        checks=dict(exactly_expected_pose_visible=[k for k,o in objects.items() if not o.hide_render]==[row['pose_id']],placement_matches=bool(np.allclose(obj.location[:],row['position_mm'],atol=1e-7)),scale_one=list(obj.scale)==[1,1,1],rotation_zero=list(obj.rotation_euler)==[0,0,0],mesh_has_no_deformation=not obj.modifiers and obj.data.shape_keys is None,minimum_world_clearance_zero=abs(float(distances.min()))<1e-5,finite_world_contact=float(areas[contact].sum())>0,positive_world_support=float(margin.min())>0,camera_fixed=scene.camera.matrix_world==camera and scene.camera.data.lens==lens)
        exposure_checks.append(dict(exposure=exposure,shooting_frame=row['frame'],pose_id=row['pose_id'],minimum_world_distance_to_table_mm=float(distances.min()),contact_area_mm2=float(areas[contact].sum()),support_margin_mm=float(margin.min()),checks=checks,passed=all(checks.values())))
    expected_meshes=set(objects.values())|{floor}
    scene_checks=dict(frame_range_40=scene.frame_start==1 and scene.frame_end==40,fps_12=scene.render.fps==12,no_extra_mesh_objects={o for o in scene.objects if o.type=='MESH'}==expected_meshes,no_external_libraries=not bpy.data.libraries,all_pose_keys_constant=all(k.interpolation=='CONSTANT' for obj in objects.values() for curve in obj.animation_data.action.fcurves for k in curve.keyframe_points),horizontal_table=abs(normal.z-1)<1e-8,all_40_exposures_pass=all(e['passed'] for e in exposure_checks))
    rows=list(csv.DictReader((OUT/'frame-to-stl.csv').open()));usage=Counter(r['stl'] for r in rows)
    row_matches=[]
    for row,target in zip(rows,manifest['frames']):
        numeric=[float(row[k]) for k in ('x_mm','y_mm','z_mm','rotation_x_deg','rotation_y_deg','rotation_z_deg','size_x_mm','size_y_mm','size_z_mm')]
        row_matches.append(row['stl']==target['stl'] and int(row['frame'])==target['frame'] and row['phase']==target['phase'] and int(row['source_v3_frame'])==target['source_v3_frame'] and int(row['stl_source_v3_frame'])==target['stl_source_v3_frame'] and numeric[:3]==target['position_mm'] and numeric[3:6]==target['rotation_degrees'] and numeric[6:]==target['dimensions_mm'] and bool(np.isfinite(numeric).all()) and int(row['exposures_12fps'])==2 and int(row['exposure_start'])==target['exposure_start'] and row['reused'].lower()==str(target['reused']).lower())
    csv_checks=dict(exact_frames_1_to_20=[int(r['frame']) for r in rows]==list(range(1,21)),all_14_stls_referenced=set(usage)=={p['stl'] for p in manifest['poses']},all_references_exist=all((ROOT/r['stl']).is_file() for r in rows),usage_matches_manifest=dict(usage)=={p['stl']:p['use_count'] for p in manifest['poses']},rows_match_manifest=len(rows)==20 and all(row_matches),all_Z_zero=all(float(r['z_mm'])==0 for r in rows),exposures_total_40=sum(int(r['exposures_12fps']) for r in rows)==40,manifest_timing=manifest['fps']==12 and manifest['total_exposures']==40 and manifest['shooting_states']==20)
    # Reassemble the GIF in temporary storage; no Blender rendering occurs in this audit.
    with tempfile.TemporaryDirectory(prefix='fireworks-gif-qa-') as tmp:
        rebuilt=Path(tmp)/'sequence.gif'
        assembly.assemble_gif([ROOT/r['render'] for r in manifest['frames']],manifest['frames'],rebuilt)
        delays=list(map(int,subprocess.check_output(['magick','identify','-format','%T ',str(OUT/'print-reproduction.gif')],text=True).split()))
        gif_checks=dict(frame_count_20=len(delays)==20,duration_333_centiseconds=sum(delays)==333,exact_reassembly_from_manifest_PNGs=sha(rebuilt)==sha(OUT/'print-reproduction.gif'),gif_hash_matches_previous_record=sha(OUT/'print-reproduction.gif')==prior['output_sha256']['print-reproduction.gif'])
    immutable_checks=dict(all_input_hashes_unchanged=all(sha(ROOT/name)==h for name,h in baseline.items()),print_scene_hash_matches_prior=sha(assembly.MODEL)==prior['scene_sha256'],v3_source_script_matches_record=sha(ROOT/'scripts/stone_to_fireworks_v3.py')==source_validation['generator_sha256'])
    passed=directory_check and all(p['passed'] for p in poses) and all(p['geometry_preserved'] for p in miniature_checks) and all(scene_checks.values()) and all(csv_checks.values()) and all(gif_checks.values()) and all(immutable_checks.values())
    report=dict(verdict='PASS' if passed else 'FAIL',checked_at_utc=datetime.now(timezone.utc).isoformat(),blender_version=bpy.app.version_string,units='STL coordinates are millimeters; import as mm because STL carries no units.',stl_directory_names_correct=directory_check,poses=poses,miniature_checks=miniature_checks,table_plane=dict(normal=list(normal),offset_mm=plane),scene_checks=scene_checks,exposure_checks=exposure_checks,csv_checks=csv_checks,gif_checks=gif_checks,input_preservation_checks=immutable_checks,input_sha256=baseline,unverified=['Exhaustive global minimum normal wall thickness and minimum feature size.','Intersections involving faces sharing vertices are excluded by the BVH check.','Slicer checks, printing support requirements, optimal printing orientation, print duration and actual printing.','Physical filming placement, lighting, friction, real printed center of mass and stability.'],miniature_note='pose-14 is a solid 7.5 x 6.25 x 5 mm scaled stone. Sampled vertical core thickness does not certify all local thickness. Shallow submillimeter relief is intentional and may be lost in FDM; no printer/nozzle resolution guarantee is made.')
    REPORT.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    lines=['# Stone to Fireworks - Final STL QA','','Final verdict: **'+report['verdict']+'**. Checked at '+report['checked_at_utc']+'.','',('This verdict permits proceeding to slicer inspection; it does not certify successful FDM printing.' if passed else 'Required checks did not all pass; inspect the failed fields before handoff.')+' No original STL, scene, animation or earlier study was modified.','','## Scope','','14 print-set-v1 STLs, its frame-to-stl CSV, manifest, validation, saved Blender scene and reproduction script. Approved v3 scene, generator and source STL files provide the geometric reference. Blender '+bpy.app.version_string+' was used for read-only geometry checks; no rendering or slicing was performed.','','## Stored STL results','','| STL | v3 frame | X x Y x Z (mm) | Volume mm3 | Contact mm2 | Support margin mm | Result |','|---|---:|---|---:|---:|---:|---|']
    for p in poses:
        g=p['geometry'];lines.append('| '+Path(p['stl']).name+' | '+str(p['source_v3_frame'])+' | '+' x '.join(f'{x:.3f}' for x in p['dimensions_mm'])+f" | {g['signed_volume_mm3']:.3f} | {g['table_contact_area_mm2']:.3f} | {g['support_hull_margin_mm']:.3f} | "+('PASS' if p['passed'] else 'FAIL')+' |')
    lines+=['','## SHA-256','','```text']+[Path(p['stl']).name+'  '+p['sha256'] for p in poses]+['```','','## Integrity and v3 identity','','The stored binary STLs were parsed again and imported independently with Blender native STL import. Coordinates, triangle counts and canonical surfaces agree. Fresh topology, orientation, volume, degeneracy, nonadjacent BVH intersections, dimension, contact and support checks are recorded per file in final-qa.json. Source scene fingerprints and canonical surfaces match. The v3 generator independently regenerated all 14 shapes into temporary STLs in this QA process; byte hashes and source mesh fingerprints match. STL float32 coordinates preserve the approved scale.','','## Miniature detail and thickness','','The 65%, 40% and 25% meshes retain the scaled rest geometry within float precision. Edge-length percentiles and minimum triangle areas are recorded to describe actual mesh resolution; no zero-area or collapsed geometry was detected. The smallest model is 7.5 x 6.25 x 5 mm. Its sampled vertical core minimum is '+f"{poses[-1]['geometry']['sampled_minimum_vertical_core_mm']:.3f}"+' mm. This is not a global minimum normal thickness proof. Shallow submillimeter relief is intentional and may not survive FDM resolution. No nozzle, layer height or guaranteed minimum printable feature is assumed.','','## Tabletop filming and CSV','','The actual saved tabletop plane was derived from its world-space vertices. For all 40 exposures, transformed stone vertices were measured against that plane. The minimum world clearance is zero, contact area is positive, and the uniform-density center-of-mass projection is inside the world contact hull. This includes the recoil/flight shooting states 13-20. Grounding is therefore checked from geometry, not merely a Z placement parameter. No aerial filming supports are required by this layout. Physical stability and friction remain untested.','','The CSV contains frames 1-20 exactly once, references all 14 STLs, and has usage totaling 20. Positions, rotations, dimensions, source frames, reuse flags and exposure starts match the manifest. Each shooting state holds for two exposures, totaling 40 at 12 fps. The saved scene has exactly the expected stone/floor mesh objects, constant held animation, no shape-key/modifier deformation, unit scales and a fixed camera.','','## Preview provenance','','The original approved GIF was not changed. Reassembly from the manifest PNG paths and exposure counts in a temporary directory matches the saved GIF byte-for-byte: 20 states, 3.33 seconds after centisecond rounding. Its hash also matches the prior validation record. Saved-scene mesh assignments and all 40 exposures agree with the manifest/CSV. This verifies stored provenance and assembly; it is not a new image-to-scene render comparison. No hands, fingers or fireworks occur among the scene meshes.','','## Bambu Studio handoff','','Import STL as millimeters. Check actual dimensions, especially pose-14. Inspect the miniature relief at the intended nozzle/layer profile. Review layer continuity, local thin areas, adhesion, overhangs and support needs. Filming resting orientation is not necessarily the optimal printing orientation. Verify print time/material estimates in the slicer rather than treating them as measured here. Printing and physical tests are the user workflow.','','## Unverified conditions','']+['- '+x for x in report['unverified']]+['','The full machine-readable evidence is [final-qa.json](../previews/stone-to-fireworks/print-set-v1/final-qa.json). The audit can be repeated using `Blender --background --threads 2 --python-exit-code 1 --python scripts/stone_to_fireworks_print_set_v1_qa.py`. It writes only the two QA reports and temporary verification files.']
    DOC.write_text('\n'.join(lines)+'\n')
    print('FINAL QA',report['verdict'],flush=True)
if __name__=='__main__':main()
