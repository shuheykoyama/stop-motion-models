"""Assemble the adopted 43-STL/59-prop plan from unchanged existing solids."""
import argparse
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
from mathutils import Matrix

sys.path.insert(0,str(Path(__file__).resolve().parent))
import rolling_cube_pen_print_set_v2 as shared

ROOT=shared.ROOT
OUT=ROOT/'previews/rolling-cube-pen/print-set-v3'
EXPORT=ROOT/'exports/rolling-cube-pen/print-set-v3'
MODEL=ROOT/'models/rolling-cube-pen-print-set-v3.blend'
REVIEW=shared.OUT/'review/analysis.json'


def write_csv(path,rows):
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def selection():
    base=json.loads((shared.OUT/'manifest.json').read_text())
    review=json.loads(REVIEW.read_text())
    adopted={r['pose']:r['parts'] for r in review['proposed_placements'] if r['plan']=='hybrid59'}
    frames=[]
    paths=[]
    for row in base['frames']:
        # The review's adopted placements replace only the six separated poses.
        parts=adopted[row['frame']] if row['frame']>=56 else row['parts']
        frames.append(dict(frame=row['frame'],phase=row['phase'],direction=row['direction'],
                           exposure_start=row['exposure_start'],exposures_12fps=row['exposures_12fps'],
                           parts=parts))
        for part in parts:
            if part['stl'] not in paths:paths.append(part['stl'])
    assert len(paths)==43 and len(frames)==61
    return frames,paths


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-render',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    assert bpy.app.version[:2]==(4,5)
    for path in (OUT,EXPORT,OUT/'frames',OUT/'comparison',OUT/'selected'):
        path.mkdir(parents=True,exist_ok=True)
    # Preserve existing tracked and untracked motif assets; all outputs are new v3 paths.
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    # Tracked v3 outputs are deliberately regenerated; protect all other existing assets.
    paths=[ROOT/p for p in tracked if p and (ROOT/p).is_file() and not (ROOT/p).is_relative_to(OUT) and not (ROOT/p).is_relative_to(EXPORT) and ROOT/p!=MODEL]
    for folder in (ROOT/'previews/rolling-cube-pen',ROOT/'exports/rolling-cube-pen'):
        paths += [p for p in folder.rglob('*') if p.is_file() and not p.is_relative_to(OUT) and not p.is_relative_to(EXPORT)]
    paths += [p for p in (ROOT/'models').glob('rolling-cube-pen*.blend') if p!=MODEL]
    # Finder metadata can change while the user browses previews; it is not a model asset.
    protected={str(p.relative_to(ROOT)):shared.study.digest(p) for p in paths if p.name!='.DS_Store'}
    chosen,source_paths=selection()
    approved=json.loads((shared.study.OUT/'manifest-v2.json').read_text())
    sources={}
    for manifest in (shared.OUT/'manifest.json',shared.OUT/'self-standing-cubes/manifest.json'):
        for group in json.loads(manifest.read_text())['stls']:sources[group['stl']]=group
    bpy.ops.wm.open_mainfile(filepath=str(shared.study.MODEL),use_scripts=False)
    scene=bpy.context.scene
    scene.frame_set(1)
    camera=shared.study.camera_signature(scene)
    originals={r['id']:bpy.data.objects[r['id']] for r in approved['mesh_validation']}
    templates={}
    groups=[]
    geometry=[]
    for index,source_path in enumerate(source_paths,1):
        source=sources[source_path]
        path=EXPORT/f'pose-{index:02}.stl'
        shutil.copyfile(ROOT/source_path,path)
        assert shared.study.digest(path)==source['sha256']
        a,f,normals=shared.previous.read_stl(path)
        assert np.isfinite(a).all() and np.isfinite(normals).all()
        obj=shared.study.base.make_mesh(scene,f'template/pose-{index:02}',a.tolist(),f.tolist())
        original=originals[source['source_v2_mesh']]
        for material in original.data.materials:obj.data.materials.append(material)
        for p,q in zip(obj.data.polygons,original.data.polygons):
            p.use_smooth=True
            p.material_index=q.material_index
        check=shared.study.validate(obj)
        check.update(id=f'pose-{index:02}',stl=str(path.relative_to(ROOT)))
        geometry.append(check)
        group=dict(id=f'pose-{index:02}',stl=str(path.relative_to(ROOT)),source_stl=source_path,
                   source_v2_mesh=source['source_v2_mesh'],sha256=shared.study.digest(path),
                   dimensions_mm=check['dimensions_mm'],volume_mm3=check['volume_mm3'],
                   kind=source['kind'],surface_sha256=shared.previous.surface_hash(a,f),
                   mesh_fingerprint=shared.study.base.mesh_fingerprint(obj))
        groups.append(group)
        templates[source_path]=obj
        print('V3 STL',group['id'],flush=True)
    by_source={g['source_stl']:g for g in groups}
    maximum=Counter()
    frames=[]
    for row in chosen:
        counts=Counter()
        parts=[]
        for p in row['parts']:
            group=by_source[p['stl']]
            counts[group['id']]+=1
            reference=dict(p)
            reference.update(stl_id=group['id'],stl=group['stl'],source_stl=group['source_stl'],
                             instance_id=f"{group['id']}-copy-{counts[group['id']]:02}",scale=[1,1,1])
            reference.pop('key',None)
            reference.pop('holding_feasibility',None)
            parts.append(reference)
        maximum|=counts
        frames.append(dict(row,parts=parts))
    assert sum(maximum.values())==59
    objects={}
    for group in groups:
        group.update(print_copies=maximum[group['id']],used_frames=[r['frame'] for r in frames if any(p['stl_id']==group['id'] for p in r['parts'])],
                     appearances=sum(sum(p['stl_id']==group['id'] for p in r['parts']) for r in frames))
        for copy in range(1,group['print_copies']+1):
            name=f"{group['id']}-copy-{copy:02}"
            obj=bpy.data.objects.new(name,templates[group['source_stl']].data)
            scene.collection.objects.link(obj)
            obj['stl_id']=group['id']
            obj['stl_path']=group['stl']
            objects[name]=obj
    for obj in list(originals.values())+list(templates.values()):bpy.data.objects.remove(obj,do_unlink=True)
    placement_checks=[]
    for row in frames:
        active={p['instance_id']:p for p in row['parts']}
        for name,obj in objects.items():
            obj.hide_render=name not in active
            obj.hide_viewport=name not in active
            obj.keyframe_insert('hide_render',frame=row['exposure_start'])
            obj.keyframe_insert('hide_viewport',frame=row['exposure_start'])
            if name in active:
                p=active[name]
                obj.location=p['position_mm'];obj.rotation_euler=np.radians(p['rotation_degrees'])
                obj.keyframe_insert('location',frame=row['exposure_start'])
                obj.keyframe_insert('rotation_euler',frame=row['exposure_start'])
        scene.frame_set(row['exposure_start'])
        for p in row['parts']:
            obj=objects[p['instance_id']];a,f=shared.previous.mesh_arrays(obj)
            matrix=np.asarray(obj.matrix_world);world=a@matrix[:3,:3].T+matrix[:3,3]
            volume,com,area,margin=shared.study.support_properties(world,f)
            stable=bool(area>1e-6 and margin>0)
            assert abs(float(world[:,2].min()))<2e-5
            if p['cell_index'] is not None:assert stable
            p.update(contact_area_mm2=area,support_margin_mm=margin if math.isfinite(margin) else None,
                     self_standing=stable,holding_required=not stable,
                     minimum_world_z_mm=float(world[:,2].min()))
            placement_checks.append(dict(pose=row['frame'],instance=p['instance_id'],self_standing=stable))
    for obj in objects.values():
        for curve in obj.animation_data.action.fcurves:
            for key in curve.keyframe_points:key.interpolation='CONSTANT'
    scene.name='Rolling Cube Pen - adopted print-set-v3'
    scene.frame_set(1)
    assert scene.frame_end==74 and shared.study.camera_signature(scene)==camera
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(MODEL),compress=True)
    manifest=dict(status='Adopted 43-STL / 59-prop hybrid; Final QA pending',stl_types=43,physical_objects=59,
                  poses=61,exposures=74,fps=12,duration_seconds=74/12,round_trips=6,units='mm',
                  source_animation=str(shared.study.MODEL.relative_to(ROOT)),source_review=str(REVIEW.relative_to(ROOT)),
                  source_review_sha256=shared.study.digest(REVIEW),fixed_camera=camera,stls=groups,frames=frames,
                  accepted_changes=['Use the adopted hybrid59 placements for poses 56-61.','Pose 57 roll -84 to -90 degrees; pose 60 roll -6 to 0 degrees.',
                                    'Rigid reuse and the inherited one-cylinder plan for poses 1-21; no geometry changes.'],
                  separation_max_surface_difference_mm=.6570087671279907,
                  known_phase1_max_surface_difference_mm=1.899467945098877,protected_sha256=protected)
    rows=[]
    for row in frames:
        for p in row['parts']:
            group=next(g for g in groups if g['id']==p['stl_id'])
            change=p.get('note','Inherited approved print-set-v2 reuse; no new change') if row['frame']>=56 else ('One cylinder reused; pose-specific sole differs from animation v2' if row['phase']==1 else 'No geometric change')
            rows.append(dict(pose=row['frame'],phase=row['phase'],direction=row['direction'],exposure_start=row['exposure_start'],
                             exposures_12fps=row['exposures_12fps'],stl=p['stl'],physical_object_id=p['instance_id'],
                             cell_index_from_cap=p['cell_index'],required_print_copies=group['print_copies'],
                             x_mm=p['position_mm'][0],y_mm=p['position_mm'][1],z_mm=p['position_mm'][2],
                             rotation_x_deg=p['rotation_degrees'][0],rotation_y_deg=p['rotation_degrees'][1],rotation_z_deg=p['rotation_degrees'][2],
                             scale_x=1,scale_y=1,scale_z=1,self_standing=p['self_standing'],holding_required=p['holding_required'],
                             contact_area_mm2=p['contact_area_mm2'],support_margin_mm=p['support_margin_mm'],changes_from_v2=change))
    write_csv(OUT/'frame-to-stl.csv',rows)
    write_csv(OUT/'print-inventory.csv',[dict(stl=g['stl'],print_copies=g['print_copies'],kind=g['kind'],
                              x_mm=g['dimensions_mm'][0],y_mm=g['dimensions_mm'][1],z_mm=g['dimensions_mm'][2],
                              volume_mm3=g['volume_mm3'],used_poses=' '.join(map(str,g['used_frames'])),appearances=g['appearances'],sha256=g['sha256']) for g in groups])
    validation=dict(stl_geometry_passed=True,geometry=geometry,placement_checks=placement_checks,
                    cube_postures_all_self_standing=True,phase1_holding_required_poses=sorted({r['pose'] for r in placement_checks if not r['self_standing']}))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    (OUT/'validation.json').write_text(json.dumps(validation,indent=2,allow_nan=False)+'\n')
    if args.no_render:
        assert all(shared.study.digest(ROOT/p)==h for p,h in protected.items())
        validation.update(previous_assets_unchanged=True,scene_sha256=shared.study.digest(MODEL),generator_sha256=shared.study.digest(Path(__file__)))
        (OUT/'validation.json').write_text(json.dumps(validation,indent=2,allow_nan=False)+'\n')
        print('V3 ASSEMBLED WITHOUT RENDERING: 43 types / 59 objects',flush=True)
        return
    images=[];comparisons=[]
    for row in frames:
        scene.frame_set(row['exposure_start'])
        assert shared.study.camera_signature(scene)==camera
        path=OUT/'frames'/f"frame-{row['frame']:02}.png"
        scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        assert gpu.platform.vendor_get()=='AMD Radeon Pro 5600M' and gpu.platform.backend_type_get()=='METAL'
        ideal=shared.study.OUT/'frames'/path.name
        paired=OUT/'comparison'/path.name
        subprocess.run(['magick',str(ideal),str(path),'+append',str(paired)],check=True)
        images.append(path);comparisons.append(paired)
    shared.previous.assemble_gif(images,frames,OUT/'print-reproduction.gif')
    shared.previous.assemble_gif(comparisons,frames,OUT/'v2-vs-print-set.gif')
    shared.study.montage([(f"{r['frame']:02} / P{r['phase']}",p) for r,p in zip(frames,images)],OUT/'contact-sheet.png',6)
    # Review stills use the same full-resolution framing on both sides.
    for view in ('front','top'):
        tiles=[]
        for frame in range(56,62):
            row=frames[frame-1];scene.frame_set(row['exposure_start'])
            if view=='top':
                scene.camera.location=(0,0,280);scene.camera.rotation_euler=(0,0,math.pi)
                path=OUT/f'top-{frame}.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
                ideal=shared.OUT/'review/images'/f'approved-{frame}-top.png'
            else:
                path=images[frame-1];ideal=shared.study.OUT/'frames'/path.name
            tiles.extend([(f'{frame}: approved v2',ideal),(f'{frame}: adopted print-set-v3',path)])
        command=['magick','montage','-background','#20232a','-fill','white','-font','Helvetica','-pointsize','24']
        for label,path in tiles:command+=['-label',label,str(path)]
        subprocess.run(command+['-geometry','800x500+0+14','-tile','2x',str(OUT/f'poses-56-61-{view}.png')],check=True)
    # The saved animation retains the fixed front camera; detail thumbnails are not animation frames.
    scene.camera.matrix_world=Matrix(camera['matrix_world'])
    for obj in objects.values():obj.animation_data_clear();obj.hide_render=True
    thumbs=[]
    for group in groups:
        obj=objects[group['id']+'-copy-01'];obj.location=(0,0,0);obj.rotation_euler=(0,0,0);obj.hide_render=False
        scene.camera.data.ortho_scale=30 if group['kind']=='cube' else 190
        path=OUT/'selected'/(group['id']+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        thumbs.append((f"{group['id']} / print x{group['print_copies']}",path));obj.hide_render=True
    shared.study.montage(thumbs,OUT/'selected-shapes.png',6)
    assert all(shared.study.digest(ROOT/p)==h for p,h in protected.items())
    validation.update(previous_assets_unchanged=True,scene_sha256=shared.study.digest(MODEL),generator_sha256=shared.study.digest(Path(__file__)))
    (OUT/'validation.json').write_text(json.dumps(validation,indent=2,allow_nan=False)+'\n')
    print('V3 COMPLETE: 43 types / 59 objects / 61 poses / 74 exposures',flush=True)


if __name__=='__main__':
    main()
