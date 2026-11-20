# Stone to Bread

## 目的と仕様

現時点では**13ポーズのCGプレビューと石の形状が暫定承認**。正式完成版や実印刷済みモデルとは区別する。
石が転がりながら伸び、中央を手前へ押し引きした後、反発してパンへ切り替わる。
順序はr01–r07、p01–p04、c01、b01。12種類の石が印刷対象で、パンb01は実物との交換を想定したCG参照。
選定テンポは12 fps、44露光、約3.67秒。

## 制作過程と設計判断

| 問題と検証結果 | 判断と変更 |
|---|---|
| 単純な拡縮だけでは、同じ石が転がって伸びるように見えない | 共通トポロジーと非対称な凹凸を維持し、回転と伸長を同じ基準メッシュへ適用 |
| 押した形が指への追従として読めない | 中央の局所押圧と手前への引っ張りを組み合わせ、端部へ滑らかに接続 |
| 復元とパンへの切替を曖昧にすると反発が弱い | c01を1露光の反発にし、b01へのハードカットを採用 |
| 旧承認形状と作業ファイルの一部が一致しなくなった | STLハッシュと保存メッシュ指紋を分けて検査し、必要な旧シーンを固定入力として回復 |
| 複数の検討シーンに現行形状が分散 | 13ポーズの統合シーンを用意し、元STLと頂点座標が一致することを確認 |

## 検証結果

[統合manifest](../previews/stone-to-bread/full-sequence-v1/manifest.json)を現行の寸法、露光、配置、ハッシュの正本とする。
12 STLは元の幾何検証で閉鎖性、manifold、単一連結、法線、退化面、検出対象の交差、接地と支持を確認した。
統合時には12 STLのSHA-256と13個の保存メッシュ指紋を照合した。
パンの実物への適合、網羅的な肉厚、FDM強度、スライス、実撮影は未検証。

## 現行成果物と依存入力

- [統合Blend](../models/stone-to-bread-full-sequence-v1.blend)、[選定GIF](../previews/stone-to-bread/full-sequence-v1/sequence-realistic-deliberate.gif)、[構成PNG](../previews/stone-to-bread/full-sequence-v1/)
- 石r01–r07：[STL](../exports/stone-to-bread/rolling-elongating-study-v4/)
- 石p01–p04：[STL](../exports/stone-to-bread/pulling-study-v1/)
- 石c01：[STL](../exports/stone-to-bread/recoil-study-v1/)
- [統合生成器](../scripts/stone_to_bread_full_sequence.py)、[伸長](../scripts/stone_to_bread_rolling_elongating_study_v4.py)、[引っ張り](../scripts/stone_to_bread_pulling_study.py)、[反発](../scripts/stone_to_bread_recoil_study.py)

STLの旧Study名は現行12形状の保存先であり、削除対象ではない。
編集・再構成の入力は統合Blendと統合manifestに集約した。全13形状のメッシュ指紋、配置、12 STLとの頂点一致を検査する。
伸長・引っ張り・反発の形状計算は各生成器に残し、引っ張りと反発は統合Blendのr07・p04・b01を読む。
旧Blend4件と旧反発の比較メッシュは不要になった。
`exports/stone-to-bread/frame-01.stl`はFireworksの形状生成用の元石として保持する。

撮影プレビューの再構成はBlenderで`stone_to_bread_full_sequence.py -- --output-root <別の一時ディレクトリ>`を実行する。
形状・STL照合だけなら隔離コピーで`--validate-only`を使う。別テンポ・無彩色の比較出力は保存しない。
共有`stone_to_bread.py`と`generate.py`、`review_previews.py`も必要。
撮影ではパンを実物へ交換し、STLはmmとして読み込む。
