# Rolling Cube Pen - Final QA

Decision: WARNING. Checked at 2026-11-10T23:04:43.895965+00:00.

Data integrity passes for 43 STL types, 59 props, 61 poses and 74 exposures.
All 72 separated-cube placements pass static support. Phase 1 requires finger holding in 18 poses.
This is not a claim that filming or printing has been physically tested.

## Executed checks

- All saved STL files: binary reader and independent Blender importer, with automatic correction disabled.
- Watertightness, manifold edges and vertices, one component, positive volume, consistent winding and STL normals.
- No degenerate triangles, non-finite vertices or detected non-adjacent BVH intersections.
- Dimensions, bounds, volume and gross volume/bounding-box ratio recorded below and in JSON.
- All source SHA-256 hashes match. Independent assembly into a temporary directory also matches.
- Saved scene reopened separately: surfaces, transforms, CSV, manifest and 59 persistent prop IDs checked.
- All 61 poses and 74 exposures: contact, framing, fixed camera, unit scale, constant keys and no part collisions.
- Adopted review placements match exactly; front/top renders compared to the adopted reference stills.

Finder .DS_Store metadata is excluded from immutable model-asset hashes; any observed metadata changes are recorded in JSON.

## Support and accepted differences

Minimum cube support margin: 0.683997 mm.
Pose 57 roll changes from -84 to -90 degrees; pose 60 changes from -6 to 0 degrees.
The adopted separation-section maximum sampled surface difference is about 0.657 mm.
This is not the maximum over the whole animation: inherited Phase 1 reuse has a known difference up to 1.899 mm.
Unsupported Phase 1 poses: 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20.

## Files

| STL | X x Y x Z (mm) | Volume (mm3) | SHA-256 |
|---|---|---:|---|
| pose-01 | 141.800 x 13.200 x 12.150 | 16459.084 | 7cabbb5cb9175238d64e919777d208d32a9e4c87a0540ad47982c9f2bf9cf7a8 |
| pose-02 | 141.800 x 13.200 x 12.666 | 16495.464 | 69b2895e79e4d658aec142fee842540f979993f9aa1c29d9ba668cddeb5ca1d2 |
| pose-03 | 141.800 x 13.258 x 13.060 | 16606.069 | 50386efdbc66d39b407119c21f9429639e363bb674bfc4431a5279b376580082 |
| pose-04 | 141.800 x 13.337 x 13.153 | 16778.402 | 2b58a45364273e42d29c47a679dbfb9ce93dd56eba2c023f70b2209bdfaa5080 |
| pose-05 | 141.800 x 13.239 x 12.785 | 16979.614 | 2b252ff1479143c72fa14715fd889a3ad93864535bdf0dec975a270b070dffd5 |
| pose-06 | 141.800 x 12.984 x 12.098 | 17175.801 | 96b4a6048878ee35a1fe803155452af38f9bf0a63401b7af317f51d372f6b67a |
| pose-07 | 141.800 x 13.284 x 12.934 | 17523.478 | e104da5a197e7a1d2e79321f8a876e2f52e246bcd621e61ed5e4b549eeeb4e81 |
| pose-08 | 141.800 x 13.867 x 13.784 | 17863.731 | 8520f6cff25eb65fa68375a4cbc8375c3212044571ea5624916cc7ed4785f3ef |
| pose-09 | 141.800 x 14.029 x 13.979 | 18176.120 | c522733c669d04151f16c073e94ce5a9d7a49fcab7bdddc5e8d2deb04eb6096d |
| pose-10 | 141.800 x 13.299 x 13.153 | 18443.736 | 8d774dcfd1357ad40f1373504e1250841bc14d7a47e44550f8e95568607dd7c5 |
| pose-11 | 141.800 x 12.643 x 12.142 | 18584.599 | 9cc575fb079c4398c76091e39d2367e9e1bc36c69f7e96c78203d3044264af7d |
| pose-12 | 141.800 x 13.235 x 13.059 | 18898.758 | ddee9fbd6a98e6a25b0e4058f079d20aa2d80bf09c3e4d936e4791869030dd62 |
| pose-13 | 141.800 x 14.632 x 14.125 | 19000.412 | 14365a811bb79055cb7fba18a87c5af7865ec8eead4f3d5317af7eb87508feba |
| pose-14 | 141.800 x 14.741 x 14.075 | 19096.538 | c2b2e0d48879ba80c556ff21a5862e1ecc7a3872bc7b0fdd9a4c97a85ce70253 |
| pose-15 | 141.800 x 13.087 x 12.717 | 19276.491 | dbc990a8afcb5dcb361997f41787332ca1e90b3da9926309df18b43f8b6ef634 |
| pose-16 | 141.800 x 12.277 x 12.107 | 19543.652 | 5b5a0808037bbc3f263cd0cfb35ba4a8721073cae4c08490ba4ead939af85216 |
| pose-17 | 141.800 x 12.982 x 12.545 | 19358.402 | 8677940e96e84b36c6aa7d7ff0703fdb233202a301723b73702379d920682538 |
| pose-18 | 141.800 x 15.045 x 13.824 | 19149.600 | 40d1619a1160d811b24bff95f9b9632bb9651909ec826757c2b14ec5276a1514 |
| pose-19 | 141.800 x 15.106 x 13.795 | 19125.747 | b89e62db46f756ab0b3789622c508e36d23bf5da988aa9b2b9609c70895f3c30 |
| pose-20 | 141.800 x 12.782 x 12.334 | 19347.916 | 268f282f042e57ffba1a8cbec7c734bd82697a93fb1b224fe17ed211ac1a1cfd |
| pose-21 | 141.800 x 12.006 x 11.908 | 19575.668 | a1832961b11cebf561b4d7d08cc1a1aeb0d2dcf6cd438e65e6af1fb9e4d28ad2 |
| pose-22 | 141.800 x 12.761 x 12.315 | 19340.839 | 1a9824ac1cd1e94ea2b89a057ffe5414b459f3b15b681e782d6b32e0d5d9a45c |
| pose-23 | 141.800 x 15.157 x 13.771 | 19089.059 | cd388bdd4f2708d169a91f1dad589922c9479827a905e79f15e588b7bfcfc349 |
| pose-24 | 141.800 x 15.157 x 13.771 | 19078.550 | f75ed0290e193381730d6de8e80f82ddbb0ec776cd44e2748b2c2c65156745b0 |
| pose-25 | 141.800 x 12.761 x 12.314 | 19301.642 | 982d1d807cc62bf2f2788c49a625d7ee34ed55ca648dfea0fc79e7649328df19 |
| pose-26 | 141.800 x 12.008 x 11.906 | 19485.400 | 6cb94094ba35bfce7812e72872dbaad2006cc776ee897db249148ecb2e4161e7 |
| pose-27 | 141.800 x 12.761 x 12.314 | 19176.603 | 2b8b45d6440df174dcfa2e562fa1561d0c51fe2a7c013feaea219cca9cfbc8dd |
| pose-28 | 141.800 x 15.157 x 13.771 | 18850.659 | ce59f59549455d5f5c2d639f5d27d078098ff6417f82e33e31268edfbff3bc1c |
| pose-29 | 141.800 x 15.157 x 13.771 | 18788.935 | 36cf300479b7bed307342646aa5ad82d4c7ab55495cffd4ed5b9e3a22ec89ade |
| pose-30 | 141.800 x 12.761 x 12.315 | 18981.635 | c1baa82a3c61b3ffa3cf2ed6e720ae916472edf7c14d76078b9feffa30e134a5 |
| pose-31 | 141.800 x 12.006 x 11.908 | 19168.303 | 45138b0f6b3f5e65f06b6c4ee461addbe8cdb03b46ad2889d42e903227943130 |
| pose-32 | 141.800 x 12.761 x 12.315 | 18913.947 | 4e8af00d270276d88cb4121ca135de74d235e78d9063d8b7f6b934daed77fe2b |
| pose-33 | 141.800 x 15.157 x 13.771 | 18655.376 | 177436f24263458dc66a418100a26c835510c66f5e156c187b4f3f3cae8ace98 |
| pose-34 | 141.800 x 15.157 x 13.771 | 18640.831 | c11d7485383756e7a2aabeb30ce7b9fd73333b2df5bb577dc971bcd251a840b8 |
| pose-35 | 141.800 x 12.761 x 12.314 | 18871.265 | 1d0b0f79538d518a95515aa134fb4403471fd289b01144957fbcf40ade44eef9 |
| pose-36 | 11.817 x 12.006 x 11.908 | 1626.550 | 861750df69adc8920da2245d103a8644a2098ecc6d0d780a7277434f3cdbace3 |
| pose-37 | 11.817 x 12.006 x 11.908 | 1635.328 | 6e9f180d663ee000b5dcc6a691c70e2df728ee22dd2060b62608a02923493fba |
| pose-38 | 11.817 x 12.006 x 11.908 | 1630.844 | 38f90c510bf3fcbd261556d677cac123445ffcfbc6c49644b5f5fb500eca1987 |
| pose-39 | 11.817 x 11.817 x 11.717 | 1621.412 | d2c47556039d3d6747910e987ef835ac195be5e5c5324b81238055b4a63f4cbc |
| pose-40 | 11.817 x 15.157 x 13.771 | 1586.858 | 4f63213845bb5c8fca6959b2cddfcdd2e4b62d9da9f990acc1e2ff681353298f |
| pose-41 | 11.817 x 15.157 x 13.771 | 1595.635 | 704f086ea71b9b3ecb995a748acee44c5c00eed479f03d80a7b2bb352e6a523b |
| pose-42 | 11.817 x 15.157 x 13.771 | 1591.151 | d209f9e0a5e4e116b57bc71c9cc4f844845f5806a3a983087f291955383a9024 |
| pose-43 | 11.817 x 15.157 x 13.537 | 1581.719 | 2eb59d03e13f6cb70a39f5127248f3f533c9dd0b6fda3ba16cb8e810c0f2e999 |

## Limited feature assessment and unverified work

Closed solid geometry and overall proportions were checked; exhaustive local wall thickness was not measured.
Existing design details include about 0.25 mm clip relief, 0.22 mm end treatment and narrow grooves.
These are design parameters, not measured minimum wall thicknesses. Their slicer reproduction is unverified.
No repair, reinforcement or rescaling was applied. STL is unitless: import as millimeters at 100% scale.
Filming contact orientation is not necessarily the best printing orientation.
Finger holding, dynamic stability, tiny-gap placement, slicing, supports, print success and physical filming remain unverified.

[Filming and printing guide](rolling-cube-pen-print-set-v3.md)
[Machine-readable QA](../previews/rolling-cube-pen/print-set-v3/final-qa.json)

STL importer API reference: [Blender 4.5 documentation](https://docs.blender.org/api/4.5/bpy.ops.wm.html#bpy.ops.wm.stl_import).
