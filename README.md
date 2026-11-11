# Stop Motion Models

Procedural stop-motion props generated with Blender 4.5 LTS. The original three motifs each have seven interchangeable STL models in millimeters; reverse playback reuses those seven shapes.

## Project status

**Pen, Stones and Cup Frames 01–07 are approved and final (2026-11-07): all 21 models. Do not change their geometry or regenerate finalized outputs without a separate user request.** Stones' approved sequence uses the revised 35%/70% child-relief sampling.

| Motif | Editable scene | STL exports | Visual review |
| --- | --- | --- | --- |
| Pen — final | [pen.blend](models/pen.blend) | `exports/pen/frame-01.stl` through `frame-07.stl` | [Oblique](previews/pen/contact-sheet.png), [top-down](previews/pen/contact-sheet-top.png), [forward/reverse GIF](previews/pen/forward-reverse.gif) |
| Stones — final | [stones.blend](models/stones.blend) | `exports/stones/frame-01.stl` through `frame-07.stl` | [Oblique](previews/stones/contact-sheet.png), [GIF](previews/stones/forward-reverse.gif), [top-down](previews/stones/contact-sheet-top.png) |
| Cup — final | [cup.blend](models/cup.blend) | `exports/cup/frame-01.stl` through `frame-07.stl` | [Oblique](previews/cup/contact-sheet.png), [GIF](previews/cup/forward-reverse.gif), [top-down](previews/cup/contact-sheet-top.png), [top GIF](previews/cup/forward-reverse-top.gif) |

The approved collections contain 3 editable scenes and 21 STL exports. Their scenes contain seven static mesh objects sharing one origin and datum, with Frame 01 visible by default. To inspect another frame, switch both viewport and render visibility. Cameras, lights and preview floors are staging objects and are excluded from STL exports. Do not shift or normalize individual frames independently.

## Stone to Bread

The current [Stone to Bread checkpoint](docs/stone-to-bread.md) is a **provisionally approved CG previsualization**, with 12 printable stone poses (`r01`–`r07`, `p01`–`p04`, `c01`) and one preview-only bread pose (`b01`). The stone rolls and elongates, its center is pressed and pulled toward the viewer, then it recoils before a hard cut to bread. Physical printing has not been tested.

**[Watch the primary 13-pose GIF](previews/stone-to-bread/full-sequence-v1/sequence-realistic-deliberate.gif)** · [Front contact sheet](previews/stone-to-bread/full-sequence-v1/contact-front.png) · [Top contact sheet](previews/stone-to-bread/full-sequence-v1/contact-top.png) · [Editable scene](models/stone-to-bread-full-sequence-v1.blend) · [Pose manifest](previews/stone-to-bread/full-sequence-v1/manifest.json)

The earlier ten-frame sequence and rolling studies remain available as historical references. See the motif documentation for their status and the recovered legacy geometry.

## Rolling Wavy Pen

**Rolling Wavy Pen is approved for stop-motion and print-data preparation.** The approved animation is `storyboard-study-v11`: 30 exposures over 4.8 seconds, progressing from Straight to Single Arc, Arc + Waves, and Arc + Stronger Waves. The approved print set contains 16 STL poses. Import STL coordinates as **millimeters**; STL files do not encode units.

- [Approved 30-pose animation](previews/rolling-wavy-pen/storyboard-study-v11/sequence.gif) · [Contact sheet](previews/rolling-wavy-pen/storyboard-study-v11/contact-sheet.png) · [Editable v11 scene](models/rolling-wavy-pen-storyboard-study-v11.blend)
- **Official print files:** [`exports/rolling-wavy-pen/print-set-v2/pose-01.stl` through `pose-16.stl`](exports/rolling-wavy-pen/print-set-v2/)
- [30-frame filming map](previews/rolling-wavy-pen/print-set-v2/frame-to-stl.csv) · [Print-set documentation](docs/rolling-wavy-pen-print-set-v2.md)
- **Final QA: PASS.** [QA report](docs/rolling-wavy-pen-final-qa.md) · [Machine-readable results](previews/rolling-wavy-pen/print-set-v2/final-qa.json)

CAM and slicer verification, support assessment, print-time estimates, and physical printing have not been performed. `print-set-v1` and `storyboard-study-v1`–`v10` are historical studies; use only `print-set-v2` for the approved print set.

## Stone to Fireworks

**Stone to Fireworks v3 and the 14-model `print-set-v1` are approved.** A natural stone is pressed three times, pulled toward the viewer, then released and sent into the distance. The physical filming plan uses **20 poses, 40 exposures at 12 fps, approximately 3.33 seconds**, with every stone resting on the tabletop. Smaller physical stone models replace aerial scaling; no hands or fireworks are modeled.

- **Official print files:** [`exports/stone-to-fireworks/print-set-v1/pose-01.stl` through `pose-14.stl`](exports/stone-to-fireworks/print-set-v1/). Import as **millimeters**; STL has no unit metadata.
- **[Tabletop filming preview](previews/stone-to-fireworks/print-set-v1/print-reproduction.gif)** · [20-pose contact sheet](previews/stone-to-fireworks/print-set-v1/contact-sheet.png) · [Selected models](previews/stone-to-fireworks/print-set-v1/selected-shapes.png)
- [Approved v3 animation reference](previews/stone-to-fireworks/v3/sequence-v3.gif) · [v3 versus tabletop comparison](previews/stone-to-fireworks/print-set-v1/v3-vs-tabletop.gif). The reference includes lift; use the tabletop preview and CSV for physical filming.
- [Filming CSV](previews/stone-to-fireworks/print-set-v1/frame-to-stl.csv) · [Pose manifest](previews/stone-to-fireworks/print-set-v1/manifest.json) · [Editable print scene](models/stone-to-fireworks-print-set-v1.blend) · [Editable v3 scene](models/stone-to-fireworks-v3.blend)
- **Final QA: PASS.** [Report](docs/stone-to-fireworks-final-qa.md) · [Machine-readable results](previews/stone-to-fireworks/print-set-v1/final-qa.json) · [Production guide and reproduction commands](docs/stone-to-fireworks-print-set-v1.md)

CAM, slicer verification, printing support assessment, print-time estimates and physical printing are unverified. Earlier v1/v2 files included as frozen generator dependencies are historical, not alternate print sets. Additional historical render and export files remain local and are not required for the official tabletop handoff. Review-pending labels in original generation records predate approval.

## Rolling Cube Pen

**The official print set is `print-set-v4`: 12 STL types, 20 physical props.** Reuse the same props throughout the **61 poses, 74 exposures at 12 fps (approximately 6.17 seconds)**. The black capped marker rolls through six round trips, becomes a square prism, then separates into twelve cubes. The cap stays on screen left; the camera and model scale stay fixed.

- **Official STL files:** [pose-01.stl through pose-12.stl](exports/rolling-cube-pen/print-set-v4/). Import into Bambu Studio as **millimeters at 100% scale**; STL has no unit metadata.
- [Final reproduction GIF](previews/rolling-cube-pen/print-set-v4/print-reproduction.gif) · [v2 comparison](previews/rolling-cube-pen/print-set-v4/v2-vs-print-set.gif) · [Contact sheet](previews/rolling-cube-pen/print-set-v4/contact-sheet.png) · [Selected models](previews/rolling-cube-pen/print-set-v4/selected-shapes.png)
- [Filming CSV](previews/rolling-cube-pen/print-set-v4/frame-to-stl.csv) · [Print quantities](previews/rolling-cube-pen/print-set-v4/print-inventory.csv) · [Manifest](previews/rolling-cube-pen/print-set-v4/manifest.json) · [Editable scene](models/rolling-cube-pen-print-set-v4.blend)
- **Final data QA: PASS.** [QA record](previews/rolling-cube-pen/print-set-v4/validation.json) · [Final QA report](docs/rolling-cube-pen-print-set-v4-final-qa.md) · [Filming and printing guide](docs/rolling-cube-pen-print-set-v4.md)

Eighteen Phase 1 poses require finger holding. Dynamic rolling, model-swap registration, fine-gap placement, exhaustive minimum thickness, slicing, supports, print time and physical printing remain unverified. Data QA does not guarantee physical filming or printing success. The approved ideal animation v2 and the former official [print-set-v3](docs/rolling-cube-pen-print-set-v3.md) remain preserved as historical references; print v4 for the current production plan.

## Documentation and verification

- [Specification](docs/specification.md): current approved pen dimensions and deformation; existing stones/cup requirements.
- [Preview and measurement guide](previews/README.md): current seven-frame measurements, comparisons, and clearly separated historical review records.
- [Combined validation record](previews/validation.json): current results for all 21 exports, with final approval and asset hashes under each motif's `finalization` entry.
- [Pen progression validation](previews/pen/intermediates-validation.json): all seven measured pen shapes, five regenerated intermediate checks, endpoint preservation and deterministic reproduction.
- [Stones progression validation](previews/stones/progression-validation.json): resampled intermediate timing, preserved endpoint/midpoint fingerprints, geometry checks and protected-file hashes.

Recorded checks cover dimensions, connected components, manifoldness, winding/normals, degenerate geometry and nonadjacent-triangle intersections. Directional thickness samples cover functional regions only. Exhaustive adjacent-triangle intersections, global minimum feature thickness, slicing, supports, physical printing and filmed registration remain unverified. Final visual approval does not constitute physical print validation.

## Reproducibility

[scripts/generate.py](scripts/generate.py) is the procedural source of truth; [scripts/pen_previews.py](scripts/pen_previews.py) creates endpoint inspection views without changing geometry. Each `.blend` embeds its generator source. The pen scene also retains legacy sources for historical intermediate shapes; those are not the final generation definitions.

For the final Stones progression, [scripts/stones_progression.py](scripts/stones_progression.py) samples the unchanged shared shape function at child-relief blends 0%, 35%, 70% and 100% in each hierarchy stage. During refinement it changed only Frames 02, 03, 05 and 06, retaining Frames 01, 04 and 07. Use its `--no-render --output-root /absolute/path` arguments for isolated reproduction; running the generic generator with uniform frame times would recreate the earlier spacing. All three motifs' shape code and assets are now frozen. Embedded review-status strings and earlier reports predate final approval; the combined validation record holds the current approval status.

Use Blender's bundled Python, not the project uv interpreter, for `bpy`. For a separate reproduction of the final pen set, direct all generated files to a temporary output root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/generate.py -- --motif pen --all-frames --no-render --output-root /private/tmp/stop-motion-pen-reproduction
```

This command reads the existing approved endpoint scene and writes reproduction outputs outside the finalized directories. Compare STL SHA-256 values against `pen.finalization.asset_sha256` in the combined validation record. Omit `--no-render` only when reproduction previews are needed. Do not run default/root-output regeneration or endpoint-revision commands against final pen assets.

Python tooling uses mise and uv as described in [AGENTS.md](AGENTS.md); no dependency changes are needed for this handoff. Bambu Studio, slicing and printer operation remain with the user. Commits and pushes require an explicit request.
