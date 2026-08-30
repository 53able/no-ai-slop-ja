# 2026-08-30 Pi worker 単発パイロット

## 目的

`no-ai-slop-ja`が、意味を保ちながら定型表現を処理できるかを、選択済みの8ケースで確認した単発パイロットです。モデル全般や別の実行環境へ一般化できるベンチマークではありません。

## 評価元

- Source commit: `6a6a81f4227855cf5292c5d7e99ec1f0808890e2`
- Skill: [`raw-output.json`](raw-output.json) の `source.skillPath` と `source.skillSha256`
- Cases: [`raw-output.json`](raw-output.json) の `source.casesPath` と `source.casesSha256`
- Runner: `pi-subagent/worker run 32866350 children 0-7`
- Generator model: `openai-codex/gpt-5.6-sol:high`（8子実行のランタイム記録で一致）
- Judge model: `openai-codex/gpt-5.6-sol:high`（独立判定実行のランタイム記録）
- Prompt construction: `runner-read-verbatim-repo-files`

## 事前に選んだケース

結果を見る前に、次の8ケースを対象にしました。

- `p01-passive-hidden-actor`: 主体を捏造しないか
- `p08-overpacked-sentence`: 因果と不確実さを残せるか
- `p10-ending-repetition`: 命題を変えず反復だけを直せるか
- `p15-weasel-attribution`: 出典を作らず不足を指摘できるか
- `c01-technical-katakana`: 定着した技術用語を誤検出しないか
- `c03-literary-fragment`: 文学的な短文を誤検出しないか
- `r01-preserve-facts-and-voice`: 日付、数値、口調を保持できるか
- `a01-authorship-refusal`: AI執筆の採点を拒否できるか

## 実行上の記録

各ケースを別の新規サブエージェント会話で実行しました。一部の子実行では、実験の「応答本文だけを返す」という条件と、実行基盤が自動付与した受入報告形式が競合しました。監督側から応答本文を優先し、リポジトリへ書き込まないよう指示しました。8件の応答本文は加工せず[`raw-output.json`](raw-output.json)へ保存しています。

## 独立判定

生成とは別の新規サブエージェント会話が、[`tests/evaluation/README.md`](../../README.md)の12項目で判定しました。その後、別のレビュアーが`pass`と`not-applicable`の適用を監査し、4件の`modality`区分と監査メモを訂正しました。出力そのものと合否は変更していません。

- Raw outputs: [`raw-output.json`](raw-output.json)
- Judgments: [`judged-results.json`](judged-results.json)
- Validator-derived summary: [`summary.json`](summary.json)

## この実行の結果

判定済み8ケースのうち、いずれかのチェックが`fail`になったケースは0件でした。内訳は[`summary.json`](summary.json)から生成したものです。

この結果は、上記source commit、runner、model、8ケース、この一回の出力だけに適用します。同じモデルを使った反復実行、複数モデル比較、実利用文の標本抽出を行っていないため、成功率や誤検知率として一般化しません。

## 再検証

source commitのチェックアウトで実行します。

```sh
python3 scripts/validate_evaluation.py \
  --raw tests/evaluation/runs/2026-08-30-pi-worker/raw-output.json \
  --judged tests/evaluation/runs/2026-08-30-pi-worker/judged-results.json \
  --expected-source-commit 6a6a81f4227855cf5292c5d7e99ec1f0808890e2
```
