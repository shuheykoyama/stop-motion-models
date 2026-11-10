# Rolling Wavy Pen storyboard study v2

Status: visual review pending. This revision keeps the v1 study intact and carries the centerline deformation across the complete pen, including cap, barrel, seam, and tip. The common longitudinal parameter drives every section, so the cap no longer remains straight. The cap diameter step and clip relief are retained and follow the local section frame.

The four stages are straight, one-sign-curvature bow, gentle multi-lobe wave, and stronger irregular wave. Each has a main and opposite printed resting pose. Opposite poses rotate 180 degrees around the pen's longitudinal axis and use the existing integral tabletop sole correction. The centerline arc length is designed to remain 141.8 mm; endpoint distance and axis-aligned bounds vary by pose and are recorded in `previews/rolling-wavy-pen/storyboard-study-v2/validation.json`.

Eight printable candidates are exported under `exports/rolling-wavy-pen/storyboard-study-v2/`. The black and neutral renders, top views, comparison sheets, and GIFs are stored under `previews/rolling-wavy-pen/storyboard-study-v2/`. The editable Blender scene is `models/rolling-wavy-pen-storyboard-study-v2.blend`. Reproduce with Blender 4.5 LTS using `blender --background --python scripts/rolling_wavy_pen_storyboard_study_v2.py`; add `-- --output-root /tmp/repro --geometry-only` for isolated geometry regeneration.

Validation covers mesh closure/manifold topology, connected components, winding and normals, degenerate triangles, detected non-adjacent BVH intersections, tabletop contact area, and center-of-mass support. Exhaustive local wall thickness, slicer support behavior, and physical print testing are not performed. Geometry and previews are the same mesh; all four stages remain pending visual approval.
