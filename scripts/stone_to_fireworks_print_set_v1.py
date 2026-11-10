"""Assemble approved v3 STL solids into a tabletop-only physical filming study."""
import sys,json,csv,hashlib,shutil,subprocess
from pathlib import Path
from collections import Counter
import bpy,numpy as np,gpu
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import stone_to_fireworks as shared
base=shared.base
ROOT=base.ROOT
OUT=ROOT/'previews/stone-to-fireworks/print-set-v1'
EXPORT=ROOT/'exports/stone-to-fireworks/print-set-v1'
MODEL=ROOT/'models/stone-to-fireworks-print-set-v1.blend'

def surface_hash(vertices,triangles):
    """Canonicalize triangle coordinates independently of STL vertex numbering."""
    xyz=np.asarray(vertices,dtype=np.float32)[triangles]
    # Sort vertex triples within each face, then sort whole faces for a surface comparison.
    order=np.lexsort((xyz[:,:,2],xyz[:,:,1],xyz[:,:,0]),axis=1)
    rows=np.take_along_axis(xyz,order[:,:,None],axis=1).reshape(-1,9)
    rows=rows[np.lexsort(rows.T[::-1])]
    return hashlib.sha256(rows.tobytes()).hexdigest()

def assemble_gif(images,records,path):
    command=['magick'];previous=0
    for image,record in zip(images,records):
        cumulative=round((record['exposure_start']-1+record['exposures_12fps'])*100/12)
        command+=['-delay',str(cumulative-previous),str(image)];previous=cumulative
    subprocess.run(command+['-loop','0',str(path)],check=True)

def main():
    assert bpy.app.version[:2]==(4,5)
    OUT.mkdir(parents=True,exist_ok=True);EXPORT.mkdir(parents=True,exist_ok=True)
    source_manifest=json.loads((ROOT/'previews/stone-to-fireworks/v3/manifest-v3.json').read_text())
    source_validation=json.loads((ROOT/'previews/stone-to-fireworks/v3/validation-v3.json').read_text())
    protected=[p for folder in ('previews/stone-to-fireworks/v3','exports/stone-to-fireworks/v3') for p in (ROOT/folder).rglob('*') if p.is_file()]
    protected += [ROOT/'models/stone-to-fireworks-v3.blend',ROOT/'scripts/stone_to_fireworks_v3.py',ROOT/'docs/stone-to-fireworks-v3.md']
    protected_hashes={str(p.relative_to(ROOT)):shared.sha(p) for p in protected}
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/stone-to-fireworks-v3.blend'),use_scripts=False)
    scene=bpy.context.scene;material=bpy.data.objects['rest'].data.materials[0]
    source_checks={p['id']:p for p in source_validation['poses']}
    source_objects={name:bpy.data.objects[name] for name in source_checks}
    source_surfaces={name:surface_hash([v.co[:] for v in obj.data.vertices],np.array([p.vertices[:] for p in obj.data.polygons])) for name,obj in source_objects.items()}
    source_fingerprints={name:base.mesh_fingerprint(obj) for name,obj in source_objects.items()}
    for name,obj in source_objects.items():
        assert source_fingerprints[name]==source_checks[name]['mesh_fingerprint'],name
    # Rebuild the render objects from the actual printable STL, with no deformation or scaling.
    for obj in source_objects.values():bpy.data.objects.remove(obj,do_unlink=True)
    names=list(dict.fromkeys(f['pose'] for f in source_manifest['frames']))
    usage=Counter(f['pose'] for f in source_manifest['frames'])
    objects={};poses=[];by_name={}
    for index,name in enumerate(names,1):
        source=ROOT/source_checks[name]['stl'];destination=EXPORT/f'pose-{index:02}.stl'
        assert shared.sha(source)==source_checks[name]['sha256']
        shutil.copyfile(source,destination)
        assert shared.sha(destination)==shared.sha(source)
        vertices,faces,_=base.read_stl(destination)
        assert np.isfinite(vertices).all()
        canonical=surface_hash(vertices,faces);assert canonical==source_surfaces[name]
        obj=base.make_mesh(scene,f'print-set-v1/pose-{index:02}',vertices.tolist(),faces.tolist())
        obj.data.materials.append(material)
        for polygon in obj.data.polygons:polygon.use_smooth=True
        assert surface_hash([v.co[:] for v in obj.data.vertices],np.array([p.vertices[:] for p in obj.data.polygons]))==canonical
        check=base.validate(destination,1,np.eye(3),expected_dimensions=source_checks[name]['local_dimensions_mm'],core_dimensions=[8*(vertices[:,2].max()/20),8,vertices[:,2].max()])
        integrity=('boundary_edges','nonmanifold_edges','nonmanifold_vertices','inconsistent_winding_edges','degenerate_faces','stl_normal_disagreements','nonadjacent_bvh_intersections')
        passed=(check['dimensions_pass'] and all(check[k]==0 for k in integrity) and check['components']==1 and check['signed_volume_mm3']>0 and check['table_contact_area_mm2']>0 and check['support_hull_margin_mm']>0 and check['minimum_table_clearance_mm']>=-1e-5)
        check['bread_study_absolute_thresholds_passed']=check.pop('passed');check['passed']=bool(passed)
        check['path']=str(destination.relative_to(ROOT));assert passed,json.dumps(check)
        source_frame=next(f['frame'] for f in source_manifest['frames'] if f['pose']==name)
        pose=dict(id=f'pose-{index:02}',v3_pose=name,source_v3_frame=source_frame,source_stl=str(source.relative_to(ROOT)),stl=str(destination.relative_to(ROOT)),stl_sha256=shared.sha(destination),canonical_surface_sha256=canonical,source_mesh_fingerprint=source_fingerprints[name],render_mesh_fingerprint=base.mesh_fingerprint(obj),dimensions_mm=check['local_dimensions_mm'],use_count=usage[name],stl_bytes_identical_to_v3=True,source_render_and_stl_surface_identical=True,validation=check)
        poses.append(pose);by_name[name]=pose;objects[name]=obj
        print('VALIDATED',pose['id'],name,flush=True)
    records=[]
    for f in source_manifest['frames']:
        pose=by_name[f['pose']];position=list(f['position_mm']);position[2]=0
        record=dict(frame=f['frame'],phase=f['phase'],pose_id=pose['id'],v3_pose=f['pose'],stl=pose['stl'],source_v3_frame=f['frame'],stl_source_v3_frame=pose['source_v3_frame'],position_mm=position,rotation_degrees=[0,0,0],scene_scale=[1,1,1],dimensions_mm=pose['dimensions_mm'],reused=pose['use_count']>1,exposure_start=f['exposure_start'],exposures_12fps=f['exposures_12fps'],source_v3_position_mm=f['position_mm'],note='All stones rest on Z=0; positions are physical filming guides. No aerial support.' )
        records.append(record)
        for name,obj in objects.items():
            obj.hide_render=name!=f['pose'];obj.keyframe_insert('hide_render',frame=f['exposure_start'])
        obj=objects[f['pose']];obj.location=position;obj.keyframe_insert('location',frame=f['exposure_start'])
    for obj in objects.values():
        for curve in obj.animation_data.action.fcurves:
            for key in curve.keyframe_points:key.interpolation='CONSTANT'
    scene.frame_start=1;scene.frame_end=40;scene.render.fps=12
    scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=16
    scene.render.resolution_x,scene.render.resolution_y=640,480;scene.render.resolution_percentage=100
    camera_matrix=scene.camera.matrix_world.copy();camera_lens=scene.camera.data.lens
    images=[];comparisons=[];all_world_clearances=[]
    for r in records:
        scene.frame_set(r['exposure_start']);obj=objects[r['v3_pose']]
        assert [name for name,o in objects.items() if not o.hide_render]==[r['v3_pose']]
        assert list(obj.scale)==[1,1,1] and list(obj.rotation_euler)==[0,0,0]
        assert scene.camera.matrix_world==camera_matrix and scene.camera.data.lens==camera_lens
        clearance=min((obj.matrix_world@v.co).z for v in obj.data.vertices)
        assert abs(clearance)<1e-5,clearance
        all_world_clearances.append(clearance)
        path=OUT/f"frame-{r['frame']:02}.png";scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        assert gpu.platform.vendor_get()=='AMD Radeon Pro 5600M' and gpu.platform.backend_type_get()=='METAL'
        r['render']=str(path.relative_to(ROOT));images.append(path)
        comparison=OUT/f"comparison-{r['frame']:02}.png"
        ideal=ROOT/source_manifest['frames'][r['frame']-1]['render']
        subprocess.run(['magick','montage','-background','#20232a','-fill','white','-font','Helvetica','-pointsize','18','-label','Approved v3 / aerial',str(ideal),'-label','Print reproduction / tabletop',str(path),'-geometry','640x480+0+8','-tile','2x1',str(comparison)],check=True)
        comparisons.append(comparison)
    scene.frame_set(1);scene.name='Stone to Fireworks tabletop print-set-v1'
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(MODEL))
    shared.sheet([(f"{r['frame']:02} {r['phase']} / {r['pose_id']}",p) for r,p in zip(records,images)],OUT/'contact-sheet.png',4)
    assemble_gif(images,records,OUT/'print-reproduction.gif');assemble_gif(comparisons,records,OUT/'v3-vs-tabletop.gif')
    # Show all physical models at one common tabletop datum, independently of their filming travel.
    scene.camera.data.type='ORTHO';scene.camera.data.ortho_scale=85;scene.camera.location=(0,85,110)
    scene.camera.rotation_euler=(Vector((0,0,8))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    for obj in objects.values():obj.animation_data_clear();obj.hide_render=True
    selected=[]
    for pose in poses:
        obj=objects[pose['v3_pose']];obj.location=(0,0,0);obj.hide_render=False
        path=OUT/(pose['id']+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        selected.append((pose['id']+' / '+pose['v3_pose'],path));obj.hide_render=True
    shared.sheet(selected,OUT/'selected-shapes.png',4)
    with (OUT/'frame-to-stl.csv').open('w',newline='') as handle:
        columns=['frame','phase','stl','source_v3_frame','stl_source_v3_frame','x_mm','y_mm','z_mm','rotation_x_deg','rotation_y_deg','rotation_z_deg','size_x_mm','size_y_mm','size_z_mm','reused','exposure_start','exposures_12fps','notes']
        writer=csv.DictWriter(handle,fieldnames=columns,lineterminator='\n');writer.writeheader()
        for r in records:
            writer.writerow(dict(frame=r['frame'],phase=r['phase'],stl=r['stl'],source_v3_frame=r['source_v3_frame'],stl_source_v3_frame=r['stl_source_v3_frame'],x_mm=r['position_mm'][0],y_mm=r['position_mm'][1],z_mm=0,rotation_x_deg=0,rotation_y_deg=0,rotation_z_deg=0,size_x_mm=r['dimensions_mm'][0],size_y_mm=r['dimensions_mm'][1],size_z_mm=r['dimensions_mm'][2],reused=r['reused'],exposure_start=r['exposure_start'],exposures_12fps=r['exposures_12fps'],notes=r['note']))
    assert all(shared.sha(ROOT/p)==h for p,h in protected_hashes.items())
    manifest=dict(status='Print-set candidate awaiting visual review',fps=12,shooting_states=20,total_exposures=40,duration_seconds=40/12,poses=poses,frames=records,scene=str(MODEL.relative_to(ROOT)),camera_unchanged_from_v3=True,camera_location_mm=list(camera_matrix.translation),camera_lens_mm=camera_lens)
    report=dict(passed=all(p['validation']['passed'] for p in poses),fresh_stl_checks=True,all_stls_byte_identical_to_v3=True,all_source_and_render_surfaces_match=True,all_world_minimum_z_mm=all_world_clearances,scene_scale_always_one=True,all_scene_rotations_zero=True,v3_unchanged=True,v3_protected_sha256=protected_hashes,rendering=dict(engine=scene.render.engine,gpu=gpu.platform.vendor_get(),backend=gpu.platform.backend_type_get(),samples=16),poses=poses,limitations=['STL coordinates are millimeters; STL format has no unit metadata.','Sampled vertical core thickness is not an exhaustive minimum wall or feature thickness analysis.','Shared-vertex triangle intersections are excluded from the BVH test.','Fine shallow relief on 25% miniature may not resolve in FDM; no reliable nozzle/profile is specified.','Slicer, print orientation, supports during printing, material strength and physical filming are unverified.','Tabletop retreat intentionally replaces aerial travel; perceived sliding remains a visual-review concern.'])
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('TABLETOP PRINT SET COMPLETE',flush=True)
if __name__=='__main__':main()
