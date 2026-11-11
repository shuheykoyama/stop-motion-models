# Rolling Cube Pen — print-set-v4正式版

`print-set-v4`は、承認済みv2の動きと見た目を保ちながら印刷準備の負荷を下げるための**正式承認済みの印刷セット**。
現在の正式版は`print-set-v4`。旧正式版v3と理想アニメーションv2は履歴として保持する。

## 印刷計画

| | print-set-v3 | print-set-v4正式版 | 削減 |
|---|---:|---:|---:|
| STL種類 | 43 | 12 | 31種類（72.1%） |
| 印刷する物体 | 59 | 20 | 39個（66.1%） |
| モデル固体体積の合計 | 688,296.88 mm³ | 167,978.78 mm³ | 75.6% |

体積はモデル本体のCAD体積合計で、サポート、ブリム、パージ材などを含まない。
スライサーを使っていないため、造形時間や実際の材料使用量は算出していない。

| v4 STL | v3から選んだ形状 | 使い道 | 印刷個数 |
|---|---|---|---:|
| pose-01 | pose-01 | 円筒ペン、Phase 1と角ばり初期 | 1 |
| pose-02 | pose-06 | 円筒から四角柱への中間 | 1 |
| pose-03 | pose-11 | 円筒から四角柱への中間 | 1 |
| pose-04 | pose-16 | 四角柱化の終盤 | 1 |
| pose-05 | pose-21 | 四角柱 | 1 |
| pose-06 | pose-25 | 浅い分割溝 | 1 |
| pose-07 | pose-30 | 中程度の分割溝 | 1 |
| pose-08 | pose-35 | 深い分割溝・分離直前 | 1 |
| pose-09 | pose-36 | キャップ側の立方体0 | 1 |
| pose-10 | pose-37 | キャップ側の立方体1 | 1 |
| pose-11 | pose-38 | キャップ側の立方体2 | 1 |
| pose-12 | pose-39 | 本体側の立方体3〜11 | 9 |

合計は12種類・20個。
立方体は異なる3つのキャップ側モデルと共通の本体側モデル9個で構成し、同じ12個を56〜61ポーズで繰り返し使う。
58・59ポーズも追加の立方体セットを印刷せず、この12個を再配置する。

## 61ポーズのモデル交換

| ポーズ | 使用モデル |
|---|---|
| 01〜25 | pose-01（円筒） |
| 26〜30 | pose-02 |
| 31〜35 | pose-03 |
| 36〜40 | pose-04 |
| 41〜44 | pose-05（四角柱） |
| 45〜48 | pose-06（浅い溝） |
| 49〜51 | pose-07（中程度の溝） |
| 52〜55 | pose-08（深い溝） |
| 56〜61 | キャップ3個と本体9個の独立立方体 |

フレーム別の物体ID、配置、回転、露光数、接地値は[frame-to-stl.csv](../previews/rolling-cube-pen/print-set-v4/frame-to-stl.csv)に記録した。
[print-inventory.csv](../previews/rolling-cube-pen/print-set-v4/print-inventory.csv)が必要印刷数の一覧。
形状を切り替えるフレーム範囲は、[reduced-models.csv](../previews/rolling-cube-pen/print-set-v4/reduced-models.csv)にあるv3形状の代表選定と対応する。

アニメーションは61ポーズ、74露光、12 fps、約6.17秒。
カメラは固定、モデル倍率は全軸1、STLの移動・回転・交換のみで、メッシュ補間をしていない。
キャップは画面左側。
円筒から四角柱への変化は各段階を3〜5ポーズ保持するため、v2より離散的に見える箇所がある。
分割溝も3段階へ集約される。

## プレビューと編集データ

- [印刷候補だけを使った再現GIF](../previews/rolling-cube-pen/print-set-v4/print-reproduction.gif)
- [v2との比較GIF](../previews/rolling-cube-pen/print-set-v4/v2-vs-print-set.gif)
- [61ポーズのコンタクトシート](../previews/rolling-cube-pen/print-set-v4/contact-sheet.png)
- [12種類の形状一覧](../previews/rolling-cube-pen/print-set-v4/selected-shapes.png)
- [編集用Blenderシーン](../models/rolling-cube-pen-print-set-v4.blend)
- [生成スクリプト](../scripts/rolling_cube_pen_print_set_v4.py)
- [独立読み戻しQAスクリプト](../scripts/rolling_cube_pen_print_set_v4_qa.py)
- [機械可読manifest](../previews/rolling-cube-pen/print-set-v4/manifest.json)
- [検証JSON](../previews/rolling-cube-pen/print-set-v4/validation.json)

STLの頂点座標はmmスケールだが、STL形式に単位情報はない。
プリント用には`exports/rolling-cube-pen/print-set-v4/pose-01.stl`から`pose-12.stl`をmm、倍率100%で読み込む。

## 検証・未確認事項

12 STLはすべてv3の既存STLをバイト単位でコピーした。
独立したBlender STL読み込み後に閉鎖性、manifold、連結性、正体積、法線、退化三角形、検出対象の自己交差、寸法と体積を検証した。
Blendを別プロセスで再度開き、シーン内メッシュ指紋、20個の物体、61ポーズ、74露光、CSV、カメラ固定、スケール固定を照合した。
全ポーズが机に接地し、分離後の立方体は全配置で静的に自立する。
Phase 1の18ポーズ（02〜10、12〜20）は指で保持する必要があり、実際の保持と転がしは未検証。

最小肉厚の網羅測定、Bambu Studioでのスライス、サポート、造形時間、実印刷、実際の撮影条件は未検証。
幾何検証と静的支持は造形・撮影の成功を保証しない。


## 再生成と最終QA

Blender 4.5 LTSとImageMagickを使用し、リポジトリ直下から実行する。

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 2 --python-exit-code 1 --python scripts/rolling_cube_pen_print_set_v4.py
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 2 --python-exit-code 1 --python scripts/rolling_cube_pen_print_set_v4_qa.py
```

生成はコミット済みのv3 STL、manifest、Blenderシーンとv2比較画像、共有スクリプトを固定入力として利用する。
中間の個別レンダーは生成時に作成し、Gitには最終GIFと一覧画像を保存する。
形状を再生成せずデータを確認するときはQAコマンドのみを実行する。
[正式版の最終QA記録](rolling-cube-pen-print-set-v4-final-qa.md)を参照。
モデル交換時の位置合わせと、分離直後の立方体の配置精度も未検証である。
