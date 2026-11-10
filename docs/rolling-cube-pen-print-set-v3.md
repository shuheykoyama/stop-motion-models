# Rolling Cube Pen: 正式印刷セット print-set-v3

正式承認済みの印刷用モデルはprint-set-v3で、43種類、合計59個のハイブリッド印刷セット。
承認済みアニメーションv2と、分離部分レビューの`hybrid59`配置を参照する。
旧アニメーション、print-set-v1、print-set-v2、既存STLは変更していない。

Final QAは **WARNING**。
Phase 1の実際の指保持に起因するWARNINGは依頼者が許容したが、保持の実現性は未検証のまま記録する。
STLと撮影データの整合性は確認済みで、分離後の全立方体は静的支持を満たす。
Phase 1の18ポーズは自立せず、指で保持する必要がある。
その実撮影方法は未検証なので、全撮影が無条件に成立するという判定ではない。

## 印刷するもの

[正式STLフォルダ](../exports/rolling-cube-pen/print-set-v3/)の`pose-01.stl`から`pose-43.stl`を使う。
ファイルごとの必要印刷個数は[print-inventory.csv](../previews/rolling-cube-pen/print-set-v3/print-inventory.csv)を正本とする。

| 用途 | STL | 種類数 | 印刷個数 |
|---|---|---:|---:|
| 円筒ペン | pose-01 | 1 | 1 |
| 円筒から四角柱の中間形状 | pose-02から21 | 20 | 20 |
| 分離前の溝付き一体形状 | pose-22から35 | 14 | 14 |
| 基準立方体のキャップ側 | pose-36から38 | 3 | 各1、計3 |
| 基準立方体の本体側 | pose-39 | 1 | 9 |
| 傾き用立方体のキャップ側 | pose-40から42 | 3 | 各1、計3 |
| 傾き用立方体の本体側 | pose-43 | 1 | 9 |
| 合計 | | 43 | 59 |

41種類を1個ずつ、pose-39とpose-43を9個ずつ印刷する。
分離用に保有する実物は24個だが、各ポーズで並べるのは12個。
物体の登場回数ではなく、同時使用に必要な個数を撮影全体で保有する計画である。
各STLは既存の検証済みファイルからバイト単位でコピーし、形状の修正や追加最適化はしていない。

STLには単位がないため、**mmとして倍率100%で読み込む**。
STLの局所原点・接地姿勢は撮影用であり、印刷時の最適な造形方向とは区別する。

## 撮影計画

61ポーズ、74露光、12 fps、計画上6.1667秒。
GIFの時間精度では6.17秒。

| フェーズ | ポーズ | 露光数 | 往復 |
|---|---|---:|---:|
| 円筒 | 01から21 | 26 | 2 |
| 円筒から四角柱 | 22から41 | 24 | 2 |
| 溝の形成と分離 | 42から61 | 24 | 2 |

キャップは画面左、先端は右。
カメラはv2と同じ固定正投影、Orthographic Scale 190 mm、800 x 500。
メッシュの補間とスケール変更は使わず、実寸のモデル交換と剛体移動・回転だけで再現する。

[frame-to-stl.csv](../previews/rolling-cube-pen/print-set-v3/frame-to-stl.csv)は127行。
01から55は各1行、56から61は各12行で、全物体を記載している。
同じポーズの露光数が各物体行に繰り返し載るため、127行の露光列をそのまま合計しない。
各ポーズの露光数を一度ずつ数えると74になる。

1. `pose`で撮影するポーズの全行を選ぶ。
2. `stl`と`physical_object_id`でモデルを用意する。同じ個体IDを後のポーズで再使用する。
3. mm単位の`x_mm, y_mm, z_mm`へ配置し、記載したXYZ Euler回転を追加する。
4. スケールは全軸1にし、`exposures_12fps`だけ露光する。
5. `self_standing`がFalseの行では、指による保持が必要なことを確認する。

右手座標系で、Xが長手方向、Zが机から上。
正のXが画面左、正のYがこのカメラの手前方向。
机面はZ=0。
モデルに焼き込まれた転がり姿勢を再度加算せず、CSVの追加回転だけを適用する。

## 分離後の12個

立方体番号はキャップ側から0から11。
0から2に対応する3個を左端に置き、本体側9個を続ける。
個体IDは同じ役割の立方体を追跡でき、部品の順番を交換しない。

| ポーズ | 使用モデル | 再使用 |
|---|---|---|
| 56、57、60、61 | pose-36、37、38を各1個、pose-39を9個 | 同じ基準12個 |
| 58、59 | pose-40、41、42を各1個、pose-43を9個 | 同じ傾き用12個 |

57は長軸回転を-84度から-90度へ、60は-6度から0度へ変更する採用案。
59では傾き用の同じモデルを机面法線まわりに180度回して共用する。
これらを含む最終回転値がCSVに入っているため、追加の手計算は不要。
隙間、奥行きずれ、細かな向きは採用済みレビュー配置をそのまま使用する。

## 形状一致と既知の差

全43 STLのSHA-256が選定元と一致する。
独立した一時ディレクトリで同じ選定を組み立てても同じSHA-256となる。
今回は既存形状を手続き的に再生成せず、検証済みの保存STLを使用した。

採用した56から61の位置・回転はレビューJSONと一致する。
分離区間のv2との最大表面サンプル差は約0.657 mm。
57、60の面置き調整とキャップの小さな痕跡の向きの違いを含む。
円筒1本共用のPhase 1には、従来から最大約1.899 mmの表面差がある。
0.657 mmをアニメーション全体の最大差とは扱わない。

## 確認用成果物

- [STLだけによる印刷再現GIF](../previews/rolling-cube-pen/print-set-v3/print-reproduction.gif)
- [左がv2、右が正式セットの比較GIF](../previews/rolling-cube-pen/print-set-v3/v2-vs-print-set.gif)
- [全61ポーズ](../previews/rolling-cube-pen/print-set-v3/contact-sheet.png)
- [43形状の一覧](../previews/rolling-cube-pen/print-set-v3/selected-shapes.png)
- [56から61の正面比較](../previews/rolling-cube-pen/print-set-v3/poses-56-61-front.png)
- [56から61の真上比較](../previews/rolling-cube-pen/print-set-v3/poses-56-61-top.png)
- [編集用Blenderシーン](../models/rolling-cube-pen-print-set-v3.blend)
- [manifest](../previews/rolling-cube-pen/print-set-v3/manifest.json)
- [生成時検証](../previews/rolling-cube-pen/print-set-v3/validation.json)
- [Final QA JSON](../previews/rolling-cube-pen/print-set-v3/final-qa.json)
- [Final QAレポート](rolling-cube-pen-final-qa.md)

形状一覧だけは判別のため立方体を拡大した静止図を使う。
撮影アニメーションのカメラやモデル倍率は変更していない。

## 未検証事項と注意

Phase 1の02から10、12から20は自立しない。
指保持、転がりの動的安定性、印刷誤差や摩擦、実際の照明と撮影条件は未検証。
分離直後の0.05 mm隙間を手で配置する精度も未検証。
網羅的な最小肉厚、スライス結果、サポート要否、実印刷の成功は確認していない。
クリップの痕跡や狭い溝などの微細要素は、スライサーで再現状態を確認する必要がある。
自動修復や形状補強はしていない。

## 再生成・QA

リポジトリ直下から実行する。
既存のv2、print-set-v2、分離レビューのJSONと画像を入力として使う。
入力を変更せず、v3の既知の生成物だけを再生成する。
コミットにはv3と、その再生成が直接読む固定入力だけを含める。
固定入力は承認済みv2シーン、v2の配置JSON・比較用画像、print-set-v2の選定元STLとmanifest、採用レビューJSON・参照画像、共有生成コードである。
旧セットの全体や作業用レンダーを再公開するものではない。印刷には必ず上記のv3フォルダを使う。
Final QAの保護ハッシュには当時のローカル開発履歴も含まれるため、再実行では存在するRolling Cube Pen資産を照合し、コミット対象外の履歴資産は未配置として別記する。
正式STL、選定元、採用レビュー、シーン、CSVの必須入力検証は省略しない。

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 2 --python-exit-code 1 --python scripts/rolling_cube_pen_print_set_v3.py
/Applications/Blender.app/Contents/MacOS/Blender --background --threads 2 --python-exit-code 1 --python scripts/rolling_cube_pen_print_set_v3_qa.py
```

形状・撮影配置・シーンの再組み立てだけを確認する場合は、生成コマンドの末尾に`-- --no-render`を付ける。
これは画像を再描画しない。正式版を保持したい場合は、別の作業コピーで実行する。

プレビューはEEVEEとAMD Radeon Pro 5600MのMetal描画を使う。
QAは保存済みシーンを別プロセスで開き、STLの独立読み込みでは自動補正を無効にする。
Finderの`.DS_Store`はモデル資産のハッシュ検査から除外し、変化があればQA JSONへ別記する。
