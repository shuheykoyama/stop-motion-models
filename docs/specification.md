# Stop-Motion 3D Model Specification

## 1. Purpose and scope

Create three families of physical props for stop-motion animation: a collapsing capped marker, a pebble-relief sheet with changing grain size, and a cup with thickening walls. Each family has seven interchangeable shapes, for **21 final models**. The animation is filmed from an elevated oblique angle. Reverse playback reuses the seven photographed states; no extra reverse models are necessary.

The deliverable is reproducible Blender geometry, editable `.blend` scenes, preview images, and STL files. The user handles Bambu Studio, slicing, printing, and physical testing. Target printer: **Bambu Lab X1 Carbon**.

**Current status (2026-11-07): Pen, Stones and Cup Frames 01–07 are visually approved and final: all 21 models. Preserve their geometries and finalized outputs; further changes require a separate user request.** Stones approval applies to the revised intermediate progression below. See the [project index](../README.md) for files and the [validation record](../previews/validation.json) for all final asset hashes.

## 2. Status conventions

- **Confirmed**: an explicit project decision; preserve unless the user changes it.
- **Provisional**: a starting value or implementation proposal; expose it as a parameter, evaluate visually and geometrically, and report changes.
- **Undecided**: do not present as an agreed requirement; select a reasonable prototype value only if necessary and document the choice.

## 3. Requirements shared by all motifs

- **Confirmed:** Seven variants per motif, named `frame-01` through `frame-07`. The first and last represent the two extremes of one continuous transformation.
- **Confirmed:** The photographed props are swapped between exposures; each STL must represent one independently printable object. Transformations are *not* required to be mechanically deformable.
- **Confirmed:** Render previews from a consistent elevated oblique viewpoint. Keep the camera, framing, scale, and lighting fixed within each motif.
- **Confirmed:** Use Blender 4.5 LTS and procedural Blender Python (`bpy`). Keep generators reproducible and use Blender MCP for interaction or inspection when available.
- **Confirmed:** State physical dimensions in millimeters. STL has no intrinsic units: exported vertex coordinates must be in millimeters and verified after export.
- **Confirmed:** Produce connected, closed geometry with actual surface relief/deformation (not shader-only effects). Check dimensions, connected components, manifoldness, normals, and degenerate faces; check self-intersections and local minimum thickness where feasible.
- **Confirmed:** Preserve a stable object origin, orientation, placement datum, and unchanged visual features across all seven variants of a motif. Avoid apparent position jumps when replacing props.
- **Provisional:** Begin with a normalized deformation parameter `t` taking values `0, 1/6, 2/6, 3/6, 4/6, 5/6, 1`. Adjust spacing only after visual review.
- **Implementation choice:** Generate seven variants from one definition per motif; fixed random seeds for procedural detail. Prioritize visual continuity over physical simulation.
- **Printing caveat:** Digital mesh checks do not guarantee printability, strength, or print time. Do not claim physical print validation.

## 4. Motif A — Collapsing capped marker

### Confirmed

- A marker-like prop with the **cap attached/closed**; no exposed nib, no detachable cap, and no separate uncapped variant.
- Reference shape: a broad permanent marker (similar in proportions to Zebra Hi-Mckee), not a precise commercial product replica.
- Overall length: **140.8 mm**.
- Undeformed maximum diameter and unchanged cap diameter: **21.8 mm**. The approved deformed body may exceed this envelope; final Frame 07 overall width is **27.7 mm**.
- `frame-01`: uncrushed marker.
- `frame-07`: center locally pressed downward and pushed from the far side toward the near side along the tabletop. The upper surface slopes downward toward near while the material centerline bows toward the viewer; the near-side sole is supported by the table.
- Maintain overall length, the cap, both ends, and their alignment. Concentrate changes around the middle.
- The compression should read as localized flattening with plausible transitions and optional folds, **not** merely a uniform narrowing of a cylinder.

### Approved implementation and measurements

- Deformation zone: **40 mm**, with a **14 mm** flattening plateau; source barrel diameter **18 mm**. Preserve the current cap detailing, folds and solid printable geometry. This is a visual proxy for thin plastic, not a hollow-shell simulation.
- Final central section: **7.065 mm high × 20.000 mm wide**, replacing the earlier provisional 2–3 mm height. Material centerline displacement is **6.000 mm toward near**; this is separate from the **6.800 mm** section-envelope midpoint created by unequal spreading.
- At equal ±5 mm offsets from the moved central material line, the far/near roof heights above the tabletop are **6.396/4.002 mm**, a **2.394 mm** difference. Near/far section extents relative to the original centerline are **+16.800/−3.200 mm**.
- Frame 01 bounding box: **140.800 × 21.800 × 21.800 mm**. Final Frame 07: **140.800 × 27.700 × 21.850 mm**. Longitudinal coordinates, cap and unchanged ends are identical across all frames.
- Frame/t sampling is fixed for this approved sequence: `0, 1/6, 2/6, 3/6, 4/6, 5/6, 1`. Central material displacement progresses **0→1→2→3→4→5→6 mm**. Height decreases, and width and far/near roof difference increase, monotonically.
- Directions are derived from the saved scene. In that scene, the longitudinal axis is world +X, tabletop up is +Z, and horizontal near is −Y. The actual preview floor is at **Z=−0.0500000007 mm**, below the original cap datum Z=0. Preserve this datum rather than repositioning exports. Frame 02's central bottom remains **0.144 mm** above the table; Frames 03–07 contact it. The existing early table approach makes the first step larger than later steps; this timing is part of the approved sequence.
- The configured functional core-thickness threshold is **2.5 mm**. Final Frame 07's sampled minimum vertical thickness is **3.595 mm**, not an exhaustive global minimum or a shell wall thickness. Full measurements and unverified checks are in the [preview guide](../previews/README.md).

## 5. Motif B — Pebble-relief sheet

### Confirmed

- Square footprint: **80 × 80 mm**.
- One piece: all pebble-like forms are joined to a continuous backing sheet; no loose stones.
- Surface should evoke densely arranged natural stones in a karesansui-style garden.
- `frame-01`: visibly coarse stones. `frame-07`: visibly fine stones.
- Communicate the transformation **primarily through pebble size**, not through a change of material, color, or mere bump amplitude.
- Keep the square outline, placement datum, and base thickness consistent across frames.

### Provisional / undecided

- Backing thickness: **2.0–2.4 mm**, with an initial test value of **2.0 mm**. Increase if print preview or physical handling indicates insufficient strength or warping.
- Representative stone size: **8.0 mm** at `frame-01` down to **2.5 mm** at `frame-07`.
- Pebble relief above the sheet: roughly **1–2 mm**, adjusted if fine stones fail to read or become unprintable.
- Prefer a structured or hierarchical subdivision so the progression appears related rather than random. If overly complex, prioritize clear progressive grain-size changes and deterministic generation.
- Stone shapes should have readable boundaries but remain fused to the backing. Avoid isolated solids and very narrow connections.

### Approved final progression

- Retain the existing deterministic hierarchy, fixed seed, site positions, pebble shapes, 80 × 80 mm outline and 2 mm backing. Frames 01, 04 and 07 are unchanged.
- Resample only Frames 02, 03, 05 and 06 by inverting the existing smoothstep easing so child-relief blends progress through 0%, 35%, 70% and 100% within each of the two hierarchy stages. The slightly shorter final blend compensates for the stronger visibility of fine grooves near a hierarchy landmark. This reduces the earlier large middle step and strengthens the final step without changing the endpoint shapes or the 400 ms preview timing.
- [`scripts/stones_progression.py`](../scripts/stones_progression.py) calls the unchanged geometry definition in `scripts/generate.py`; this preserves the finalized Pen/Cup generator source. The final sampler is embedded in `models/stones.blend`. The user approved these sample positions and all seven output shapes.
- User's final review: coarse-to-fine transformation reads clearly; 02→03 is more natural; 05→06 remains one of the larger changes but is acceptable; 06→07 remains distinguishable; no positional or boundary jumps are visible. Preserve this accepted variation rather than further equalizing it.

## 6. Motif C — Thickening cup

### Confirmed

- Ordinary cup with a **closed bottom** and **open top**.
- Height: **80 mm**.
- Outer diameter: **80 mm**, fixed across all seven frames.
- Adopt **A-2: the entire sidewall thickens**, not just the rim.
- Make the interior diameter smaller as the walls thicken; maintain the exterior silhouette, cup height, and bottom position.
- `frame-01`: thin walls. `frame-07`: thick walls.
- The intended gesture is clockwise tracing around the rim to thicken the cup, and counterclockwise tracing to reverse it. Gesture direction is conveyed in filmed playback, not encoded in an individual STL.
- Camera viewpoint: elevated oblique, with enough interior visible to read the wall-thickness change. A top-down check is also useful.

### Approved implementation

- Sidewall thickness: **2, 3, 4, 5, 6, 7, 8 mm** across Frames 01–07, giving straight-wall inner diameters **76, 74, 72, 70, 68, 66, 64 mm**. Outer diameter and height remain **80 mm**.
- Bottom thickness: **2.4 mm**, held constant across variants.
- Rim rounding: **0.25 mm**, held constant. All existing Cup geometry, STL files and review previews are final and preserved.
- A simple rotationally symmetric cup is sufficient initially; avoid unnecessary decorative detail.

## 7. Generation and review workflow

### Initial prototype (historical, completed): only six models

Generate only the endpoint variants:

- `pen/frame-01.stl` and `pen/frame-07.stl`
- `stones/frame-01.stl` and `stones/frame-07.stl`
- `cup/frame-01.stl` and `cup/frame-07.stl`

For each motif, save its reusable generator in `scripts/`, editable Blender scene in `models/`, STL exports under `exports/<motif>/`, and comparisons in `previews/`. Report the exact paths, measured STL bounding boxes, mesh checks performed, unverified checks, and any deviations from provisional values.

### Review criteria

1. **Marker:** Does the center look crushed/flattened like plastic rather than merely tapered? Are the recognizable cap and ends unchanged?
2. **Stone sheet:** Is the difference in grain size immediately readable? Are pebbles integrated into the sheet, with meaningful boundaries?
3. **Cup:** Can the viewer perceive a substantial change in wall thickness from an elevated oblique view while the exterior stays fixed?
4. **All:** Are positioning, scale, and unchanged features stable between endpoint frames? Are the STL dimensions and mesh quality acceptable for further print preparation?

After review and explicit approval, generate `frame-02` through `frame-06` for each motif, check interpolation and progression, and export the full set of **21 STLs**. Reverse animation is produced during video editing using the filmed sequence `01→02→03→04→05→06→07→06→05→04→03→02→01`.

The existing output sets now contain all 21 STLs. All three seven-frame sequences have received final visual approval; their contact sheets and 13-state forward/reverse GIFs are current. Preserve their assets and use an isolated output root for any reproducibility work. Earlier endpoint/intermediate review instructions are historical and do not authorize changes to finalized motifs.

## 8. Non-goals

- Do not operate Bambu Studio or the printer.
- Do not optimize or promise exact print duration without slicing data.
- Do not simulate real plastic deformation or actual stone crushing unless later requested.
- Do not generate the five intermediate variants before endpoint review.
- Do not add a second marker style or separate marker-tip variants.
