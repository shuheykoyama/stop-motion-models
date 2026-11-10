# Rolling Wavy Pen — print-set-v2

Status: **approved print-data set; Final QA PASS**. This is the only approved Rolling Wavy Pen STL set for CAM/slicer review. Physical printing has not been performed.

This set reproduces the approved 30-pose v11 sequence using 16 printable STL meshes. The v11 mesh generator and source scene remain the geometric source of truth; no shape, scale, or surface profile was redesigned for this set.

The selected STLs retain the v11 baked roll/contact orientation. Reuse is achieved by reassigning the same STL and changing its recorded Y placement. The additional roll correction is zero for the 30-frame assignment so each STL remains on its validated contact plane.

## Printable models

Dimensions are STL bounding-box X × Y × Z in millimeters. Usage counts refer to the 30-frame CSV.

| STL pose | Source v11 frame | Dimensions (mm) | Uses | File |
|---|---:|---:|---:|---|
| pose-01 | v11 frame-01 | 141.800 × 13.197 × 13.092 | 4 | pose-01.stl |
| pose-02 | v11 frame-04 | 141.800 × 13.753 × 12.518 | 3 | pose-02.stl |
| pose-03 | v11 frame-08 | 141.800 × 14.212 × 13.092 | 1 | pose-03.stl |
| pose-04 | v11 frame-09 | 141.800 × 16.437 × 13.092 | 1 | pose-04.stl |
| pose-05 | v11 frame-10 | 141.800 × 19.183 × 12.518 | 1 | pose-05.stl |
| pose-06 | v11 frame-11 | 141.800 × 21.929 × 12.518 | 1 | pose-06.stl |
| pose-07 | v11 frame-12 | 141.800 × 23.993 × 12.518 | 1 | pose-07.stl |
| pose-08 | v11 frame-13 | 141.800 × 23.993 × 13.092 | 3 | pose-08.stl |
| pose-09 | v11 frame-16 | 141.800 × 24.454 × 12.518 | 2 | pose-09.stl |
| pose-10 | v11 frame-18 | 141.800 × 25.853 × 12.518 | 1 | pose-10.stl |
| pose-11 | v11 frame-19 | 141.800 × 26.685 × 13.092 | 1 | pose-11.stl |
| pose-12 | v11 frame-21 | 141.800 × 28.024 × 13.092 | 2 | pose-12.stl |
| pose-13 | v11 frame-22 | 141.800 × 28.061 × 12.518 | 3 | pose-13.stl |
| pose-14 | v11 frame-25 | 141.800 × 28.410 × 13.092 | 1 | pose-14.stl |
| pose-15 | v11 frame-27 | 141.800 × 28.714 × 13.092 | 2 | pose-15.stl |
| pose-16 | v11 frame-30 | 141.800 × 27.978 × 12.518 | 3 | pose-16.stl |

## Stop-motion placement

Follow `previews/rolling-wavy-pen/print-set-v2/frame-to-stl.csv` in frame order. It records the phase, reused STL, source v11 frame, rolling direction, baked roll, and X/Y/Z filming position. Positions are millimeter starting guides; adjust them to match the actual table and camera during filming. Preserve the exported STL scale and use its Z=0 contact side on the table.

## Review and validation

- Print-only reconstruction: `previews/rolling-wavy-pen/print-set-v2/print-reproduction.gif`
- Side-by-side v11 ideal versus print-set reconstruction: `previews/rolling-wavy-pen/print-set-v2/ideal-vs-print-reproduction.gif`
- Candidate pose sheet: `previews/rolling-wavy-pen/print-set-v2/selected-shapes.png`
- Validation and SHA-256 records: `previews/rolling-wavy-pen/print-set-v2/validation.json`

All 16 solids passed final mesh checks and independent regeneration/hash comparison. Import as millimeters; do not apply another roll rotation because each STL already contains its approved print/contact orientation. Minimum feature thickness, slicer behavior, support requirements, and physical printing remain unverified. Approval here confirms the geometry/data package, not successful physical printing.
