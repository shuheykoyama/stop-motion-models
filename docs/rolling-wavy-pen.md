# Rolling Wavy Pen

Status: **approved** — `storyboard-study-v11` for the animation and `print-set-v2` for the 16 printable poses. This motif is separate from the approved compressed Pen.

## Current approved version

The animation shows the same pen rolling back and forth as it changes from a straight marker to a single arc, then develops multiple waves and stronger irregular waves. The approved sequence has 30 exposures at 12 fps (4.8 seconds). The 16 print-set-v2 models reproduce those 30 exposures using the checked placements in `previews/rolling-wavy-pen/print-set-v2/frame-to-stl.csv`.

- Animation: `previews/rolling-wavy-pen/storyboard-study-v11/sequence.gif`
- Editable animation scene: `models/rolling-wavy-pen-storyboard-study-v11.blend`
- Official printable STLs: `exports/rolling-wavy-pen/print-set-v2/pose-01.stl` through `pose-16.stl`
- Editable print-set scene: `models/rolling-wavy-pen-print-set-v2.blend`
- QA: **PASS** — see `docs/rolling-wavy-pen-final-qa.md` and `previews/rolling-wavy-pen/print-set-v2/final-qa.json`.

Import STL coordinates as **millimeters** because STL does not store units. CAM/slicer checks, support planning, print-time estimates, physical printing, and filming have not been completed.

The four-shape prototype documented below is historical and is not the approved print target. `storyboard-study-v1`–`v10` and `print-set-v1` remain development history; do not use their STLs for production.

## Historical four-shape prototype

The four printable forms are Straight, Curved, Wavy, and Highly Wavy. Their centerlines progress from straight to one broad arc, then three unequal lobes, then larger unequal lobes. The same closed mesh is exported to STL and rendered in both material styles. Filming Y placement is separate from printable coordinates.

The proportions follow Zebra's [Mackee Gokuhoso specifications](https://www.zebra.co.jp/pro/detail/mackee_gokuhoso/): 141.8 mm overall length and 11.9 mm shaft diameter. The cap radius is 6.6 mm and the barrel radius is 5.95 mm; the bent poses have a larger overall bounding-box depth because of their centerline shape. The cap seam, rounded ends, and a broad integral clip relief are actual geometry. All parts are rendered black without labels or logos. The clip is a simplified raised relief, not a functional spring clip.

## Files and reproduction

- Generator: `scripts/rolling_wavy_pen.py`
- Editable scene: `models/rolling-wavy-pen.blend`
- Four STL files: `exports/rolling-wavy-pen/{straight,curved,wavy,highly-wavy}.stl`
- Fixed-camera comparison sheets: `previews/rolling-wavy-pen/contact-front.png`, `contact-neutral-front.png`, `contact-top.png`
- Four-stage study animation: `previews/rolling-wavy-pen/sequence.gif`
- Before/after Straight comparison at identical orthographic scale: `previews/rolling-wavy-pen/comparison-straight-before-after.png`
- Measured geometry and export hashes: `previews/rolling-wavy-pen/validation.json`

Run `/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/rolling_wavy_pen.py`. The script also uses the installed `magick` command for sheets and GIF assembly. For a reproducibility check, rerun with `-- --output-root /path/to/temporary-directory --geometry-only` and compare STL hashes.

The four-stage GIF is a shape review, not a claim that the final rolling motion is fluent. The study uses a fixed front oblique camera, 0°, +18°, −14°, and +25° cross-section roll, and separate Y filming positions of 0, +3, −2, and +4 mm. These four sampled poses alone cannot demonstrate every proposed 10-frame rolling beat.

| Form | STL bounds X × Y × Z (mm) | Table contact (mm²) | COM support margin (mm) |
|---|---:|---:|---:|
| Straight | 141.800 × 13.200 × 12.520 | 720.3 | 2.60 |
| Curved | 141.800 × 28.768 × 12.519 | 734.1 | 6.99 |
| Wavy | 141.800 × 27.402 × 12.892 | 734.3 | 7.64 |
| Highly Wavy | 141.800 × 31.699 × 12.518 | 734.2 | 9.60 |

The GIF holds the first three forms for about 330 ms each and the last for about 580 ms, approximating 4/4/4/7 exposures at 12 fps after GIF timing quantization.

## Provisional 10-frame plan

| Frame | Role | Printable form |
|---|---|---|
| 01 | Straight, initial orientation | Straight |
| 02 | Begin rolling; still straight | Reuse Straight with new physical orientation/placement if stable |
| 03 | Broad arc begins | New slight-curve form |
| 04 | Broad arc clear | Curved |
| 05 | First secondary wave appears | New early-wave form |
| 06 | Several waves become legible | Wavy |
| 07 | Waves grow, roll continues | New stronger-wave form |
| 08 | Large irregular waves begin | New late-wave form |
| 09 | Near-final irregular waviness | Reuse late-wave form with changed placement only if credible; otherwise new form |
| 10 | Full storyboard-like waviness | Highly Wavy |

This is 8 unique shapes if Frames 02 and 09 can reuse existing forms; if a reused form is unstable at the intended roll angle or lacks enough visual change, make that frame a ninth shape. A 12 fps base is provisional. No intermediate frame geometry has been generated.

## Geometry and print boundaries

The meshes are solid and have a shallow planar sole on each study pose. A broad clip relief is integrated into the cap to avoid a thin, separate spring feature. Geometry validation covers export dimensions, watertight/manifold topology, one component, face winding, degenerate triangles, non-adjacent BVH overlaps, table clearance, finite contact area, and uniform-density center-of-mass support. The validation JSON records individual measurements.

The nominal barrel diameter is 11.9 mm. The cap is approximately 13.2 mm across before its raised clip relief. The straight pose has 720.3 mm² of table contact and 2.60 mm center-of-mass support margin; the bent poses retain over 734 mm² and at least 6.99 mm margin. Exhaustive minimum-feature-thickness analysis, slicer behavior, support requirements, printing time/material use, and physical print results remain unverified.

All four independent STL regenerations matched byte for byte. The saved Blender scene's four mesh fingerprints and filming Y placements matched `validation.json`. Existing motif files were not changed.
