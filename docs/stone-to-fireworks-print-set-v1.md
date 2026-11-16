# Stone to Fireworks

## 目的と仕様

承認済み形状はv3、正式な机上撮影セットはprint-set-v1の14 STL。
石を3回押し、手前へ引っ張り、離した反動で奥へ遠ざける。
20ポーズ、各2露光、12 fps、計40露光、約3.33秒。
通常石は30 × 25 × 20 mm、最小石は7.5 × 6.25 × 5 mm。
指と最後の折り紙花火は実写で用意する。

## 制作過程と設計判断

| 問題と検証結果 | 判断と変更 |
|---|---|
| 石全体の平行移動では指に追従して見えない | Stone to Breadの局所変形を再利用。接触点の影響を距離で減衰させ、奥側を残して伸ばす |
| ぷにぷにが読みにくい | 局所的なへこみと周囲の膨らみを強め、押す、戻るを3回繰り返す |
| 復元後に止まってから飛び出すように見える | 最大伸長からの復元と奥方向への移動を重ね、元位置を通過させる |
| 滑らかな楕円が粘土に見える | 共通の基準メッシュに非対称な面、浅い欠けと膨らみを付け、その同じ頂点を全ポーズで変形 |
| v3の浮遊が実写机上撮影に合わない | 13–20の上昇を除去。移動と実寸65%、40%、25%の小石への交換だけで距離を表現 |

v3の空中演出版は形状と動作意図の参照として保持し、机上版を実写撮影の正本とする。
石の質感は形状で作り、テクスチャだけに頼らない。
実寸の異なる小石を用意し、CGのオブジェクト拡縮は使わない。

## 検証結果

[Final QA](stone-to-fireworks-final-qa.md)はPASS。
14 STLはv3の選定元とバイト一致。保存データを再読込し、閉鎖性、manifold、単一連結、正体積、法線、退化面、検出対象の交差を確認した。
全20配置のワールド底面が机に接し、静的重心支持を満たす。
最小石の接地面積は約7.202 mm²、支持余裕は約1.153 mm。
網羅的な最小肉厚、微細な起伏のFDM再現性、スライサーと実機での独立確認は未検証。
詳細数値とSHA-256の正本は[最終QA JSON](../previews/stone-to-fireworks/print-set-v1/final-qa.json)。

## 最終成果物と撮影

- [正式STLと3MF](../exports/stone-to-fireworks/print-set-v1/)、[机上Blend](../models/stone-to-fireworks-print-set-v1.blend)
- [撮影CSV](../previews/stone-to-fireworks/print-set-v1/frame-to-stl.csv)、[manifest](../previews/stone-to-fireworks/print-set-v1/manifest.json)
- [机上GIF](../previews/stone-to-fireworks/print-set-v1/print-reproduction.gif)、[構成PNG](../previews/stone-to-fireworks/print-set-v1/)、[v3との比較](../previews/stone-to-fireworks/print-set-v1/v3-vs-tabletop.gif)
- [v3 GIF](../previews/stone-to-fireworks/v3/sequence-v3.gif)、[v3 Blend](../models/stone-to-fireworks-v3.blend)
- [形状生成器](../scripts/stone_to_fireworks_v3.py)、[机上版生成器](../scripts/stone_to_fireworks_print_set_v1.py)、[QA](../scripts/stone_to_fireworks_print_set_v1_qa.py)

CSVのXは左右、Y正方向が手前、Z正方向が上。原点を揃え直さずmmで読み込む。
13–20のYは-14、-40、-82、-130、-180、-230、-280、-315 mmで、底面は常にZ=0。
通常石を6回、最小石を2回再利用する。約315 mmの奥行きを確保する。
机上版は空中版より滑走に見える可能性があり、実際のカメラと照明で調整する。

生成は隔離コピーで行う。
v3生成器には元の`rest.stl`、初期シーン、`validation-v1.json`が必要。初期シーンはスタジオ入力としてのみ保持する。
机上版はv3のシーン、14 STL、manifest、validation、フレームPNGを読み込む。
これらは形状入力であり、旧v2の出力は不要。

実印刷済み[3MF](../exports/stone-to-fireworks/print-set-v1/stone-to-fireworks.3mf)は14種類、14個を含む。
保存設定はBambu Studio 02.09.01.70、X1E 0.6 mm、0.30 mm Standard。
公開コピーはDesignerUserIdだけを除去し、配置と印刷設定を保持した。GUI再読込は未検証。
SHA-256は`c09503684df64015075b8acd45d6738249c343897a0a981cb9e47038e0fc4523`。
