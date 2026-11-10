# Stone to Fireworks v2

Initial v2, awaiting visual review. v1 and all earlier motifs are preserved.
The storyboard image was not attached to this request; the written phase directions are the reference.

## Motion and timing

20 discrete shooting states, two exposures per state at 12 fps: 40 exposures, 3.333 seconds.
The GIF uses cumulative centisecond rounding (3.33 seconds).

| Shooting states | Action |
|---|---|
| 01 | Original stone |
| 02–03 | Press 1 / full recovery |
| 04–05 | Press 2 / full recovery |
| 06–07 | Press 3 / full recovery |
| 08–12 | Progressive forward pull, using the v1 pull geometry |
| 13–14 | Recoil overlaps backward travel and lift |
| 15–20 | Fast airborne retreat, perspective shrink and physical miniatures |

The three press strengths are 85%, 100%, and 95%. A narrower smooth contact envelope depresses the top locally; a small annular rise expresses material displaced around the fingertip. The planar resting base is preserved. There is no finger geometry.

At state 13 the pull is still 42% extended while the stone has already moved to Y=-14 mm and Z=+2 mm. State 14 retains 8% stretch, compresses in depth and moves to Y=-40 mm, Z=+10 mm. Recovery never pauses at the original location.

The flight then moves through Y=-82,-130,-180,-230,-280,-315 mm and Z=24,38,48,54,52,44 mm. This is a discrete launch/rise/fall path, not a physical simulation. It is stronger than the previous tabletop-slide illusion. All scene scales remain (1,1,1). The distant stones are separately modeled at 65%, 40%, and 25% size, with the 25% stone reused for the final two shots. No CGI-only mesh interpolation is used.

## Models and production

The 30 × 25 × 20 mm v1 rest mesh is the common source. All material vertices retain their correspondence. Fourteen unique candidate solids cover the 20 shooting states; this is not a finalized production print set. Rest is reused during the three recoveries and early flight. Mesh generation and STL export use the same geometry as rendering.

The STLs are in resting local coordinates, in millimeters. Scene X/Y/Z placement is recorded separately in the manifest. Positive Y is toward the viewer; negative Y is toward the background. States 13–20 are above the table and require a practical support/removal or compositing technique. No support fixture is generated. Static support checks describe each STL's local resting orientation, not unsupported aerial stability.

## Validation

The generator checks the reread STL for closed/manifold geometry, a single connected solid, winding, positive volume, degenerate faces, detected nonadjacent BVH intersections, dimensions, local tabletop contact and uniform-density center-of-mass support. It independently regenerates the candidates in a second Blender process and compares their STL SHA-256 hashes. Exported vertex coordinates are compared against the render meshes.

Global minimum normal thickness and intersections involving shared vertices are not exhaustively checked. The old bread-study's absolute contact-area and sampling thresholds are recorded separately because they are not a specification for small physical miniatures. Slicing, supports, strength, material choice, physical printing and filming remain unverified.

## Outputs

- [Sequence GIF](../previews/stone-to-fireworks/v2/sequence-v2.gif)
- [All 20 shooting states](../previews/stone-to-fireworks/v2/contact-sheet-v2.png)
- [Representative oblique shapes](../previews/stone-to-fireworks/v2/key-poses-v2.png)
- [Representative top shapes](../previews/stone-to-fireworks/v2/key-poses-top-v2.png)
- [Manifest](../previews/stone-to-fireworks/v2/manifest-v2.json)
- [Validation](../previews/stone-to-fireworks/v2/validation-v2.json)
- [Candidate STLs](../exports/stone-to-fireworks/v2/)
- [Editable Blender scene](../models/stone-to-fireworks-v2.blend)
- [Generator](../scripts/stone_to_fireworks_v2.py)

The saved Blender timeline contains the same 40 held exposures as the GIF. The camera is fixed globally and fitted before rendering; there is no pose-specific recentering in the animation. Top comparisons temporarily remove filming translation to compare the shapes at a common datum.

Reproduction uses Blender 4.5 LTS, ImageMagick, and the existing v1 source assets:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 2 --python-exit-code 1 --python scripts/stone_to_fireworks_v2.py
```

Preview rendering uses EEVEE / Metal on the AMD Radeon Pro 5600M at 16 samples. CPU-side work is limited to two threads for these background processes. No hands, fingers, sparks or fireworks are modeled. The last small-stone hold is the intended cut point for physical origami fireworks.
