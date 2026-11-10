# Rolling Wavy Pen storyboard study v1

Status: visual review pending. This study preserves the earlier eight-pose sequence in `sequence-v1`.

The left four rows of the supplied storyboard define the shape stages: straight, a single bow, several gentle alternating bends, and larger irregular bends. The black 141.8 mm pen retains an approximately 11.9 mm shaft, a 13.2 mm cap, and an integral clip relief. It has no white band, text, or logo.

Each stage has a main and opposite resting pose. The opposite pose places the shaft centerline and cross section 180° around the longitudinal axis, then reapplies the tabletop contact correction. These are separate printable solids because a rigidly rotated original sole would not rest stably. The cap follows the tangent at the shaft seam and remains straight. Film placement is stored on the Blender objects and omitted from the STL coordinates.

The main representative STLs are in `exports/rolling-wavy-pen/storyboard-study-v1/` as `straight-main.stl`, `curved-main.stl`, `wavy-main.stl`, and `highly-wavy-main.stl`. The four `*-opposite.stl` files support the rolling comparison. All eight are study print candidates; the final animation frame count and print count remain undecided.

The fixed camera contact sheets and GIFs are in `previews/rolling-wavy-pen/storyboard-study-v1/`. The editable scene is `models/rolling-wavy-pen-storyboard-study-v1.blend`. Reproduce with Blender 4.5 LTS using `blender --background --python scripts/rolling_wavy_pen_storyboard_study.py`. Use `-- --output-root /tmp/repro --geometry-only` for independent STL regeneration.

The validation JSON records dimensions, STL and mesh hashes, topology, detected non-adjacent intersections, tabletop area, and projected center-of-mass margin. Exhaustive minimum feature thickness, slicing/support behavior, and physical printing remain unverified. The shaft and clip are a single solid; hollowing and split assembly were not introduced for this study.
