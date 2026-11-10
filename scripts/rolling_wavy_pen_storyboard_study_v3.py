"""Full-body cap-to-tip deformation study v3 for the Rolling Wavy Pen."""
import argparse,json,math,subprocess,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
from generate import make_mesh
from rolling_wavy_pen import geometry,environment,material,validate
NAMES=("straight","curved","wavy","highly-wavy")
def curve(x,stage):
    t=(x+70.9)/141.8; e=math.sin(math.pi*t)
    if stage==0:return 0.0
    if stage==1:return 15.0*4*t*(1-t)
    if stage==2:return 8.0*e*math.sin(4*math.pi*t)
    return e*(13.0*math.sin(3.3*math.pi*t)+4.0*math.sin(6.1*math.pi*t+.55))
def main():
    p=argparse.ArgumentParser();p.add_argument("--output-root",type=Path,default=ROOT);p.add_argument("--geometry-only",action="store_true");a=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []);root=a.output_root.resolve();ex=root/"exports/rolling-wavy-pen/storyboard-study-v3";pv=root/"previews/rolling-wavy-pen/storyboard-study-v3";ex.mkdir(parents=True,exist_ok=True)
    if not a.geometry_only:pv.mkdir(parents=True,exist_ok=True);(root/"models").mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene; black=material("matte black marker",(.014,.014,.015),.3);neutral=material("neutral shape review",(.5,.53,.57),.65);objs=[];reports=[]
    for i,n in enumerate(NAMES):
        vs,fs,xs=geometry(i,0,lambda x,i=i:curve(x,i));ob=make_mesh(sc,n,vs,fs);ob["storyboard_pose"]=True;ob["stage"]=n;ob.data.materials.append(black);ob.data.materials.append(neutral);path=ex/f"{n}.stl";bpy.ops.object.select_all(action="DESELECT");ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.wm.stl_export(filepath=str(path),export_selected_objects=True,use_scene_unit=False,global_scale=1,apply_modifiers=True,forward_axis="Y",up_axis="Z");ob.select_set(False);r=validate(path,ob,i,xs,pose_name=n);r.update(centerline_length_mm=141.8,full_length_deformation=True)
        if not r["passed"]:raise RuntimeError(f"{n}: {r}")
        reports.append(r);objs.append(ob);print("VALID",n,r["dimensions_mm"],flush=True)
    if not a.geometry_only:
        environment(sc);sc.cycles.samples=8;sc.render.resolution_x=640;sc.render.resolution_y=432
        for i,(n,o) in enumerate(zip(NAMES,objs)):
            for q in objs:q.hide_render=q is not o
            for style,mi,cam,suf in (("black",0,"front oblique","black-front"),("neutral",1,"front oblique","neutral-front"),("neutral",1,"top","top")):
                for poly in o.data.polygons:poly.material_index=mi
                sc.camera=bpy.data.objects[cam];sc.render.filepath=str(pv/f"{n}-{suf}.png");bpy.ops.render.render(write_still=True)
        sc["motif"]="Rolling Wavy Pen storyboard study v3, full body deformation";bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(root/"models/rolling-wavy-pen-storyboard-study-v3.blend"))
        for suf,out in (("black-front","contact-front-black.png"),("neutral-front","contact-front-neutral.png"),("top","contact-top.png")):
            cmd=["magick","montage","-background","#191919","-fill","white","-font","Helvetica","-pointsize","20"]
            for n in NAMES:cmd +=["-label",n.upper(),str(pv/f"{n}-{suf}.png")]
            subprocess.run(cmd+["-geometry","600x405+8+16","-tile","2x2",str(pv/out)],check=True)
        subprocess.run(["magick",*[arg for n in NAMES for arg in ("-delay","45",str(pv/f"{n}-black-front.png"))],"-loop","0",str(pv/"four-stages.gif")],check=True)
    (ex if a.geometry_only else pv).joinpath("validation.json").write_text(json.dumps({"status":"review pending","blender":bpy.app.version_string,"reports":reports,"unverified":["minimum wall thickness","slicer behavior","physical print"]},indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__":main()
