# Repository cleanup - 2026-11-15

Branch main, HEAD 3f118deb61327492acacc3a95a9c6be86d187aa8. Tracked tree initially clean and synchronized. No commit, push, history rewrite or LFS changes.

## Actions

Deleted 31 files, 678,587 bytes: OS metadata and unreferenced Python bytecode only.
[Inventory CSV](repository-cleanup-inventory.csv) lists every pre-cleanup working-tree file, A/B/C/D classification, exact deletion path/reason, Git state, size, hash, literal text references and duplicate group.
All studies, model assets, images, print projects and ZIPs were retained. Bytecode named in historical preservation snapshots was conservatively retained. The small virtual environment was retained. Existing ignore rules already cover OS metadata, bytecode and Blender backups.

## Before and after

Regular files only; symlinks excluded. Sizes are logical bytes, not APFS shared-block or compressed physical disk usage. Git internals were not cleaned. After totals include the README edit and two new report files.

| Metric | Before | After |
|---|---:|---:|
| Working-tree regular files, excluding .git | 2741 | 2712 |
| Untracked files | 1722 | 1724 |
| Ignored files from Git listing | 54 | 23 |
| Working tree MiB | 3,416.08 | 3,416.85 |
| .git regular files | 1063 | 1063 |
| .git MiB | 1,188.31 | 1,188.31 |
| All regular files including .git | 3804 | 3775 |
| Total logical MiB including .git | 4,604.39 | 4,605.17 |

## Directory inventory before cleanup

| Directory | Files | MiB | Tracked / untracked / ignored |
|---|---:|---:|---|
| models | 37 | 1,510.39 | 20 / 17 / 0 |
| exports | 370 | 814.98 | 201 / 164 / 5 |
| previews | 2219 | 1,089.04 | 680 / 1530 / 9 |
| scripts | 68 | 1.47 | 40 / 6 / 22 |
| docs | 24 | 0.14 | 19 / 5 / 0 |
| .venv | 14 | 0.03 | 0 / 0 / 14 |

## Classification

| Class | Files | MiB | Treatment |
|---|---:|---:|---|
| A | 729 | 1,105.70 | Retain official assets, PNGs, source, docs and print projects |
| B | 463 | 834.49 | Retain tracked history, fixed inputs, referenced bytecode and environment |
| C | 31 | 0.65 | Delete OS metadata and unreferenced bytecode |
| D | 1518 | 1,475.25 | Retain unclear untracked history pending approval |

Literal references are evidence, not a complete dependency graph. No text match does not prove that dynamically computed paths are unused. B/D assets were not deleted.

## Official asset verification

75 STL hashes match existing Final QA/final manifests: Pen/Stones/Cup 7 each, Fireworks 14, Wavy 16, Cube 12, Bread 12.
Every surviving hashed baseline file except the intentionally updated README is byte-identical. Scenes, GIFs, CSVs, scripts, print projects and source inputs were preserved. Existing LFS configuration and both Wavy Blend objects were retained.
Primary PNG counts verified: Fireworks tabletop 20, Cube v4 61, Wavy v11 30, Wavy print reproduction 30, Bread realistic front 13. Cube ZIP passes CRC validation and contains 61 PNGs.
Cube PNGs currently reside in rolling-cube-pen-frames/, rather than the future generator output frames/. No move or regeneration was performed. README now links the actual filming frames and reproduction sources.
Some final PNGs and print projects are local/untracked: GitHub alone does not restore every local filming asset. They were protected, not staged.

## Print projects retained

| Path | MiB | State |
|---|---:|---|
| exports/stone-to-fireworks/print-set-v1/stone-to-fireworks.3mf | 12.29 | untracked |
| exports/rolling-wavy-pen/rolling-wavy-pen.3mf | 4.99 | untracked |
| exports/rolling-cube-pen/print-set-v4/rolling-cube-pen.3mf | 3.10 | untracked |

3MF files may preserve actual print layouts/settings and are not redundant merely because STLs exist. They were not opened in Bambu Studio. Git inclusion remains a separate decision. No .blend1 or similar backup was found.

## Deferred candidates, descending size

Only D files are aggregated below. These are review candidates, not instructions to delete the entire named directory: tracked fixed inputs and protected outputs can share these directories.

| Candidate scope | D files | MiB |
|---|---:|---:|
| previews/rolling-cube-pen/print-set-v2 | 306 | 153.96 |
| exports/rolling-cube-pen/print-set-v1 | 61 | 94.63 |
| previews/rolling-cube-pen/print-set-v1 | 192 | 88.46 |
| models/rolling-wavy-pen-storyboard-study-v10.blend | 1 | 74.68 |
| models/rolling-wavy-pen-storyboard-study-v8.blend | 1 | 74.20 |
| models/rolling-wavy-pen-storyboard-study-v6.blend | 1 | 71.18 |
| models/rolling-wavy-pen-storyboard-study-v7.blend | 1 | 63.87 |
| previews/rolling-cube-pen/print-set-v3 | 159 | 56.22 |
| exports/stone-to-fireworks/v2 | 14 | 43.41 |
| models/rolling-wavy-pen-storyboard-study-v5.blend | 1 | 39.59 |
| previews/rolling-wavy-pen/storyboard-study-v6 | 76 | 38.18 |
| models/rolling-wavy-pen-storyboard-study-v9.blend | 1 | 37.65 |
| previews/rolling-wavy-pen/storyboard-study-v2 | 31 | 33.09 |
| previews/rolling-wavy-pen/storyboard-study-v5 | 47 | 31.58 |
| models/rolling-cube-pen.blend | 1 | 30.95 |
| models/rolling-cube-pen-print-set-v1.blend | 1 | 30.62 |
| previews/rolling-wavy-pen/storyboard-study-v3 | 18 | 30.02 |
| models/rolling-wavy-pen-storyboard-study-v4.blend | 1 | 29.89 |
| models/rolling-cube-pen-print-set-v2-tabletop.blend | 1 | 27.39 |
| models/rolling-cube-pen-print-set-v2.blend | 1 | 27.06 |
| previews/rolling-wavy-pen/sequence-v1 | 28 | 24.28 |
| previews/rolling-cube-pen/frames | 61 | 22.76 |
| previews/rolling-wavy-pen/storyboard-study-v4 | 38 | 22.00 |
| exports/rolling-wavy-pen/print-set-v1 | 12 | 20.98 |
| previews/rolling-wavy-pen/storyboard-study-v7 | 66 | 19.86 |
| previews/rolling-wavy-pen/storyboard-study-v1 | 17 | 18.77 |
| previews/rolling-wavy-pen/storyboard-study-v8 | 124 | 16.32 |
| models/rolling-wavy-pen-print-set-v1.blend | 1 | 15.00 |
| exports/rolling-wavy-pen/sequence-v1 | 9 | 14.01 |
| exports/rolling-wavy-pen/storyboard-study-v1 | 9 | 14.00 |
| exports/rolling-wavy-pen/storyboard-study-v2 | 9 | 14.00 |
| previews/stone-to-fireworks/v2 | 32 | 13.56 |
| models/rolling-wavy-pen-sequence-v1.blend | 1 | 10.73 |
| models/rolling-wavy-pen-storyboard-study-v2.blend | 1 | 10.73 |
| previews/rolling-wavy-pen/print-set-v1 | 14 | 10.42 |

## Exact duplicates

101 SHA-256 duplicate groups found. Retaining only one file per group gives a mechanical upper bound of 294.33 MiB, not a safe deletion estimate: official assets and source dependencies are included. No duplicate model/image asset was deleted.
All groups are searchable in the CSV duplicate_group_sha256 column. Largest examples:

| MiB per file | Copies | Paths |
|---|---:|---|
| 1.75 | 8 | exports/rolling-wavy-pen/straight.stl ; exports/rolling-wavy-pen/storyboard-study-v1/straight-main.stl ; exports/rolling-wavy-pen/storyboard-study-v6/straight.stl ; exports/rolling-wavy-pen/sequence-v1/frame-01.stl ; exports/rolling-wavy-pen/storyboard-study-v5/straight.stl ; exports/rolling-wavy-pen/storyboard-study-v2/straight-main.stl ; exports/rolling-wavy-pen/storyboard-study-v3/straight.stl ; exports/rolling-wavy-pen/storyboard-study-v4/straight.stl |
| 2.76 | 4 | exports/rolling-cube-pen/print-set-v1/pose-30.stl ; exports/rolling-cube-pen/print-set-v4/pose-06.stl ; exports/rolling-cube-pen/print-set-v3/pose-25.stl ; exports/rolling-cube-pen/print-set-v2/pose-25.stl |
| 2.76 | 4 | exports/rolling-cube-pen/print-set-v1/pose-35.stl ; exports/rolling-cube-pen/print-set-v4/pose-07.stl ; exports/rolling-cube-pen/print-set-v3/pose-30.stl ; exports/rolling-cube-pen/print-set-v2/pose-30.stl |
| 2.76 | 4 | exports/rolling-cube-pen/print-set-v1/pose-40.stl ; exports/rolling-cube-pen/print-set-v4/pose-08.stl ; exports/rolling-cube-pen/print-set-v3/pose-35.stl ; exports/rolling-cube-pen/print-set-v2/pose-35.stl |
| 3.10 | 3 | exports/stone-to-fireworks/rest.stl ; exports/stone-to-fireworks/v2/rest.stl ; exports/stone-to-bread/frame-01.stl |
| 2.03 | 4 | exports/rolling-cube-pen/print-set-v1/pose-26.stl ; exports/rolling-cube-pen/print-set-v4/pose-05.stl ; exports/rolling-cube-pen/print-set-v3/pose-21.stl ; exports/rolling-cube-pen/print-set-v2/pose-21.stl |
| 2.03 | 4 | exports/rolling-cube-pen/print-set-v1/pose-21.stl ; exports/rolling-cube-pen/print-set-v4/pose-04.stl ; exports/rolling-cube-pen/print-set-v3/pose-16.stl ; exports/rolling-cube-pen/print-set-v2/pose-16.stl |
| 2.03 | 4 | exports/rolling-cube-pen/print-set-v1/pose-11.stl ; exports/rolling-cube-pen/print-set-v4/pose-02.stl ; exports/rolling-cube-pen/print-set-v3/pose-06.stl ; exports/rolling-cube-pen/print-set-v2/pose-06.stl |
| 2.03 | 4 | exports/rolling-cube-pen/print-set-v1/pose-16.stl ; exports/rolling-cube-pen/print-set-v4/pose-03.stl ; exports/rolling-cube-pen/print-set-v3/pose-11.stl ; exports/rolling-cube-pen/print-set-v2/pose-11.stl |
| 2.03 | 4 | exports/rolling-cube-pen/print-set-v1/pose-01.stl ; exports/rolling-cube-pen/print-set-v4/pose-01.stl ; exports/rolling-cube-pen/print-set-v3/pose-01.stl ; exports/rolling-cube-pen/print-set-v2/pose-01.stl |

## Remaining decisions

Review large legacy studies, untracked Blend/STL sets and previews before any larger removal. Determine whether final local PNGs and 3MF projects should be versioned separately.
No slicing, model generation, rendering or physical testing was performed. Owner-reported completed printing is distinct from the dated scope of historical QA.

## Follow-up preservation and deletion review - 2026-11-15

No large asset was deleted or staged. The original cleanup report/README edits remain. The inventory CSV now adds review_class (KEEP/DELETE/REVIEW), preservation_plan, dependency_evidence and history_recoverable columns; each filename and byte size is listed individually.
Git history recovery means reachable local refs, including the synchronized origin/main ref; it does not certify deleted remote branches or external backups. No GitHub recovery was simulated.

### Important local-only assets

| Group | Files | MiB | Recommended storage |
|---|---:|---:|---|
| previews/rolling-cube-pen/print-set-v4 | 134 | 48.43 | Final filming PNGs: recommend Git; supplementary views: local backup |
| Distribution ZIP | 1 | 22.78 | Local backup of distribution copy |
| 3MF projects | 3 | 20.38 | Local backup, preserve actual printer settings |
| previews/rolling-cube-pen/v2 | 19 | 14.02 | Final filming PNGs: recommend Git; supplementary views: local backup |
| previews/stone-to-fireworks/print-set-v1 | 34 | 10.33 | Final filming PNGs: recommend Git; supplementary views: local backup |

Total important untracked assets examined: 191 files / 115.95 MiB. No additions to Git were made.
All 191 paths are absent from reachable Git path history and have no SHA-256-identical currently tracked counterpart. This is not an exhaustive search for identical content under every historical blob name.
Recommended Git addition, subject to approval: the 61 Cube v4 filming PNGs at previews/rolling-cube-pen/print-set-v4/rolling-cube-pen-frames/frame-01.png through frame-61.png, totaling 22.77 MiB. The complete per-file byte sizes are in the CSV.
Local backup is sufficient for the remaining 130 assets (93.18 MiB): 126 supplementary PNGs, the distribution ZIP, and three actual print projects. Keep more than one durable backup location for irreplaceable production settings; their Git inclusion remains an option, not an action taken here.
The CSV separates files recoverable by identical tracked content from those unavailable in Git. ZIP CRC and byte comparison against individual Cube filming PNGs are checked below.

### Five prioritized candidate scopes

| Scope (untracked files only) | Files | MiB | KEEP | DELETE | REVIEW |
|---|---:|---:|---:|---:|---:|
| previews/rolling-cube-pen/print-set-v2 | 306 | 153.96 | 77 | 161 | 68 |
| exports/rolling-cube-pen/print-set-v1 | 61 | 94.63 | 61 | 0 | 0 |
| previews/rolling-cube-pen/print-set-v1 | 192 | 88.46 | 192 | 0 | 0 |
| models/rolling-wavy-pen-storyboard-study-v10.blend | 1 | 74.68 | 0 | 0 | 1 |
| models/rolling-wavy-pen-storyboard-study-v8.blend | 1 | 74.20 | 0 | 0 | 1 |

The original 153.96/94.63/88.46 MiB figures cover untracked subsets, not whole folders. Tracked manifest/review inputs remain protected and are not deletion candidates.

Cube v1 STL: KEEP. Old v2 source selection and v1 QA consume these files, and the old v2 preservation guard covers them. Byte-identical official copies do not replace required source paths.
Cube v1 preview: KEEP. Existing v2 protected_sha256 verification covers the old outputs, and frame PNGs are direct inputs to v2/tabletop comparisons. Deletion would break these existing workflows even though current v4 does not read them directly.
Cube v2 preview: split decision. KEEP actual frames/manifests and required references; DELETE only derived comparison and thumbnail PNGs that the generators recreate from retained inputs. Retain other review analysis images as REVIEW because their provenance or value is not fully established.
Wavy v8/v10 Blend: REVIEW. Neither is opened by current official v11/print-v2 generation; v8 Python remains a required import. Their old generators can create study scenes, but exact saved-file regeneration and absence of user edits were not established. They are not byte-equivalent to the official v11 scene, so no deletion is proposed without a preservation decision.

Dependency evidence: scripts/rolling_cube_pen_print_set_v4.py reads the v3 scene/manifest/STLs; v3.py reads print-set-v2 manifests, selected STLs and adopted review records. v3_qa.py reads the adopted hybrid59 review PNGs. Those tracked references are outside DELETE. v2.py reads v1 STL files and v1 frame PNGs. v2_tabletop.py reads the retained v1/v2 frames and creates its self-standing comparison PNGs. v2_qa.py checks the inherited protected_sha256 dictionary and reproduction GIF, without consuming the DELETE comparison or thumbnail directories. v1_qa.py also checks the inherited preservation hashes. No preservation key in these archived v1/v2 dictionaries names any of the 161 DELETE files.
Generation of the deleted-pending derived PNGs is provided by the existing v2.py and v2_tabletop.py sources; their original source scenes, STL inputs, manifests and frame PNGs all remain. No rendering was run in this investigation. Historical per-frame STL soles and old study geometry are not equivalent to current representative v4 or v11 meshes, even where they serve a similar visual purpose.

### DELETE scope, pending approval

| Path prefix | Files | Logical MiB | Allocated MiB |
|---|---:|---:|---:|
| previews/rolling-cube-pen/print-set-v2/comparison | 61 | 19.55 | 19.68 |
| previews/rolling-cube-pen/print-set-v2/self-standing-cubes/comparison | 61 | 19.27 | 19.39 |
| previews/rolling-cube-pen/print-set-v2/selected | 39 | 14.67 | 14.75 |

DELETE total: 161 files / 53.49 MiB logical, 53.82 MiB allocated blocks before APFS sharing/compression. Nothing deleted in this follow-up.
At measurement time total repository logical size including .git is 4,605.34 MiB. Approval of DELETE files would reduce it to approximately 4,551.85 MiB; report edits make this estimate slightly time-dependent. Git history/LFS size stays unchanged.
All 61 Cube ZIP PNGs match the retained individual filming PNGs byte for byte. The ZIP can be a local distribution backup rather than a second Git copy; it is not part of DELETE.
No guarantee of exact wall-clock print/render reproduction is implied. Deleting old derived comparisons preserves current printing/filming/model-edit inputs, while discarding redundant pixel outputs that can be rebuilt.

## Approved derived-PNG removal and filming-frame staging - 2026-11-15

This section supersedes the earlier pending-deletion/staging decisions for exactly these PNGs. Other deferred assets retain their previous KEEP/REVIEW status. No commit or push was performed.

Deleted exactly 161 approved PNGs / 56,086,264 bytes (53.49 MiB). Each path and SHA-256 matched the prior DELETE inventory. No unexpected files were found in the three directories, and directories themselves were not removed.
The current v4/v3 generation and QA inputs, the inherited v1/v2 preservation guards, v1 STLs/previews, and required v2 frame inputs remain intact.

Staged exactly 61 authoritative Cube v4 filming PNGs / 23,871,812 bytes (22.77 MiB). No other paths were staged. All index bytes match the unchanged work-tree PNGs.
All PNGs decoded successfully. The GIF contains 61 full canvases whose delays match the manifest/CSV 74-exposure timing, totaling 617 centiseconds. Corresponding PNG/GIF normalized RMSE is at most 0.00584748; GIF palette quantization is expected. The GIF itself was not modified.
PNG input order is frame-01.png through frame-61.png in rolling-cube-pen-frames/. The generator uses a frames/ output folder; this investigation verified the existing renamed filming set against the final GIF without moving or regenerating it.

### Before/after measurements for this operation

Regular files and logical sizes; symlinks excluded. The Git index/object additions are reported separately. Report edits are included in the after figures.

| Metric | Before | After |
|---|---:|---:|
| Work-tree files (.git excluded) | 2712 | 2551 |
| Work-tree logical MiB | 3,417.04 | 3,363.58 |
| Untracked files | 1724 | 1502 |
| .git files | 1063 | 1124 |
| .git logical MiB | 1,188.31 | 1,211.08 |
| Total files including .git | 3775 | 3675 |
| Total logical MiB including .git | 4,605.35 | 4,574.66 |

### Actual print projects preserved

| Motif | Exact path | Bytes | MiB | Git / external backup |
|---|---|---:|---:|---|
| Stone to Fireworks | exports/stone-to-fireworks/print-set-v1/stone-to-fireworks.3mf | 12889977 | 12.29 | Untracked; external backup not confirmed |
| Rolling Wavy Pen | exports/rolling-wavy-pen/rolling-wavy-pen.3mf | 5229906 | 4.99 | Untracked; external backup not confirmed |
| Rolling Cube Pen | exports/rolling-cube-pen/print-set-v4/rolling-cube-pen.3mf | 3254298 | 3.10 | Untracked; external backup not confirmed |

All three are valid 3MF ZIP containers and include Metadata settings files. They remain at their original paths with unchanged hashes. External backups are outside this repository and were not available for confirmation; no backup exists claim is made.
If separately approved for Git, their total payload would be 20.38 MiB before Git compression. Each is under 100 MiB, so Git LFS is not required by the per-file limit. Ordinary Git would increase clone/history size; LFS would add storage/download usage for the same payload and explicit path rules. No LFS change or 3MF staging occurred.

### Verification and remaining local assets

All 75 official STL hashes match existing QA records. Every baseline file outside the approved deletions was verified byte-identical before the intentional README/report updates. No formal Blend, GIF, CSV, STL, other-motif source or retained image changed. README destinations resolve. Existing Git attributes and LFS settings remain unchanged.
Remaining important untracked assets: 126 supplementary PNGs, three print projects and the distribution ZIP. They remain 130 files / 93.18 MiB. Historical studies are also retained. The staged 61 PNGs are not yet recoverable from GitHub until a later authorized commit/push.
The inventory retains its baseline git_state/bytes_before columns and adds current_git_state. action=deleted identifies both the earlier cache cleanup and the newly approved PNG deletions. action=git_staged identifies only the 61 official PNGs.

## Final cleanup checkpoint

The approved cleanup is packaged as one signed commit containing README, this report, the inventory CSV and the 61 official Cube v4 filming PNGs. Earlier staging and pending-commit statements above describe the recorded intermediate stages; the PNGs become tracked history in this checkpoint. Publishing to GitHub requires a separately authorized push.

Pre-commit checks confirmed the 75 official STL hashes, exact PNG index contents, README links and the absence of home-directory paths, email addresses or recognizable credential/private-key patterns in the report and inventory. The CSV records repository-relative paths and historical Git states only. The actual print projects, distribution ZIP, supplementary images and remaining studies are preserved without further cleanup. No Git settings or LFS rules changed.

## Public print-project handoff - 2026-11-15

This section supersedes earlier untracked-3MF status and placement statements. The three public copies are prepared for ordinary Git at the paths below. No commit or push was performed. Original archives are preserved in a private owner-only backup outside the repository; that path and account values are intentionally excluded from this public report.

| Public path | Model types / objects | Bytes | Public SHA-256 |
|---|---:|---:|---|
| exports/stone-to-fireworks/print-set-v1/stone-to-fireworks.3mf | 14 / 14 | 13195701 | c09503684df64015075b8acd45d6738249c343897a0a981cb9e47038e0fc4523 |
| exports/rolling-wavy-pen/print-set-v2/rolling-wavy-pen.3mf | 14 / 14 | 5476966 | 688dc6ad624a5b8dfc26ccabc426e1fc4f5478c967dd1111986dca44ac28dc52 |
| exports/rolling-cube-pen/print-set-v4/rolling-cube-pen.3mf | 12 / 20 | 3389484 | 1b187b1f4a430420655ca4f2722275d513be8806b95a99d196d12fd408c5b7d6 |

Only Wavy moved, from exports/rolling-wavy-pen/rolling-wavy-pen.3mf into its print-set-v2 directory. No new repository hierarchy was created. The Wavy archive intentionally retains 14 shapes, without pose-15/pose-16.
DesignerUserId is a designer-account association field in [Bambu Studio source](https://github.com/bambulab/BambuStudio/blob/master/src/libslic3r/Format/bbs_3mf.cpp), distinct from the separately preserved Designer/Copyright/License fields. These three archives had empty attribution-name, copyright, license and origin fields; no third-party attribution text was removed. The sole nonempty account identifier was removed from each public copy. Generated internal UUIDs and all functional identifiers remain.
Privacy inspection found no home-directory source paths, email addresses, recognizable authentication-token/private-key patterns or other nonempty user-profile account metadata. This inspection is not a guarantee against every possible encoded secret. Original archives remain unmodified in private backup.
Every ZIP passes CRC checks; member lists match; only one metadata element in 3D/3dmodel.model differs. Every other member is byte-identical, including meshes, build/model-instance transforms, project/model settings, filament settings, layer heights, infill, walls, support and brim settings. The resulting XML is parseable and remains an editable Bambu project.
All use Bambu Studio 02.09.01.70. Fireworks and Cube store X1E 0.6 nozzle settings; Wavy stores X1 Carbon 0.4 nozzle settings. These labels must not be presented as verified actual printer hardware. No G-code exists in these archives. GUI import and warning-free loading are unverified; no slicing or printing was performed.
The existing three print guides record both original and public SHA-256 values. Only the three project rows in the inventory are updated to their public paths/hashes and staging status; each reason field retains the original path/hash and records the current byte size. Other inventory rows remain unchanged. No additional profile/configuration management files were introduced.
