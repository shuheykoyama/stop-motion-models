# Stone to Fireworks - Tabletop print-set-v1

Approved tabletop print-data set: 14 models, 20 shooting poses, 40 exposures. Final QA is PASS; slicing and physical printing remain unverified. Use this set for the official handoff. Original generation metadata retains its earlier review-pending status as historical evidence.

## Reproduction

20 shooting states, two exposures each at 12 fps: 40 exposures, 3.333 seconds (3.33 seconds in GIF). Three presses, pulling and recoil retain the v3 timing. The only placement change is setting Z=0 for states 13-20. Y travel, geometry, miniature sizes, rotations, camera, lighting and holds are unchanged.

All 14 files are byte-identical copies of the corresponding approved v3 STLs. The render meshes are read from these STLs; canonical triangle-coordinate hashes also match the original v3 scene meshes. No model is interpolated, simplified or scaled in the scene. Rest is reused six times and the smallest miniature twice. The three press strengths are close but remain separate to preserve the approved shapes exactly.

## Approved print models

| STL | v3 pose | First source frame | X x Y x Z (mm) | Uses |
|---|---|---:|---|---:|
| pose-01.stl | rest | 1 | 30.000 x 25.000 x 20.000 | 6 |
| pose-02.stl | press-a | 2 | 30.004 x 25.000 x 18.233 | 1 |
| pose-03.stl | press-b | 4 | 30.005 x 25.000 x 18.110 | 1 |
| pose-04.stl | press-c | 6 | 30.004 x 25.000 x 18.150 | 1 |
| pose-05.stl | pull-start | 8 | 30.022 x 27.989 x 18.127 | 1 |
| pose-06.stl | pull-low | 9 | 30.028 x 31.979 x 17.603 | 1 |
| pose-07.stl | pull-mid | 10 | 30.033 x 36.973 x 17.118 | 1 |
| pose-08.stl | pull-high | 11 | 30.036 x 42.965 x 16.756 | 1 |
| pose-09.stl | pull-max | 12 | 30.039 x 49.960 x 16.441 | 1 |
| pose-10.stl | release | 13 | 30.014 x 33.772 x 18.552 | 1 |
| pose-11.stl | snap | 14 | 30.000 x 23.753 x 21.355 | 1 |
| pose-12.stl | small | 17 | 19.500 x 16.250 x 13.000 | 1 |
| pose-13.stl | tiny | 18 | 12.000 x 10.000 x 8.000 | 1 |
| pose-14.stl | distant | 19 | 7.500 x 6.250 x 5.000 | 2 |

## Filming guide

Use [frame-to-stl.csv](../previews/stone-to-fireworks/print-set-v1/frame-to-stl.csv) for all 20 shots. The initial stone datum is X=0,Y=0. X is horizontal, positive Y is toward the viewer, negative Y is away, and positive Z is up. All rotations are zero; all scene scales are one. Do not independently recenter models after importing. STL has no unit metadata: import as millimeters.

Recoil and retreat positions are Y=-14,-40,-82,-130,-180,-230,-280,-315 mm, always at Z=0. Recoil starts moving before full recovery; there is no pause at the original position. States 17,18,19 replace the stone with physical 65%,40%,25% miniatures. States 19-20 reuse the 25% model. The final small stone is the intended cut point to physical origami fireworks. No hands, sparks, aerial support or fixtures are modeled.

The fixed perspective camera is inherited unchanged from v3: location (0,160,245) mm, target (0,-65,15) mm, focal length about 27.436 mm. Match the physical sensor/field of view and use CSV positions as initial guides. Allow approximately 315 mm of rearward travel on the table. Resting orientation for filming is separate from optimal printing orientation.

The approved tabletop version removes visible lift and separated shadows. It can therefore read more like sliding than aerial v3. Retreat speed and smaller physical models convey distance.

## Validation and remaining checks

All saved STLs were reread and checked for dimensions, finite coordinates, closed/manifold geometry, a single connected solid, winding/normals, positive volume, degenerate faces and detected nonadjacent BVH intersections. Finite local contact and uniform-density center-of-mass support were verified. The rendered world minimum Z is zero in every shooting state.

The smallest stone is 7.5 x 6.25 x 5 mm, with contact area about 7.202 mm2 and support margin about 1.153 mm. Its sampled vertical core thickness is at least about 3.956 mm at the sampled locations. This is not an exhaustive minimum wall-thickness proof. Its shallow surface relief may not resolve in FDM; no reliable nozzle/profile is specified. Shared-vertex face intersections are excluded from the BVH test. Slicing, optimal print orientation, printing supports, print time, actual strength, physical printing and filming remain unverified. Printed infill can change the center of mass.

## Outputs

- [Tabletop reproduction GIF](../previews/stone-to-fireworks/print-set-v1/print-reproduction.gif)
- [Approved v3 vs tabletop GIF](../previews/stone-to-fireworks/print-set-v1/v3-vs-tabletop.gif)
- [All 20 shooting states](../previews/stone-to-fireworks/print-set-v1/contact-sheet.png)
- [All selected shapes](../previews/stone-to-fireworks/print-set-v1/selected-shapes.png)
- [STLs](../exports/stone-to-fireworks/print-set-v1/)
- [Manifest](../previews/stone-to-fireworks/print-set-v1/manifest.json)
- [Validation](../previews/stone-to-fireworks/print-set-v1/validation.json)
- [Editable scene](../models/stone-to-fireworks-print-set-v1.blend)
- [Reproduction script](../scripts/stone_to_fireworks_print_set_v1.py)

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 2 --python-exit-code 1 --python scripts/stone_to_fireworks_print_set_v1.py
```

Run reproduction commands in an isolated checkout or copy to preserve the approved output files. The script reads existing v3 sources and writes the print-set output. It checks the STLs and places them rather than regenerating geometry. Blender 4.5 LTS and ImageMagick are required. EEVEE uses the Radeon Pro 5600M via Metal, at 16 samples. The saved scene plays the same 40 held exposure frames as the GIF.

The unchanged v3 generator also reads the original v1 scene/rest STL/validation and checks the existence of the v2 scene, script and documentation. Those frozen dependencies are versioned alongside the official scenes. Earlier auxiliary renders and provisional STL sets remain local; they are not official print targets. Approval wording in this guide was updated after Final QA; the QA record retains the document hash from its original inspection time.
