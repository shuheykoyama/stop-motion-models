# Rolling Wavy Pen

## 目的と仕様

正式アニメーションはv11、正式印刷セットはprint-set-v2の16 STL。
黒いキャップ付きペンが、直線から単一弧へ曲がり、その弧に複数のうねりが育つ。
30ポーズ、各160 ms、計4.8秒。長さの基準は141.8 mm、軸径は11.9 mm。

## 制作過程と設計判断

| 問題と検証結果 | 判断と変更 |
|---|---|
| キャップだけ硬く見え、端部に曲がりが集中した | 部品を区別しない一本の棒として中心線を先に設計し、断面と外観を後から適用 |
| うねりへの置換で大きな弧が失われた | 低周波の単一弧を残し、高周波成分を重ねる構成を採用 |
| 初期形状が弧に固定され、Straightが消えた | 直線を保持する往復、弧を育てる往復、うねりを育てる往復を分離 |
| 全区間の補間追加でCGのように滑らかになった | 30ポーズへ整理し、転がりでシルエットが反転するストップモーションのテンポを採用 |
| 同じ関数を使っても中央が平坦、端が高曲率になった | 一定径の棒、中心線、曲率分布で空間的な偏りを評価してv11を確定 |
| CGの全30形状を印刷する負荷 | 16形状を選び、剛体配置だけの再現版と比較。平均RMS差0.053 mm、最大頂点差0.677 mmを採用 |

中心線の接線と曲率、キャップ境界の連続性を検査し、装飾による見かけと中心線自体の問題を区別した。
今回の整理ではv11が旧v8から読み込んでいた定数をv11内へ移し、全30形状の生成座標と保存メッシュの一致を確認した。
旧v8とv10のBlendは現行生成の入力ではない。

## 検証結果

[Final QA](rolling-wavy-pen-final-qa.md)はPASS。
16 STLの再読込で閉鎖性、manifold、単一連結、面方向、体積、退化面、検出対象の交差、接地と重心支持を確認した。
寸法、使用回数、元フレームとSHA-256は[manifest](../previews/rolling-wavy-pen/print-set-v2/manifest.json)と[最終QA JSON](../previews/rolling-wavy-pen/print-set-v2/final-qa.json)に記録している。
網羅的な最小肉厚と実物の撮影安定性は未検証。

## 最終成果物と撮影

- [正式STL](../exports/rolling-wavy-pen/print-set-v2/)、[印刷版Blend](../models/rolling-wavy-pen-print-set-v2.blend)
- [撮影CSV](../previews/rolling-wavy-pen/print-set-v2/frame-to-stl.csv)、[撮影再現GIF](../previews/rolling-wavy-pen/print-set-v2/print-reproduction.gif)、[構成PNG](../previews/rolling-wavy-pen/print-set-v2/reproduction-frames/)
- [理想v11 GIF](../previews/rolling-wavy-pen/storyboard-study-v11/sequence.gif)、[理想PNG](../previews/rolling-wavy-pen/storyboard-study-v11/frames/)、[v11 Blend](../models/rolling-wavy-pen-storyboard-study-v11.blend)
- [形状生成器](../scripts/rolling_wavy_pen_storyboard_study_v11.py)、[印刷版生成器](../scripts/rolling_wavy_pen_print_set_v2.py)、[QA](../scripts/rolling_wavy_pen_print_set_v2_qa.py)

CSVは各STLに焼き込まれたロールと接地面を前提とし、追加回転0°で再配置する。
STLはmmとして読み込み、独自に原点や下面を揃え直さない。
印刷版生成はv11シーンを開いた隔離コピーで行う。共有モジュール`rolling_wavy_pen.py`も必要。
Blend2件はGit LFS管理なので、復元時にはLFS実体を取得する。

実印刷済み[3MF](../exports/rolling-wavy-pen/print-set-v2/rolling-wavy-pen.3mf)は**14形状版**で、pose-01–14を含む。
正式STLは16形状だが、pose-15と16は3MFに含まれない。全形状を再印刷する場合は追加配置と再スライスが必要。
保存設定はBambu Studio 02.09.01.70、X1 Carbon 0.4 mm、0.28 mm Extra Draft。
公開コピーはDesignerUserIdだけを除去し、形状と印刷設定を保持した。GUI再読込は未検証。
SHA-256は`688dc6ad624a5b8dfc26ccabc426e1fc4f5478c967dd1111986dca44ac28dc52`。
