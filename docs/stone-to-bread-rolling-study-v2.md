# Stone-to-Bread rolling study v2 — Milestone 1

This isolated revision is awaiting visual review. Existing Stone-to-Bread scenes, exports, previews and approvals remain reference assets; Pen, Stones and Cup are unchanged. No pressing, elongation, center pulling, recoil or bread states are generated here.

The provisional complete sequence has 16–18 unique poses: seven compact rolling poses, then separate pressing/elongation and center pulling, one recoil pose, and one preview-only bread pose. The rolling poses remain a 30 mm pebble; horizontal rod formation belongs to the next milestone. Review this milestone before developing those later poses.

## Poses and placement

Local X follows the eventual rod, local positive Y points toward the camera along the tabletop, and Z points upward. They map to world +X, −Y, +Z. Roll is baked around local X, followed by a shallow contact correction. Each STL is centered on the source pebble datum in X/Y and rests at Z=0. Filming Y placement is stored separately in the manifest and Blender object location; it is not baked into STL geometry.

| Pose | Gesture | X rotation (rad) | Near Y placement (mm) | X × Y × Z (mm) | Exposures: deliberate / energetic |
| --- | --- | ---: | ---: | --- | --- |
| r01 | Initial | 0.00 | 0.0 | 30.000 × 25.000 × 20.600 | 3 / 2 |
| r02 | Toward, midpoint | −0.45 | 4.0 | 30.000 × 24.231 × 21.136 | 2 / 1 |
| r03 | Toward, turnaround | −0.90 | 8.0 | 30.000 × 23.532 × 22.801 | 4 / 3 |
| r04 | Away, midpoint | −0.20 | 1.5 | 30.000 × 24.683 × 20.099 | 2 / 1 |
| r05 | Away, turnaround | 0.50 | −5.0 | 30.000 × 24.484 × 22.049 | 4 / 3 |
| r06 | Toward again, midpoint | −0.15 | 1.0 | 30.000 × 24.777 × 20.131 | 2 / 1 |
| r07 | Toward again, end | −0.80 | 7.0 | 30.000 × 23.572 × 22.541 | 5 / 4 |

Playback uses a 12 fps exposure grid. The deliberate version has 22 exposures (1.833 s), and the energetic version 15 exposures (1.250 s), using exactly the same seven poses. GIF centisecond timing rounds cumulative exposure times; the manifest records the actual delays. GIFs loop for inspection; the end-to-start reset is not an additional designed rolling gesture. Holds reuse poses and require no additional printed models.

## Geometry, materials and rendering

One persistent asymmetric pebble surface supplies all seven poses. Broad shoulders and a shallow hollow are actual geometry and move with rotation. The shape is neither independently randomized nor scaled per pose. After rotation, a 1.4 mm lower cap is flattened into a finite sole, with a 1 mm curved transition at its perimeter. This deliberately sacrifices exact rigid rolling to produce independently resting physical props.

The STL and render mesh vertex coordinates are compared before applying scene-only placement. Neutral and realistic rendering switch only the material on the same mesh objects. Natural stone shading uses restrained mottling with material coordinates attached to the original pebble, low specular intensity and microscopic roughness. The fixed orthographic camera is frontal, perpendicular to X, at 50° elevation; scale is 120 mm with no per-pose recentering. The same soft area-light rig, fixed sampling seed and denoising are used throughout. A low-cost 8-sample test precedes 48-sample 800 × 600 renders.

## Files

- Source: [`scripts/stone_to_bread_rolling_study.py`](../scripts/stone_to_bread_rolling_study.py), reusing the existing topology, mesh construction, STL validation and contact-sheet helpers.
- Editable scene: [`models/stone-to-bread-rolling-study-v2.blend`](../models/stone-to-bread-rolling-study-v2.blend).
- Seven printable STLs: [`exports/stone-to-bread/rolling-study-v2/`](../exports/stone-to-bread/rolling-study-v2/), `pose-r01.stl` through `pose-r07.stl`.
- Previews, manifest, validation and reproduction records: [`previews/stone-to-bread/rolling-study-v2/`](../previews/stone-to-bread/rolling-study-v2/).
- Contact sheets: `contact-realistic-front.png`, `contact-neutral-front.png`, `contact-neutral-top.png`, `contact-neutral-side.png`.
- Four GIFs: `rolling-{realistic,neutral}-{deliberate,energetic}.gif`.

Generate with Blender 4.5 LTS:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 8 --python-exit-code 1 --python scripts/stone_to_bread_rolling_study.py
```

Append `-- --geometry-only` for independent geometry regeneration without rendering. All writes are scoped to this revision. The existing validator accepts explicit expected posed bounds and core dimensions; its previous default behavior is unchanged.

## Validation and limitations

All seven poses pass dimensions at the existing 0.1 mm tolerance, watertight/manifold edges and vertices, one component, outward winding and STL normals, positive volume, no degenerate faces and no detected intersections between nonadjacent triangles. Every pose has finite contact area and a uniform-density projected center of mass inside its support hull. Contact areas range from 78.87 to 221.12 mm²; support margins from 1.88 to 6.29 mm. All 39 vertical-core probes hit each solid; the smallest sampled thickness is 14.09 mm. Independent generation verifies STL and mesh hashes. Baseline asset hashes are recorded and checked for preservation.

Adjacent/shared-vertex intersections and exhaustive minimum normal thickness are not verified. Static support is an ideal geometric calculation, not a friction or handling test. No nozzle, layer or support settings were invented; Bambu X1 Carbon is only the existing target printer assumption. Slicer checks, supports, material strength, warping and physical print testing remain unverified. The geometry and timing are a proposal pending visual review; the impression of three rolling gestures still needs artistic assessment.
