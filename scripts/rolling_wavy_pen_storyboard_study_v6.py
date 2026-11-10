"""Slow, full-length rolling and deformation storyboard study v6."""
import argparse,json,math,subprocess,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
from generate import make_mesh
from rolling_wavy_pen import geometry,environment,material,validate
NAMES=("straight","curved","wavy","highly-wavy")
def sm(t):t=max(0,min(1,t));return t*t*(3-2*t)
def center(x,p,sign=1):
    t=(x+70.9)/141.8
    # Use identical whole-length basis functions without a cap or end attenuation mask.
    bow=15.0*4*t*(1-t)
    wave=7.0*math.sin(6*math.pi*t)
    irregular=7.0*math.sin(6*math.pi*t)+2.6*math.sin(10*math.pi*t)
    if p<=.30:return sign*bow*sm(p/.30)
    w=sm((p-.30)/.70)
    if p<.65:return sign*((1-w)*bow+w*wave)
    q=sm((p-.65)/.35)
    return sign*((1-q)*wave+q*irregular)
def mesh(p,sign=1,roll=0):
    return geometry(min(3,round(p*3)),roll,lambda x:center(x,p,sign))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-root',type=Path,default=ROOT);ap.add_argument('--geometry-only',action='store_true');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);root=a.output_root.resolve();ex=root/'exports/rolling-wavy-pen/storyboard-study-v6';pv=root/'previews/rolling-wavy-pen/storyboard-study-v6';ex.mkdir(parents=True,exist_ok=True)
    if not a.geometry_only:pv.mkdir(parents=True,exist_ok=True);(root/'models').mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;black=material('black marker',(.014,.014,.015),.3);neutral=material('neutral',(.5,.53,.57),.65);rep=[];reports=[]
    for i,(n,p) in enumerate(zip(NAMES,(0,.30,.65,1))):
      v,f,xs=mesh(p);o=make_mesh(sc,n,v,f);o['progress']=p;o.data.materials.append(black);o.data.materials.append(neutral);path=ex/f'{n}.stl';bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.wm.stl_export(filepath=str(path),export_selected_objects=True,use_scene_unit=False,global_scale=1,apply_modifiers=True,forward_axis='Y',up_axis='Z');o.select_set(False);r=validate(path,o,i,xs,pose_name=n)
      if not r['passed']:raise RuntimeError(f'{n}: {r}')
      reports.append(r);rep.append(o)
    # Six stepped exposures per round trip make both motion and deformation legible.
    progress=[];directions=[]
    for cycle in range(2):
      for j in range(6):progress.append(0.0);directions.append(-1 if j<3 else 1)
    for j,p in enumerate((.02,.045,.07,.095,.12,.15,.18,.21,.24,.27,.29,.30)):
      progress.append(p);directions.append(-1 if j%6<3 else 1)
    for j,p in enumerate((.32,.35,.38,.41,.44,.47,.50,.53,.56,.59,.62,.65,.68,.71,.74,.77,.80,.83)):
      progress.append(p);directions.append(-1 if j%6<3 else 1)
    if not a.geometry_only:
      environment(sc);sc.cycles.samples=4;sc.render.resolution_x=420;sc.render.resolution_y=284;anim=[];meta=[]
      for i,(p,direction) in enumerate(zip(progress,directions),1):
        roll=direction*18;v,f,_=mesh(p,direction,roll);o=make_mesh(sc,f'anim-{i:02}',v,f);o.location.y=direction*2.5;o.data.materials.append(black);o["progress"]=p;o["direction"]="away" if direction<0 else "toward";anim.append(o);meta.append(dict(frame=i,progress=p,direction=o["direction"],y_mm=o.location.y,roll_degrees=roll,preview_only=True))
      for i,o in enumerate(anim,1):
        for q in rep+anim:q.hide_render=q is not o
        sc.camera=bpy.data.objects['front oblique'];sc.render.filepath=str(pv/f'anim-{i:02}.png');bpy.ops.render.render(write_still=True)
      for o in rep:
        for q in rep+anim:q.hide_render=q is not o
        for mi,cam,suf in ((0,'front oblique','black-front'),(1,'front oblique','neutral-front'),(1,'top','top')):
          for poly in o.data.polygons:poly.material_index=mi
          sc.camera=bpy.data.objects[cam];sc.render.filepath=str(pv/f'{o.name}-{suf}.png');bpy.ops.render.render(write_still=True)
      bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(root/'models/rolling-wavy-pen-storyboard-study-v6.blend'))
      for suf,out in (('black-front','contact-black.png'),('neutral-front','contact-neutral.png'),('top','contact-top.png')):
        cmd=['magick','montage','-background','#191919','-fill','white','-font','Helvetica','-pointsize','18']
        for n in NAMES:cmd+=['-label',n.upper(),str(pv/f'{n}-{suf}.png')]
        subprocess.run(cmd+['-geometry','540x365+8+14','-tile','2x2',str(pv/out)],check=True)
      cmd=['magick'];
      for i in range(1,len(progress)+1):cmd+=['-delay','10',str(pv/f'anim-{i:02}.png')]
      subprocess.run(cmd+['-loop','0',str(pv/'sequence.gif')],check=True)
      subprocess.run(['magick','montage','-background','#191919','-fill','white','-font','Helvetica','-pointsize','12',*[v for i in range(1,len(progress)+1) for v in ('-label',str(i),str(pv/f'anim-{i:02}.png'))],'-geometry','280x190+4+8','-tile','5x8',str(pv/'contact-sequence.png')],check=True)
      subprocess.run(['magick','montage','-background','#191919','-fill','white','-font','Helvetica','-pointsize','16',*[v for n in ('curved','wavy','highly-wavy') for v in ('-label',f'V5 {n}',str(ROOT/f'previews/rolling-wavy-pen/storyboard-study-v5/{n}-black-front.png'),'-label',f'V6 {n}',str(pv/f'{n}-black-front.png'))],'-geometry','420x284+5+10','-tile','2x3',str(pv/'contact-v5-v6.png')],check=True)
    m=dict(status='review pending',capture_frames=len(progress),straight_round_trips=2,curved_round_trips=2,wave_round_trips=3,representatives=reports,animation_frames=meta if not a.geometry_only else progress,unique_print_shapes=4,unverified=['preview intermediate pose printability','minimum wall thickness','slicer behavior','physical printing']);(pv if not a.geometry_only else ex).joinpath('manifest.json').write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
if __name__=='__main__':main()
