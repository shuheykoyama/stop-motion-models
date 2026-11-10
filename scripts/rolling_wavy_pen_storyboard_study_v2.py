"""Generate the full-body deformation revision of the storyboard pen study."""
import argparse, hashlib, json, math, subprocess, sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
from generate import make_mesh
from rolling_wavy_pen import geometry, environment, material, validate
NAMES=("straight","curved","wavy","highly-wavy")
ROLLS=(0.0,16.0,22.0,26.0)
def curve(x,stage,sign=1):
    t=(x+70.9)/141.8; env=math.sin(math.pi*t)
    if stage==0: return 0.0
    if stage==1: return sign*6.5*4*t*(1-t)
    if stage==2: return sign*4.5*env*math.sin(4*math.pi*t)
    return sign*env*(7.5*math.sin(3.3*math.pi*t)+2.5*math.sin(6.1*math.pi*t+0.55))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output-root",type=Path,default=ROOT); ap.add_argument("--geometry-only",action="store_true")
    a=ap.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []); root=a.output_root.resolve()
    ex=root/"exports/rolling-wavy-pen/storyboard-study-v2"; pv=root/"previews/rolling-wavy-pen/storyboard-study-v2"; ex.mkdir(parents=True,exist_ok=True)
    if not a.geometry_only: pv.mkdir(parents=True,exist_ok=True); (root/"models").mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene; black=material("black marker",(.014,.014,.015),.3); neutral=material("neutral",(.51,.54,.58),.66); objs=[]; reports=[]
    # Every section, including cap, seam, barrel and tip, uses the same centerline.
    for i,name in enumerate(NAMES):
      for side,sgn,roll in (("main",1,ROLLS[i]),("opposite",-1,ROLLS[i]+180)):
        vs,fs,xs=geometry(i,roll,lambda x,i=i,sgn=sgn:curve(x,i,sgn)); ob=make_mesh(sc,f"{name}-{side}",vs,fs); ob["storyboard_pose"]=True; ob["stage"]=name; ob["roll_degrees"]=roll; ob.data.materials.append(black); ob.data.materials.append(neutral)
        path=ex/f"{name}-{side}.stl"; bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active=ob; bpy.ops.wm.stl_export(filepath=str(path),export_selected_objects=True,use_scene_unit=False,global_scale=1,apply_modifiers=True,forward_axis="Y",up_axis="Z"); ob.select_set(False)
        r=validate(path,ob,i,xs,pose_name=f"{name}-{side}"); r.update(stage=name,side=side,roll_degrees=roll,centerline_length_mm=141.8)
        if not r["passed"]: raise RuntimeError(f"{name}-{side}: {r}")
        reports.append(r); objs.append(ob); print("VALID",name,side,r["dimensions_mm"],flush=True)
    if not a.geometry_only:
      environment(sc); sc.cycles.samples=12; sc.render.resolution_x=720; sc.render.resolution_y=486
      for i,name in enumerate(NAMES):
        for side in ("main","opposite"):
          ob=next(o for o in objs if o.name==f"{name}-{side}")
          for x in objs: x.hide_render=x is not ob
          for style,idx,cam,suf in (("black",0,"front oblique","black-front"),("neutral",1,"front oblique","neutral-front"),("neutral",1,"top","top")):
            for p in ob.data.polygons:p.material_index=idx
            sc.camera=bpy.data.objects[cam]; sc.render.filepath=str(pv/f"{name}-{side}-{suf}.png"); bpy.ops.render.render(write_still=True)
      sc["motif"]="Rolling Wavy Pen storyboard study v2; review pending"; bpy.context.preferences.filepaths.save_version=0; bpy.ops.wm.save_as_mainfile(filepath=str(root/"models/rolling-wavy-pen-storyboard-study-v2.blend"))
      for view,suf in (("black-front","contact-front-black.png"),("neutral-front","contact-front-neutral.png"),("top","contact-top.png")):
        files=[pv/f"{n}-main-{view}.png" for n in NAMES]; cmd=["magick","montage","-background","#191919","-fill","white","-font","Helvetica","-pointsize","20"]
        for n,f in zip(NAMES,files):cmd +=["-label",n.upper(),str(f)]
        subprocess.run(cmd+["-geometry","600x405+8+16","-tile","2x2",str(pv/suf)],check=True)
      cmd=["magick","montage","-background","#191919","-fill","white","-font","Helvetica","-pointsize","18"]
      for n in NAMES:
        for s in ("main","opposite"):cmd +=["-label",n.upper()+" "+s.upper(),str(pv/f"{n}-{s}-black-front.png")]
      subprocess.run(cmd+["-geometry","540x365+8+14","-tile","2x4",str(pv/"contact-roll.png")],check=True)
      for out,files in (("four-stages.gif",[pv/f"{n}-main-black-front.png" for n in NAMES]),("rolling-views.gif",[pv/f"{n}-{s}-black-front.png" for n in NAMES for s in ("main","opposite")])):
        cmd=["magick"]
        for f in files:cmd +=["-delay","40",str(f)]
        subprocess.run(cmd+["-loop","0",str(pv/out)],check=True)
    m={"status":"review pending","blender":bpy.app.version_string,"stages":NAMES,"reports":reports,"unverified":["exhaustive minimum wall thickness","slicer/support verification","physical printing"]}; (ex if a.geometry_only else pv).joinpath("validation.json").write_text(json.dumps(m,indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__":main()
