# Stones — final seven-frame sequence

**Stones Frames 01–07 received final visual approval on 2026-11-07. Pen and Cup remain final: all 21 models are approved.** No geometry, Blender scene, STL, image, GIF or generator was changed when recording this approval. Final asset hashes and the user's review are recorded under `stones.finalization` in [`validation.json`](validation.json). Earlier embedded review-status strings and progression-report status fields are historical; the current approval record supersedes them without rewriting the frozen assets.

The user confirmed clear coarse-to-fine progression, a more natural 02→03, an acceptable larger 05→06 change, sufficiently distinguishable 06→07, and no positional or boundary jumps. Preserve this accepted sequence without further geometry adjustments.

Only Stones **Frames 02, 03, 05 and 06** were regenerated. **Frames 01, 04 and 07** retain their existing STL bytes and saved mesh fingerprints. Fixed seed, pebble sites, hierarchy ancestry, shape function, backing, 80 × 80 mm outline, materials, camera, lights and reference positions are unchanged.

Updated review files:

- [Seven-frame elevated oblique contact sheet](stones/contact-sheet.png).
- [Forward/reverse GIF](stones/forward-reverse.gif): the existing 13-state sequence, 400 ms per state, 5.2-second infinite loop, 720 × 480, shared palette. No temporal interpolation or additional frames.
- [Seven-frame top-down contact sheet](stones/contact-sheet-top.png), updated to match the revised geometry.
- [`models/stones.blend`](../models/stones.blend) and `exports/stones/frame-02.stl`, `frame-03.stl`, `frame-05.stl`, `frame-06.stl`.
- [`stones/progression-validation.json`](stones/progression-validation.json): actual shape sampling, geometry checks, unchanged hierarchy/endpoint fingerprints, before/after height changes, fixed render rig and protected-file hashes. The older [`review-validation.json`](review-validation.json) is a historical preview record for the previous Stones spacing; its Cup images remain the final approved ones.

The existing smoothstep concentrated child-groove changes in the middle of each hierarchy stage. The final sampler chooses child-relief blends **0%, 35%, 70%, 100%**, replacing **0%, 25.926%, 74.074%, 100%**. This shifts some of the 02→03 and 05→06 changes into their neighboring transitions and retains more of the parent relief in Frame 06, making 06→07 clearer. The shorter final blend relative to the first two steps compensates for fine grooves becoming more visible near full subdivision. This sampling and its resulting shapes are now approved.

[`scripts/stones_progression.py`](../scripts/stones_progression.py) calls the unchanged `stones_geometry` definition from `scripts/generate.py` and is embedded in the updated scene. Reproduce only the current Stones intermediate sampling with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/stones_progression.py
```

The command above documents generation and must not be run against finalized outputs without a separate request. Always append `--no-render --output-root /absolute/path` for isolated reproducibility checks. Do not run the old uniform-time generation or the previous all-motif preview command against the finalized sets. The sampler leaves every Pen/Cup asset and the shared geometry source unchanged.

Checks cover dimensions, 2 mm backing, one connected closed solid, manifold edges/vertices, outward winding/STL normals, positive volume, degenerate geometry and nonadjacent-triangle intersections for the four changed exports. Unchanged 01/04/07 reuse their existing passing records after verifying STL hashes. Shared-vertex/adjacent-triangle intersections, exhaustive local-normal minimum feature thickness, slicing, strength, warping, supports and physical printing remain unverified; no physical printability guarantee is made.

| Frame | Overall dimensions (mm) | Hierarchy stage | Child-relief blend |
| --- | --- | --- | --- |
| 01, unchanged | 80.000 × 80.000 × 3.598 | coarse→middle | 0% |
| 02, updated | 80.000 × 80.000 × 3.415 | coarse→middle | 35% |
| 03, updated | 80.000 × 80.000 × 3.366 | coarse→middle | 70% |
| 04, unchanged | 80.000 × 80.000 × 3.399 | middle landmark | 100% / 0% |
| 05, updated | 80.000 × 80.000 × 3.301 | middle→fine | 35% |
| 06, updated | 80.000 × 80.000 × 3.231 | middle→fine | 70% |
| 07, unchanged | 80.000 × 80.000 × 3.199 | middle→fine | 100% |

The unchanged hierarchy contains 100, 319 and 1,023 cells at its three levels. Maximum vertex-height changes are now 0.559, 0.559, 0.479, 0.489, 0.489 and 0.419 mm. Specifically, 02→03 decreases from 0.769 to 0.559 mm and 05→06 from 0.673 to 0.489 mm; 06→07 increases from 0.362 to 0.419 mm. An independent regeneration produced identical SHA-256 digests for all four updated STLs and passed the same geometry checks. Pen/Cup final inventories and protected Stones files also match their original hashes.

Visual review finds less concentrated middle-stage changes and a clearer remaining 06→07 transition, with fixed boundaries and no site migration. Top-view RGB image differences for 02→03 and 05→06 are about 25% lower than before, and 06→07 is about 13% higher; these are diagnostic differences, not a measure of perceptual approval. Fine grooves still emerge as hierarchical stages and may remain more noticeable than neighboring transitions, especially at GIF resolution. The overall peak relief is not strictly monotonic at the middle hierarchy landmark; the approved relief shapes and backing remain unchanged. The user accepted the remaining larger 05→06 change as part of the final sequence.

<details>
<summary>Previous Stones/Cup preview review (historical; Cup subsequently approved)</summary>

# Stones and Cup — awaiting final visual review

These are preview-only deliverables from the existing seven-frame scenes. Neither motif is finally approved. All `.blend` models and STL exports, all Pen files and its two generator sources, and the reused Stones/Cup oblique renders/contact sheets are protected by SHA-256 comparisons. No geometry is generated, edited or saved. The final Pen sequence and its approval record remain unchanged.

| Motif/view | Seven-frame contact sheet | Forward/reverse GIF |
| --- | --- | --- |
| Stones, existing elevated oblique | [Contact sheet](stones/contact-sheet.png), reused | [GIF](stones/forward-reverse.gif) |
| Stones, top-down inspection | [Contact sheet](stones/contact-sheet-top.png) | Not requested |
| Cup, existing elevated oblique | [Contact sheet](cup/contact-sheet.png), reused | [GIF](cup/forward-reverse.gif) |
| Cup, top-down inspection | [Contact sheet](cup/contact-sheet-top.png) | [GIF](cup/forward-reverse-top.gif) |

All sheets label Frames 01–07 in reading order: 01–04 on the first row, 05–07 on the second. All GIFs contain exactly 01→02→03→04→05→06→07→06→05→04→03→02→01, with 400 ms per state, a 5.2-second infinite loop, and a 720 × 480 canvas matching Pen. GIFs contain only the existing seven states; no temporal interpolation, morphing or additional frames are used. The two oblique views reuse the existing still images. Each new top-down sequence holds camera, scale, framing, lighting, background and materials fixed; the camera is temporary and is never saved to a model.

GIF encoding uses one shared palette across all states with Floyd–Steinberg dithering to reduce changing color bands; this affects only the GIF representation, not the original stills, materials or lighting. GIF palette/dithering noise remains a limitation of the preview format. See the [ImageMagick color-remapping reference](https://imagemagick.org/command-line-options/#remap).

Reproduce the preview-only outputs with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/review_previews.py
```

[`review-validation.json`](review-validation.json) records fixed camera/light/material settings, source hashes, protected asset checks, decoded GIF state order, timing and infinite-loop verification. The existing [geometric validation record](validation.json) is reused without changes; no new geometry validation or print testing is implied by preview generation.

Visual continuity assessment:

- **Stones:** Coarse-to-fine subdivision and its reverse are understandable. The 80 × 80 mm outline, position and parent-cell placement remain fixed. Changes are unevenly spaced: 02→03 and 05→06 introduce the strongest child-groove changes, while 03→04 and 06→07 are subtler. The sequence reads as staged subdivision rather than an evenly paced shrink; these changes can appear as texture popping at 400 ms per state. No random lateral rearrangement is apparent. The added top-down sheet makes the parent/child boundaries clearer; oblique fine relief is low-contrast at reduced GIF size. These observations are for user review, not final approval.
- **Cup:** Thickness progresses 2→3→4→5→6→7→8 mm, with straight-wall inner diameter 76→74→72→70→68→66→64 mm in the existing measured exports. External diameter and height remain 80 mm. Forward playback thickens the wall and closes the opening; reverse playback opens it again. No sudden exterior/rim-position jumps are apparent in the oblique comparison. The top-down inspection isolates the changing aperture; the existing fixed 0.25 mm rim rounding is retained. No geometry or frame timing was adjusted to change the appearance.

Perceptual smoothness remains subject to the user's visual review and eventual filmed/printed results; numerical frame-order and timing verification does not establish absence of every visible flicker.

</details>

# Pen final seven-frame sequence — sloped compression and near-side bow

**Final visual approval: 2026-11-07, Frames 01–07. Preserve every pen geometry and finalized output.** No geometry, model, STL, image, animation or generator was changed during final documentation. Stones and cup assets are unchanged. The [project index](../README.md) links all three existing motif sets. Final pen file hashes and approval are recorded under `pen.finalization` in [`validation.json`](validation.json).

Frames 02–06 now use the approved sloped/bowed tabletop-compression definition at t = 1/6 through 5/6. The shape algorithm and parameters are unchanged. Existing Frame 01 and Frame 07 STL files are read without rewriting, and both saved endpoint mesh fingerprints are preserved. Stones and cup models, STLs and PNG previews are protected by SHA-256 checks. Blender 4.5.15 LTS and Blender MCP are available; generation uses Blender's bundled Python in a separate process.

Current outputs:

- [`models/pen.blend`](../models/pen.blend): seven static interchangeable meshes, unchanged endpoint objects, current generator embedded, Frame 01 visible by default.
- `exports/pen/frame-02.stl` through `frame-06.stl`: the five regenerated exports. Frame 01 and Frame 07 are preserved byte-identically.
- [Elevated oblique seven-frame contact sheet](pen/contact-sheet.png) and [top-down seven-frame contact sheet](pen/contact-sheet-top.png). Both are ordered 01–04 across the first row and 05–07 across the second. Individual renders are `pen/frame-01.png` through `frame-07.png` and `pen/frame-01-top.png` through `frame-07-top.png`. Each view uses a fixed camera, scale, framing and lights across all seven frames. The top camera uses the same scene-derived orientation as the endpoint review; these continuity renders show clean geometry without centerline annotations.
- [Forward/reverse GIF](pen/forward-reverse.gif): 01→02→03→04→05→06→07→06→05→04→03→02→01, 0.4 seconds per state, 5.2 seconds per loop, 720 × 480.
- [`pen/intermediates-validation.json`](pen/intermediates-validation.json): STL measurements, mesh checks, original material-meridian displacement, monotonic progression assertions, endpoint preservation, camera settings, animation metadata and protected-file hashes. [`validation.json`](validation.json) updates only the pen record; the endpoint-specific [`pen/tabletop-validation.json`](pen/tabletop-validation.json) remains the prior approved shape review.

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/generate.py -- --pen-intermediates
```

The command above records how the intermediates were produced; it overwrites final pen outputs if run as shown. For future reproduction, always append `--no-render --output-root /absolute/path` or use the isolated full-set command in the [project index](../README.md). Further geometry changes require a separate user request. No endpoint export, other-motif generation or printer operation is part of the selective command.

The existing [oblique endpoint pair](pen/comparison-oblique.png), [top-down pair with centerline overlays](pen/comparison-top.png), [side pair](pen/comparison-side.png), and [central cross-sectional overlay](pen/comparison-section.png) still show the same approved endpoint geometry. Historical reports below contain superseded dimensions/status; the current seven-frame validation JSON is authoritative for the progression.

All measurements below are from the exported STLs in millimeters. Roof difference is far-side height minus near-side height, measured at equal ±5 mm offsets about the moved material centerline.

| Frame | Overall X × Y × Z | Center height | Center width | Near centerline shift | Roof difference | Sampled minimum vertical thickness |
| --- | --- | --- | --- | --- | --- | --- |
| 01 | 140.800 × 21.800 × 21.800 | 18.000 | 18.000 | 0.000 | 0.000 | 12.442 |
| 02 | 140.800 × 21.800 × 21.800 | 15.876 | 18.333 | 1.000 | 0.363 | 11.274 |
| 03 | 140.800 × 22.500 × 21.850 | 13.776 | 18.667 | 2.000 | 0.743 | 9.952 |
| 04 | 140.800 × 23.800 × 21.850 | 11.732 | 19.000 | 3.000 | 1.141 | 8.501 |
| 05 | 140.800 × 25.100 × 21.850 | 9.806 | 19.333 | 4.000 | 1.550 | 6.950 |
| 06 | 140.800 × 26.400 × 21.850 | 8.202 | 19.667 | 5.000 | 1.968 | 5.308 |
| 07 | 140.800 × 27.700 × 21.850 | 7.065 | 20.000 | 6.000 | 2.394 | 3.595 |

All five regenerated exports pass dimensions, one connected closed solid, manifold edges/vertices, outward face winding and agreement with stored STL normals, positive volume, zero loose vertices and degenerate triangles, and zero BVH intersections between nonadjacent triangles. End/cap displacement is exactly zero and every axial coordinate is unchanged. Central height decreases monotonically, while width, roof difference and actual material-centerline displacement increase monotonically; matching crown/sole meridian vertices independently confirm the 0→1→2→3→4→5→6 mm bow progression. An isolated regeneration into a separate temporary directory reproduced all five STL SHA-256 hashes and passed the same checks. The decoded GIF matches the specified 13-state order and 0.4-second timing.

Visual review shows progressive flattening and a progressively bowed top silhouette without registration or cap jumps. The existing early table-approach motion makes temporal spacing nonuniform: maximum vertex motion is 4.141 mm for 01→02, 2.579 mm for 02→03, then approximately 2.449 mm per step. Frame 02's central sole is 0.144 mm above the actual tabletop; Frames 03–07 contact it. This preserves the approved continuous deformation rather than silently retiming it. The maximum exported table penetration is 0.000000190 mm from float32 rounding, below the stated 0.00001 mm tolerance. The global 0.05 mm Z increase reflects reaching the existing floor below the unchanged cap datum.

Unverified: exhaustive self-intersections involving adjacent/shared-vertex triangles, global local-normal minimum feature thickness, support/nozzle/layer-specific suitability, slicing, strength, warping, physical printing and filmed continuity. Vertical ray sampling follows the displaced central region and verifies the configured 2.5 mm core-thickness threshold; it does not establish a global minimum or guarantee printability. No Bambu Studio/printer operations, commits or pushes were performed.

<details>
<summary>Previous endpoint and progression reviews (historical)</summary>

# Pen Frame 07 — sloped compression and near-side centerline bow

Only Pen Frame 07 was regenerated. Frame 01–06 STL files and saved mesh fingerprints are unchanged; stones and cup `.blend`, STL and preview hashes are unchanged. **Frames 02–06, seven-frame contact sheets and `pen/forward-reverse.gif` are now outdated and await approval of this endpoint.** They were not regenerated or retimed.

Current files: [`models/pen.blend`](../models/pen.blend), [`exports/pen/frame-07.stl`](../exports/pen/frame-07.stl), [`scripts/generate.py`](../scripts/generate.py), and [`pen/tabletop-validation.json`](pen/tabletop-validation.json). The scene embeds the revised source and preserves the previous intermediate generator as `pen-intermediates-tabletop.py`. Frame 01 is visible by default; intermediate objects are explicitly marked outdated in scene metadata. The combined [`validation.json`](validation.json) updates only the pen endpoint and its status.

Review comparisons (Frame 01 left, revised Frame 07 right): [elevated oblique](pen/comparison-oblique.png), [top-down with centerlines](pen/comparison-top.png), [side](pen/comparison-side.png), and [central cross-sectional overlay](pen/comparison-section.png). The top view overlays the measured original blue centerline and revised orange material centerline, with a near-direction arrow. The cross section overlays the actual saved X=0 rings at one shared origin/scale, includes the tabletop, and indicates far→near and downward pressure. It does not independently recenter the displaced section. Preview annotations are temporary render objects and are never saved in the model or exported.

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/generate.py -- --pen-frame07
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/pen_previews.py
```

For isolated geometry reproducibility, append `--output-root /absolute/path` to the first command. Do not regenerate intermediates until endpoint approval. The preview command reads the saved model without saving any geometry.

The saved scene determines longitudinal world +X, tabletop normal +Z, tabletop Z=-0.0500000007 mm, and horizontal near world −Y by projecting the actual camera direction perpendicular to the marker and table normal. The existing oblique camera, lights, object transforms and unchanged end regions are retained. Both images in each rendered pair have identical camera/framing/scale.

Provisional parameters are `centerline_displacement=6.0 mm`, `compression_slope=2.2 mm`, `compressed_height=5.2 mm` (roof-height coefficient, not total section height), and `deformation_intensity=1.0`. The translated centerline follows a compact cubic bow over X=−20…+20 mm, with zero displacement, slope and curvature at the boundary. A near-dependent roof height lowers toward the viewer while the broad sole remains supported; this is a section deformation, not a rotation. Existing 1.8/0.2 mm unequal spreading, restrained folds and the 14 mm flattening plateau are retained. The shared shape function supports continuous t interpolation; no intermediate geometry was generated in this iteration.

| Measurement (mm unless stated) | Frame 01 | Previous Frame 07 | Revised Frame 07 |
| --- | --- | --- | --- |
| Overall bounding box X × Y × Z | 140.800 × 21.800 × 21.800 | 140.800 × 21.800 × 21.850 | 140.800 × 27.700 × 21.850 |
| Longitudinal length | 140.800 | 140.800 | 140.800 |
| Central height | 18.000 | 2.800 | 7.065 |
| Central width | 18.000 | 20.000 | 20.000 |
| Material centerline near displacement | 0.000 | 0.000 | +6.000 |
| Near extent from original centerline | +9.000 | +10.800 | +16.800 |
| Far extent from original centerline | −9.000 | −9.200 | −3.200 |
| Central bottom above tabletop | 1.950 | approximately 0 | approximately 0 |
| Coplanar sole width | 0.000 | 16.629 | 16.629 |
| Coplanar contact area (mm²) | 0.000 | 232.481 | 232.481 |

At X=0 and equal ±5 mm offsets from the moved material centerline, vertical STL ray probes measure far-side roof height 6.396 mm and near-side roof height 4.002 mm above the table: a **2.394 mm downward difference toward near**. The section envelope midpoint is +6.800 mm; the additional 0.800 mm comes from unequal spreading and is distinct from the +6.000 mm material-centerline shift. Matching crown/sole material vertices in the editable mesh independently confirm exactly +6.000 mm translation. Central roof height increases relative to the old 2.8 mm endpoint to make room for the requested wedge. Overall width increases by 5.900 mm and intentionally exceeds the original 21.8 mm cap envelope under the user's revised instruction.

Validation passes: unchanged 140.8 mm axial extent, cap/end vertex displacement exactly zero, all longitudinal vertex coordinates unchanged, one closed connected solid, manifold edges/vertices, consistent outward winding and STL normals, positive volume, no loose vertices or degenerate faces, and zero BVH intersections among nonadjacent triangles. A 15 × 25 vertical ray grid follows the displaced centerline across the functional central region and measures minimum sampled vertical thickness **3.595 mm**, above the configured 2.5 mm threshold. Coplanar contact spans 13.980 mm longitudinally with 2,240 triangles. Minimum exported table clearance is −0.000000190 mm from float32 rounding, within the explicitly stated 0.00001 mm tolerance; no larger penetration is accepted. The existing cap/floor clearance remains 0.05 mm. The previous 0.05 mm extra global height reflects reaching the actual floor without moving the cap/end datum.

Independent regeneration to a temporary directory produces the identical Frame 07 STL SHA-256 (`3d6436db2ba8029e898d0a9f5fcca37c9cee9b38e1f2d30a4f697d0a6e38a2be`) and passes the same checks. Frame 01 remains byte-identical; all protected files and six retained meshes remain unchanged.

Unavailable/inconclusive: exhaustive intersections involving shared-vertex/adjacent triangles, global minimum local-normal feature thickness, nozzle/layer-specific detail, support-free orientation, slicing, physical printing/strength/warping and filmed continuity. Directional core samples do not establish a global minimum thickness or guarantee printability. This is a deterministic solid proxy for crushed plastic, not a shell/material simulation. No printer/Bambu Studio operations, commits or pushes were performed.

<details>
<summary>Previous tabletop and seven-frame review records (historical for pen)</summary>

# Pen approved tabletop-compression progression

Pen Frames 02–06 now interpolate the approved tabletop-compression algorithm at t = 1/6 through 5/6. Frame 01 and Frame 07 STL files remain byte-identical, and both saved endpoint mesh fingerprints are unchanged. Stones and cup `.blend`, STL and preview files are protected by SHA-256 comparisons and remain unchanged. Blender 4.5.15 LTS and Blender MCP inspection confirm the saved seven-frame scene and existing camera.

## Current outputs and commands

- Editable scene: [`models/pen.blend`](../models/pen.blend), with seven interchangeable static meshes, Frame 01 visible, and the current generator embedded. `pen-intermediates-legacy.py` retains the earlier generator source for reference.
- Updated STLs: `exports/pen/frame-02.stl` through `frame-06.stl`. The selective command reads and validates the approved Frame 01 and Frame 07 exports without rewriting them.
- Current oblique progression: [seven-frame contact sheet](pen/contact-sheet.png), individual `pen/frame-01.png` through `frame-07.png`, and [forward/reverse GIF](pen/forward-reverse.gif). The GIF uses exactly 01→02→03→04→05→06→07→06→05→04→03→02→01, 0.4 seconds per state, 5.2 seconds per loop, at 720 × 480. Camera, framing, scale and lights match across all seven renders.
- Endpoint comparisons: [elevated oblique](pen/comparison-oblique.png), [top-down](pen/comparison-top.png), [side](pen/comparison-side.png), [central section overlay](pen/comparison-section.png). Left is Frame 01 and right is Frame 07 in the three rendered pairs. The section overlays blue Frame 01 and orange Frame 07 with the tabletop and separate downward/horizontal arrows.
- Current measurements, mesh checks, endpoint mesh preservation, animation metadata and protected-file digests: [`pen/intermediates-validation.json`](pen/intermediates-validation.json). The combined [`validation.json`](validation.json) updates only the pen record. Earlier endpoint-specific measurements remain in [`pen/tabletop-validation.json`](pen/tabletop-validation.json).
- The earlier `pen/contact-sheet-top.png` and intermediate `frame-02-top.png` through `frame-06-top.png` still show the historical depth-only progression. They were not regenerated in this oblique-preview task. The approved endpoint top/side/section pairs remain valid.

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/generate.py -- --pen-intermediates
```

Use `--no-render --output-root /absolute/path` with this selective command for isolated reproducibility checks. It regenerates only the five intermediate STL files and corresponding editable scene, retaining approved endpoints from the existing scene. The earlier `--pen-frame07` command is for endpoint revisions and is not needed here.

## Intermediate measurements and visual continuity

All dimensions below are measured from exported STL coordinates in millimeters. The cap and endpoints have zero vertex displacement and every longitudinal coordinate is identical across frames. Bounding boxes are 140.800 × 21.800 × 21.800 for Frames 01–02, and 140.800 × 21.800 × 21.850 for Frames 03–07 when the central sole reaches the existing tabletop.

| Frame | Center height | Center width | Near extent | Far extent | Center bottom above table | Sampled minimum vertical thickness |
| --- | --- | --- | --- | --- | --- | --- |
| 01 | 18.000 | 18.000 | +9.000 | -9.000 | 1.950 | 12.442 |
| 02 | 15.467 | 18.333 | +9.300 | -9.033 | 0.144 | 11.145 |
| 03 | 12.933 | 18.667 | +9.600 | -9.067 | 0.000 | 9.676 |
| 04 | 10.400 | 19.000 | +9.900 | -9.100 | 0.000 | 8.064 |
| 05 | 7.867 | 19.333 | +10.200 | -9.133 | 0.000 | 6.338 |
| 06 | 5.333 | 19.667 | +10.500 | -9.167 | 0.000 | 4.509 |
| 07 | 2.800 | 20.000 | +10.800 | -9.200 | approximately 0 | 2.597 |

The contact sheet shows monotonic flattening without position/cap jumps. Motion spacing is deliberately reported as nonuniform: the approved algorithm includes an early approach to the table, so the maximum vertex movement is 4.339 mm for 01→02, 2.678 mm for 02→03, and approximately 2.533 mm for each later step. Frame 02's center still has 0.144 mm clearance; Frames 03–07 contact the table. Uniform t sampling preserves the approved algorithm rather than silently retiming or changing endpoint shapes. No new camera or deformation changes were made.

All five regenerated STLs pass dimensions, one connected closed solid, manifold edges/vertices, face orientation and stored normals, positive volume, zero degenerate triangles, and zero BVH intersections among nonadjacent triangles. Their sampled functional vertical thickness minima range from 11.145 to 4.509 mm, above the 2.5 mm configured threshold. An independent generation into a separate temporary output directory reproduced all five STL SHA-256 digests exactly and passed the same checks. Exhaustive adjacent/shared-vertex intersection checks and global local-normal minimum thickness remain unverified. These directional samples do not establish a global minimum or guarantee physical printability.

## Actual scene coordinates and deformation

Blender MCP inspection measured the marker axis as world (1,0,0), tabletop normal as (0,0,1), and the tabletop at world Z = -0.0500000007 mm. Projecting the actual oblique camera direction onto the table and perpendicular to the marker gives horizontal near direction (0,-1,0). These directions are derived from the saved object/camera/floor transforms and floor vertices; the generator does not treat the slanted viewing-depth vector as the compression axis.

The 40 mm central deformation zone contains a 14 mm maximum-compression plateau. The whole section lowers and flattens to 2.8 mm height, with a broad planar sole. Near-side expansion is 1.8 mm and far-side expansion 0.2 mm: 90% of the 2 mm width increase is toward the viewer. A 20% roof taper toward the near lip and small transition folds create a shallow asymmetric section. Width is deliberately kept within the original 21.8 mm maximum cap envelope. The cap, both ends and every longitudinal coordinate remain unchanged. This remains a solid printable proxy for crushed plastic, not a hollow shell simulation.

| Measurement (mm unless noted) | Frame 01, unchanged | Revised Frame 07 |
| --- | --- | --- |
| STL bounding box X × Y × Z | 140.800 × 21.800 × 21.800 | 140.800 × 21.800 × 21.850 |
| Longitudinal length | 140.800 | 140.800 |
| Center section height above its bottom | 18.000 | 2.800 |
| Center section horizontal width | 18.000 | 20.000 |
| Near extent relative to original centerline | +9.000 | +10.800 |
| Far extent relative to original centerline | -9.000 | -9.200 |
| Center bottom above actual tabletop | 1.950 | approximately 0 |
| Center top above actual tabletop | 19.950 | 2.800 |
| Center width of coplanar sole | 0 | 16.629 |
| Coplanar contact area (mm²) | 0 | 232.481 |

The actual flat contact patch spans 13.980 mm along the marker and comprises 2,240 STL triangles, measured independently through MCP from the exported file. The table-contact tolerance is 0.00001 mm; the minimum exported clearance is -0.000000190 mm (float32 rounding). Vertical rays across a 15 × 25 sample grid in the functional flat region give minimum thickness 2.597 mm. At the nominal plateau transition boundary, triangulation gives a maximum sampled sole clearance of 0.000329 mm; the central coplanar contact patch itself is at the table plane.

The **0.05 mm increase in the global Z bounding box is intentional and reported**: the existing preview floor is 0.05 mm below the original cap datum Z=0. The new sole reaches that actual floor while the cap and endpoints remain fixed. Frame 01's original 0.05 mm cap/floor render clearance and 1.95 mm center clearance are preserved. The revised STL has minimum world Z approximately -0.05 mm; it is not silently shifted upward for export.

## Validation and review status

The approved Frame 07 passes measured dimensions/length, center height/width/near/far extents, positive contact area, no material penetration beyond the stated floating-point tolerance, one connected component, closed/manifold edges and vertices, consistent face winding, agreement with STL normals, no degenerate faces, positive volume, and zero BVH intersections between nonadjacent triangles. The selective intermediate command revalidates both existing endpoints without rewriting them; their STL digests and mesh fingerprints are unchanged.

A separate selective regeneration into a temporary output directory produced the same Frame 07 STL SHA-256 digest and passed validation. The existing oblique camera and lighting are retained. Each rendered comparison pair has identical camera position, rotation, scale and framing. The section uses true mesh rings, a common original-center reference and the actual tabletop; +Y is toward the viewer and +Z is tabletop up.

Checks not completed: exhaustive intersections involving shared-vertex/adjacent triangles; exhaustive local normal thickness and nozzle/layer-specific features; slicing, supports, strength, warping, physical printing and filmed continuity. The directional thickness samples do not establish a global minimum feature thickness or guarantee printability. Generated intermediate previews are available for user review; physical models have not been printed or filmed. No Bambu Studio/printer operations, commits or pushes were performed.

<details>
<summary>Previous seven-frame generation record (historical for pen)</summary>

# Seven-frame stop-motion model sets

Frames 01–07 are provided for pen, stones and cup: 21 models, including 15 new intermediate models. The six approved endpoint mesh objects are retained in the editable scenes; their coordinates are checked against the unchanged procedural shape definitions, and re-exported endpoint STLs are checked against their pre-generation SHA-256 digests. The existing `docs/specification.md` was read and left unchanged; subsequent approved endpoint decisions govern the pen's view-depth compression and the stones hierarchy. Blender 4.5.15 LTS and MCP add-on 1.8 were verified. Generation uses a separate Blender process to preserve the user's original unsaved scene.

## Files and regeneration

The shared generator is [`scripts/generate.py`](../scripts/generate.py). The existing three continuous shape functions and parameters are unchanged. The full set uses the specification's provisional uniform sampling `t = 0, 1/6, 2/6, 3/6, 4/6, 5/6, 1`. No project or Blender Python dependencies were added.

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/generate.py -- --all-frames
```

Optional arguments go after `--`: `--motif pen|stones|cup`, `--no-render`, `--validate-only`, or `--output-root /absolute/path`. Keep `--all-frames` for full-set generation or validation; without it, the legacy endpoint-only mode remains available. `--validate-only` reads the existing STL files without regenerating geometry or scenes. Regeneration overwrites this generator's outputs; use a separate output root to compare reproducibility. Existing camera, world, lights and render settings are reused verbatim. In full-set mode the actual approved endpoint objects are kept and only script-owned intermediate objects are rebuilt. A fresh checkout without model files uses the equivalent procedural filming rig.

| Motif | Editable scene | Exported STLs | Oblique comparison |
| --- | --- | --- | --- |
| Marker | [`models/pen.blend`](../models/pen.blend) | `exports/pen/frame-01.stl` through `frame-07.stl` | [Frames 01–07](pen/contact-sheet.png) |
| Pebbles | [`models/stones.blend`](../models/stones.blend) | `exports/stones/frame-01.stl` through `frame-07.stl` | [Frames 01–07](stones/contact-sheet.png) |
| Cup | [`models/cup.blend`](../models/cup.blend) | `exports/cup/frame-01.stl` through `frame-07.stl` | [Frames 01–07](cup/contact-sheet.png) |

Individual oblique renders are `previews/<motif>/frame-01.png` through `frame-07.png` (21 images). Pen top renders are `previews/pen/frame-01-top.png` through `frame-07-top.png` (7 images), with a separate [top-down continuity sheet](pen/contact-sheet-top.png). All four sheets are labelled and ordered left-to-right, top-to-bottom: 01–04 on the first row, 05–07 on the second. Full-resolution individual renders remain available for closer inspection. The existing endpoint pair `comparison.png` files and cup endpoint top checks are retained.

### Pen viewpoint inspection (geometry unchanged)

Additional preview-only images read the existing `models/pen.blend`; they do not run the model generator or save a `.blend`/STL:

- [Existing elevated oblique camera](pen/comparison-oblique.png): left Frame 01, right Frame 07.
- [Top-down comparison](pen/comparison-top.png): left Frame 01, right Frame 07; X runs horizontally, +Y upward.
- [Central cross-section overlay](pen/comparison-section.png): exact saved vertex rings at X=0, viewed from +X toward -X with +Z up and +Y right. Blue is Frame 01, orange Frame 07. Both outlines share the same datum and scale; the arrow follows the actual camera-derived far-to-near compression normal. Grid spacing is 5 mm.

Reproduce those endpoint diagnostic views with `/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/pen_previews.py`. Its [view-settings.json](pen/view-settings.json) describes the earlier preview-only inspection; its model-file hashes predate the full seven-frame scenes. Endpoint geometry and inspection camera settings remain unchanged. The current all-frame validation and endpoint-preservation records are in `validation.json`.

Each scene contains all seven meshes at the same origin and physical datum. Frame 01 is visible by default. Hide the visible prop and unhide the desired frame in both viewport and render visibility; these are interchangeable static solids, not a deforming animation rig. Cameras, lights and the explicitly named preview floor are staging objects, never part of STL exports. The latest source, parameters and frame/t mappings are embedded in each `.blend`. `stones.blend` also embeds complete parent/child identities, centers and cell areas as `pebble_ancestry_json`. Object coordinates are millimeters; the scene uses metric scale 0.001. STL export disables scene-unit conversion, preserving numeric millimeter coordinates.

## Measurements and checks

Machine-readable results for all 21 STLs, SHA-256 digests, frame/t mappings, endpoint-preservation records and per-step vertex differences are in [`validation.json`](validation.json). Endpoint reference values below are rounded to 0.001 mm; bounding-box axes are X/Y/Z.

| STL | Bounding box (mm) | Functional dimensions (mm) |
| --- | --- | --- |
| pen/frame-01 | 140.800 × 21.800 × 21.800 | Center height 18.000; center width 18.000 |
| pen/frame-07 | 140.800 × 21.800 × 21.800 | Center view-depth 6.500; transverse width 19.999; world-Z extent 15.042 |
| stones/frame-01 | 80.000 × 80.000 × 3.598 | Backing 2.000; relief up to 1.598; 100 coarse cells |
| stones/frame-07 | 80.000 × 80.000 × 3.199 | Backing 2.000; relief up to 1.199; 1,023 fine cells |
| cup/frame-01 | 80.000 × 80.000 × 80.000 | Straight wall 2.000; inner diameter 76.000; bottom 2.400 |
| cup/frame-07 | 80.000 × 80.000 × 80.000 | Straight wall 8.000; inner diameter 64.000; bottom 2.400 |

Validation reads the binary STL back independently of the source mesh, welds exact float32 vertex coordinates, and checks dimensions (0.005 mm tolerance), one connected component, zero boundary/nonmanifold edges and vertices, consistent winding, no loose vertices, no degenerate triangles, agreement between stored STL normals and triangle winding, and positive signed volume. BVH overlap checks cover triangle pairs that share no vertices. Functional section checks measure exported geometry; additional rays sample marker vertical thickness and cup straight-wall thickness. The JSON records the precise scope and each pass/fail result.

Validation is re-run on every exported STL, including all 15 intermediate frames. Pen functional checks use each frame's interpolated near/far section extents, full view-depth and width, plus 41 axial × 33 transverse ray pairs. Cup checks use each frame's interpolated sidewall thickness and the fixed 2.4 mm bottom. Stone checks verify the 2 mm backing and 1–2 mm relief range; reported nominal grain scale is a design proxy, not a measured diameter for every irregular stone. These are sampled directional thicknesses and functional sections, not exhaustive minimum normal thickness. Re-exported endpoint STLs are required to match the six approved hashes exactly.

All 21 STLs passed dimension, closed/manifold, connected-component, orientation and degenerate-face checks: one component per file, zero boundary/nonmanifold edges and vertices, zero winding/normal disagreements, zero degenerate faces and positive signed volume. No nonadjacent BVH intersection pairs were detected. All six approved endpoint STLs remain byte-identical. The complete seven-frame sets were visually inspected in the four contact sheets.

A second full generation into a fresh temporary output root, with rendering disabled, passed all 21 STL checks and produced byte-identical SHA-256 digests for all 21 files. The stones hierarchy digest also matched. This verifies procedural reproducibility independently of the first run's saved intermediate meshes.

| Frame | Pen center view-depth (mm) | Pen transverse width (mm) | Cup wall (mm) | Cup inner diameter (mm) | Stones overall height (mm) |
| --- | --- | --- | --- | --- | --- |
| 01 | 17.999 | 17.999 | 2.000 | 76.000 | 3.598 |
| 02 | 16.082 | 18.332 | 3.000 | 74.000 | 3.436 |
| 03 | 14.166 | 18.666 | 4.000 | 72.000 | 3.365 |
| 04 | 12.249 | 18.999 | 5.000 | 70.000 | 3.399 |
| 05 | 10.333 | 19.332 | 6.000 | 68.000 | 3.320 |
| 06 | 8.416 | 19.665 | 7.000 | 66.000 | 3.223 |
| 07 | 6.500 | 19.999 | 8.000 | 64.000 | 3.199 |

All pen bounding boxes are 140.800 × 21.800 × 21.800 mm; all cups are 80 × 80 × 80 mm. All stones sheets retain an 80 × 80 mm footprint and 2 mm backing. Their maximum height need not decrease monotonically: Frame 03 → 04 rises by 0.034 mm as the maximum moves between blended relief peaks. Grain subdivision, rather than monotonically falling height, is the approved transformation. Minimum sampled pen directional thickness over the seven frames is 3.991 mm; cup wall samples match 2–8 mm and every bottom remains 2.4 mm. No exhaustive local thickness claim is made.

Blender MCP inspection confirmed seven props per saved scene, correct `t` mappings, matching dimensions, identity transforms, zero unapplied modifiers, retained camera settings and embedded generator source matching the repository. Appended inspection scenes are named `pen-seven-frames`, `stones-seven-frames` and `cup-seven-frames`. The user's original live scene is kept active and was not saved over.

Reference-feature checks cover every frame: unchanged marker ends/cap outside X = -20…20 mm and identical axial coordinates; unchanged cup exterior; identical stone XY coordinates and backing/outline. The compression axis has dot product zero with the marker axis. The pen's endpoint section area decreases from 254.367 to 104.725 mm² (41.17% retained); its final depth midpoint is 0.750 mm toward the viewer. Every frame uses the same orthographic camera, framing, lighting, material and render settings within a motif/view. The pen oblique camera remains at (110, -190, 212) mm with scale 177 mm; its top camera is (0, 0, 260), rotation zero, scale 177 mm. The oblique camera's stored rotation projected perpendicular to X gives near normal (0, -0.679765, 0.733430).

## Provisional choices and specification differences

- Marker: a single solid volume with a visual thin-plastic crush effect. Barrel diameter is 18 mm and cap diameter 21.8 mm. Every complete ring in the 40 mm central deformation zone blends into an asymmetric flattened cross section; the central 14 mm plateau has constant compression. In camera-depth coordinates, the near half-depth is 1 mm and the far half-depth 5.5 mm, compared with 9 mm on both sides before compression. The near face is additionally flattened with exponent 0.30, while the far side retains an elliptical arc. The section is displaced 3 mm in the far-to-near direction before applying those asymmetric half-depths. This places the near face at +4 mm and far face at -2.5 mm relative to the original center, with a combined depth of 6.5 mm and depth midpoint +0.75 mm. Lateral displacement is only 1 mm per side, giving 20 mm width. A single shallow 0.25 mm S-fold in each axial transition suggests plastic creasing. There is no axial shortening, rotation of the cross-section basis, twisting or whole-marker bend. All these dimensions are parameters.
- Marker near/far interpretation: "far side more intact" means it retains substantially more cross-sectional rounding (5.5/9 of its original half-depth versus 1/9 on the near side). Its position also changes: the far surface moves about 6.5 mm toward the camera; near-side flattening and restrained lateral spread complete the collapse. There is no closed oval contact footprint or carved pit in the new definition.
- Marker specification difference: the old provisional 2–3 mm *world-Z center extent* is superseded by view-depth compression perpendicular to the pen axis. World-Z center extent is now 15.042 mm; compression is evaluated along the actual camera-derived normal. The cap, endpoints, horizontal orientation and Z=0 resting datum remain unchanged. Physical shell mechanics are not simulated.
- Pebbles: 2 mm backing, 0.25 mm surface grid, seed 42017, nominal 0.30 mm inter-cell inset gap. Best-candidate sites and Voronoi clipping create irregular tightly arranged coarse domains. Two centroid-relaxation passes reduce slivers. Each fixed parent is subdivided into children clipped to its exact boundary; another subdivision supplies fine grains. The persistent hierarchy has 100 → 319 → 1,023 cells. Median equivalent *cell* diameters are 9.164 → 5.009 → 2.780 mm; rounded/inset pebble outlines are smaller and varied, so nominal 8/2.5 mm grain settings are not exact equal stone diameters. Smooth power-norm rounding and small three/five-lobed perturbations produce oval and subtly irregular outlines with natural orientations. These are actual heightfield geometry fused to the backing.
- Pebble progression: `t` smoothly blends the root and first-child relief fields over 0…0.5, then the first and second-child fields over 0.5…1. Frame 01 uses the 100 root cells, Frame 04 the 319 first-level cells, and Frame 07 the 1,023 fine cells. Frames 02–03 and 05–06 contain blended inherited relief fields. Shared ancestral boundaries remain fixed and internal child grooves emerge progressively; sites never migrate or get re-randomized. Smoothstep weights make the definition continuous with zero derivatives at level transitions. Actual photographed continuity remains unverified.
- Pebble provisional adjustment: maximum relief is 1.6 mm for coarse stones and 1.2 mm for fine stones, with 0.88–1.0 deterministic per-stone height variation. The lower fine relief avoids excessively tall narrow features; grain count and footprint size remain the primary visual transformation. Both relief values remain within the specification's 1–2 mm range.
- Cup: straight-wall radial thickness 2 to 8 mm, fixed bottom 2.4 mm, rotational symmetry, no handle or decoration. Rounding radius is 0.25 mm. Rounding reduces the flat horizontal rim span to 1.5 mm / 7.5 mm at the very top; the main sidewall remains 2 mm / 8 mm throughout its straight height.
- Uniform `t` spacing is provisional; pen view-depth decreases linearly from 18 to 6.5 mm and cup sidewall thickness increases in 1 mm increments from 2 to 8 mm. Stone geometry is continuous but visual grain evolution is not linear in `t` because it uses two smooth subdivision stages. No equal-perceived-motion or physical-print claims are made.
- No approved endpoint shape changes or deviations from confirmed overall dimensions are intended; all six endpoint STL hashes are checked during generation.

## Limits of validation

Self-intersection testing excludes pairs sharing a vertex. The constructions also avoid foldovers by using monotonically ordered marker rings, a single-valued stone heightfield, and a simple noncrossing cup profile; this is not an exhaustive numerical intersection test of adjacent triangles. Local minimum thickness was checked only at the reported sections/samples, not at every surface point or in every direction. Tiny relief tips, valleys and the shallow cap seam have not been checked against a nozzle/layer profile.

Support requirements, bridges/overhangs, slicing, warping, strength and physical printing remain unverified. In particular, the marker's horizontal orientation is a filming datum, not a verified support-free print orientation. Digital mesh checks do not guarantee printability. Bambu Studio and the printer were not operated. No commits or pushes were made.

API references used: [Blender Mesh.from_pydata](https://docs.blender.org/api/4.5/bpy.types.Mesh.html), [BVHTree construction, overlap and ray casting](https://docs.blender.org/api/current/mathutils.bvhtree.html). Actual operator properties and Blender version were additionally inspected through MCP in the installed Blender 4.5 instance.

</details>

</details>

</details>
