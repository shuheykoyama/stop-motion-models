# Stop Motion Models

Procedural stop-motion props generated with Blender 4.5 LTS. Each motif has seven interchangeable STL models in millimeters; reverse playback reuses those seven shapes.

## Project status

**Pen, Stones and Cup Frames 01–07 are approved and final (2026-11-07): all 21 models. Do not change their geometry or regenerate finalized outputs without a separate user request.** Stones' approved sequence uses the revised 35%/70% child-relief sampling.

| Motif | Editable scene | STL exports | Visual review |
| --- | --- | --- | --- |
| Pen — final | [pen.blend](models/pen.blend) | `exports/pen/frame-01.stl` through `frame-07.stl` | [Oblique](previews/pen/contact-sheet.png), [top-down](previews/pen/contact-sheet-top.png), [forward/reverse GIF](previews/pen/forward-reverse.gif) |
| Stones — final | [stones.blend](models/stones.blend) | `exports/stones/frame-01.stl` through `frame-07.stl` | [Oblique](previews/stones/contact-sheet.png), [GIF](previews/stones/forward-reverse.gif), [top-down](previews/stones/contact-sheet-top.png) |
| Cup — final | [cup.blend](models/cup.blend) | `exports/cup/frame-01.stl` through `frame-07.stl` | [Oblique](previews/cup/contact-sheet.png), [GIF](previews/cup/forward-reverse.gif), [top-down](previews/cup/contact-sheet-top.png), [top GIF](previews/cup/forward-reverse-top.gif) |

The repository contains 3 editable scenes and 21 STL exports. Scenes contain seven static mesh objects sharing one origin and datum, with Frame 01 visible by default. To inspect another frame, switch both viewport and render visibility. Cameras, lights and preview floors are staging objects and are excluded from STL exports. Do not shift or normalize individual frames independently.

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
