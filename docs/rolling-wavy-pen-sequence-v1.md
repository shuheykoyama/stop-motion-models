# Rolling Wavy Pen — Sequence v1

Status: **review pending**. This 8-frame sequence develops the temporarily accepted Straight, Curved, Wavy, and Highly Wavy forms into a print-oriented stop-motion proposal. It is a physical-prop previsualization, not a finished CG animation.

## Pose plan

| Frame | Pose | Shape role | Centerline state | Roll | Filming Y | Printable geometry |
|---|---|---|---:|---:|---:|---|
| 01 | Straight | Initial straight pen | 0.0 | 0° | 0 mm | Straight key |
| 02 | Straight-mid | Slight bend begins | 0.5 | 9° | +1.5 mm | New intermediate |
| 03 | Curved | Broad arc | 1.0 | 18° | +3 mm | Curved key |
| 04 | Curved-wavy-mid | Arc develops into undulations | 1.5 | 2° | +0.5 mm | New intermediate |
| 05 | Wavy | Several smooth waves | 2.0 | −14° | −2 mm | Wavy key |
| 06 | Wavy-strong-mid | Larger, less uniform bends | 2.5 | 5.5° | +1 mm | New intermediate |
| 07 | Highly Wavy | Strong irregular waves | 3.0 | 25° | +4 mm | Highly Wavy key |
| 08 | Highly Wavy hold | Arrival/afterglow | 3.0 | 25° | +4 mm | Reuses frame 07 geometry |

Centerline state is linearly interpolated between the four shared procedural key shapes. The keyed rotation and filming Y values are interpolated over the same state. The held last pose makes 8 animation frames from 7 unique printable shapes; the frame 08 STL is identical to frame 07 and is not an additional print design.

## Measured STL bounds

| Frame | X × Y × Z (mm) |
|---|---:|
| 01 | 141.800 × 13.200 × 12.520 |
| 02 | 141.800 × 20.655 × 12.518 |
| 03 | 141.800 × 28.768 × 12.519 |
| 04 | 141.800 × 27.456 × 12.517 |
| 05 | 141.800 × 27.402 × 12.892 |
| 06 | 141.800 × 29.531 × 12.517 |
| 07 | 141.800 × 31.699 × 12.518 |
| 08 | 141.800 × 31.699 × 12.518 |

## Outputs

- Generator: `scripts/rolling_wavy_pen_sequence.py`
- Editable scene: `models/rolling-wavy-pen-sequence-v1.blend`
- Frame STLs: `exports/rolling-wavy-pen/sequence-v1/frame-01.stl` through `frame-08.stl`
- Manifest and geometry checks: `previews/rolling-wavy-pen/sequence-v1/manifest.json`
- Black front-oblique sheet: `previews/rolling-wavy-pen/sequence-v1/contact-black.png`
- Neutral front-oblique sheet: `previews/rolling-wavy-pen/sequence-v1/contact-neutral.png`
- Top sheet: `previews/rolling-wavy-pen/sequence-v1/contact-top.png`
- GIF: `previews/rolling-wavy-pen/sequence-v1/sequence.gif`

STLs are separate files for each animation frame, including the repeated final hold for convenience. Frames 01, 03, 05, and 07 use the previously established representative states. Frames 02, 04, and 06 are new mesh states. Comparing hashes in the manifest shows which files share geometry. The neutral and black previews render the same meshes; only the material differs.

All shapes use a nominal 11.9 mm shaft diameter and 141.8 mm straight length. Frames are generated as solid, closed meshes with shallow tabletop soles. Contact, support margin, topology, winding, degenerate triangles, and detected non-adjacent triangle overlap are checked. Minimum feature thickness has not been exhaustively measured; slicer behavior and physical printing remain unverified. No slicer or printer was operated.

The black, neutral, and top contact sheets use fixed framing and object placement. The GIF uses discrete renders only, with a 12 fps exposure reference and a longer hold for frame 08. No interpolated render-only poses are added.
