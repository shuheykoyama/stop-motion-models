# Stop Motion Models

Blender 4.5 LTSで制作した、実物のモデルを交換して撮影するストップモーション用データ。
完成データと、その編集に必要な入力を保持する。

| 作品 | 状態と印刷対象 | 編集シーン | アニメーションと構成PNG | 仕様と制作経緯 |
|---|---|---|---|---|
| Pen | 完成、[7 STL](exports/pen/) | [Blend](models/pen.blend) | [GIF](previews/pen/forward-reverse.gif)、[PNG](previews/pen/) | [仕様書](docs/specification.md) |
| Stones | 完成、[7 STL](exports/stones/) | [Blend](models/stones.blend) | [GIF](previews/stones/forward-reverse.gif)、[PNG](previews/stones/) | [仕様書](docs/specification.md) |
| Cup | 完成、[7 STL](exports/cup/) | [Blend](models/cup.blend) | [GIF](previews/cup/forward-reverse.gif)、[PNG](previews/cup/) | [仕様書](docs/specification.md) |
| Stone to Bread | 暫定承認、12 STLとCG用パン | [Blend](models/stone-to-bread-full-sequence-v1.blend) | [GIF](previews/stone-to-bread/full-sequence-v1/sequence-realistic-deliberate.gif)、[PNG](previews/stone-to-bread/full-sequence-v1/) | [ガイド](docs/stone-to-bread.md) |
| Rolling Wavy Pen | 完成、[print-set-v2、16 STL](exports/rolling-wavy-pen/print-set-v2/) | [Blend](models/rolling-wavy-pen-print-set-v2.blend) | [撮影再現GIF](previews/rolling-wavy-pen/print-set-v2/print-reproduction.gif)、[PNG](previews/rolling-wavy-pen/print-set-v2/reproduction-frames/) | [ガイド](docs/rolling-wavy-pen-print-set-v2.md) |
| Stone to Fireworks | 完成、[print-set-v1、14 STL](exports/stone-to-fireworks/print-set-v1/) | [Blend](models/stone-to-fireworks-print-set-v1.blend) | [机上GIF](previews/stone-to-fireworks/print-set-v1/print-reproduction.gif)、[PNG](previews/stone-to-fireworks/print-set-v1/) | [ガイド](docs/stone-to-fireworks-print-set-v1.md) |
| Rolling Cube Pen | 完成、[print-set-v4、12 STL、20個](exports/rolling-cube-pen/print-set-v4/) | [Blend](models/rolling-cube-pen-print-set-v4.blend) | [撮影再現GIF](previews/rolling-cube-pen/print-set-v4/print-reproduction.gif)、[61 PNG](previews/rolling-cube-pen/print-set-v4/rolling-cube-pen-frames/) | [ガイド](docs/rolling-cube-pen-print-set-v4.md) |

STLに単位情報はないため、Bambu Studioでは**mm、倍率100%**として読み込む。
Wavy Pen、Fireworks、Cube Penの各印刷セットには、実印刷に使用した`<motif>.3mf`も保存している。
3MFを印刷設定の正本とし、保存プロファイルと実際の機器を混同しない。
実印刷の実施はユーザーからの報告であり、データQAは造形や撮影の成功を保証しない。

撮影CSV、在庫、最終QA、理想版との相違、再生成手順は各ガイドを参照する。
Stone to Bread以外の最終QAはPASS。Cube Penの転がり途中には、承認済みの指保持が必要な姿勢がある。
Git LFSはWavy Penの2つの最終Blendだけに適用する。clone後に`git lfs pull`で実体を取得する。

## 開発と再生成

Pythonは`mise.toml`、依存関係は`pyproject.toml`と`uv.lock`で管理する。
`bpy`処理はBlenderのPythonで実行し、通常のPython検証は`uv run`を使う。
ImageMagickをプレビューの合成に使用する。
再生成は一時ディレクトリまたは隔離したコピーで実施し、承認済み出力を上書きしない。
具体的な入力とコマンドは各ガイドに記載した。

保存ディレクトリは`models/`が編集シーン、`exports/`が実寸モデル、`previews/`が撮影と検証、`scripts/`が生成器、`docs/`が設計判断。
旧名の入力を残す理由と今回の整理結果は[整理記録](docs/repository-cleanup.md)を参照する。
