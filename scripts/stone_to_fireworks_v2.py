"""Three presses and an overlapping recoil/airborne launch; Blender 4.5."""
import sys,json,math,tempfile,subprocess,argparse
from pathlib import Path
import bpy,numpy as np,gpu
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0,str(Path(__file__).resolve().parent))
import stone_to_fireworks as v1
base=v1.base
ROOT=base.ROOT
# Pose identity is independent of filming placement; rest and miniatures are reused.
SPECS=[('rest',0,0,0,1,0,0),('press-a',.85,0,0,1,0,0),('rest',0,0,0,1,0,0),('press-b',1,0,0,1,0,0),('rest',0,0,0,1,0,0),('press-c',.95,0,0,1,0,0),('rest',0,0,0,1,0,0),('pull-start',.4,.12,0,1,0,0),('pull-low',.5,.28,0,1,0,0),('pull-mid',.6,.48,0,1,0,0),('pull-high',.65,.72,0,1,0,0),('pull-max',.7,1,0,1,0,0),('release',.25,.42,.4,1,-14,2),('snap',0,.08,1,1,-40,10),('rest',0,0,0,1,-82,24),('rest',0,0,0,1,-130,38),('small',0,0,0,.65,-180,48),('tiny',0,0,0,.4,-230,54),('distant',0,0,0,.25,-280,52),('distant',0,0,0,.25,-315,44)]

def shape(source,spec):
    name,press,pull,recoil,size,_,_=spec
    if name.startswith('press-'):
        points=source.copy();x,y,z=source.T
        # A narrower top contact makes a local dimple, while the bottom remains fixed.
        radius=(x/6.5)**2+((y-3)/7)**2
        weight=np.exp(-radius);roof=np.clip(z/20,0,1)
        points[:,2]=z*(1-.38*press*weight*roof**1.5)
        # An annular rise around the contact suggests displaced, soft stone material.
        points[:,2]+=.9*press*radius*np.exp(-radius)*roof
        points[:,0]=x*(1+.08*press*weight*roof)
        return points
    return v1.deform(source,press,pull,recoil,size)

def export(scene,name,coords,faces,path):
    obj=base.make_mesh(scene,name,coords.tolist(),faces.tolist())
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.wm.stl_export(filepath=str(path),export_selected_objects=True,global_scale=1,use_scene_unit=False,forward_axis='Y',up_axis='Z')
    return obj

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--geometry-only',action='store_true');parser.add_argument('--output-root',type=Path,default=ROOT)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=args.output_root/'previews/stone-to-fireworks/v2';out.mkdir(parents=True,exist_ok=True)
    exports=args.output_root/'exports/stone-to-fireworks/v2';exports.mkdir(parents=True,exist_ok=True)
    # Protect v1 files explicitly; no earlier motif is opened for writing.
    protected=[ROOT/'models/stone-to-fireworks.blend',ROOT/'scripts/stone_to_fireworks.py',ROOT/'docs/stone-to-fireworks.md']
    protected+=list((ROOT/'previews/stone-to-fireworks').glob('*.*'))+list((ROOT/'exports/stone-to-fireworks').glob('*.stl'))
    hashes={str(p.relative_to(ROOT)):v1.sha(p) for p in protected}
    source,faces,_=base.read_stl(ROOT/'exports/stone-to-fireworks/rest.stl')
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/stone-to-fireworks.blend'),use_scripts=False)
    scene=bpy.context.scene;material=bpy.data.objects['rest'].data.materials[0]
    # Keep the v1 studio, replacing only its stone objects in this separate scene revision.
    old=json.loads((ROOT/'previews/stone-to-fireworks/validation-v1.json').read_text())
    for p in old['poses']:bpy.data.objects.remove(bpy.data.objects[p['id']],do_unlink=True)
    objects={};checks=[];records=[]
    for i,spec in enumerate(SPECS):
        name,press,pull,recoil,size,y,z=spec
        if name not in objects:
            coords=shape(source,spec);path=exports/f'{name}.stl'
            obj=export(scene,name,coords,faces,path);objects[name]=obj
            obj.data.materials.append(material)
            for poly in obj.data.polygons:poly.use_smooth=True
            result=base.validate(path,1,np.eye(3),expected_dimensions=np.ptp(coords,axis=0).tolist(),core_dimensions=[8*size,8,20*size])
            integrity=('boundary_edges','nonmanifold_edges','nonmanifold_vertices','inconsistent_winding_edges','degenerate_faces','stl_normal_disagreements','nonadjacent_bvh_intersections')
            passed=all(result[k]==0 for k in integrity) and result['components']==1 and result['signed_volume_mm3']>0 and result['table_contact_area_mm2']>0 and result['support_hull_margin_mm']>0 and result['minimum_table_clearance_mm']>=-1e-5 and result['dimensions_pass']
            result['bread_study_absolute_thresholds_passed']=result.pop('passed');result['passed']=bool(passed)
            assert passed,json.dumps(result)
            vertices,_,_=base.read_stl(path);order=lambda a:a[np.lexsort(a.T)]
            assert np.array_equal(order(vertices.astype(np.float32)),order(coords.astype(np.float32)))
            result.update(id=name,stl=str(path.relative_to(args.output_root)),mesh_fingerprint=base.mesh_fingerprint(obj),render_stl_vertices_identical=True)
            checks.append(result);print('VALIDATED',name,flush=True)
        phase='rest' if i==0 else 'press-recover' if i<7 else 'pull' if i<12 else 'recoil-launch' if i<14 else 'flight'
        records.append(dict(frame=i+1,phase=phase,pose=name,press=press,pull=pull,recoil=recoil,physical_size_factor=size,scene_scale=[1,1,1],position_mm=[0,y,z],exposures_12fps=2,exposure_start=2*i+1,stl=f'exports/stone-to-fireworks/v2/{name}.stl',requires_flight_support=z>0))
    report=dict(status='v2 awaiting visual review',poses=checks,frames=records,source='exports/stone-to-fireworks/rest.stl',source_sha256=v1.sha(ROOT/'exports/stone-to-fireworks/rest.stl'),v1_sha256=hashes,limitations=['No attached storyboard image was available; written phase descriptions guide this revision.','Airborne filming poses require a support/removal or compositing method; no jig is generated.','Minimum normal wall thickness, shared-vertex intersections, slicer and physical print tests remain unverified.','Support margins refer to local resting STLs, not airborne scene stability.'])
    if not args.geometry_only:
        # Independent Blender regeneration writes only into a temporary directory.
        with tempfile.TemporaryDirectory(prefix='fireworks-v2-regen-') as tmp:
            subprocess.run([bpy.app.binary_path,'--background','--threads','2','--python-exit-code','1','--python',__file__,'--','--geometry-only','--output-root',tmp],check=True,stdout=subprocess.DEVNULL)
            for c in checks:
                c['independent_stl_sha256']=v1.sha(Path(tmp)/c['stl']);assert c['independent_stl_sha256']==c['sha256']
                c['independent_process_hash_matches']=True
        for r in records:
            for name,obj in objects.items():
                obj.hide_render=name!=r['pose'];obj.keyframe_insert('hide_render',frame=r['exposure_start'])
            obj=objects[r['pose']];obj.location=r['position_mm'];obj.keyframe_insert('location',frame=r['exposure_start'])
        for obj in objects.values():
            for curve in obj.animation_data.action.fcurves:
                for k in curve.keyframe_points:k.interpolation='CONSTANT'
        scene.frame_start=1;scene.frame_end=40;scene.render.fps=12
        scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=16
        scene.render.resolution_x,scene.render.resolution_y=640,480;scene.render.resolution_percentage=100
        camera=scene.camera;camera.data.type='PERSP';camera.data.lens=32;camera.location=(0,160,245)
        camera.rotation_euler=(Vector((0,-65,15))-camera.location).to_track_quat('-Z','Y').to_euler()
        # Adjust one global focal length before any rendering; never reframe per pose.
        def bounds(r):
            scene.frame_set(r['exposure_start']);obj=objects[r['pose']]
            projected=[world_to_camera_view(scene,camera,obj.matrix_world@Vector(v)) for v in obj.bound_box]
            return [min(v.x for v in projected),max(v.x for v in projected),min(v.y for v in projected),max(v.y for v in projected)]
        for attempt in range(20):
            boxes=[bounds(r) for r in records]
            if all(min(b[0],b[2])>.04 and max(b[1],b[3])<.96 for b in boxes):break
            camera.data.lens*=.95
        else:raise RuntimeError('Fixed framing cannot contain all poses')
        images=[]
        for r in records:
            scene.frame_set(r['exposure_start'])
            assert [name for name,obj in objects.items() if not obj.hide_render]==[r['pose']]
            path=out/f"frame-{r['frame']:02}.png";scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
            assert gpu.platform.vendor_get()=='AMD Radeon Pro 5600M' and gpu.platform.backend_type_get()=='METAL'
            images.append((f"{r['frame']:02} {r['phase']} / {r['pose']}",path));r['render']=str(path.relative_to(args.output_root))
        scene.frame_set(1);scene.name='Stone to Fireworks v2'
        (args.output_root/'models').mkdir(exist_ok=True);bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(args.output_root/'models/stone-to-fireworks-v2.blend'))
        v1.sheet(images,out/'contact-sheet-v2.png',4);keys=(0,3,8,11,12,13,15,18)
        v1.sheet([images[k] for k in keys],out/'key-poses-v2.png',4)
        command=['magick'];previous=0
        for (_,path),r in zip(images,records):
            cumulative=round((r['exposure_start']+1)*100/12);command+=['-delay',str(cumulative-previous),str(path)];previous=cumulative
        subprocess.run(command+['-loop','0',str(out/'sequence-v2.gif')],check=True)
        report['camera']=dict(location_mm=list(camera.location),lens_mm=camera.data.lens,projection_bounds=boxes)
        camera.data.type='ORTHO';camera.data.ortho_scale=85;camera.location=(0,10,250);camera.rotation_euler=(0,0,math.pi)
        tops=[]
        for k in keys:
            r=records[k];scene.frame_set(r['exposure_start']);obj=objects[r['pose']]
            curves=[c for c in obj.animation_data.action.fcurves if c.data_path=='location']
            for c in curves:c.mute=True
            obj.location=(0,0,0);bpy.context.view_layer.update()
            path=out/f"top-{r['frame']:02}.png";scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);tops.append((r['pose'],path))
            for c in curves:c.mute=False
        v1.sheet(tops,out/'key-poses-top-v2.png',4)
        report['rendering']=dict(engine=scene.render.engine,gpu=gpu.platform.vendor_get(),backend=gpu.platform.backend_type_get(),samples=16)
        report['single_visible_pose_per_frame']=True
    assert all(v1.sha(ROOT/p)==h for p,h in hashes.items())
    report['v1_unchanged']=True
    (out/'validation-v2.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'manifest-v2.json').write_text(json.dumps(dict(fps=12,shooting_states=20,total_exposures=40,duration_seconds=40/12,frames=records),indent=2)+'\n')
    print('V2 COMPLETE',flush=True)
if __name__=='__main__':main()
