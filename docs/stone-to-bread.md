# Stone to Bread

## Current checkpoint: 13 poses

The 13-pose CG previsualization and stone geometry are **provisionally approved**. The sequence is `r01→r02→r03→r04→r05→r06→r07→p01→p02→p03→p04→c01→b01`. During `r01`–`r07`, three back-and-forth rolls progressively elongate the pebble. During `p01`–`p04`, pressure flattens and pulls its center toward the viewer. `c01` is a one-exposure recoil; `b01` replaces it with bread through a hard cut.

The 12 printable stone STLs remain in their validated study locations: seven under [`rolling-elongating-study-v4`](../exports/stone-to-bread/rolling-elongating-study-v4/), four under [`pulling-study-v1`](../exports/stone-to-bread/pulling-study-v1/), and one under [`recoil-study-v1`](../exports/stone-to-bread/recoil-study-v1/). Bread `b01` is a preview-only mesh in the [integrated scene](../models/stone-to-bread-full-sequence-v1.blend); real bread is planned for filming, so no production bread STL exists. The [manifest](../previews/stone-to-bread/full-sequence-v1/manifest.json) lists every pose's dimensions, STL hash, mesh fingerprint, filming position and exposure count.

The selected reference is the [realistic deliberate GIF](../previews/stone-to-bread/full-sequence-v1/sequence-realistic-deliberate.gif) at 12 fps: 44 exposures across 13 discrete poses (3.667 s before GIF time quantization). The [energetic GIF](../previews/stone-to-bread/full-sequence-v1/sequence-realistic-energetic.gif), [neutral-material GIF](../previews/stone-to-bread/full-sequence-v1/sequence-neutral-deliberate.gif), [front contact sheet](../previews/stone-to-bread/full-sequence-v1/contact-front.png), [top contact sheet](../previews/stone-to-bread/full-sequence-v1/contact-top.png), and [side comparison](../previews/stone-to-bread/full-sequence-v1/contact-side.png) use the same stone meshes. The fixed front camera uses a 50° elevation and 126 mm orthographic scale.

Generation uses Blender 4.5 LTS with its bundled Python and ImageMagick. Run these commands **only in an isolated checkout**, because they write to study directories:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/stone_to_bread_rolling_elongating_study_v4.py
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/stone_to_bread_pulling_study.py
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/stone_to_bread_recoil_study.py
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/stone_to_bread_full_sequence.py
```

Compare resulting STL SHA-256 hashes and saved-scene mesh fingerprints with the study manifests and the [integrated manifest](../previews/stone-to-bread/full-sequence-v1/manifest.json).

The integrated audit matched all 12 existing STL hashes and render-mesh coordinates, all 13 saved-scene mesh fingerprints, and 401 protected source/asset file hashes. Existing per-pose records report closed/manifold, single-component stone solids, outward normals, no degenerate faces, no detected nonadjacent triangle intersections, finite tabletop contact and positive uniform-density support margins. The audit reused those geometric checks; it did not rerun an exhaustive mesh analysis. Global minimum thickness, intersections involving shared vertices, slicer behavior, support needs, material strength, physical printing and live-action registration remain unverified. Rendering noise and visual consistency can be refined later without changing the checkpoint geometry.

## Historical ten-frame prototype

The earlier ten-frame sequence was visually approved as a prototype. Its old Frame 02 and 03 STL hashes no longer match the current root-level files after later rolling experiments. Exact approved STL bytes are preserved in [`approved-geometry-recovery`](../exports/stone-to-bread/approved-geometry-recovery/), and all ten meshes in the [recovery scene](../models/stone-to-bread-approved-geometry-recovery.blend) match the recorded approved mesh fingerprints. The recovery scene's `.blend` file bytes differ from the old scene hash; the current root scene differs in the Frame 02 and 03 meshes. The root generator scripts also differ from their historical recorded byte hashes. These historical files were retained without replacement.

## Sequence and dimensions

Dimensions are measured STL bounds in local X × Y × Z, in millimeters. Local X follows the rod, positive Y points toward the camera along the tabletop, and Z points up; the corresponding world directions are +X, −Y and +Z. The tabletop is at Z=0.

| Frame | Action | Dimensions (mm) |
| --- | --- | --- |
| 01 | Original irregular stone | 30.000 × 25.000 × 20.000 |
| 02 | Rolling and initial elongation | 40.370 × 23.704 × 19.481 |
| 03 | Further rolling and elongation | 59.630 × 21.296 × 18.519 |
| 04 | Elongated rod | 70.000 × 20.000 × 18.000 |
| 05 | Initial central pressure and pull | 70.000 × 25.457 × 17.361 |
| 06 | Intermediate flattened stretch | 70.000 × 37.480 × 16.121 |
| 07 | Near-maximum pressed stretch | 70.000 × 49.508 × 15.038 |
| 08 | Maximum pressed, flattened stretch | 70.000 × 54.976 × 14.565 |
| 09 | Sudden recoil with a short flattened remnant | 40.000 × 29.997 × 18.000 |
| 10 | Instant replacement with bread | 80.000 × 60.000 × 50.000 (preview mesh) |

The historically approved Frames 01–09 are stone solids. For the original approved Frame 02 and 03 bytes, use the recovery directory above; the other old exports remain in [`exports/stone-to-bread/`](../exports/stone-to-bread/). Frame 10 is a procedural stand-in in the [historical Blender scene](../models/stone-to-bread-approved-geometry-recovery.blend): real bread is intended for filming, so no bread STL was exported. The recovery scene contains ten named mesh objects, a fixed camera and a preview-only tabletop.

## Previews and source

- [Oblique contact sheet](../previews/stone-to-bread/sequence-oblique.png), [top-down contact sheet](../previews/stone-to-bread/sequence-top.png), and [side comparison, 04–09](../previews/stone-to-bread/sequence-side.png).
- [Complete forward GIF](../previews/stone-to-bread/sequence.gif): 01→10, with 400 ms for Frames 01–08, the approved 80 ms quick-release reference for Frame 09, and 700 ms for Frame 10. The 09→10 change is a hard cut.
- [Rolling GIF](../previews/stone-to-bread/rolling.gif) and [pressing/stretching GIF](../previews/stone-to-bread/stretching.gif).
- Procedural source: [`stone_to_bread.py`](../scripts/stone_to_bread.py) and [`stone_to_bread_sequence.py`](../scripts/stone_to_bread_sequence.py). Geometry is deterministic and uses Blender 4.5 LTS; the independently reproduced intermediate exports match by SHA-256.

## Validation and limitations

[Motif validation](../previews/stone-to-bread/validation.json) records measurements and checks for all nine STLs. [Sequence validation](../previews/stone-to-bread/sequence-validation.json) records the intermediate checks, reproducibility, protected-asset hashes and preview timing. The [aggregate record](../previews/validation.json) contains the final approval and asset hashes. These records include the STL SHA-256 values and saved-scene mesh fingerprints.

The historical validation records report that all nine originally approved exports passed closed/manifold mesh checks, one connected component, consistent outward winding and STL normals, positive volume, no degenerate faces, no BVH-detected intersections between nonadjacent triangles, tabletop contact, and a positive uniform-density center-of-mass support margin. Their recorded hashes match the recovery Frame 02 and 03 STLs and the other seven root exports; all ten recovery-scene mesh fingerprints match the old approval record.

The intersection test excludes adjacent and shared-vertex triangle pairs. Vertical core-thickness samples are not an exhaustive minimum-thickness or small-feature check. Static support does not verify friction or handling. Slicing, support requirements, nozzle/layer suitability, material strength, warping and physical printing remain unverified; visual approval is not a physical print test. The bread stand-in still needs to be matched to the real bread during filming. Volume conservation and physical material behavior were not simulated.
