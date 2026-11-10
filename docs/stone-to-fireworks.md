# Stone to Fireworks — Initial study v1

Status: awaiting visual review. No production print set is approved.

The storyboard attachment was not present in this request. This interpretation follows the six written phases; the earlier Rolling Wavy Pen storyboard was not used.

## Animation

18 discrete shooting states, 36 exposures at 12 fps (3.0 seconds before GIF rounding). One gentle press/recovery cycle precedes a progressively flattened forward pull. Two quick release states lead directly into the backward launch.

| Frames | Action |
|---|---|
| 01 | Rest, short hold |
| 02–05 | Local press and recovery |
| 06–10 | Increasing forward pull; maximum hold |
| 11–12 | One exposure each: recoil and launch preparation |
| 13–18 | Accelerated backward travel, then distant small-stone hold |

## Geometry and filming

The unchanged Stone-to-Bread frame-01 STL provides the 30 × 25 × 20 mm starting mesh. The new generator reuses its topology and natural asymmetry. Pressure falls off smoothly around local X=0, Y=+3 mm, while a monotone positive-Y displacement draws the near surface forward and keeps the far surface anchored. Recovery uses the same material vertices. All coordinates and STL dimensions are millimeters.

Positive Y is toward the viewer, negative Y is toward the background, and Z=0 is the tabletop. Scene placements are separate from each resting mesh. The fixed perspective camera uses 34 mm focal length at (0,145,205), aimed at (0,-40,0).

The launch is currently a tabletop depth illusion: every stone rests at Z=0. It does not depict a physically airborne arc, and no support jig is generated. Distance perspective and three separately printable miniature meshes (65%, 40%, 25%) create the final shrink. Scene scale is always (1,1,1). There are no fingers, hands, sparks or fireworks in the scene.

14 unique candidate meshes currently cover 18 states. The original stone is reused for frames 01,05,13,14; the smallest stone is reused for 17,18. The three miniature substitutions may be noticeable and require visual review. Final print-count reduction is deferred.

## Candidate geometry

| Mesh | X × Y × Z (mm) | Contact mm² | Support margin mm |
|---|---|---:|---:|
| rest | 30.000 × 25.000 × 20.000 | 113.209 | 4.516 |
| press-light | 30.027 × 25.000 × 18.204 | 115.004 | 4.434 |
| press | 30.059 × 25.000 × 17.156 | 117.198 | 4.317 |
| recover | 30.015 × 25.000 × 18.827 | 114.206 | 4.472 |
| pull-start | 30.024 × 27.995 × 18.095 | 133.668 | 4.789 |
| pull-low | 30.030 × 31.989 × 17.573 | 159.380 | 5.117 |
| pull-mid | 30.035 × 36.985 × 17.085 | 191.610 | 5.100 |
| pull-high | 30.038 × 42.981 × 16.697 | 230.021 | 5.069 |
| pull-max | 30.041 × 49.977 × 16.330 | 274.927 | 5.029 |
| release | 30.015 × 33.451 × 18.380 | 168.404 | 5.071 |
| snap | 30.000 × 22.658 × 21.504 | 103.713 | 4.053 |
| flight-small | 19.500 × 16.250 × 13.000 | 47.831 | 2.935 |
| flight-tiny | 12.000 × 10.000 × 8.000 | 18.113 | 1.806 |
| flight-distant | 7.500 × 6.250 × 5.000 | 7.076 | 1.129 |

All 14 exported candidates passed closed/manifold, single-component, winding, positive volume, dimension, degenerate-face and detected nonadjacent BVH intersection checks. All have a finite contact patch, no tabletop penetration and a positive uniform-density support margin. Render and exported vertex coordinates match. A separate Blender process regenerated all candidate STLs and matched their SHA-256 hashes.

The bread-study absolute support-area and core-sampling thresholds are recorded separately: they were designed for larger bread-sequence props and are not a miniature print specification. This study requires positive measured support area and margin, and records the actual sizes. Global minimum thickness and shared-vertex triangle intersections are not exhaustively checked. Sampled vertical core thickness is not a minimum wall-thickness proof. Slicing, support needs, friction, material strength and physical printing remain unverified.

## Outputs

- [Animation](../previews/stone-to-fireworks/sequence-v1.gif)
- [All shooting states](../previews/stone-to-fireworks/contact-sheet-v1.png)
- [Oblique representative shapes](../previews/stone-to-fireworks/key-poses-v1.png)
- [Top representative shapes](../previews/stone-to-fireworks/key-poses-top-v1.png)
- [Manifest](../previews/stone-to-fireworks/manifest-v1.json)
- [Validation](../previews/stone-to-fireworks/validation-v1.json)
- [Editable scene](../models/stone-to-fireworks.blend)
- [Candidate STLs](../exports/stone-to-fireworks/)

Regenerate only this initial study with Blender 4.5 LTS:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 2 --python-exit-code 1 --python scripts/stone_to_fireworks.py
```

The generator saves the front-camera scene before producing separate top views. In Blender, frames 1–36 play the held 12 fps exposure timeline; the 18 shooting states and their exposure-start frames are in the manifest. The GIF ends on the distant stone; the later origami-fireworks replacement belongs to physical production.

## GPU preview rendering

New previews use EEVEE with 16 render samples on the existing Metal backend. Blender 4.5 Cycles cannot use AMD GPUs on macOS; its device list exposes only the CPU on this Mac. The Radeon Pro 5600M is available to EEVEE. Existing Cycles preview images need regeneration before comparison with EEVEE output. Switching engines is not a guarantee of lower temperatures.

To redraw the saved validated meshes without rebuilding geometry, append `-- --render-only` to the command above. This uses the Radeon Pro 5600M through Metal/EEVEE, checks one visible stone per state and a 2.5% fixed-camera border, and rebuilds the GIF and comparison sheets. The render-only pass preserves the independent STL regeneration evidence.
