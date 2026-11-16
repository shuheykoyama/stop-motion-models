# Rolling Cube Pen

## 目的と仕様

正式印刷セットは**print-set-v4、STL12種類、印刷物20個**。
円筒ペンを転がし、四角柱を経て12個の立方体へ分離する。
61ポーズ、74露光、12 fps、約6.17秒で、各段階を2往復ずつ、計6往復する。
キャップは画面左、カメラは固定、全モデルのスケールは1。

## 制作過程と設計判断

| 段階 | 問題と検証結果 | 判断と変更 |
|---|---|---|
| 形状と運動 | 円筒と四角柱では接地半径と転がり方が異なる | 断面を段階的に角ばらせ、面から面への倒れ込みを表現。最後は順序を保った12個を少しずらす |
| 個別ポーズのモデル化 | 姿勢ごとの下面補正まで固定すると61種類、85個になった | 剛体変換で共用できる形状を検査し、形状差と姿勢差を区別した |
| 自立性 | 12個共用案の57–60は面が傾き、線接触となる。XY移動では支持状態は改善しない | 57と60を6°調整し、58と59に傾き用モデルを共用する43種類、59個の案を一度採用 |
| 印刷負荷 | 厳密な連続形状と全姿勢の自立を優先すると印刷物が多い | 数コマ同じ形状を使う段階的な変化を承認。転がり途中の指保持を許容し、12種類、20個へ削減 |
| 最終構成 | 同じ12個の立方体を全分離ポーズで使い回せる | キャップ由来3種類を各1個、本体由来1種類を9個使用。分離後は面置きして自立させる |

v4は理想アニメーションv2への厳密なポーズ別形状一致より、実写での再利用と印刷負荷の削減を優先した承認版。
通常円筒1本、中間3本、四角柱1本、溝付き3本と独立立方体12個を交換して撮る。
STLと配置を凍結入力とし、旧印刷セットを読み込まずに再構成できるようにした。
旧版との対応は`reduced-models.csv`に記録している。

## 検証結果

[最終QA](rolling-cube-pen-print-set-v4-final-qa.md)はPASS。
保存STLの再読込、正体積、閉鎖性、manifold、単一連結、法線、退化面、検出対象の交差を確認した。
61ポーズが机に接触し、分離後の72物体配置は静的支持を満たす。
寸法とSHA-256の正本は[検証JSON](../previews/rolling-cube-pen/print-set-v4/validation.json)。
今回の依存整理では、12 STLのバイト一致、全61ポーズの配置一致、一時再構成シーンのQAを別途確認した。

## 最終成果物と撮影

- [STLと3MF](../exports/rolling-cube-pen/print-set-v4/)、[編集Blend](../models/rolling-cube-pen-print-set-v4.blend)
- [撮影CSV](../previews/rolling-cube-pen/print-set-v4/frame-to-stl.csv)、[必要印刷個数](../previews/rolling-cube-pen/print-set-v4/print-inventory.csv)、[manifest](../previews/rolling-cube-pen/print-set-v4/manifest.json)
- [撮影再現GIF](../previews/rolling-cube-pen/print-set-v4/print-reproduction.gif)、[構成PNG](../previews/rolling-cube-pen/print-set-v4/rolling-cube-pen-frames/)、[コンタクトシート](../previews/rolling-cube-pen/print-set-v4/contact-sheet.png)
- [理想v2](../previews/rolling-cube-pen/v2/sequence-v2.gif)、[比較GIF](../previews/rolling-cube-pen/print-set-v4/v2-vs-print-set.gif)、[理想版Blend](../models/rolling-cube-pen-v2.blend)
- [再構成スクリプト](../scripts/rolling_cube_pen_print_set_v4.py)、[QAスクリプト](../scripts/rolling_cube_pen_print_set_v4_qa.py)、[理想版生成器](../scripts/rolling_cube_pen_v2.py)

撮影CSVの個体IDで同じ実物を追跡する。
1–25は円筒、26–30、31–35、36–40は中間3本、41–44は四角柱、45–48、49–51、52–55は溝付き3本、56–61は同じ12個の立方体を使う。
Phase 1の02–10と12–20（18ポーズ）は指保持が必要で、実物の動的安定性、交換精度、微小な隙間の配置は未検証。
網羅的な最小肉厚、スライス、サポート、造形時間の独立検証も未実施。

再構成はBlender 4.5 LTSで、正式データとは別の出力ルートを必ず指定する。

```sh
blender --background --threads 2 --python-exit-code 1 --python scripts/rolling_cube_pen_print_set_v4.py -- --output-root /private/tmp/cube-rebuild --no-render
```

実印刷済みの[3MF](../exports/rolling-cube-pen/print-set-v4/rolling-cube-pen.3mf)は12種類、20個を含む。
保存設定はBambu Studio 02.09.01.70、X1E 0.6 mm、0.30 mm Standardプロファイル。
これは保存された機器設定であり、実使用機器の独立確認ではない。
公開コピーはDesignerUserIdだけを除去し、設定と配置を保持した。GUI再読込は未検証。
SHA-256は`1b187b1f4a430420655ca4f2722275d513be8806b95a99d196d12fd408c5b7d6`。
STLはmmとして読み込む。
