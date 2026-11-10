# Rolling Wavy Pen — print-set-v2 final QA

- Checked: 2026-11-10T05:18:47.893276+00:00
- Verdict: **PASS**
- Targets: `exports/rolling-wavy-pen/print-set-v2/`, `previews/rolling-wavy-pen/print-set-v2/frame-to-stl.csv`, `models/rolling-wavy-pen-print-set-v2.blend`
- Method: binary STL was reread and its triangles revalidated; Blender's STL importer was also used as a second reader. Source v11 mesh and regenerated mesh fingerprints were checked against the manifest.
- Units: STL has no unit field. Import each file interpreting coordinates as **millimeters** (1 Blender unit = 1 mm).

## STL results

| STL | v11 frame | Dimensions X × Y × Z (mm) | Volume (mm³) | Contact (mm²) | Support margin (mm) | SHA-256 | Result |
|---|---:|---:|---:|---:|---:|---|---|
| `pose-01.stl` | 01 | 141.800 × 13.197 × 13.092 | 16382.916 | 751.952 | 2.744 | `1aae3c251191e9b9cb9a7ae1de19fdc4ee265a28c8e16c9b5c893d85db152fe9` | PASS |
| `pose-02.stl` | 04 | 141.800 × 13.753 × 12.518 | 16382.916 | 751.854 | 2.703 | `5f50f6b1489c5bbca97547a0cd3aa588fe6cf5e9ed16bcbb2557c3331a31d932` | PASS |
| `pose-03.stl` | 08 | 141.800 × 14.212 × 13.092 | 16382.916 | 751.952 | 3.268 | `e63bcbe4160e9b946f0b12fea96088bc908ac21db0deec3c0d903f1ccf81972d` | PASS |
| `pose-04.stl` | 09 | 141.800 × 16.437 × 13.092 | 16382.916 | 751.952 | 4.251 | `e4f6c1c530697aaba300b18aac9ba6e01e88745a272c04008bf2973503197f12` | PASS |
| `pose-05.stl` | 10 | 141.800 × 19.183 × 12.518 | 16382.916 | 751.854 | 5.374 | `17676eb2d06b8ebb2221c224f2a54e6b5f4e1d10fb451954350f2b479949900d` | PASS |
| `pose-06.stl` | 11 | 141.800 × 21.929 × 12.518 | 16382.916 | 751.854 | 6.447 | `daaaf2a74597ddeb82d133e0052c699117e10787e361f2d439be05a06ea4878d` | PASS |
| `pose-07.stl` | 12 | 141.800 × 23.993 × 12.518 | 16382.916 | 751.854 | 7.251 | `938b7f9a3ba3cabfca61ef7a8406e76082427992eced0ba539dd1baed2b6946c` | PASS |
| `pose-08.stl` | 13 | 141.800 × 23.993 × 13.092 | 16382.916 | 751.952 | 7.201 | `ce86da4086f61f3de8f50e2d894913104e289edc411fff26d7d4e21fce6fdc74` | PASS |
| `pose-09.stl` | 16 | 141.800 × 24.454 × 12.518 | 16382.916 | 751.854 | 7.685 | `c03d2dc5834e1a694d2b708ece9b8770d60ef30e489a3e2a4a1679ef5498b5b5` | PASS |
| `pose-10.stl` | 18 | 141.800 × 25.853 × 12.518 | 16382.916 | 751.854 | 8.973 | `98d270b659619449683510d47c291a57b62d4cccbb3f0257113f02a83a032084` | PASS |
| `pose-11.stl` | 19 | 141.800 × 26.685 × 13.092 | 16382.916 | 751.952 | 9.667 | `6ead7c443bb5596d3a46aa8283666fe741e60e331ee11ae7f75c3fad797f58bc` | PASS |
| `pose-12.stl` | 21 | 141.800 × 28.024 × 13.092 | 16382.916 | 751.952 | 9.936 | `75f53846908980bf13ba11cac9038ddfabb3ebdc2d0c388f036006682c3e2c9b` | PASS |
| `pose-13.stl` | 22 | 141.800 × 28.061 × 12.518 | 16382.916 | 751.854 | 9.878 | `30a51c3b55a467fd44d0d31532f83e950e27174f926d4ddeedbfb8f6fad7eee6` | PASS |
| `pose-14.stl` | 25 | 141.800 × 28.410 × 13.092 | 16382.916 | 751.952 | 9.908 | `60ceb2af3b633ca56723e576a71aa7d185c3b49c3c548bde6458d23f63e1e233` | PASS |
| `pose-15.stl` | 27 | 141.800 × 28.714 × 13.092 | 16382.916 | 751.952 | 9.896 | `095d5ad31577f428cfee5a22b99a73ca35123b9f1963366c3ebc0524adbd6898` | PASS |
| `pose-16.stl` | 30 | 141.800 × 27.978 × 12.518 | 16382.916 | 751.854 | 9.842 | `7a591c3b045fd619aae6ef8d530b4c26e17b0a08a9b2f535b1a88b8014bb32ac` | PASS |

All 16 files have finite coordinates, valid binary STL length, nonempty triangle data, the expected X length, and match their v11 fingerprints and recorded hashes. All have one connected component, are watertight/manifold, consistently oriented with positive volume, contain no degenerate triangles, have zero detected non-adjacent BVH overlap pairs, rest at Z=0, and have a positive static support margin.

## 30-frame CSV and placement

- CSV rows: 30; frame IDs 01–30 each occur once: True
- Referenced STLs: 16; usage total: 30; all references exist: True
- CSV rows match manifest transforms: True
- Saved Blender scene: 11/11 checks passed; 16 meshes, 30 placements, and fixed camera verified.
- Scene external references: 0 linked libraries, 0 unresolved image paths.
- The baked roll is retained in each STL. CSV additional rotation is 0°; translations are millimeter filming guides. The tabletop contact side is at Z=0.
- Read [frame-to-stl.csv](../previews/rolling-wavy-pen/print-set-v2/frame-to-stl.csv) for each frame's pose, direction, baked angle, and X/Y/Z placement.

## Source integrity and checks

- v11 blend SHA-256: `54084ab7e007712da9801579f19a68621a9ca9d644222c19e10a9432cea68c9e`; matches print-set manifest: True.
- v11 generator SHA-256: `38522075dd84033c083e075fef632b337cc84bb2409bdaf9c2284adc4e29c10e`; matches print-set manifest: True.
- Per-pose geometry and independent regeneration checks: 16/16 passed.
- CSV checks: 10/10 passed.
- Blender scene checks: 11/11 passed.
- The corresponding v11 pose generator was rerun for every selected frame. Its fingerprint matches the saved v11 mesh; source mesh vertices match STL vertices within float32 coordinate quantization (maximum measured delta recorded in JSON).

## Slicer handoff and limitations

- Import as millimeters; STL does not encode units. Do not apply an additional roll rotation: the approved roll/contact orientation is already baked into the geometry.
- Keep the current axis/orientation for this handoff. This QA does not optimize print orientation or support placement.
- PASS means the checked files are internally consistent and ready for the user's slicer review; it does not guarantee a successful print.
- Not verified: exhaustive minimum wall/feature thickness, slicer support needs, slicer print-time estimate, physical print strength, and actual printing/filming.
- Static support margin does not test vibration, accidental contact, or filming stability. BVH overlap checking is a detector, not an exhaustive proof against all possible self-intersections.

Machine-readable results: `previews/rolling-wavy-pen/print-set-v2/final-qa.json`.
