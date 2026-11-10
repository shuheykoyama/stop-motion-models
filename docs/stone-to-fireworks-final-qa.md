# Stone to Fireworks - Final STL QA

Final verdict: **PASS**. Checked at 2026-11-10T15:26:44.015976+00:00.

This verdict permits proceeding to slicer inspection; it does not certify successful FDM printing. No original STL, scene, animation or earlier study was modified.

## Scope

14 print-set-v1 STLs, its frame-to-stl CSV, manifest, validation, saved Blender scene and reproduction script. Approved v3 scene, generator and source STL files provide the geometric reference. Blender 4.5.15 LTS was used for read-only geometry checks; no rendering or slicing was performed.

## Stored STL results

| STL | v3 frame | X x Y x Z (mm) | Volume mm3 | Contact mm2 | Support margin mm | Result |
|---|---:|---|---:|---:|---:|---|
| pose-01.stl | 1 | 30.000 x 25.000 x 20.000 | 7837.513 | 115.237 | 4.612 | PASS |
| pose-02.stl | 2 | 30.004 x 25.000 x 18.233 | 7217.499 | 115.237 | 4.436 | PASS |
| pose-03.stl | 4 | 30.005 x 25.000 x 18.110 | 7105.323 | 115.237 | 4.400 | PASS |
| pose-04.stl | 6 | 30.004 x 25.000 x 18.150 | 7142.807 | 115.237 | 4.412 | PASS |
| pose-05.stl | 8 | 30.022 x 27.989 x 18.127 | 8148.644 | 136.110 | 4.903 | PASS |
| pose-06.stl | 9 | 30.028 x 31.979 x 17.603 | 8897.333 | 162.340 | 5.109 | PASS |
| pose-07.stl | 10 | 30.033 x 36.973 x 17.118 | 9763.515 | 195.219 | 5.112 | PASS |
| pose-08.stl | 11 | 30.036 x 42.965 x 16.756 | 10772.661 | 234.402 | 5.099 | PASS |
| pose-09.stl | 12 | 30.039 x 49.960 x 16.441 | 11812.721 | 280.212 | 5.071 | PASS |
| pose-10.stl | 13 | 30.014 x 33.772 x 18.552 | 9747.323 | 174.439 | 5.070 | PASS |
| pose-11.stl | 14 | 30.000 x 23.753 x 21.355 | 7909.099 | 112.532 | 4.284 | PASS |
| pose-12.stl | 17 | 19.500 x 16.250 x 13.000 | 2152.377 | 48.688 | 2.998 | PASS |
| pose-13.stl | 18 | 12.000 x 10.000 x 8.000 | 501.601 | 18.438 | 1.845 | PASS |
| pose-14.stl | 19 | 7.500 x 6.250 x 5.000 | 122.461 | 7.202 | 1.153 | PASS |

## SHA-256

```text
pose-01.stl  d2e220a228433dceee7d213ed38167a96efeb8b0b9206e0dd0c70ca5a4718df0
pose-02.stl  6b17454064878343ffa541086c8ba4afb4ed3481f36dff5245e3d2423abe9d77
pose-03.stl  f6ad12a4d003c7197a32bc52e4bc1baba2611a3c14351af2631af932f19b0da9
pose-04.stl  67fdf6327d76c246033ba9c49424fe9a28ec76e616c4a5d7ce7574db11f48814
pose-05.stl  134baba0ee4e8aaf1438409e25c5040ee1f6247325b5c5bdcaae4fd4ebc36991
pose-06.stl  a9470712ceab3bb13246085d2c2c48534d6c03b5667f0325cdbce89e7a732d72
pose-07.stl  5427b5f9091b8c690e6ba401ea8a492defbf5e43fd4fe285b303f357b3b15298
pose-08.stl  febe4f29d38b359ac521194bbe0f2c985588d630a2d684a0c9ec7296548e1056
pose-09.stl  ebedfdaee7eb348ffb34b43f88069aa7d3338fd0be3f559ad75d0cfbf998367c
pose-10.stl  77955df694f7500a06e0e597fffd41028b9e7bf81d7dd808b50a1f01fbdcb687
pose-11.stl  e65d9e527fab5a0ec6744e1e732a9ca2e3f5a93c5e6f2c9b21eef379a9d427f3
pose-12.stl  126fe0e08f25c809a3f2b48608e6d8e3aa21756717fa73d27ae75ee2ac68becd
pose-13.stl  57b4fad426373c2d27c78d9c55e662f2704111b240d3f44bf29a4acb80da9264
pose-14.stl  5cfd433e0b51ba800515e2bd7ec9b1ace0f7b33b1d495f6ab676c9043dcbc64f
```

## Integrity and v3 identity

The stored binary STLs were parsed again and imported independently with Blender native STL import. Coordinates, triangle counts and canonical surfaces agree. Fresh topology, orientation, volume, degeneracy, nonadjacent BVH intersections, dimension, contact and support checks are recorded per file in final-qa.json. Source scene fingerprints and canonical surfaces match. The v3 generator independently regenerated all 14 shapes into temporary STLs in this QA process; byte hashes and source mesh fingerprints match. STL float32 coordinates preserve the approved scale.

## Miniature detail and thickness

The 65%, 40% and 25% meshes retain the scaled rest geometry within float precision. Edge-length percentiles and minimum triangle areas are recorded to describe actual mesh resolution; no zero-area or collapsed geometry was detected. The smallest model is 7.5 x 6.25 x 5 mm. Its sampled vertical core minimum is 3.956 mm. This is not a global minimum normal thickness proof. Shallow submillimeter relief is intentional and may not survive FDM resolution. No nozzle, layer height or guaranteed minimum printable feature is assumed.

## Tabletop filming and CSV

The actual saved tabletop plane was derived from its world-space vertices. For all 40 exposures, transformed stone vertices were measured against that plane. The minimum world clearance is zero, contact area is positive, and the uniform-density center-of-mass projection is inside the world contact hull. This includes the recoil/flight shooting states 13-20. Grounding is therefore checked from geometry, not merely a Z placement parameter. No aerial filming supports are required by this layout. Physical stability and friction remain untested.

The CSV contains frames 1-20 exactly once, references all 14 STLs, and has usage totaling 20. Positions, rotations, dimensions, source frames, reuse flags and exposure starts match the manifest. Each shooting state holds for two exposures, totaling 40 at 12 fps. The saved scene has exactly the expected stone/floor mesh objects, constant held animation, no shape-key/modifier deformation, unit scales and a fixed camera.

## Preview provenance

The original approved GIF was not changed. Reassembly from the manifest PNG paths and exposure counts in a temporary directory matches the saved GIF byte-for-byte: 20 states, 3.33 seconds after centisecond rounding. Its hash also matches the prior validation record. Saved-scene mesh assignments and all 40 exposures agree with the manifest/CSV. This verifies stored provenance and assembly; it is not a new image-to-scene render comparison. No hands, fingers or fireworks occur among the scene meshes.

## Bambu Studio handoff

Import STL as millimeters. Check actual dimensions, especially pose-14. Inspect the miniature relief at the intended nozzle/layer profile. Review layer continuity, local thin areas, adhesion, overhangs and support needs. Filming resting orientation is not necessarily the optimal printing orientation. Verify print time/material estimates in the slicer rather than treating them as measured here. Printing and physical tests are the user workflow.

## Unverified conditions

- Exhaustive global minimum normal wall thickness and minimum feature size.
- Intersections involving faces sharing vertices are excluded by the BVH check.
- Slicer checks, printing support requirements, optimal printing orientation, print duration and actual printing.
- Physical filming placement, lighting, friction, real printed center of mass and stability.

The full machine-readable evidence is [final-qa.json](../previews/stone-to-fireworks/print-set-v1/final-qa.json). The audit can be repeated using `Blender --background --threads 2 --python-exit-code 1 --python scripts/stone_to_fireworks_print_set_v1_qa.py`. It writes only the two QA reports and temporary verification files.
