"""Shared stone deformation and preview helpers for the final Fireworks generators."""
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
