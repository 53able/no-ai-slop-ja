# No AI Slop JA

日本語の下書きから定型的な「AIっぽさ」を取り除き、書き手自身の語彙、リズム、迷い、ユーモアを残すためのAgent Skillです。

文章を一律に短くしたり、丁寧で無難な文体へそろえたりはしません。観察できるパターンだけを手掛かりに、必要な箇所を最小限直します。

## できること

- **改稿**: 日本語固有の不自然さを直し、全文と変更点を返す
- **検出**: 該当箇所、パターン名、理由、直し方だけを示す
- **声の保持**: 書き手の語彙、文の長短、断定の強さ、ユーモア、専門性を守る
- **根拠の保護**: 引用、数値、固有名詞、URL、出典を勝手に変えない

AI検出器ではありません。文章がAIによって書かれたかどうかを推測せず、「AIらしさ」の点数も出しません。

## 対象にするパターン

日本語固有のパターンを中心に点検します。

- 主体のない受け身
- 「ことができます」などの「こと」の殻
- 「の」の連鎖
- 漢語サ変名詞の渋滞
- カタカナ抽象語の重なり
- 修飾先の迷子と無言の主語交代
- 一文への詰め込み
- 責任を隠す過剰敬語
- 文末の単調な反復
- 根拠のない「注目されています」「専門家は指摘します」
- 二項対立、重要性の自己申告、抽象的な締め、装飾過多

各パターンには誤検知を避ける条件があります。技術用語、法令文、引用、文学的な表現などを機械的に言い換えません。全21項目は [`SKILL.md`](skills/no-ai-slop-ja/SKILL.md) で確認できます。

## インストール

利用する製品の仕様は変わることがあります。以下は製品ごとの入口です。現在の配置方法と利用条件は、リンク先の公式文書を確認してください。

### 汎用インストーラー

[`skills` CLI](https://skills.sh/docs) を使う環境では、次のコマンドでこのリポジトリから対象スキルを選べます。

```sh
npx skills add 53able/no-ai-slop-ja --skill no-ai-slop-ja --global --yes
```

ローカルのチェックアウトでは、ネットワークを使わず次のように検出できます。

```sh
npx skills add . --list
```

### ChatGPT

ChatGPTで利用できるスキルの作成方法と提供条件は、[OpenAIのBuilding skills公式文書](https://learn.chatgpt.com/docs/build-skills) を確認してください。このリポジトリは `skills/no-ai-slop-ja` を配布単位にしていますが、GitHub URLからの直接インストールには対応状況を確認していません。公式文書で案内される方法に従ってください。

### Codex

Codexのスキル配置と呼び出しは、[OpenAIのBuilding skills公式文書](https://learn.chatgpt.com/docs/build-skills) を参照してください。インストール後は通常の日本語で依頼できます。リポジトリ内のOpenAI用メタデータは `skills/no-ai-slop-ja/agents/openai.yaml` にあります。

### Claude Code

Claude Codeのスキル配置と呼び出しは、[AnthropicのSkills公式文書](https://code.claude.com/docs/en/skills) を参照してください。文書で案内される個人用またはプロジェクト用の場所へ `skills/no-ai-slop-ja` ディレクトリを配置し、自然言語で改稿または検出を依頼します。

## 使い方

### 改稿する

```text
no-ai-slop-jaを使い、次の文章を私の語り口を残して改稿してください。

（本文）
```

出力は、改稿後の全文と短い「変更点」です。例は [`examples/edit.md`](examples/edit.md) にあります。

### 検出だけ行う

```text
no-ai-slop-jaを使い、次の文章を書き換えず、該当するパターンだけ検出してください。

（本文）
```

検出では原文を書き換えません。例は [`examples/detect.md`](examples/detect.md) にあります。

## 限界

- AIによる執筆か、人間による執筆かは判定できません。
- 文章の正確性、引用元、法的妥当性を自動で保証しません。
- 小説、広告、スピーチ、法令、社内規程では、一般的な文章とは異なるリズムや定型が必要です。
- 改稿結果は、公開前に書き手自身が事実、意図、語調を確認してください。
- 単発パイロットの結果は、記録したモデル、実行環境、コミット、ケースだけに適用され、一般的な性能や誤検知率を示しません。

## 検証

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build_plugin.py --check
npx --yes skills add . --list
uvx --from skills-ref agentskills validate ./skills/no-ai-slop-ja
```

プラグインZIPを作る場合:

```sh
python3 scripts/build_plugin.py
```

`tests/cases.json` は、期待するパターン名、保持対象、反例を記述した宣言的なケース集です。テストは構造と網羅性を検証しますが、言語モデルを実行して出力品質を測るものではありません。

実モデルの出力を任意で確認する場合は、[`tests/evaluation/README.md`](tests/evaluation/README.md) の単発パイロット手順を使います。生出力を保存し、別の判定者が意味保持、過剰修正、誤検知、形式を評価します。これは特定の一回を記録する手順であり、ベンチマークではありません。

保存した生出力と判定結果は、次のコマンドで検証・集計できます。スクリプト自体はモデルを実行せず、欠けた結果を生成しません。

```sh
python3 scripts/validate_evaluation.py --raw raw-output.json --judged judged-results.json
```

## 構成

- [`skills/no-ai-slop-ja/SKILL.md`](skills/no-ai-slop-ja/SKILL.md): 手順とパターン
- [`skills/no-ai-slop-ja/eval.md`](skills/no-ai-slop-ja/eval.md): 改稿・検出別の評価表
- [`skills/no-ai-slop-ja/agents/openai.yaml`](skills/no-ai-slop-ja/agents/openai.yaml): OpenAI用メタデータ
- [`tests/cases.json`](tests/cases.json): 正例、反例、声と事実の保持ケース
- [`tests/evaluation/README.md`](tests/evaluation/README.md): 任意の単発パイロット評価手順
- [`scripts/validate_evaluation.py`](scripts/validate_evaluation.py): 生出力と独立判定の検証・集計CLI
- [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json): プラグインメタデータ

## 原著とライセンス

このプロジェクトは、Peter Yang氏の [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop) を基に、日本語の文法、語順、敬語、語彙選択に合わせて再設計した派生物です。参照した原著の版は [`d30eddb9e04562234f2070b5ee63ca4649d9a05e`](https://github.com/petergyang/no-ai-slop/tree/d30eddb9e04562234f2070b5ee63ca4649d9a05e) です。

原著と本プロジェクトはMIT Licenseで提供されます。詳細は [`LICENSE`](LICENSE) と [`NOTICE`](NOTICE) を参照してください。
