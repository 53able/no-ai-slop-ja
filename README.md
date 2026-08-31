<p align="center">
  <strong>English</strong> · <a href="./README.ja.md">日本語</a>
</p>

<h1 align="center">No AI Slop JA</h1>

<p align="center">
  <strong>Remove formulaic AI-like Japanese without erasing the writer's voice.</strong>
</p>

`no-ai-slop-ja` is an Agent Skill for removing formulaic “AI-like” patterns from Japanese drafts while preserving the writer's vocabulary, rhythm, hesitation, humor, and expertise.

It does not shorten every sentence or normalize the draft into uniformly polite, inoffensive prose. It uses observable patterns to make the smallest necessary edits.

## Capabilities

- **Edit**: Fix Japanese-specific awkwardness and return the complete revision with a short change summary
- **Detect**: Report only the affected passage, pattern name, reason, and suggested fix
- **Preserve voice**: Keep the writer's vocabulary, sentence-length variation, degree of certainty, humor, and expertise
- **Protect evidence**: Do not silently alter quotations, numbers, proper nouns, URLs, or sources

This is not an AI detector. It does not guess whether a text was written by AI or assign an “AI-likeness” score.

## Patterns it checks

The Skill focuses on patterns specific to Japanese prose, including:

- Passive constructions with no identifiable actor
- Empty nominal shells such as 「ことができます」
- Long chains of 「の」
- Congestion of Sino-Japanese verbal nouns
- Stacks of abstract katakana terms
- Stranded modifiers and silent subject changes
- Too many ideas packed into one sentence
- Excessive honorifics that obscure responsibility
- Monotonous sentence-ending repetition
- Unsupported phrases such as 「注目されています」 and 「専門家は指摘します」
- Forced binaries, self-declared importance, abstract conclusions, and decorative excess

Each pattern includes safeguards against false positives. The Skill does not mechanically rewrite technical terms, legal language, quotations, or deliberate literary expression. See all 21 patterns in [`SKILL.md`](skills/no-ai-slop-ja/SKILL.md).

## Installation

Product behavior can change. The sections below provide entry points for each supported environment; check the linked official documentation for current placement rules and requirements.

### General-purpose installer

In environments that use the [`skills` CLI](https://skills.sh/docs), select this Skill from the repository with:

```sh
npx skills add 53able/no-ai-slop-ja --skill no-ai-slop-ja --global --yes
```

#### If you use PromptScript

[PromptScript](https://getpromptscript.dev/latest/getting-started/) generates configuration files for tools such as Claude Code, GitHub Copilot, and Cursor from a single `.prs` definition. Skip this section if you do not use PromptScript.

The `skills` CLI detects PromptScript when the current project contains a `.promptscript/` directory or `promptscript.yaml`. In the current [`skills` CLI definition](https://github.com/vercel-labs/skills/blob/main/src/agents.ts), PromptScript does not support global installation. The command above may therefore finish with `PromptScript does not support global skill installation` even when installation succeeded for other detected agents. That message does not affect the Skill itself or agents reported as successful.

To install it for PromptScript, run the command from the target project root without `--global` and select PromptScript explicitly:

```sh
npx skills add 53able/no-ai-slop-ja \
  --skill no-ai-slop-ja \
  -a promptscript \
  --yes
```

From a local checkout, list the detected Skill without network access:

```sh
npx skills add . --list
```

### ChatGPT

See OpenAI's official [Building skills documentation](https://learn.chatgpt.com/docs/build-skills) for the current process and availability requirements. This repository distributes `skills/no-ai-slop-ja` as the Skill directory, but direct installation from a GitHub URL has not been verified. Follow the method described in the official documentation.

### Codex

See OpenAI's official [Building skills documentation](https://learn.chatgpt.com/docs/build-skills) for Skill placement and invocation in Codex. After installation, invoke the Skill with a normal Japanese request. OpenAI-specific metadata is stored in `skills/no-ai-slop-ja/agents/openai.yaml`.

### Claude Code

See Anthropic's official [Skills documentation](https://code.claude.com/docs/en/skills) for placement and invocation. Put the `skills/no-ai-slop-ja` directory in the documented personal or project location, then request either editing or detection in natural language.

## Usage

### Edit a draft

```text
Use no-ai-slop-ja to revise the following Japanese text while preserving my voice.

(Text)
```

The output contains the complete revised text and a short change summary. See [`examples/edit.md`](examples/edit.md) for an example in Japanese.

### Detect patterns without rewriting

```text
Use no-ai-slop-ja to inspect the following Japanese text without rewriting it. Report only the matching patterns.

(Text)
```

Detection mode does not rewrite the source text. See [`examples/detect.md`](examples/detect.md) for an example in Japanese.

## Limitations

- It cannot determine whether a text was written by AI or by a person.
- It does not guarantee factual accuracy, source validity, or legal suitability.
- Fiction, advertising, speeches, legislation, and internal policies may require rhythms and conventions that differ from general prose.
- Before publication, the writer must review the result for facts, intent, and tone.
- A recorded one-off pilot applies only to its documented model, runtime, commit, and cases. It does not establish general performance or a false-positive rate.

## Validation

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build_plugin.py --check
npx --yes skills add . --list
uvx --from skills-ref agentskills validate ./skills/no-ai-slop-ja
```

To build the plugin ZIP:

```sh
python3 scripts/build_plugin.py
```

`tests/cases.json` is a declarative case set that records expected pattern names, content that must be preserved, and counterexamples. The tests validate structure and coverage; they do not run a language model or measure output quality.

For an optional one-off evaluation with a real model, follow [`tests/evaluation/README.md`](tests/evaluation/README.md). The procedure saves raw outputs and asks a separate judge to assess meaning preservation, over-editing, false positives, and output format. It records one specific run and is not a benchmark.

The first recorded pilot used `openai-codex/gpt-5.6-sol:high` to run eight preselected cases in separate conversations. An independent judgment marked zero cases as `fail`. Raw outputs, judgments, aggregate results, and limitations are stored in [`tests/evaluation/runs/2026-08-30-pi-worker/`](tests/evaluation/runs/2026-08-30-pi-worker/). This single run must not be interpreted as a general success rate or false-positive rate.

Validate and aggregate saved raw outputs and judgments with:

```sh
python3 scripts/validate_evaluation.py --raw raw-output.json --judged judged-results.json
```

The script does not run a model or generate missing results.

## Repository layout

- [`skills/no-ai-slop-ja/SKILL.md`](skills/no-ai-slop-ja/SKILL.md): Procedure and pattern catalog (Japanese)
- [`skills/no-ai-slop-ja/eval.md`](skills/no-ai-slop-ja/eval.md): Evaluation rubric for editing and detection (Japanese)
- [`skills/no-ai-slop-ja/agents/openai.yaml`](skills/no-ai-slop-ja/agents/openai.yaml): OpenAI metadata
- [`tests/cases.json`](tests/cases.json): Positive cases, counterexamples, and voice/evidence preservation cases
- [`tests/evaluation/README.md`](tests/evaluation/README.md): Optional one-off pilot procedure (Japanese)
- [`scripts/validate_evaluation.py`](scripts/validate_evaluation.py): CLI for validating and aggregating raw outputs and independent judgments
- [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json): Plugin metadata

## Upstream project and license

This project is a derivative of Peter Yang's [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop), redesigned for Japanese grammar, word order, honorifics, and vocabulary choices. It is based on upstream revision [`d30eddb9e04562234f2070b5ee63ca4649d9a05e`](https://github.com/petergyang/no-ai-slop/tree/d30eddb9e04562234f2070b5ee63ca4649d9a05e).

The upstream project and this derivative are available under the MIT License. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
