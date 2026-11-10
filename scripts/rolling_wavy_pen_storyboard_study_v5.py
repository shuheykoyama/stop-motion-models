"""Slow storyboard animation revision with centerline-following pen sections."""
import argparse,json,math,subprocess,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
from generate import make_mesh
from rolling_wavy_pen import environment,material,validate,geometry
NAMES=("straight","curved","wavy","highly-wavy")
def sstep(t):t=max(0,min(1,t));return t*t*(3-2*t)
def center(x,p,sign=1):
    t=(x+70.9)/141.8;e=math.sin(math.pi*t); bow=15*4*t*(1-t); w=sstep((p-.34)/.66)
    # Grow a single arc first; then blend it down as broad wave lobes grow in.
    a=sstep(p/.34);wave=e*(7*math.sin(3.4*math.pi*t)+p*2.8*math.sin(6.2*math.pi*t+.35))
    return sign*((1-w)*a*bow+w*wave)
def mesh(p,sign=1,roll=0):
    # Reuse the validated v4 section rings, soles, and end caps; only supply the
    # new full-length centerline. This avoids a second, divergent mesh topology.
    return geometry(min(3,round(p*3)),roll,lambda x:center(x,p,sign))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-root',type=Path,default=ROOT);ap.add_argument('--geometry-only',action='store_true');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);root=a.output_root.resolve();ex=root/'exports/rolling-wavy-pen/storyboard-study-v5';pv=root/'previews/rolling-wavy-pen/storyboard-study-v5';ex.mkdir(parents=True,exist_ok=True)
    if not a.geometry_only:pv.mkdir(parents=True,exist_ok=True);(root/'models').mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;black=material('matte black',(.014,.014,.015),.3);neutral=material('neutral',(.5,.53,.57),.65);rep=[];reports=[]
    for i,(name,p) in enumerate(zip(NAMES,(0,.34,.67,1))):
      v,f,xs=mesh(p);o=make_mesh(sc,name,v,f);o['progress']=p;o.data.materials.append(black);o.data.materials.append(neutral);path=ex/f'{name}.stl';bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.wm.stl_export(filepath=str(path),export_selected_objects=True,use_scene_unit=False,global_scale=1,apply_modifiers=True,forward_axis='Y',up_axis='Z');o.select_set(False);r=validate(path,o,i,xs,pose_name=name)
      if not r['passed']:raise RuntimeError(f'{name}: {r}')
      reports.append(r);rep.append(o)
    exposures=[]
    # 28 discrete exposures: two straight cycles, two arc-building cycles, then three wave-building cycles.
    for pseq in ([0]*8+[.02,.04,.08,.13,.19,.25,.31,.34]+[.38,.43,.48,.54,.60,.66,.72,.78,.84,.90,.96,1]):
      exposures.append(pseq)
    if not a.geometry_only:
      enviroment=None
      environment(sc);sc.cycles.samples=4;sc.render.resolution_x=420;sc.render.resolution_y=284;anim=[]
      for i,p in enumerate(exposures,1):
        direction=-1 if i%2 else 1;v,f,_=mesh(p,direction,direction*18);o=make_mesh(sc,f'anim-{i:02}',v,f);o.data.materials.append(black);o.location.y=direction*2.5;anim.append(o)
      for i,o in enumerate(anim,1):
        for q in rep+anim:q.hide_render=q is not o
        sc.camera=bpy.data.objects['front oblique'];sc.render.filepath=str(pv/f'anim-{i:02}.png');bpy.ops.render.render(write_still=True)
      for i,o in enumerate(rep):
        for q in rep+anim:q.hide_render=q is not o
        for mi,cam,suf in ((0,'front oblique','black-front'),(1,'front oblique','neutral-front'),(1,'top','top')):
          for poly in o.data.polygons:poly.material_index=mi
          sc.camera=bpy.data.objects[cam];sc.render.filepath=str(pv/f'{NAMES[i]}-{suf}.png');bpy.ops.render.render(write_still=True)
      bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(root/'models/rolling-wavy-pen-storyboard-study-v5.blend'))
      for suf,out in (('black-front','contact-black.png'),('neutral-front','contact-neutral.png'),('top','contact-top.png')):
        cmd=['magick','montage','-background','#191919','-fill','white','-font','Helvetica','-pointsize','18'];
        for n in NAMES:cmd+=['-label',n.upper(),str(pv/f'{n}-{suf}.png')]
        subprocess.run(cmd+['-geometry','540x365+8+14','-tile','2x2',str(pv/out)],check=True)
      cmd=['magick'];
      for i in range(1,len(anim)+1):cmd+=['-delay','10',str(pv/f'anim-{i:02}.png')]
      subprocess.run(cmd+['-loop','0',str(pv/'sequence.gif')],check=True)
      subprocess.run(['magick','montage','-background','#191919','-fill','white','-font','Helvetica','-pointsize','13',*[v for i in range(1,len(anim)+1) for v in ('-label',str(i),str(pv/f'anim-{i:02}.png'))],'-geometry','300x203+5+10','-tile','4x7',str(pv/'contact-sequence.png')],check=True)
    (ex if a.geometry_only else pv).joinpath('manifest.json').write_text(json.dumps({'status':'review pending','capture_frames':len(exposures),'printable_representatives':reports,'progress':exposures,'unique_print_shapes':4,'unverified':['intermediate-pose stability','minimum thickness','slicer and physical print']},indent=2)+'\n')
if __name__=='__main__':main()
