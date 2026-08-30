# 単発パイロット評価プロトコル

この手順は、特定の実行環境におけるモデル出力を保存し、別の判定者が確認するためのものです。**ベンチマークではありません。** モデル全般、このスキル全般、別の実行日時への性能を一般化しません。

## 1. 評価元を固定する

1. 変更のないチェックアウトを用意する。
2. `git rev-parse HEAD` で40桁のsource commitを記録する。
3. 次の二つをSHA-256で記録する。
   - [`skills/no-ai-slop-ja/SKILL.md`](../../skills/no-ai-slop-ja/SKILL.md)
   - [`tests/cases.json`](../cases.json)
4. 実行対象のcase IDを先に決める。結果を見てケースを追加・削除しない。

source commit、二つのファイルハッシュ、case IDは、生出力JSONと判定JSONに保存します。評価後にファイルを変更した場合は、新しいsource commitで別の実行として扱います。

## 2. 実行者を記録する

生出力JSONの`runner`に次を記録します。

- `identity`: CLI、エージェント、APIなど、実行経路を識別できる名前
- `model`: 実行環境が報告したモデル識別子

モデル識別子が実行環境から提供されない場合は、推測せず`not-reported-by-runtime`と記録します。この記録しかない結果を、特定モデルの評価結果として扱ってはいけません。

## 3. プロンプトを構築する

各case IDを独立した新しい会話で実行します。`SKILL.md`と`cases.json`は、source commitにあるUTF-8本文を一字も変更せず使います。プロンプトは次の順序で連結します。

```text
<skills/no-ai-slop-ja/SKILL.md の全文>

--- CASES.JSON ---
<tests/cases.json の全文>

--- TARGET CASE ID ---
<case ID>

上記スキルを適用し、TARGET CASE IDのinputだけを処理してください。modeと出力形式を守り、応答本文だけを返してください。
```

生出力JSONの`promptConstruction`には`skill-md-verbatim-plus-case-json`を記録します。モデルへ送った後の応答は、整形、誤字修正、前後の削除をせず`outputs[].output`へ保存します。

## 4. 生出力を保存する

生出力JSONは次のスキーマに従います。これは記入形式の説明であり、実行結果ではありません。

- `schemaVersion`: `1`
- `kind`: `no-ai-slop-ja-raw-output`
- `source`: `sourceCommit`、二つの相対パスとSHA-256、`casesSchemaVersion`
- `runner`: `identity`と`model`
- `promptConstruction`: `skill-md-verbatim-plus-case-json`
- `outputs`: `caseId`と未加工の`output`

`outputs`は実行前に選んだcase IDと一対一にします。失敗した呼び出しを黙って除外せず、再試行した場合は実行記録であることが分かる別ファイルとして保存します。

## 5. 独立して判定する

生出力を作った実行者とは別の会話または担当者が判定します。判定者は原文、ケースの期待値、生出力、同じsource commitの`SKILL.md`だけを読みます。書き換え案は作らず、各チェックを`pass`、`fail`、`not-applicable`のいずれかで記録します。

### 意味の不変条件

- `actor`: 主体、経験者、対象を変えていない
- `action`: 行為を削除、追加、変更していない
- `tenseAspect`: 時制、完了、継続、反復、実施済みかどうかを変えていない
- `modality`: 可能、義務、予定・意志、実績を変えていない
- `certainty`: 断定、推測、伝聞、保留の強さを変えていない
- `causalRelation`: 原因、条件、結果、目的を変えていない
- `numbers`: 数値、単位、日時、期間、順序を変えていない
- `quotes`: 引用範囲と引用文を変えていない
- `sources`: URL、著者、文献、帰属と主張の対応を変えていない

### タスク品質

- `patternHandling`: 期待するパターンを処理し、反例を誤検出していない
- `overEditing`: 問題のない声、専門語、崩しを過剰に直していない
- `outputFormat`: 改稿・検出・執筆判定拒否の形式を守っている

原文に対象要素がないチェックだけを`not-applicable`にします。一つでも`fail`があれば、そのケースは不合格です。`notes`には判断根拠となる最小限の引用または差分を記録します。

判定JSONには次を保存します。

- `schemaVersion`: `1`
- `kind`: `no-ai-slop-ja-judged-results`
- `source`: 生出力と同じsource情報
- `judge`: 判定者の`identity`と、利用した場合は`model`
- `rawSha256`: 生出力JSONそのもののSHA-256
- `judgments`: `caseId`、12項目の`checks`、`notes`

## 6. 検証して集計する

```sh
python3 scripts/validate_evaluation.py \
  --raw path/to/raw-output.json \
  --judged path/to/judged-results.json \
  --expected-source-commit "$(git rev-parse HEAD)"
```

全ケースを実行した場合は`--require-all-cases`も指定します。CLIはスキーマ、ファイルハッシュ、source commit、case IDの対応、生出力との結び付きを検証し、判定済みの件数だけを集計します。モデルを呼び出したり、欠けた結果や判定を生成したりはしません。

## 解釈上の制限

- この結果は、記録したsource commit、runner、model、case ID、実行時点だけに適用します。
- 単発実行から誤検知率や成功率を一般化しません。
- 同じプロンプトでもモデルやサービスの更新、サンプリング、会話状態で結果は変わります。
- ケース集は設計上の回帰確認用であり、実利用文の代表標本ではありません。
- 複数モデルや複数回の比較、統計的推定をしていないため、**これはベンチマークではありません。**
