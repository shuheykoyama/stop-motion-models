# Stone to Fireworks v3 — Geometry-based natural stone

Awaiting visual review. v1 and v2 are preserved.

The v2 timeline is unchanged: three press/recover cycles, five pulling states, two overlapping recoil/launch states and six airborne states. There are 20 shooting states, 40 held exposures at 12 fps, and a 3.33-second GIF. The same filming placements and physical miniature sizes are used.

## Shared base geometry

The v1/v2 rest surface provides the source topology. Before any deformation, five rounded plane cuts introduce broad, unequal face transitions across the shoulders and top. Six differently sized localized displacements add shallow chips, depressions and swells. They are intentionally clustered and unequal, not random noise distributed uniformly over a sphere. Rounded transitions retain a smooth mesh without low-poly shading or sharp points.

A height-dependent envelope preserves the existing resting sole and blends the changes into the lower surface. The visible sides remain irregular rather than receiving an artificial plinth. The finished rest envelope remains 30 × 25 × 20 mm. Contact area and support are measured again after export.

This single modified source is passed through the existing v2 press/pull/recoil functions. Features therefore remain attached to the same material vertices and deform with the stone. The miniature meshes are physical scaled copies of this base, not CGI object scaling.

All stone renders in this revision use a constant neutral gray material. No noise texture, bump or shader displacement is used to establish the stone character. The v2/v3 rest close-up applies the same neutral material, lighting and scale to both source meshes.

## Outputs

- [Animation](../previews/stone-to-fireworks/v3/sequence-v3.gif)
- [All shooting states](../previews/stone-to-fireworks/v3/contact-sheet-v3.png)
- [Key poses](../previews/stone-to-fireworks/v3/key-poses-v3.png)
- [Top key poses](../previews/stone-to-fireworks/v3/key-poses-top-v3.png)
- [Neutral v2/v3 rest close-up](../previews/stone-to-fireworks/v3/rest-closeup-v2-v3.png)
- [Editable Blender scene](../models/stone-to-fireworks-v3.blend)
- [Candidate STLs](../exports/stone-to-fireworks/v3/)
- [Manifest](../previews/stone-to-fireworks/v3/manifest-v3.json)
- [Validation](../previews/stone-to-fireworks/v3/validation-v3.json)
- [Generator](../scripts/stone_to_fireworks_v3.py)

Generation and preview rendering use Blender 4.5 LTS and EEVEE / Metal on the Radeon Pro 5600M:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 2 --python-exit-code 1 --python scripts/stone_to_fireworks_v3.py
```

## Checks and open production issues

Each exported candidate is checked for dimensions, watertight/manifold structure, one connected component, winding, positive volume, degenerate faces, detected nonadjacent triangle intersections, local resting contact and center-of-mass support. Render/export coordinates are compared. A separate Blender process regenerates the candidates and compares STL SHA-256 hashes. v1 and v2 file hashes are protected during the run.

These are study candidates, not a finalized print set. Global minimum wall thickness and shared-vertex triangle intersections are not exhaustive checks. Slicing, supports, physical strength and printing remain unverified. The airborne filming states still require practical support and removal or compositing, as in v2. No hands, fingers, fireworks or support jig are modeled.
