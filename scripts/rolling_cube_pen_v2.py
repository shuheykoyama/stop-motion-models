"""Second rolling cube pen study: left cap, settled scatter and fixed cube template, Blender 4.5."""
import sys,math,json,hashlib,subprocess,argparse
from pathlib import Path
import bpy,bmesh,numpy as np,gpu
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
import rolling_wavy_pen as pen
import stone_to_bread as base
ROOT=base.ROOT
LENGTH=141.8
COUNT=12
CELL=LENGTH/COUNT
SEGMENTS=64
OUT=ROOT/'previews/rolling-cube-pen/v2'
MODEL=ROOT/'models/rolling-cube-pen-v2.blend'

# Deterministic arrangement, indexed from cap to tip. No random scatter is generated.
FINAL_GAPS=np.array([1.0,1.8,1.2,2.2,1.1,1.6,1.3,2.4,1.0,1.9,1.4])
FINAL_Y=np.array([-2.2,1.4,-1.3,2.4,-.8,1.8,-2.0,1.0,2.2,-1.6,.6,-2.5])
FINAL_Y-=FINAL_Y.mean()
FINAL_YAW=np.array([-2.5,1.5,-1.0,3.0,-2.0,.8,2.2,-1.6,2.8,-.7,1.2,-2.2])

def camera_signature(scene):
    c=scene.camera;r=scene.render
    return dict(matrix_world=[list(row) for row in c.matrix_world],projection=c.data.type,
                ortho_scale=c.data.ortho_scale,lens=c.data.lens,shift=[c.data.shift_x,c.data.shift_y],
                resolution=[r.resolution_x,r.resolution_y,r.resolution_percentage],
                border=[r.use_border,r.use_crop_to_border,r.border_min_x,r.border_max_x,r.border_min_y,r.border_max_y])

def arrange(parts,objects,progress):
    bounds=[]
    for part in parts:
        cell=part['cell_index'];angle=math.radians(float(FINAL_YAW[cell]*progress))
        vertices=np.array([v.co[:] for v in objects[part['mesh_id']].data.vertices])
        rotated_x=vertices[:,0]*math.cos(angle)-vertices[:,1]*math.sin(angle)
        bounds.append((float(rotated_x.min()),float(rotated_x.max())))
        part['rotation_degrees']=[0,0,float(FINAL_YAW[cell]*progress)]
        part['position_mm'][1]+=float(FINAL_Y[cell]*progress)
        part['canonical_cube_edge_mm']=CELL
        part['fixed_end_bevel_mm']=.22
    gaps=.05*(1-progress)+FINAL_GAPS*progress
    centers=[0.0]
    # Cap is at positive world X, which projects to screen left with the unchanged camera.
    for i in range(1,COUNT):
        centers.append(centers[-1]+bounds[i-1][0]-bounds[i][1]-float(gaps[i-1]))
    middle=(min(x+b[0] for x,b in zip(centers,bounds))+max(x+b[1] for x,b in zip(centers,bounds)))/2
    for part,x in zip(parts,centers):part['position_mm'][0]=x-middle
    for index,part in enumerate(parts):part['projected_X_gap_to_next_mm']=float(gaps[index]) if index<COUNT-1 else None

def cube_closeup(scene,objects,records):
    """Compare actual v1/v2 final body cubes at one shared static detail scale."""
    old_manifest=json.loads((ROOT/'previews/rolling-cube-pen/manifest-v1.json').read_text())
    old_part=next(p for p in old_manifest['frames'][-1]['parts'] if p['cell_index']==6)
    with bpy.data.libraries.load(str(ROOT/'models/rolling-cube-pen.blend'),link=False) as (source,target):
        target.objects=[old_part['mesh_id']]
    old=target.objects[0];scene.collection.objects.link(old);old.animation_data_clear()
    for obj in objects.values():obj.animation_data_clear();obj.hide_render=True;obj.hide_viewport=True
    new=objects[next(p['mesh_id'] for p in records[-1]['parts'] if p['cell_index']==6)]
    for obj in (old,new):obj.location=(0,0,0);obj.rotation_euler=(0,0,0)
    camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=35
    camera.location=(0,80,95);camera.rotation_euler=(Vector((0,0,6))-camera.location).to_track_quat('-Z','Y').to_euler()
    images=[]
    for label,obj in [('v1',old),('v2',new)]:
        old.hide_render=True;old.hide_viewport=True;new.hide_render=True;new.hide_viewport=True
        obj.hide_render=False;obj.hide_viewport=False
        path=OUT/(label+'-body-cube-closeup.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        images.append((label+' / same physical scale',path))
    montage(images,OUT/'final-cube-closeup-v1-v2.png',2)


def ease(x):
    x=np.clip(x,0,1)
    return x*x*(3-2*x)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

# Recover the established marker's actual radial profile at the zero-angle vertex.
# That vertex has no clip relief; this avoids a second independent cap/profile design.
_reference,_,PROFILE_X=pen.geometry(0,roll_deg=0,centerline_fn=lambda x:0)
PROFILE_R=[_reference[i*pen.RADIAL_SEGMENTS][1] for i in range(len(PROFILE_X))]

def cross_section(x,square,division,end_reduction=0):
    radius=(1-square)*np.interp(x,PROFILE_X,PROFILE_R)+square*CELL/2
    if division:
        depth=3*ease(division/.70)
        for boundary in range(1,COUNT):
            center=-LENGTH/2+boundary*CELL
            onset=0 if boundary in (3,6,9) else .14+.025*((boundary-1)%4)
            activation=ease((division-onset)/.20)
            distance=abs(x-center)
            # Keep a shallow fixed cube-end bevel around a narrow splitting neck.
            # This avoids filling broad shrunken end faces after separation.
            bevel=.22*activation*(1-ease(distance/.85))
            neck=depth*activation*math.exp(-(distance/.18)**4)
            radius-=max(bevel,neck)
    radius-=end_reduction
    assert radius>2.5
    a=np.arange(SEGMENTS)*2*math.pi/SEGMENTS
    # Blend inverse exponent so intermediate corner roundness remains visually distinct.
    exponent=1/((1-square)/2+square/24)
    radial=radius/(np.abs(np.cos(a))**exponent+np.abs(np.sin(a))**exponent)**(1/exponent)
    # The broad integral clip remains actual geometry and diminishes into a cap-origin trace.
    cap=pen.smoothstep((x+65*pen.LENGTH_SCALE)/4)*pen.smoothstep((-37*pen.LENGTH_SCALE-x)/4)
    da=np.arctan2(np.sin(a-2.35),np.cos(a-2.35))
    clip=(.85*(1-square)+.25*square)*cap*np.exp(-.5*(da/.30)**4)
    radial+=clip*min(1,radius/(CELL/2))
    return radial*np.cos(a),radial*np.sin(a)

def support_properties(vertices,faces):
    tri=vertices[faces]
    crosses=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    weights=np.einsum('ij,ij->i',tri[:,0],np.cross(tri[:,1],tri[:,2]))/6
    volume=float(weights.sum())
    assert abs(volume)>1e-6
    center=np.sum(tri.sum(axis=1)*weights[:,None]/4,axis=0)/volume
    grounded=np.abs(vertices[:,2])<1e-5
    contact=np.all(grounded[faces],axis=1)
    area=float(np.linalg.norm(crosses[contact],axis=1).sum()/2)
    hull=base.hull(vertices[grounded,:2])
    if len(hull)<3:return volume,center,area,float('-inf')
    edge=np.roll(hull,-1,axis=0)-hull;offset=center[:2]-hull
    margin=float(((edge[:,0]*offset[:,1]-edge[:,1]*offset[:,0])/np.linalg.norm(edge,axis=1)).min())
    return volume,center,area,margin

def geometry(square,division,roll,cell=None,separation=0):
    if cell is None:
        low,high=-LENGTH/2,LENGTH/2;center=0
        xs=set(np.linspace(low,high,144).tolist())|set(PROFILE_X)
        if division:
            for k in range(1,COUNT):
                boundary=low+k*CELL
                xs.update(boundary+d for d in (-1,-.8,-.55,-.35,-.15,0,.15,.35,.55,.8,1))
    else:
        center=-LENGTH/2+(cell+.5)*CELL;low,high=center-CELL/2,center+CELL/2
        xs=set(np.linspace(low,high,14).tolist())
        for offset in (.12,.30,.55,.80,1.0):xs.update((low+offset,high-offset))
    xs=sorted({round(float(x),6) for x in xs if low-1e-5<=x<=high+1e-5})
    points=[];zero_crossings=[]
    for x in xs:
        reduction=0
        if cell is not None:
            # The separated cube template has one fixed end bevel at every separation state.
            end_distance=min(x-low,high-x)
            reduction=.22*(1-ease(end_distance/.85))
        y,z=cross_section(x,square,division if cell is None else 0,reduction)
        rotated_y=y*math.cos(roll)-z*math.sin(roll)
        rotated_z=y*math.sin(roll)+z*math.cos(roll)
        if abs(x-center)<(high-low)*.35:
            for j in range(SEGMENTS):
                k=(j+1)%SEGMENTS
                if rotated_y[j]*rotated_y[k]<=0 and abs(rotated_y[k]-rotated_y[j])>1e-12:
                    t=-rotated_y[j]/(rotated_y[k]-rotated_y[j])
                    zero_crossings.append(rotated_z[j]+t*(rotated_z[k]-rotated_z[j]))
        points.extend((x-center,float(yy),float(zz)) for yy,zz in zip(rotated_y,rotated_z))
    faces=[]
    for ring in range(len(xs)-1):
        for j in range(SEGMENTS):
            k=(j+1)%SEGMENTS;a=ring*SEGMENTS+j;b=ring*SEGMENTS+k;c=(ring+1)*SEGMENTS+k;d=(ring+1)*SEGMENTS+j
            faces.extend(((a,b,c),(a,c,d)))
    for ring,reverse in ((0,True),(len(xs)-1,False)):
        index=len(points);points.append((xs[ring]-center,0,0))
        for j in range(SEGMENTS):
            a=ring*SEGMENTS+j;b=ring*SEGMENTS+(j+1)%SEGMENTS
            faces.append((index,b,a) if reverse else (index,a,b))
    original=np.array(points);faces=np.array(faces,dtype=int)
    bottom=float(original[:,2].min())
    margin=.10+.55*abs(math.sin(2*roll))
    floor=max(bottom+.10,bottom+1.05*(1-square),min(zero_crossings)+margin)
    # Stable rigid props replace unstable edge-balanced poses. Only the underside is trimmed.
    for attempt in range(20):
        vertices=original.copy();vertices[:,2]=np.maximum(vertices[:,2]-floor,0)
        volume,com,area,support=support_properties(vertices,faces)
        if area>0 and support>.25:break
        floor+=.12
    else:raise RuntimeError('Could not establish finite stable contact')
    return vertices,faces,dict(underside_trim_depth_mm=floor-bottom,contact_area_mm2=area,support_margin_mm=support,center_of_mass_mm=com.tolist(),material_x_center_mm=center)

def validate(obj):
    vertices=np.array([v.co[:] for v in obj.data.vertices]);faces=np.array([p.vertices[:] for p in obj.data.polygons])
    bm=bmesh.new();bm.from_mesh(obj.data)
    remaining=set(bm.verts);components=0
    while remaining:
        stack=[remaining.pop()];components+=1
        while stack:
            for edge in stack.pop().link_edges:
                for vertex in edge.verts:
                    if vertex in remaining:remaining.remove(vertex);stack.append(vertex)
    tree=BVHTree.FromPolygons(vertices.tolist(),faces.tolist(),all_triangles=True,epsilon=0)
    collisions=sum(a<b and not set(faces[a]).intersection(faces[b]) for a,b in tree.overlap(tree))
    tri=vertices[faces];areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2
    volume,center,area,margin=support_properties(vertices,faces)
    result=dict(vertices=len(vertices),triangles=len(faces),components=components,boundary_edges=sum(e.is_boundary for e in bm.edges),nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),inconsistent_winding_edges=sum(e.is_manifold and not e.is_contiguous for e in bm.edges),degenerate_faces=int(np.count_nonzero(areas<1e-8)),nonadjacent_bvh_intersections=collisions,volume_mm3=volume,dimensions_mm=np.ptp(vertices,axis=0).tolist(),minimum_z_mm=float(vertices[:,2].min()),contact_area_mm2=area,support_margin_mm=margin,mesh_fingerprint=base.mesh_fingerprint(obj))
    result['passed']=bool(np.isfinite(vertices).all() and components==1 and volume>0 and area>0 and margin>0 and vertices[:,2].min()>=-1e-5 and all(result[k]==0 for k in ('boundary_edges','nonmanifold_edges','inconsistent_winding_edges','degenerate_faces','nonadjacent_bvh_intersections')))
    bm.free();assert result['passed'],json.dumps(result)
    return result

def motion(square,roll):
    # Integrate the ideal superellipse support height: a quarter-turn travels pi*r/2
    # for a circle and approaches one face width for a square.
    theta=np.linspace(0,abs(roll),129);p=1/((1-square)/2+square/24);q=p/(p-1)
    half_width=(1-square)*pen.CAP_RADIUS_MM+square*CELL/2
    heights=half_width*(np.abs(np.sin(theta))**q+np.abs(np.cos(theta))**q)**(1/q)
    return -6+float(np.sum((heights[1:]+heights[:-1])*.5*np.diff(theta)))

def montage(items,destination,columns=4):
    command=['magick','montage','-background','#20232a','-fill','white','-font','Helvetica','-pointsize','14']
    for label,path in items:command+=['-label',label,str(path)]
    subprocess.run(command+['-geometry','320x200+5+10','-tile',str(columns)+'x',str(destination)],check=True)

def cross_sections(objects,records):
    """Plot the actual center-shaft mesh sections at a common millimeter scale."""
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="280"><rect width="960" height="280" fill="#eeeeee"/>']
    for index,(frame,label) in enumerate(((1,'Circular / frame 01'),(31,'Rounded square / frame 31'),(41,'Square / frame 41'))):
        obj=objects[records[frame-1]['parts'][0]['mesh_id']]
        points=[vertex.co[:] for vertex in obj.data.vertices if abs(vertex.co.x)<1e-6]
        assert len(points)==SEGMENTS
        polygon=' '.join(f'{index*320+160+10*p[1]:.3f},{230-10*p[2]:.3f}' for p in points)
        svg.extend((f'<path d="M {index*320+30} 230 H {index*320+290}" stroke="#999"/>',
                    f'<polygon points="{polygon}" fill="#252529" stroke="#111" stroke-width="1"/>',
                    f'<text x="{index*320+160}" y="35" text-anchor="middle" font-family="Helvetica" font-size="17">{label}</text>'))
    svg.append('</svg>')
    path=OUT/'cross-sections-v2.svg';path.write_text('\n'.join(svg))
    subprocess.run(['magick',str(path),str(OUT/'cross-sections-v2.png')],check=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--no-render',action='store_true');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    assert bpy.app.version[:2]==(4,5)
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'frames').mkdir(exist_ok=True)
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    protected={p:digest(ROOT/p) for p in tracked if p and (ROOT/p).is_file()}
    v1_files=[ROOT/'models/rolling-cube-pen.blend',ROOT/'scripts/rolling_cube_pen.py',ROOT/'docs/rolling-cube-pen.md']
    v1_files += [p for p in (ROOT/'previews/rolling-cube-pen').rglob('*') if p.is_file() and not p.is_relative_to(OUT)]
    protected.update({str(p.relative_to(ROOT)):digest(p) for p in v1_files})
    scene,_,_,_=base.setup_scene();scene.name='Rolling Cube Pen - Study v2'
    scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=16
    scene.render.resolution_x,scene.render.resolution_y=800,500
    scene.render.fps=12
    scene.camera.data.type='ORTHO';scene.camera.data.ortho_scale=190
    scene.camera.location=(0,210,250);scene.camera.rotation_euler=(Vector((0,0,7))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    black=base.material('Unmarked black barrel',(.012,.012,.014));cap=base.material('Unmarked black cap',(.009,.009,.011))
    for mat,roughness in ((black,.34),(cap,.24)):
        next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Roughness'].default_value=roughness
    records=[];objects={};mesh_records=[];cache={};exposure=1
    for index in range(61):
        if index==0:phase=0;step=0;stroke=0;t=0;square=0;division=0;turn=0;direction='hold'
        else:
            phase=(index-1)//20;step=(index-1)%20+1;stroke=(step-1)//5;t=((step-1)%5+1)/5
            square=0 if phase==0 else float(ease(step/20)) if phase==1 else 1
            division=step/20 if phase==2 else 0
            tumble=float(np.interp(t,[0,.2,.4,.6,.8,1],[0,6/90,24/90,66/90,84/90,1]))
            progress=(1-square)*t+square*tumble
            turn=progress if stroke%2==0 else 1-progress
            direction='toward' if stroke%2==0 else 'away'
        roll=-math.pi/2*turn
        separated=division>=.75
        gap_progress=float(ease((division-.75)/.25)) if separated else 0
        gap=.05+.95*gap_progress if separated else 0
        parts=[]
        for cell in (range(COUNT) if separated else [None]):
            # Shared roll retains the v1 stroke; independent yaw is a rigid tabletop transform.
            part_roll=roll
            key=(round(square,8),round(division,8),round(part_roll,8),cell)
            if key not in cache:
                vertices,faces,contact=geometry(square,division,part_roll,cell,1 if separated else 0)
                # Reflect X only: cap changes screen side without reversing Y travel or the camera.
                vertices[:,0]*=-1
                faces=faces[:,::-1].copy()
                contact['center_of_mass_mm'][0]*=-1
                name=f'rolling-cube-pen-v2/mesh-{len(objects)+1:03}'
                obj=base.make_mesh(scene,name,vertices.tolist(),faces.tolist())
                obj.data.materials.append(black);obj.data.materials.append(cap)
                seam=(1-square)*(-32*pen.LENGTH_SCALE)+square*(-LENGTH/4)
                for polygon in obj.data.polygons:
                    polygon.use_smooth=True
                    polygon.material_index=int(-polygon.center.x+contact['material_x_center_mm']<seam)
                checked=validate(obj);checked.update(id=name,square_progress=square,split_progress=division,roll_degrees=math.degrees(part_roll),cell_index=cell,contact_correction=contact)
                objects[name]=obj;cache[key]=name;mesh_records.append(checked)
                print('VALIDATED',name,flush=True)
            name=cache[key]
            x=0 if cell is None else -(-LENGTH/2+(cell+.5)*CELL+(cell-(COUNT-1)/2)*gap)
            y=motion(square,part_roll)
            parts.append(dict(mesh_id=name,cell_index=cell,position_mm=[x,y,0],rotation_degrees=[0,0,0],scene_scale=[1,1,1]))
        if separated:
            arrange(parts,objects,gap_progress)
        hold=2 if index==0 or step%5==0 else 1
        records.append(dict(frame=index+1,phase=phase+1,stroke_in_phase=0 if index==0 else stroke+1,round_trip_in_phase=0 if index==0 else stroke//2+1,direction=direction,square_progress=square,split_progress=division,roll_degrees=math.degrees(roll),projected_X_gaps_mm=[p['projected_X_gap_to_next_mm'] for p in parts[:-1]] if separated else [],component_count=len(parts),parts=parts,exposure_start=exposure,exposures_12fps=hold))
        exposure+=hold
    for record in records:
        active={p['mesh_id']:p for p in record['parts']}
        for name,obj in objects.items():
            obj.hide_render=name not in active;obj.keyframe_insert('hide_render',frame=record['exposure_start'])
            obj.hide_viewport=name not in active;obj.keyframe_insert('hide_viewport',frame=record['exposure_start'])
            if name in active:
                obj.location=active[name]['position_mm'];obj.keyframe_insert('location',frame=record['exposure_start'])
                obj.rotation_euler=[math.radians(a) for a in active[name]['rotation_degrees']]
                obj.keyframe_insert('rotation_euler',frame=record['exposure_start'])
    for obj in objects.values():
        for curve in obj.animation_data.action.fcurves:
            for key in curve.keyframe_points:key.interpolation='CONSTANT'
    scene.frame_end=exposure-1;scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(MODEL),compress=True)
    manifest=dict(status='Initial study awaiting visual review; no production STL set selected',length_mm=LENGTH,nominal_barrel_diameter_mm=11.9,final_cube_nominal_edge_mm=CELL,final_cube_count=COUNT,final_target_gaps_mm=FINAL_GAPS.tolist(),final_y_offsets_mm=FINAL_Y.tolist(),final_yaws_degrees=FINAL_YAW.tolist(),fps=12,shooting_states=61,total_exposures=exposure-1,duration_seconds=(exposure-1)/12,phase_ranges={'cylinder':[1,21],'cylinder-to-square':[22,41],'square-to-cubes':[42,61]},round_trips_per_phase=2,total_round_trips=6,frames=records,mesh_validation=mesh_records,rendering=dict(engine=scene.render.engine,samples=16),limitations=['Stable underside corrections are baked into print-pose geometry; rotation is not exact rigid-body no-slip physics.','Phase 1 keeps the cylindrical visible profile, but different stable soles can require pose-specific props.','Groove neck design width is at least about 5.8 mm; global thickness, slicer, supports and physical tests are unverified.','STL selection and print-count optimization follow visual approval.','All geometry is discrete; no mesh animation or scene scaling is used.','Separated cube edge, axial length and end bevel are constant; only baked resting-sole corrections vary with rolling pose.'])
    if not args.no_render:
        images=[];fixed_camera=scene.camera.matrix_world.copy()
        fixed_signature=camera_signature(scene)
        for record in records:
            scene.frame_set(record['exposure_start'])
            assert sum(not o.hide_render for o in objects.values())==record['component_count']
            assert scene.camera.matrix_world==fixed_camera
            assert camera_signature(scene)==fixed_signature
            assert all(list(obj.scale)==[1,1,1] for obj in objects.values())
            path=OUT/'frames'/f"frame-{record['frame']:02}.png";scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
            assert gpu.platform.vendor_get()=='AMD Radeon Pro 5600M' and gpu.platform.backend_type_get()=='METAL'
            record['render']=str(path.relative_to(ROOT));images.append(path)
        montage([(f"{r['frame']:02} P{r['phase']} {r['direction']} / {r['component_count']} solids",p) for r,p in zip(records,images)],OUT/'contact-sheet-v2.png',6)
        groups={'cylinder-to-square': [1,26,31,41],'square-to-cubes':[41,46,51,55,56,61]}
        for name,frames in groups.items():montage([(f'{f:02}',images[f-1]) for f in frames],OUT/(name+'-v2.png'),4 if name=='cylinder-to-square' else 3)
        command=['magick'];previous=0
        for record,path in zip(records,images):
            cumulative=round((record['exposure_start']-1+record['exposures_12fps'])*100/12)
            command+=['-delay',str(cumulative-previous),str(path)];previous=cumulative
        subprocess.run(command+['-loop','0',str(OUT/'sequence-v2.gif')],check=True)
        # Comparison stills use common scales; they never alter animation framing.
        v1_out=ROOT/'previews/rolling-cube-pen'
        montage([('v1 / fixed animation camera',v1_out/'frames/frame-61.png'),('v2 / same camera and scale',images[-1])],OUT/'final-comparison-front-v1-v2.png',1)
        manifest['fixed_animation_camera']=fixed_signature
        scene.camera.location=(0,0,280);scene.camera.rotation_euler=(0,0,math.pi)
        tops=[]
        for f in (1,26,31,41,46,51,55,56,61):
            scene.frame_set(records[f-1]['exposure_start']);path=OUT/f'top-{f:02}.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);tops.append((f'{f:02}',path))
        montage(tops,OUT/'top-comparison-v2.png',3)
        cross_sections(objects,records)
        montage([('v1 / fixed top scale',v1_out/'top-61.png'),('v2 / same top scale',OUT/'top-61.png')],OUT/'final-comparison-top-v1-v2.png',1)
        cube_closeup(scene,objects,records)
        manifest['rendering'].update(gpu=gpu.platform.vendor_get(),backend=gpu.platform.backend_type_get())
    assert all(digest(ROOT/p)==h for p,h in protected.items())
    manifest['protected_assets_unchanged']=True;manifest['protected_sha256']=protected
    (OUT/'manifest-v2.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    (OUT/'validation-v2.json').write_text(json.dumps(dict(passed=all(m['passed'] for m in mesh_records),meshes=mesh_records,protected_assets_unchanged=True,final_independent_components=12,all_local_meshes_grounded=True),indent=2)+'\n')
    print('ROLLING CUBE PEN COMPLETE',len(records),'states',exposure-1,'exposures',flush=True)
if __name__=='__main__':main()
