# 日本語訳の表記方針

説明文は日本語にし、手法名・専門用語・ソフトウェア名は英語で残す。
例：「Metadynamics 法とは BiasPotential を積み上げて自由エネルギーを計算する手法である。」

| 用語 | 日本語の説明文での表記 |
| --- | --- |
| metadynamics | Metadynamics |
| bias potential | BiasPotential |
| umbrella sampling | Umbrella Sampling |
| collective variable | Collective Variable (CV) |
| reweighting | Reweighting |
| replica exchange | Replica Exchange |
| block averaging | Block Averaging |
| ensemble | Ensemble |
| bootstrap | Bootstrap |
| WHAM, OPES, VES, FISST | 略称をそのまま使用 |
| PLUMED, GROMACS, OpenMM, PyTorch | 製品名をそのまま使用 |
| free energy | 自由エネルギー |
| statistical error | 統計誤差 |

入力例・コマンド・変数名・ファイル名・数式・リンク先は原文を維持する。
`.po` の `msgid` は原文との照合に使うため変更せず、日本語は `msgstr` に記載する。
未訳の `msgstr` は空欄のままとし、英語をコピーして翻訳済みに見せない。
手法名だけの見出しやコードリテラルなど、英語の維持が必要な単位では同一の値を使用する。
