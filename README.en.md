[🇯🇵 日本語](README.md) | [🇬🇧 English](README.en.md)

# wiki-guessur

A benchmark that recovers which Wikipedia article a stripped lead sentence belongs to, using a combination of a fixed-coefficient formula, a retrained GBDT, and LLM re-judgment — and measures whether the answer still holds up when the corpus is regenerated.

Saying "an LLM (or RAG) solves it" and stopping there leaves nothing behind about what actually made it work. This repo tackles a single task — mapping an article title to its title-stripped body text — with two base scorers (a formula whose coefficients a human fixed, and a learned model whose coefficients a machine fits) plus an optional LLM re-judgment layer on top (consulted only on close calls), across all four combinations, to make the character differences between these approaches measurable rather than assumed.

## Results

Mean and standard deviation of MRR across 5 seeds (0–4).

| method | mean | stdev |
|---|---|---|
| formula (formula only) | 0.8383 | 0.0060 |
| formula+llm | 0.8528 | 0.0050 |
| gbdt (learned only) | 0.8580 | 0.0065 |
| gbdt+llm | 0.8735 | 0.0058 |
| mention-max (trivial baseline) | 0.7277 | 0.0053 |
| mention-min | 0.3573 | 0.0096 |
| random | 0.4716 | 0.0084 |

Both engineered methods (formula and GBDT) clearly beat the trivial baseline (picking by mention count alone) and random, with stable distributions (stdev around 0.006). The gap between formula and GBDT is under 0.02 — the self-adapting learned method has a slight edge, but the difference is not large.

The LLM re-judgment layer lifts scores consistently across all seeds 0–4 (+0.0145 on the formula side, +0.0155 on the GBDT side). However, the LLM's own accuracy on the cases it's asked to judge drops as the base scorer gets stronger (80–91% on formula's close calls, 63–75% on GBDT's). The stronger the base scorer, the more thoroughly it has already exploited the available cues, so the close calls that remain tend to be the genuinely ambiguous ones. See [Design Decisions](#design-decisions) for details.

Sweeping the difficulty knob (max candidate count k) degrades both formula and GBDT monotonically as candidates increase; this sweep alone doesn't reveal much difference in robustness between the two methods.

| method | k=2 | k=4 | k=6 | k=8 | k=10 |
|---|---|---|---|---|---|
| formula | 0.9335 | 0.8768 | 0.8514 | 0.8414 | 0.8383 |
| gbdt | 0.9395 | 0.8921 | 0.8696 | 0.8618 | 0.8580 |

To reproduce, see `report` under [Reproduce](#reproduce).

## Method

Strip the lead sentence (the "X is a ..." opening line) from a Wikipedia article's body text. Present the remaining body along with a pool of candidate titles, and have each method guess which candidate is the correct title. The candidate pool includes the correct title plus a few decoys — other articles that link to the correct title (they mention it, but aren't it). Wikipedia articles tend to repeat their own name throughout the body, while incoming links from other articles usually don't use the exact title as anchor text. Stripping the lead sentence removes one self-identification cue, but the frequency with which the name appears elsewhere in the body remains a usable signal. How fully each method exploits that remaining signal is what distinguishes the four approaches.

Evaluation uses MRR (Mean Reciprocal Rank). For each article, take the reciprocal of the rank at which the correct candidate appears (1/1 if ranked first, 1/2 if second, etc.) and average across all articles. This is a standard metric in search and recommendation ranking evaluation. Unlike Precision@k, Recall@k, or Hit Rate@k — which only ask "was it ranked first?" — MRR distinguishes a correct answer that landed at rank 2 from one that landed at rank 10. Tasks with graded relevance typically use a weighted metric like NDCG, but since this task's correct answer is singular within the candidate pool (no graded relevance), plain MRR is sufficient.

The primary evaluation axis isn't a single MRR run but the distribution (mean and variance) of MRR across corpora regenerated per seed. The question isn't "can it get one right," but "does it keep getting it right as the distribution shifts."

The four methods compared are "2 base scorers (formula / GBDT) × with or without the LLM re-judgment layer." For the full task definition, corpus generation scale, and implementation details, see [docs/method.md](docs/method.md).

## Reproduce

Not distributed as a package. Clone it and run with uv. The setup is designed so that the same procedure, same seeds, and same dump version (pinned in config.toml) reproduce the same numbers; no other environment or use case is guaranteed.

```console
$ uv sync
$ uv run wiki-guessur fetch              # fetch jawiki cirrussearch dump (~8.2GB, idempotent)
$ uv run wiki-guessur generate --seed 0  # generate corpus (deterministic per seed)
$ uv run wiki-guessur eval --method formula --seed 0        # measure MRR for one configuration
$ uv run wiki-guessur eval --method gbdt --seed 0 --llm     # with the LLM re-judgment layer (requires GEMINI_API_KEY)
$ uv run wiki-guessur compare --seeds 0..4   # generate + evaluate all methods + aggregate, in one go
$ uv run wiki-guessur diagnose --seeds 0..4  # diagnostic stats (mention rate, candidate count distribution, random baseline)
$ uv run wiki-guessur sweep --seeds 0..4     # sweep the difficulty knob (max candidate count)
$ uv run wiki-guessur report                 # MRR matrix by method × seed, plus the sweep table
```

`fetch` involves downloading a ~8.2GB dump. If you only want to read the results, or just want to evaluate your own method against an existing corpus, you don't need the dump — extract the pre-generated corpora (seeds 0–4) attached to [Releases](https://github.com/yktsnet/wiki-guessur/releases/tag/corpora-20260712), and `eval` onward is enough.

```console
$ curl -LO https://github.com/yktsnet/wiki-guessur/releases/download/corpora-20260712/corpora-seed-0.tar.gz
$ tar xzf corpora-seed-0.tar.gz -C corpora/
```

LightGBM (the gbdt method) requires libomp. On macOS without homebrew, pass libomp's lib directory via `DYLD_LIBRARY_PATH` (with Nix, `nixpkgs#llvmPackages.openmp`).

Code is licensed under MIT ([LICENSE](LICENSE)). The Wikipedia body text included in the Releases corpora is under CC BY-SA. Source: Wikipedia ([jawiki cirrussearch dump](https://dumps.wikimedia.org/other/cirrus_search_index/), as of 20260712). Reuse requires attribution and license inheritance.

## Design Decisions

- **Source is direct parsing of the cirrussearch dump.** It's the only candidate that provides both body text and the link graph without needing a wikitext parser. The dump version is pinned by date in `config.toml`, so the only variable in the robustness evaluation is the seed.
- **The exact-match penalty was rejected after being disproven.** The initial hypothesis — "decoys are likely to contain the article title" — was contradicted by measurement: 65% of correct bodies contain their own title (vs. 35% for decoys). The formula method settled on plain TF-IDF similarity alone.
- **The learned method is LightGBM's lambdarank.** Since the task is ranking, not binary classification, ranking learning is used rather than classification.
- **The LLM is a re-judgment layer, not a fourth method.** It only overrides when the base scorer's top-2 candidates are close. Its effectiveness is structurally tied to the strength of the base scorer, and that dependency is itself part of what's being compared.
- **The corpus is attached to Releases; the 9GB dump is left for each user to fetch themselves.** Most users only want to read the results or evaluate against an existing corpus, and the corpus alone is sufficient for that.

For the full decision process (including disproven hypotheses and alternatives considered and dropped), see [docs/design-decisions.md](docs/design-decisions.md).

## Scope

**Focus**: A self-contained task of mapping article titles to title-stripped bodies, sourced from Wikipedia dumps. Comparing the character differences between formula, GBDT, and the LLM re-judgment layer — not just on accuracy, but on robustness (the MRR distribution) across multiple seeds.

For the contractual guarantees enforced by tests (what is promised and what isn't), see [docs/guarantees.md](docs/guarantees.md).

**Out-of-Scope**: Adding embedding/BERT-based methods. Full parameterization of the difficulty knob (only the max candidate count is implemented; a knob for the amount of removed text is deferred due to regeneration cost). Parallelization. Packaging / registry publication. Bringing in external problem definitions or data (all source material and generation is derived from Wikipedia dumps).
