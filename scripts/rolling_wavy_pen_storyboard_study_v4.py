"""Storyboard v4: globally smooth pen deformation coordinated with rolling poses."""
import argparse, json, math, subprocess, sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
from generate import make_mesh
from rolling_wavy_pen import geometry,environment,material,validate
NAMES=("straight","curved","wavy","highly-wavy")
def smooth(t): return t*t*(3-2*t)
def line(x,p,sign=1):
    t=(x+70.9)/141.8; e=math.sin(math.pi*t)
    # A smooth blend grows one broad bow first, then develops broad wave cycles.
    bow=13.0*4*t*(1-t)
    wave=e*(8.0*math.sin(4*math.pi*t)+p*2.0*math.sin(7*math.pi*t+.4))
    activation=smooth(max(0,min(1,(p-.28)/.72)))
    y=(1-activation)*bow*p/0.28 + activation*wave
    return sign*y
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output-root",type=Path,default=ROOT);ap.add_argument("--geometry-only",action="store_true");a=ap.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []);root=a.output_root.resolve();ex=root/"exports/rolling-wavy-pen/storyboard-study-v4";pv=root/"previews/rolling-wavy-pen/storyboard-study-v4";ex.mkdir(parents=True,exist_ok=True)
    if not a.geometry_only:pv.mkdir(parents=True,exist_ok=True);(root/"models").mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;black=material("black marker",(.014,.014,.015),.3);neutral=material("neutral",(.5,.53,.57),.65);reports=[];reps=[]
    # Four print candidates map to progression milestones; each section samples the same global centerline.
    for i,(name,p) in enumerate(zip(NAMES,(0,.28,.62,1))):
        vs,fs,xs=geometry(i,0,lambda x,p=p:line(x,p));o=make_mesh(sc,name,vs,fs);o["storyboard_pose"]=True;o["progress"]=p;o.data.materials.append(black);o.data.materials.append(neutral);path=ex/f"{name}.stl";bpy.ops.object.select_all(action="DESELECT");o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.wm.stl_export(filepath=str(path),export_selected_objects=True,use_scene_unit=False,global_scale=1,apply_modifiers=True,forward_axis="Y",up_axis="Z");o.select_set(False);r=validate(path,o,i,xs,pose_name=name);r["centerline_length_target_mm"]=141.8
        if not r["passed"]:raise RuntimeError(f"{name}: {r}")
        reports.append(r);reps.append(o)
    if not a.geometry_only:
        environment(sc);sc.cycles.samples=6;sc.render.resolution_x=480;sc.render.resolution_y=324
        # Ten alternating roll gestures produce a compact 20-pose preview.
        timeline=[]
        progresses=[0,0,0,0,.04,.10,.18,.28,.34,.42,.50,.58,.66,.74,.82,.90,.96,1,1,1]
        for frame,p in enumerate(progresses,1):
            direction=-1 if frame%2 else 1; travel=direction*3.0; roll=direction*22.0
            # Build the discrete preview mesh from the same source geometry function.
            vs,fs,xs=geometry(min(3,round(p*3)),roll,lambda x,p=p,s=direction:line(x,p,s));o=make_mesh(sc,f"anim-{frame:02}",vs,fs);o.location.y=travel;o.data.materials.append(black);o["animation_preview_only"]=True;o["progress"]=p;o["travel_y_mm"]=travel;o["roll_degrees"]=roll;timeline.append(o)
        for j,(p,o) in enumerate(zip(progresses,timeline),1):
            for q in reps+timeline:q.hide_render=q is not o
            sc.camera=bpy.data.objects["front oblique"];sc.render.filepath=str(pv/f"anim-{j:02}.png");bpy.ops.render.render(write_still=True)
        for i,o in enumerate(reps):
            for q in reps+timeline:q.hide_render=q is not o
            for mi,cam,suf in ((0,"front oblique","black-front"),(1,"front oblique","neutral-front"),(1,"top","top")):
                for poly in o.data.polygons:poly.material_index=mi
                sc.camera=bpy.data.objects[cam];sc.render.filepath=str(pv/f"{NAMES[i]}-{suf}.png");bpy.ops.render.render(write_still=True)
        sc["motif"]="Rolling Wavy Pen storyboard v4; animation preview pending review";bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(root/"models/rolling-wavy-pen-storyboard-study-v4.blend"))
        for suffix,out in (("black-front","contact-front-black.png"),("neutral-front","contact-front-neutral.png"),("top","contact-top.png")):
            cmd=["magick","montage","-background","#191919","-fill","white","-font","Helvetica","-pointsize","18"]
            for n in NAMES:cmd +=["-label",n.upper(),str(pv/f"{n}-{suffix}.png")]
            subprocess.run(cmd+["-geometry","560x378+8+14","-tile","2x2",str(pv/out)],check=True)
        for out,files in (("sequence.gif",[pv/f"anim-{i:02}.png" for i in range(1,21)]),("shape-progression.gif",[pv/f"anim-{i:02}.png" for i in (1,5,9,13,17,20)])):
            cmd=["magick"]
            for f in files:cmd +=["-delay","9",str(f)]
            subprocess.run(cmd+["-loop","0",str(pv/out)],check=True)
        subprocess.run(["magick","montage","-background","#191919","-fill","white","-font","Helvetica","-pointsize","16",*[z for i in range(1,21) for z in ("-label",f"{i:02}",str(pv/f"anim-{i:02}.png"))],"-geometry","360x243+6+12","-tile","4x5",str(pv/"contact-sequence.png")],check=True)
    m={"status":"review pending","blender":bpy.app.version_string,"printable_representative_shapes":reports,"animation_exposures":[{"frame":i,"progress":p,"direction":"toward" if i%2==0 else "away","y_mm":3 if i%2 else -3,"roll_degrees":22 if i%2==0 else -22,"intermediate_stl":False} for i,p in enumerate([0,0,0,0,.04,.10,.18,.28,.34,.42,.50,.58,.66,.74,.82,.90,.96,1,1,1],1)],"proposed_capture_count":20,"proposed_unique_print_shapes":4,"unverified":["per-frame tabletop stability for preview-only interpolated meshes","minimum wall thickness","slicer behavior","physical print"]};(ex if a.geometry_only else pv).joinpath("manifest.json").write_text(json.dumps(m,indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__":main()
