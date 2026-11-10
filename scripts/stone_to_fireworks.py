"""Initial Stone to Fireworks study; Blender 4.5 Python, no physical controls."""
import sys, json, hashlib, subprocess, math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stone_to_bread as base
ROOT = base.ROOT
OUT = ROOT/'previews/stone-to-fireworks'
EXPORT = ROOT/'exports/stone-to-fireworks'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def deform(source, press, pull, recoil, size):
    points = source.copy()
    x,y,z = source.T
    # Top-centered pressure falls off smoothly toward the lateral and far surfaces.
    weight = np.exp(-(x/8)**2-((y-3)/9)**2)
    roof = np.clip(z/20,0,1)
    points[:,2] = z*(1-press*0.32*weight*roof)
    points[:,0] = x*(1+press*0.07*weight)
    # A monotone nearward map stretches the same material while anchoring the far edge.
    q = np.clip((y+12.5)/25,0,1)
    near = q*q*(3-2*q)
    across = np.exp(-(x/10)**4)
    points[:,1] += pull*25*near*across
    points[:,2] *= 1-pull*0.32*near*across
    # Release briefly gathers material and compresses it in the launch direction.
    points[:,1] *= 1-recoil*0.12
    points[:,2] *= 1+recoil*0.08
    return points*size

def sheet(items, path, columns=4):
    command=['magick','montage','-background','#20232a','-fill','white','-font','Helvetica','-pointsize','15']
    for label,image in items:
        command += ['-label',label,str(image)]
    subprocess.run(command+['-geometry','320x240+6+12','-tile',f'{columns}x',str(path)],check=True)

def main():
    assert bpy.app.version[:2] == (4,5)
    OUT.mkdir(parents=True,exist_ok=True)
    EXPORT.mkdir(parents=True,exist_ok=True)
    protected={str(p.relative_to(ROOT)):sha(p) for folder in ('exports','models','scripts','docs','previews') for p in (ROOT/folder).rglob('*') if p.is_file() and 'stone-to-fireworks' not in str(p) and p.name!='stone_to_fireworks.py' and '__pycache__' not in str(p)}
    source_path=ROOT/'exports/stone-to-bread/frame-01.stl'
    source,faces,_=base.read_stl(source_path)
    scene,_,_,_=base.setup_scene()
    scene.name='Stone to Fireworks initial study'
    scene.render.engine="BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples=16
    scene.render.resolution_x,scene.render.resolution_y=640,480
    scene.camera.data.type='PERSP'
    scene.camera.data.lens=34
    scene.camera.location=(0,145,205)
    target=Vector((0,-40,0))
    scene.camera.rotation_euler=(target-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.camera.data.clip_end=2000
    scene.render.fps=12
    mat=base.material('Smooth warm-gray pebble',(0.31,0.29,0.265))
    shader=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    shader.inputs['Roughness'].default_value=.78
    noise=mat.node_tree.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=0.34
    tex=mat.node_tree.nodes.new('ShaderNodeTexCoord')
    ramp=mat.node_tree.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color=(.22,.215,.20,1)
    ramp.color_ramp.elements[1].color=(.40,.385,.35,1)
    mat.node_tree.links.new(tex.outputs['Object'],noise.inputs['Vector'])
    mat.node_tree.links.new(noise.outputs['Fac'],ramp.inputs[0])
    mat.node_tree.links.new(ramp.outputs[0],shader.inputs['Base Color'])
    # Explicit fixed states: shape parameters are independent of filming placements.
    specs=[('rest',0,0,0,1,0,5),('press-light',.45,0,0,1,0,3),('press',1,0,0,1,0,3),('recover',.25,0,0,1,0,2),('rest',0,0,0,1,0,2),('pull-start',.4,.12,0,1,0,2),('pull-low',.5,.28,0,1,0,2),('pull-mid',.6,.48,0,1,0,2),('pull-high',.65,.72,0,1,0,2),('pull-max',.7,1,0,1,0,4),('release',.25,.38,.25,1,-2,1),('snap',0,.03,1,1,-8,1),('rest',0,0,0,1,-25,1),('rest',0,0,0,1,-58,1),('flight-small',0,0,0,.65,-100,1),('flight-tiny',0,0,0,.4,-150,1),('flight-distant',0,0,0,.25,-205,1),('flight-distant',0,0,0,.25,-230,2)]
    objects={}; records=[]; validation=[]; images=[]
    keys=(0,2,6,9,10,16)
    for i,(name,press,pull,recoil,size,y,hold) in enumerate(specs):
        timeline_frame=1+sum(r['exposures_12fps'] for r in records)
        scene.frame_set(timeline_frame)
        if name not in objects:
            coords=deform(source,press,pull,recoil,size)
            obj=base.make_mesh(scene,name,coords.tolist(),faces.tolist())
            obj.data.materials.append(mat)
            for polygon in obj.data.polygons: polygon.use_smooth=True
            objects[name]=obj
            if i>0:
                obj.hide_render=True
                obj.keyframe_insert('hide_render',frame=1)
            # Export the exact resting mesh without filming translation.
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True); bpy.context.view_layer.objects.active=obj
            path=EXPORT/f'{name}.stl'
            bpy.ops.wm.stl_export(filepath=str(path),export_selected_objects=True,global_scale=1,use_scene_unit=False,forward_axis='Y',up_axis='Z')
            report=base.validate(path,1,np.eye(3),expected_dimensions=np.ptp(coords,axis=0).tolist(),core_dimensions=[8*size,8,20*size])
            integrity=('boundary_edges','nonmanifold_edges','nonmanifold_vertices','inconsistent_winding_edges','degenerate_faces','stl_normal_disagreements','nonadjacent_bvh_intersections')
            # Miniatures intentionally have smaller support patches than the bread-study's 20 mm² threshold.
            passed=all(report[k]==0 for k in integrity) and report['components']==1 and report['signed_volume_mm3']>0 and report['table_contact_area_mm2']>0 and report['support_hull_margin_mm']>0 and report['minimum_table_clearance_mm']>=-1e-5 and report['dimensions_pass']
            report['bread_study_absolute_thresholds_passed']=report.pop('passed')
            report['passed']=bool(passed)
            report['study_passed']=bool(passed)
            assert passed, json.dumps(report)
            exported,_,_=base.read_stl(path)
            expected=deform(source,press,pull,recoil,size).astype(np.float32)
            order=lambda a:a[np.lexsort(a.T)]
            assert np.array_equal(order(exported.astype(np.float32)),order(expected))
            report.update(id=name,stl=str(path.relative_to(ROOT)),independent_geometry_regeneration_matches=True,render_stl_vertices_identical=True)
            validation.append(report)
            print('VALIDATED',name,flush=True)
        obj=objects[name]
        obj['generator']='scripts/stone_to_fireworks.py'
        for other in objects.values(): other.hide_render=True
        obj.hide_render=False; obj.location=(0,y,0)
        for other in objects.values():
            other.keyframe_insert('hide_render',frame=timeline_frame)
        obj.keyframe_insert('location',frame=timeline_frame)
        image=OUT/f'frame-{i+1:02}.png'
        scene.render.filepath=str(image)
        bpy.ops.render.render(write_still=True)
        images.append((f'{i+1:02} {name}',image))
        records.append(dict(frame=i+1,exposure_start=timeline_frame,pose=name,press=press,pull=pull,recoil=recoil,physical_size_factor=size,scene_scale=[1,1,1],position_mm=[0,y,0],exposures_12fps=hold,duration_ms=round(hold*1000/12),stl=str((EXPORT/f'{name}.stl').relative_to(ROOT)),render=str(image.relative_to(ROOT))))
    scene.frame_end=sum(r['exposures_12fps'] for r in records)
    # Discrete visibility and location keys are held, never interpolated into CGI-only poses.
    for obj in objects.values():
        if obj.animation_data:
            for fc in obj.animation_data.action.fcurves:
                for key in fc.keyframe_points: key.interpolation='CONSTANT'
    scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/stone-to-fireworks.blend'))
    sheet(images,OUT/'contact-sheet-v1.png',4)
    sheet([images[k] for k in keys],OUT/'key-poses-v1.png',3)
    command=['magick']
    for (_,image),record in zip(images,records): command+=['-delay',str(round(record['exposures_12fps']*100/12)),str(image)]
    subprocess.run(command+['-loop','0',str(OUT/'sequence-v1.gif')],check=True)
    # Orthographic top comparisons isolate deformation from perspective and filming travel.
    scene.camera.data.type='ORTHO'; scene.camera.data.ortho_scale=85
    scene.camera.location=(0,10,250); scene.camera.rotation_euler=(0,0,math.pi)
    tops=[]
    for k in keys:
        scene.frame_set(records[k]['exposure_start'])
        obj=objects[records[k]['pose']]
        for other in objects.values(): other.hide_render=other!=obj
        curves = [c for c in obj.animation_data.action.fcurves if c.data_path == 'location']
        for curve in curves: curve.mute = True
        obj.location=(0,0,0)
        path=OUT/f'key-top-{k+1:02}.png';scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True);tops.append((records[k]['pose'],path))
        for curve in curves: curve.mute = False
    sheet(tops,OUT/'key-poses-top-v1.png',3)
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    report=dict(status='Initial study awaiting visual review',source=str(source_path.relative_to(ROOT)),source_sha256=sha(source_path),poses=validation,frames=records,unique_candidate_shapes=len(objects),protected_assets_unchanged=True,protected_sha256=protected,storyboard_image_available=False,limitations=['No attached storyboard was available in this request; six written phases were used.','Flight is a tabletop depth illusion, not physical airborne motion.','Miniatures are distinct fixed meshes, never scene scaling.','Minimum normal thickness, shared-vertex intersections, slicer/support and physical tests are unverified.','Independent coordinate regeneration matches; independent-process STL byte comparison is not yet performed.'])
    (OUT/'validation-v1.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'manifest-v1.json').write_text(json.dumps(dict(fps=12,frames=records,total_exposures=sum(r['exposures_12fps'] for r in records)),indent=2)+'\n')
def render_saved():
    """Resume previews without regenerating the validated candidate solids."""
    import gpu
    from bpy_extras.object_utils import world_to_camera_view
    manifest = json.loads((OUT/'manifest-v1.json').read_text())
    report = json.loads((OUT/'validation-v1.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/stone-to-fireworks.blend'), use_scripts=False)
    scene = bpy.context.scene
    objects = {p['id']: bpy.data.objects[p['id']] for p in report['poses']}
    fingerprints = {name: base.mesh_fingerprint(obj) for name, obj in objects.items()}
    # Rebuild held exposure keys so Blender playback and GIF timing describe the same shots.
    for obj in objects.values():
        obj.animation_data_clear()
    exposure = 1
    for record in manifest['frames']:
        record['exposure_start'] = exposure
        for name, obj in objects.items():
            obj.hide_render = name != record['pose']
            obj.keyframe_insert('hide_render', frame=exposure)
        obj = objects[record['pose']]
        obj.location = record['position_mm']
        obj.keyframe_insert('location', frame=exposure)
        exposure += record['exposures_12fps']
    for obj in objects.values():
        for curve in obj.animation_data.action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'CONSTANT'
    scene.frame_end, scene.render.fps = exposure-1, 12
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_percentage = 100
    camera = scene.camera
    camera.data.type, camera.data.lens = 'PERSP', 34
    camera.location = (0, 145, 205)
    camera.rotation_euler = (Vector((0, -40, 0))-camera.location).to_track_quat('-Z', 'Y').to_euler()
    images, projection_bounds = [], []
    for record in manifest['frames']:
        scene.frame_set(record['exposure_start'])
        obj = objects[record['pose']]
        assert [name for name, other in objects.items() if not other.hide_render] == [record['pose']]
        # Project the enclosing box to conservatively check all mesh vertices against the fixed frame.
        projected = [world_to_camera_view(scene, camera, obj.matrix_world@Vector(v)) for v in obj.bound_box]
        bounds = [min(v.x for v in projected), max(v.x for v in projected),
                  min(v.y for v in projected), max(v.y for v in projected)]
        assert min(bounds[0], bounds[2]) > .025 and max(bounds[1], bounds[3]) < .975, bounds
        projection_bounds.append(bounds)
        path = ROOT/record['render']
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        assert gpu.platform.vendor_get() == 'AMD Radeon Pro 5600M'
        assert gpu.platform.backend_type_get() == 'METAL'
        images.append((f"{record['frame']:02} {record['pose']}", path))
    scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/stone-to-fireworks.blend'))
    sheet(images, OUT/'contact-sheet-v1.png', 4)
    keys = (0, 2, 6, 9, 10, 16)
    sheet([images[k] for k in keys], OUT/'key-poses-v1.png', 3)
    command = ['magick']
    # Cumulative rounding keeps the GIF's centisecond timing aligned with the 12 fps exposure timeline.
    previous = 0
    for (_, path), record in zip(images, manifest['frames']):
        cumulative = round((record['exposure_start']-1+record['exposures_12fps'])*100/12)
        command += ['-delay', str(cumulative-previous), str(path)]
        previous = cumulative
    subprocess.run(command+['-loop', '0', str(OUT/'sequence-v1.gif')], check=True)
    camera.data.type, camera.data.ortho_scale = 'ORTHO', 85
    camera.location, camera.rotation_euler = (0, 10, 250), (0, 0, math.pi)
    tops = []
    for k in keys:
        record = manifest['frames'][k]
        scene.frame_set(record['exposure_start'])
        obj = objects[record['pose']]
        curves = [c for c in obj.animation_data.action.fcurves if c.data_path == 'location']
        for curve in curves: curve.mute = True
        obj.location = (0, 0, 0)
        path = OUT/f'key-top-{k+1:02}.png'
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        tops.append((record['pose'], path))
        for curve in curves: curve.mute = False
    sheet(tops, OUT/'key-poses-top-v1.png', 3)
    assert fingerprints == {name: base.mesh_fingerprint(obj) for name, obj in objects.items()}
    report.update(frames=manifest['frames'], fixed_camera_projection_bounds=projection_bounds,
                  all_poses_inside_camera_margin=True, saved_scene_single_visible_pose_per_frame=True,
                  render_mesh_fingerprints=fingerprints,
                  rendering=dict(engine=scene.render.engine, gpu=gpu.platform.vendor_get(),
                                 backend=gpu.platform.backend_type_get(), samples=16),
                  total_exposures=exposure-1, duration_seconds=(exposure-1)/12)
    (OUT/'validation-v1.json').write_text(json.dumps(report, indent=2)+'\n')
    (OUT/'manifest-v1.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('GPU REVIEW OUTPUTS COMPLETE', flush=True)


if __name__ == '__main__':
    render_saved() if '--render-only' in sys.argv else main()
