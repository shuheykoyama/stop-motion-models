"""Focused slow-interpolation preview revision of Rolling Wavy Pen v6."""
import argparse,json,math,subprocess,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
from generate import make_mesh
from rolling_wavy_pen import geometry,environment,material
NAMES=('straight','curved','wavy','highly-wavy')
def sm(x):x=max(0,min(1,x));return x*x*(3-2*x)
def center(x,p,sign=1):
    t=(x+70.9)/141.8;bow=15*4*t*(1-t);fundamental=7*math.sin(6*math.pi*t);irregular=2.6*math.sin(10*math.pi*t)
    # Morph coefficients grow independently so no new lobe appears at full strength in one pose.
    wave=sm((p-.30)/.38);detail=sm((p-.65)/.35)
    return sign*((1-wave)*bow+wave*fundamental+detail*irregular)
def mesh(p,direction,roll):return geometry(min(3,round(p*3)),roll,lambda x:center(x,p,direction))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-root',type=Path,default=ROOT);a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);root=a.output_root.resolve();pv=root/'previews/rolling-wavy-pen/storyboard-study-v7';pv.mkdir(parents=True,exist_ok=True);(root/'models').mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;environment(sc);black=material('black marker',(.014,.014,.015),.3);neutral=material('neutral',(.5,.53,.57),.65);base=Path('previews/rolling-wavy-pen/storyboard-study-v6');rep=[];objs=[]
    for n in NAMES:
      v,f,_=mesh({'straight':0,'curved':.30,'wavy':.65,'highly-wavy':1}[n],1,0);o=make_mesh(sc,n,v,f);o.data.materials.append(black);o.data.materials.append(neutral);rep.append(o)
    progress=[0]*12+[.02,.045,.07,.095,.12,.15,.18,.21,.24,.27,.29,.30]+[.31,.32,.33,.35,.37,.39,.41,.43,.45,.47,.49,.51,.53,.55,.57,.59,.61,.63,.67,.71,.76,.82,.90,1.0]
    directions=[]
    for phase,count in ((0,12),(1,12),(2,24)):
      for j in range(count):directions.append(-1 if (j%8)<4 else 1)
    sc.render.engine='CYCLES';sc.cycles.samples=1;sc.render.resolution_x=320;sc.render.resolution_y=216
    meta=[]
    for i,(p,d) in enumerate(zip(progress,directions),1):
      roll=d*18;v,f,_=mesh(p,d,roll);o=make_mesh(sc,f'frame-{i:02}',v,f);o.location.y=d*2.5;o.data.materials.append(black);objs.append(o);meta.append(dict(frame=i,progress=p,direction='away' if d<0 else 'toward',roll_degrees=roll,scene_y_mm=o.location.y,preview_only=True))
    for i,o in enumerate(objs,1):
      for q in rep+objs:q.hide_render=q is not o
      sc.camera=bpy.data.objects['front oblique'];sc.render.filepath=str(pv/f'anim-{i:02}.png');bpy.ops.render.render(write_still=True)
    for o in rep:
      for q in rep+objs:q.hide_render=q is not o
      for mi,cam,suf in ((0,'front oblique','black-front'),(1,'front oblique','neutral-front'),(1,'top','top')):
        for poly in o.data.polygons:poly.material_index=mi
        sc.camera=bpy.data.objects[cam];sc.render.filepath=str(pv/f'{o.name}-{suf}.png');bpy.ops.render.render(write_still=True)
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(root/'models/rolling-wavy-pen-storyboard-study-v7.blend'))
    for suf,out in (('black-front','contact-black.png'),('neutral-front','contact-neutral.png'),('top','contact-top.png')):
      cmd=['magick','montage','-background','#191919','-fill','white','-font','Helvetica','-pointsize','18']
      for n in NAMES:cmd+=['-label',n.upper(),str(pv/f'{n}-{suf}.png')]
      subprocess.run(cmd+['-geometry','500x338+6+12','-tile','2x2',str(pv/out)],check=True)
    cmd=['magick']
    for i in range(1,49):cmd+=['-delay','10',str(pv/f'anim-{i:02}.png')]
    subprocess.run(cmd+['-loop','0',str(pv/'sequence.gif')],check=True)
    cmd=['magick','montage','-background','#191919','-fill','white','-font','Helvetica','-pointsize','12']
    for i in range(1,49):cmd+=['-label',str(i),str(pv/f'anim-{i:02}.png')]
    subprocess.run(cmd+['-geometry','260x176+4+8','-tile','6x8',str(pv/'contact-sequence.png')],check=True)
    # Compare whole sequence progression against v6 and isolate the cap silhouette.
    subprocess.run(['magick','montage','-background','#191919','-fill','white','-font','Helvetica','-pointsize','15',*[z for n in ('curved','wavy','highly-wavy') for z in ('-label','v6 '+n,str(ROOT/f'previews/rolling-wavy-pen/storyboard-study-v6/{n}-black-front.png'),'-label','v7 '+n,str(pv/f'{n}-black-front.png'))],'-geometry','400x270+5+10','-tile','2x3',str(pv/'contact-v6-v7.png')],check=True)
    m=dict(status='review pending',frames=48,cycles={'straight':2,'single-arc':2,'wave-development':3},progress=meta,printable_representatives_reference='storyboard-study-v6 STLs unchanged; intermediate animation meshes preview-only',unverified=['intermediate pose printability','minimum wall thickness','slicer behavior','physical print']);pv.joinpath('manifest.json').write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
if __name__=='__main__':main()
