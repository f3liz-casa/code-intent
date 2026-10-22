# Code Intent: terms, name check and embedding survey

> Update 2026-10-20: the project name was changed to **Code Intent** by the project owner. Section 3 was written before that decision; sections 5 and 6 add follow-up research, and section 8 restates the project goal after the owner's clarification (style/paradigm as the carrier of intent), section 10 adds the second goal (pause and capture the human's intent before AI writes code), and section 12 adds the third (style drift as a signal to refactor or re-architect).

Project goal (from the topic): a usable, high-level, language-agnostic layer like LSP, but expressing a code's natural-language-like purpose clearly for humans, possibly built on code embeddings.

Evidence levels: **[fetched]** = I read the source page this session. **[recall]** = from background knowledge, not re-checked; verify before citing.

## 1. Key terms

| Term | Working definition | Source |
|---|---|---|
| **Program / code semantics** | The meaning or behavior of a program. In ML papers it is not one thing: SemCoder splits it into *approximate* (overall goals, as in docstrings), *symbolic* (meaning from symbols, syntax, structure), *operational* (how each step changes state) and *abstract* (properties that hold for all inputs). | [SemCoder](https://arxiv.org/pdf/2406.01006) [fetched] |
| **Semantics, operational view** | inst2vec treats semantics as the effect of each step on system state and resources; two statements are similar if they consume the same resources. | [Neural Code Comprehension](https://arxiv.org/pdf/1806.07336) [fetched] |
| **LSP** (Language Server Protocol) | A protocol between an editor/IDE and a language server, using JSON-RPC, so language features (completion, go to definition, find references, hover docs) are built once per language instead of once per tool. Current spec 3.18. | [LSP site](https://microsoft.github.io/language-server-protocol/) [fetched] |
| **LSIF** | Language Server Index Format: precomputed code-navigation data so tools or web UIs can navigate without a local copy of the source. Graph encoding with opaque numeric IDs. | [LSP site](https://microsoft.github.io/language-server-protocol/), [SCIP post](https://sourcegraph.com/blog/announcing-scip) [fetched] |
| **SCIP** | "SCIP Code Intelligence Protocol": Sourcegraph's Protobuf indexing format for go to definition / find references, using human-readable string symbol IDs. Created because LSIF was slow, hard to debug and hard to index incrementally. Reported about 4x smaller than LSIF gzipped. | [Sourcegraph blog](https://sourcegraph.com/blog/announcing-scip) [fetched] |
| **tree-sitter** | A parser generator and incremental parsing library. It builds a concrete syntax tree and updates it as the file is edited. Goals: general, fast, robust to syntax errors, dependency-free (pure C runtime). It gives syntax only, not meaning. | [tree-sitter README](https://cdn.jsdelivr.net/gh/tree-sitter/tree-sitter@master/README.md) [fetched] |
| **Code embedding** | A dense vector for a code unit (token, statement, function, file) such that similar code or similar purpose lies close together. | See CodeBERT, inst2vec below |
| **CodeBERT** | Bimodal (NL + PL) pre-trained Transformer (RoBERTa-base, about 125M parameters), trained with masked language modeling and replaced token detection. Evaluated on NL code search and code documentation generation. | [CodeBERT](https://arxiv.org/pdf/2002.08155) [fetched] |
| **inst2vec** | Embeddings of LLVM IR statements trained on "contextual flow" (data and control flow). Uses IR because it is source-language independent. This is the closest published example of a language-agnostic representation. | [Neural Code Comprehension](https://arxiv.org/pdf/1806.07336) [fetched] |
| **Code summarization** | Generating human-readable comments, summaries, commit messages or release notes from source artifacts. A literature review covered 41 studies (2010 to 2019). | [Systematic review](https://arxiv.org/pdf/1909.04352) [fetched] |
| **Intent / purpose representation** | What the code is *for*. This matches SemCoder's "approximate semantics" and is what summarization tries to produce. There is no standard formal definition. | inference from the above |
| **Language-agnostic IR** | A representation independent of the source language (e.g., LLVM IR for inst2vec). The trade-off is that compilation may erase names and comments, which are the best purpose signals. | inference |
| **Kythe, Glean, GitHub "semantic"** | Other code-indexing and code-analysis systems with cross-language symbol graphs. | [recall] |

## 2. Where each piece sits

| Layer | What it answers | Examples |
|---|---|---|
| Syntax | What is the structure? | tree-sitter |
| Symbol / navigation | Where is it defined, who references it? | LSP, LSIF, SCIP |
| Behavioral semantics | What does it do on execution? | operational / abstract semantics, inst2vec |
| **Purpose / intent** | **Why does it exist, in plain language?** | code summarization, CodeBERT-style NL-PL embeddings |

LSP and SCIP cover the first two layers and say nothing about purpose. The project targets the fourth layer, and that is the gap.

## 3. Is "Code Semantics" a good name?

**Findings**
- The phrase is established, but in the academic sense of the *behavior or meaning of programs* (SemCoder, inst2vec; a university course is titled "Code Semantics" [search result, not opened]). Readers will expect formal or execution semantics.
- The project's real target is closer to SemCoder's *approximate semantics*, the purpose layer. The name is technically valid but broader than the goal.
- "Code semantics" in industry is often used loosely for "semantic" code search or navigation, which is what LSP/SCIP already do.
- I found no evidence of a standard product or spec named "Code Semantics" in my searches, but I did not check trademarks or package names.

**Alternatives**

| Name | Fit | Concern |
|---|---|---|
| Code Semantics | Broad, familiar, works as an umbrella | Reads as formal semantics; vague about "for humans" |
| Code Intent | Exactly the purpose layer | Less established; sounds like a single feature |
| Code Comprehension | Human-centered, matches "program comprehension" research | Names the human activity, not the artifact |
| Semantic Code Index | Accurate if the output is an index | Sounds like SCIP/LSIF, undersells the natural-language part |
| Code Purpose / Code Gloss | Plain and clear | Less searchable |

**Recommendation.** Keep **Code Semantics** as the project and umbrella name, and define it narrowly in the README as: *a language-agnostic, human-readable description of what code is for, indexed like LSP/SCIP.* Use **Code Intent** as the name for the specific artifact (the per-symbol purpose description) if one is needed. Reason: the umbrella term is recognizable to researchers and engineers, and the narrow definition removes the formal-semantics ambiguity. If you would rather avoid all ambiguity from the start, Code Intent is the strongest standalone alternative.

## 4. Open items
- Not yet checked: Kythe, Glean and GitHub semantic pages (marked [recall]); name collisions on GitHub, PyPI and npm.
- Possible next step: survey NL-PL embedding models newer than CodeBERT (e.g., CodeSearchNet-style retrieval models) and decide how purpose text would be stored alongside SCIP symbols.

## 5. Name collision check for "Code Intent"

Only a quick web search was done; no registry API lookups.
- [intent-code](https://github.com/harsharahul/intent-code) [fetched]: MIT-licensed code-knowledge index for LLM agents (tree-sitter symbol map, PageRank ranking, MCP tools, query by intent such as debugging or review). Also on PyPI as `intent-code`. It is close in *purpose* (index code for retrieval) but is a retrieval tool for agents, not a human-readable purpose description. The name differs slightly ("intent-code" vs "Code Intent").
- Other hits (TanStack "Intent", MCP servers) are unrelated.
- "Code intent" has no formal definition in the literature I found; it is a free phrase, so you can define it. Not checked: trademarks, exact repo/package names `code-intent`.

## 6. Code embedding models after CodeBERT

| Model | What it adds | Source |
|---|---|---|
| **UniXcoder** (2022) | One model for understanding and generation. Takes code, comments and AST (flattened by a one-to-one mapping); contrastive learning over these modalities. | [paper](https://arxiv.org/pdf/2203.03850) [fetched] |
| **CodeXEmbed** (2024) | Embedding family of 400M, 2B and 7B parameters, 12 languages, five retrieval categories (text-to-code, code-to-text, code-to-code, text-to-text, hybrid). Includes code summarization as a training task. The 7B model is reported first on the CoIR leaderboard (about 70.5 NDCG@10 with general training; beats Voyage-Code-002 by over 20%). | [paper](https://arxiv.org/pdf/2411.12644) [fetched] |
| **CodeRankEmbed** (CoRNStack) | Open code retrieval embedder. | listed in search results, not opened |
| **Probing study** (2022) | Pre-trained code models capture syntax well but semantics unevenly (CodeT5 and CodeBERT better on control/data dependencies, UniXcoder worse); larger LLMs not clearly better. | [paper](https://arxiv.org/pdf/2212.10017) [fetched] |

**Implication for Code Intent.** Modern embedders are trained mainly for *retrieval* (text-to-code and code-to-text), which is the closest match to "find code by purpose". But the probing result says embeddings do not reliably encode deeper behavior. So embeddings alone are a weak source of truth for "what is this code for"; a safer design is to generate a natural-language purpose description (summarization), store it next to the symbol (like a SCIP symbol ID), and use embeddings only to search and cluster those descriptions.

## 7. Suggested next steps
1. Decide the artifact: per-symbol purpose record `{symbol id (SCIP-style), intent text, confidence, source hash}`.
2. Check `code-intent` on GitHub, PyPI and npm directly before publishing.
3. Evaluate on CoIR and a small hand-labelled set from a real repo.

## 8. Refined goal: intent should determine style and paradigm

**Owner's clarification (2026-10-20).** Code Intent should help AI choose the code style or software-design paradigm (including which language is used to express the logic) that fits the intent, the way people grasp a whole UX abstractly. A human who sees only the code's style should be able to guess what it does. If that guess fails, the code was written in the wrong style or paradigm. The payoff: experimental projects keep a consistent, easy-to-understand shape as they grow.

**What this changes.** Section 3's artifact (a purpose text per symbol) is necessary but not enough. The core is a *mapping*: intent category, style/paradigm, concrete code shape. It works in two directions:
- **Generate:** given an intent, pick the style/paradigm (and language) that signals it.
- **Check:** given code, infer the intent its style suggests and compare it with the declared intent. A mismatch is a finding ("style says X, intent says Y").

**Related work** (what exists, and what is missing)

| Idea | What it gives | Gap relative to Code Intent | Source |
|---|---|---|---|
| **Coding conventions, Naturalize** | Learns a codebase's style and suggests changes for consistency. Defines a convention as a restriction not imposed by the grammar; about one third of reviews give convention feedback; 94% top-suggestion accuracy on identifier names. | Consistency within a codebase, with no link to *purpose* | [paper](https://arxiv.org/pdf/1402.4182) [fetched] |
| **LLM style inconsistency** | LLM code differs from human code in style: 24 inconsistency types in 5 dimensions; API preference most frequent. | Measures the problem; does not say which style to choose for an intent | [paper](https://arxiv.org/pdf/2407.00456) [fetched] |
| **CodeAlignBench** | Benchmarks following developer-preferred adjustments (constraints and refinements); no model saturated it, especially on semantic and cosmetic instructions. | Instruction-following test, but a possible evaluation base | [paper](https://arxiv.org/pdf/2510.27565) [fetched] |
| **Domain-Driven Design: Ubiquitous Language, Intention-Revealing Interfaces** | Names should "describe their effect and purpose, without reference to the means". A shared language links team activity to the software. | Human practice at the naming/model level; not formalised across paradigms or machine-checkable | [DDD Reference](https://domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_2015-03.pdf) [fetched] |
| **Design pattern detection/recommendation** | Surveys of detecting and recommending patterns (2015 to 2025). | Found in search results only; not opened | [survey](https://avesis.atauni.edu.tr/yayin/53406dad-ce24-4ccc-a41c-eca01b4a3187/a-systematic-and-evolutionary-analysis-of-software-design-pattern-detection-and-recommendation-approaches-20152025) |
| **Repo context files (AGENTS.md)** | Current practice for telling agents the conventions. One ICLR 2026 paper reports context files gave no improvement in task success and raised inference cost by over 20%; it advises minimal requirements. | Free-text rules do not work well, which supports a *structured* intent-to-style mapping over long prose | [paper page](https://iclr.cc/virtual/2026/10021235) [fetched] |
| **Architecture conformance** | Checking code against intended architecture (e.g., ArchUnit-style rules). | [recall] | not verified |

**Finding.** I found work on style consistency, on LLM style gaps, and on naming-for-purpose as a human practice. I did not find a published system that maps *intent categories to style/paradigm choices* and checks code against that mapping. That suggests the idea is open ground, but the search was shallow, so treat it as "not found", not "does not exist".

**Caution from the evidence.** Long free-text conventions can hurt agents (ICLR 2026 paper above). A Code Intent mapping should be short, structured and checkable, not another prose rulebook.

## 9. Proposed next steps (revised)
1. Define a small taxonomy of intents (e.g., data transform, orchestration, I/O boundary, state machine, policy/rule, experiment/prototype) and the style/paradigm that signals each (pure function pipeline, class with lifecycle, declarative table, etc.).
2. Write the check as a "style to intent" guess: show the code without its intent label to a human or model, ask what it does, compare with the declared intent.
3. Pilot on one small experimental repo; measure how often style-only guesses match intent, before and after applying the mapping.
4. Search more deeply for prior art (design-pattern recommendation, architecture conformance, code idiom mining) before claiming novelty.

## 10. Second goal: pause and capture the human's intent before AI writes

**Owner's point (2026-10-20).** In AI-driven development people let AI write features, and AI follows the *best practice* of other people. At that moment it can be better to stop writing and first ask: what is the main purpose, and what detail did you notice in existing services? Nobody makes a creative project without building on their own experience.

**What this adds.** Code Intent then has two halves:
1. **Capture** (before code): record the human's purpose and experience-based details as a short intent record.
2. **Carry** (in code): choose and check style/paradigm against that record (section 8).
Best practice becomes the *fallback*, not the starting point.

**Related work**

| Idea | Finding | Gap | Source |
|---|---|---|---|
| **ClarifyGPT** | Detects ambiguous requirements (by checking whether sampled solutions disagree), asks targeted questions, adds answers to the requirement. GPT-4 Pass@1 on MBPP-sanitized 70.96% to 80.80% with ten human participants. | Clarifies *what to build* to get correct code; does not ask about the person's motivation or experience | [paper](https://arxiv.org/pdf/2310.10996) [fetched] |
| **Curiosity by Design** | Classifier flags unclear queries; a small fine-tuned model asks clarifying questions before code. Users preferred its questions and answers. Part of the study used simulated users. | Same: clarity for correctness, not creative direction | [paper](https://arxiv.org/html/2507.21285v1) [fetched] |
| **Design homogenization in web vibe coding** | Frictionless generation can worsen homogenization; proposes "productive friction" so creators can challenge default outputs. | The closest match to the owner's concern. It targets web design, not code structure | [paper](https://www.alphaxiv.org/abs/2603.13036.md) [fetched] |
| **SpecFirst** | Separates specification elicitation from code synthesis; reports test-pass gains of 6.9% to 21.3% on ProgramBench. | The spec comes from a program binary and docs, not from the human's experience | [paper](https://www.alphaxiv.org/abs/2607.27167.md) [fetched] |
| **Spec-driven development, intent-driven tools** | A current practice of writing specs before agents code. | Found in search results only; not opened | [Allegro blog](https://blog.allegro.tech/2026/06/spec-driven-development-best-practices) |

**Finding.** Prior work asks questions to remove ambiguity or to resolve a spec. The "productive friction" paper is the nearest to the owner's concern about homogenization. I did not find work that asks for the person's *experience and motivation* and stores it as a durable, checkable record tied to the code. Same caveat as section 8: shallow search, "not found".

**Design implications**
- The intent record should hold prompts like: main purpose; what you liked or disliked in existing services (specific details); what must *not* be generic; what you are willing to trade away.
- Ask only when it matters (ClarifyGPT-style trigger), since the AGENTS.md evidence in section 8 says extra requirements can hurt. A short record beats a long form.
- Evidence of success: fewer generic results, plus the style-only guess test from section 9.

## 11. Revised next steps
1. Draft the intent record template (5 or fewer questions) and the intent-to-style taxonomy together.
2. Pilot on one new experimental feature: capture intent first, then let AI build; compare with a no-intent baseline for how generic the result is and whether style-only guesses match the intent.
3. Deeper prior-art search: productive friction, design-pattern recommendation, spec-driven tools.

## 12. Third goal: style drift as a refactoring signal

**Owner's point (2026-10-20).** Code Intent can make AI stop and reconsider style/paradigm. If AI keeps extending code or comments unnecessarily, the current style is no longer right for that part of the code. That is the signal to separate, refactor or re-architect, in DDD terms.

**Mechanism.** Each code region has a declared intent and a style/paradigm chosen for it (section 8). Watch for *drift*: the region grows, collects comments to explain itself, or needs a style-only reader to ask "what is this?". When drift passes a threshold, the agent does not add more; it asks whether the region has become more than one intent, and proposes a split. In DDD terms, a region whose language and rules diverge from its neighbors may be a separate bounded context.

**Related work**

| Idea | Finding | Link to Code Intent | Source |
|---|---|---|---|
| **Code smells** | Classic smells (large class, divergent change, shotgun surgery) are refactoring triggers. One analysis maps 31 smells to "relative essence", the share of code that expresses the core purpose, and argues most problems come from missing modularization. "Comments / Deodorant" is listed as a smell, with extract method as the fix. | Matches the owner's signal: more comments to explain code can mean the structure should change | [smells page](https://sape.inf.usi.ch/essence/algorithmic/smells.html) [fetched] |
| **GitClear, 153M lines (2020 to 2023)** | Churn (code changed or reverted within two weeks) rose from about 3 to 4% to 5.5%. Duplicated code up 11% vs 2021. "Moved" (refactored) code down 17%. Authors suggest AI favors new code over reuse. Correlation with Copilot adoption is not proof of cause. Vendor study, not peer reviewed. | Evidence that AI tends to add rather than restructure, which is why an explicit trigger is needed | [summary](https://arc.dev/developer-blog/impact-of-ai-on-code/) [fetched] |
| **MonoEmbed** | LLM embeddings of a monolith's classes, fine-tuned with contrastive learning, clustered into microservices; scored above Mono2Micro and Code2VecDec in its evaluation (inter-service coupling above average). | Embeddings can cluster code into candidate contexts, which is a way to propose a split | [paper](https://arxiv.org/html/2502.04604v1) [fetched] |
| **DDD bounded contexts** | Language structured around a domain model within a context (see section 8). | The target of a re-architecture proposal | [DDD Reference](https://domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_2015-03.pdf) |

**Finding.** Smells, decomposition tools and AI-bloat measurements each exist. I did not find a system that uses a *declared intent plus expected style* as the baseline and flags drift from it, specifically to stop an AI agent mid-edit. Same caveat as earlier sections: shallow search.

**Design implications**
- Cheap drift signals to test first: lines or comment ratio added to one region per change; number of distinct intents a reader names for the region; churn of the region.
- Trigger: when a signal crosses its threshold, the agent must stop editing and write a short proposal (split, extract, re-architect, or "intent still single, style changes") for the human to accept.
- Use embeddings (MonoEmbed-style) only to *suggest where to cut*, not to decide.
- Risk: thresholds that fire too often will be ignored, like long AGENTS.md files (section 8). Start with one or two signals.

## 13. Combined picture and next steps
Code Intent covers three moments: **before** AI writes (capture intent, section 10), **while** it writes (fit style/paradigm to intent, section 8), and **after/over time** (detect drift and trigger refactor or re-architecture, section 12).

1. Draft the intent record, the intent-to-style taxonomy and one drift signal together as a small spec.
2. Pilot on one experimental repo: add a feature with and without the record; track comments added, region growth, and the style-only guess test.
3. Deeper prior-art search (productive friction, drift detection, architecture erosion) before claiming novelty.

## 14. Pilot status (2026-10-20)

**Corpora cloned (shallow, read-only):** SQLite (sqlite/sqlite, 360 C files), QuickJS (bellard/quickjs, 64 C files), Julia (JuliaLang/julia, 956 `.jl` files), Firefox (mozilla/gecko-dev, sparse: `netwerk/protocol/http` and `dom/base` only, 684 C++ files). **Not yet done:** Lavandula (owner/repo not known), Haskell (which project?), other legacy projects.

**What ran:** `pilot/baseline.py` splits code into functions with tree-sitter, measures style metrics, and embeds each function with TF-IDF + SVD (64 dims). This is a **lexical baseline, not a neural code embedding.** Neural models could not be used because the environment's network policy blocks huggingface.co (connection fails); PyPI works. Results: `pilot/baseline_results.json`.

| Corpus | Functions | Median lines | Comment lines / 100 | Within-file cohesion |
|---|---|---|---|---|
| SQLite | 8238 | 18 | 7.4 | 0.52 |
| QuickJS | 1499 | 14 | 3.0 | 0.51 |
| Julia | 10136 | 9 | 9.0 | 0.56 |
| Firefox (2 dirs) | 9564 | 10 | 10.2 | 0.54 |

**Reading.** No clear split between the "clear" group and Firefox on these metrics. This does not test the hypothesis yet, for these reasons:
- Julia docstrings are string literals, so comment counts and doc-comment share are not comparable with C/C++.
- Firefox is two directories of one subsystem, not the whole code base.
- TF-IDF cohesion measures shared words, not shared intent.
- Metrics for different languages are not comparable; comparisons should be within a language (e.g., SQLite vs. Firefox C/C++).

**Needed for a real test:** (1) a neural embedding model, which needs the network policy to allow huggingface.co (or another model host); (2) the repository names for Lavandula and the Haskell project; (3) a ground-truth "intent" label set (e.g., hand-labelled functions, or the paper-backed vs. legacy grouping) and the style-only guess test from section 9.

## 15. Pilot update: more corpora, neural model still blocked

**Added (shallow clones):** Lavandula (ashtonjamesd/lavandula, 81 C files), pandoc (jgm/pandoc, 366 `.hs` files as the Haskell case), and Firefox JS from the sparse checkout (`toolkit/modules`, `browser/components`). `baseline.py` now also parses Haskell and JavaScript. Results: `pilot/baseline_results_2.json`.

| Corpus | Functions | Median lines | Comment lines / 100 | Within-file cohesion |
|---|---|---|---|---|
| Lavandula (C) | 353 | 10 | 1.3 | 0.72 |
| pandoc (Haskell) | 3910 | 7 | 4.6 | 0.36 |
| Firefox JS, toolkit/modules | 1310 | 12 | 8.6 | 0.55 |
| Firefox JS, browser/components | 223 | 15 | 8.9 | 0.54 |

**Reading.** Firefox JS has the highest comment density of the new group and the longest tail of function lengths; Lavandula, a small single-author project, has the highest cohesion. That fits the hypothesis only loosely. These are lexical metrics on very different languages and sizes, and the nesting metric is meaningless for Haskell here (0.0, node types not mapped), so no conclusion yet.

**Blocker.** The owner allowed huggingface.co, but this session still cannot reach it (connection fails; the environment setting applies to sessions started after the change). A neural embedding run needs a new session on the updated environment.

## 16. Pilot: UniXcoder embeddings, clear vs drifted (2026-10-20)

**Setup.** huggingface.co and its CDN now work from the session. Model: `microsoft/unixcoder-base` (125M, CPU, mean-pooled last layer, max 256 tokens, L2-normalised). Per corpus, up to 60 random files with at least 4 functions of 4+ lines, up to 12 random functions each (seed 0). Same sample also embedded with the TF-IDF+SVD(64) baseline. Code: `pilot/embed_unixcoder.py`, numbers: `pilot/unixcoder_results.json`.

**Metrics (per corpus, within its own sample).**
- *Lift* = mean cosine of function pairs in the same file minus mean cosine of pairs in different files.
- *kNN5/chance* = how often a function's 5 nearest neighbours come from its own file, divided by what chance would give.

| Corpus | Group | Lang | Funcs | UniXcoder within | across | lift | kNN5 / chance | TF-IDF lift | TF-IDF kNN5 / chance |
|---|---|---|---|---|---|---|---|---|---|
| SQLite | clear | C | 620 | 0.509 | 0.308 | 0.201 | 30.4 | 0.338 | 23.1 |
| QuickJS | clear | C | 446 | 0.469 | 0.299 | 0.170 | 15.2 | 0.227 | 9.2 |
| Lavandula | clear | C | 196 | 0.548 | 0.238 | 0.310 | 13.9 | 0.634 | 14.4 |
| Firefox netwerk/http | drifted | C++ | 580 | 0.508 | 0.319 | 0.189 | 24.6 | 0.380 | 21.1 |
| Firefox dom/base | drifted | C++ | 552 | 0.485 | 0.282 | 0.203 | 31.1 | 0.404 | 26.4 |
| Firefox toolkit/modules | drifted | JS | 536 | 0.383 | 0.183 | 0.200 | 29.2 | 0.267 | 19.0 |
| Firefox browser/components | drifted | JS | 486 | 0.434 | 0.254 | 0.180 | 26.9 | 0.324 | 22.1 |
| Julia | clear | Julia | 569 | 0.428 | 0.201 | 0.227 | 35.4 | 0.256 | 22.1 |
| pandoc | clear | Haskell | 566 | 0.364 | 0.238 | 0.127 | 20.7 | 0.216 | 14.8 |

**Reading: no split.**
- Within C and C++, the "clear" projects (lift 0.17 to 0.31) and Firefox C++ (0.19 to 0.20) overlap completely. Lavandula is highest, but it is a small single-author project (21 files), which is a size effect as much as a clarity one. QuickJS is the lowest of the C group.
- Firefox JS (0.18 to 0.20) is as cohesive as SQLite and QuickJS and more than pandoc. Julia has the best kNN5/chance, ahead of SQLite and Firefox, but Julia and Haskell are different languages, so this is not a like-for-like comparison.
- The neural and lexical rankings agree on most corpora but not all; e.g. QuickJS is last among C under both. The neural model compresses the spread (lift 0.13 to 0.31) compared with TF-IDF (0.22 to 0.63).

**Why this is weak evidence either way.**
- Within-file cohesion measures how topical a file is, not whether the project has a stated intent. A drifted code base can still have tidy files; a clear one can have a grab-bag file (SQLite's `util.c`).
- Firefox is four subdirectories of one subsystem, which may be the cleanest part of it. A fairer "drifted" group would be older, unowned code, or the same project measured over time (before and after a rewrite).
- UniXcoder was trained mainly on Java, Python, JS, PHP, Ruby and Go. C, C++, Julia and Haskell are outside that; numbers there may reflect token-level similarity more than intent.
- One sample (seed 0), 196 to 620 functions per corpus, no confidence intervals. Differences of about 0.03 in lift should be treated as noise.

**What would test the hypothesis better.** (1) A measure of *style consistency* (the section 9 style-only guess test, or variance of style metrics across files) instead of topical cohesion. (2) Bootstrap intervals over file samples. (3) Matched pairs within one language, e.g. a clear C project vs. a legacy C project of similar size. (4) A code model with C/C++ coverage (CodeXEmbed or similar) to check the result isn't a model artifact.

## 17. Pilot: Qwen3-Embedding-0.6B repeat (2026-10-20)

**Setup.** Same functions, same sampling (seed 0), same metrics as section 16, but embedded with `Qwen/Qwen3-Embedding-0.6B` (the newest Qwen text embedding that runs on CPU; the 4B and 8B versions are too slow here, and the Qwen3-VL-Embedding models are multimodal). Last-token pooling with the model's appended end-of-text token, max 256 tokens, no instruction prefix, fp32 on CPU (about 45 minutes). Code: `pilot/embed_qwen3.py`, numbers: `pilot/qwen3_results.json`.

| Corpus | Group | Qwen3 within | across | lift | kNN5 / chance | UniXcoder lift | UniXcoder kNN5 / chance |
|---|---|---|---|---|---|---|---|
| SQLite | clear | 0.636 | 0.448 | 0.187 | 31.4 | 0.201 | 30.4 |
| QuickJS | clear | 0.568 | 0.398 | 0.170 | 16.5 | 0.170 | 15.2 |
| Lavandula | clear | 0.643 | 0.322 | 0.321 | 15.5 | 0.310 | 13.9 |
| Firefox netwerk/http (C++) | drifted | 0.569 | 0.397 | 0.173 | 23.2 | 0.189 | 24.6 |
| Firefox dom/base (C++) | drifted | 0.575 | 0.352 | 0.223 | 34.1 | 0.203 | 31.1 |
| Firefox toolkit/modules (JS) | drifted | 0.463 | 0.264 | 0.199 | 27.9 | 0.200 | 29.2 |
| Firefox browser/components (JS) | drifted | 0.508 | 0.332 | 0.176 | 27.2 | 0.180 | 26.9 |
| Julia | clear | 0.575 | 0.340 | 0.235 | 37.8 | 0.227 | 35.4 |
| pandoc (Haskell) | clear | 0.521 | 0.378 | 0.144 | 22.9 | 0.127 | 20.7 |

**Reading: still no split.** Lift differs from UniXcoder by at most 0.02 on every corpus, and the ordering is the same: Lavandula highest, then Julia and Firefox dom/base, with QuickJS and pandoc lowest. Firefox C++ (0.17 and 0.22) still overlaps the clear C projects (0.17 to 0.32). So the null result in section 16 is not an artifact of UniXcoder's training languages, and a stronger general embedding does not separate the groups. The remaining caveats from section 16 stand: this measures how topical a file is, not stated intent, with one seed and no confidence intervals. The next test should change the measure (style consistency, matched pairs within one language) rather than the model.

## 18. Pilot: LoRA finetune of Qwen3-Embedding-0.6B, and an "alien code" check (2026-10-21)

**Finetune.** LoRA (r=16, attention projections, 4.6M trainable parameters) on 1,265 comment-to-code pairs: the doc comment is the query, the function (inner comments stripped) is the document. Training data is C from SQLite and C/C++/JS from Firefox only. In-batch contrastive loss, batch 16, temperature 0.05, one epoch (79 steps, about 50 min on 4 CPU cores). Code: `pilot/make_pairs.py`, `pilot/finetune_qwen3.py`; numbers: `pilot/finetune_results.json`; adapter weights: `pilot/qwen3_lora.pt`. Note: the first run finished training but crashed while saving (missing Jinja2), and I retrained with a fallback save; the reported numbers are from that second run.

**Alien-code test.** Retrieval over a pool of one set at a time: given the function's doc comment, rank all functions in the set (MRR; R@1; R@10 is 5% by chance). Sets never seen in training:
- QuickJS (C, unseen repo), Julia and pandoc (Haskell, unseen languages).
- QuickJS rewritten into an invented language "zorb" (keywords renamed, braces as `begin~`/`~end`, `;` as `.`, `==` as `isq`; identifiers kept).
- The same with identifiers also replaced by hashes.

| Set | n | MRR before | MRR after | R@1 before | R@1 after |
|---|---|---|---|---|---|
| QuickJS (C) | 111 | 0.880 | 0.872 | 0.829 | 0.811 |
| Julia | 200 | 0.792 | 0.800 | 0.720 | 0.730 |
| pandoc (Haskell) | 46 | 0.890 | 0.916 | 0.826 | 0.870 |
| QuickJS in "zorb" syntax | 111 | 0.849 | 0.829 | 0.766 | 0.730 |
| zorb + hashed identifiers | 111 | 0.266 | 0.274 | 0.171 | 0.180 |

Original-vs-rewritten match (does the embedding of a function find its own rewritten version among 111?): zorb R@1 100% before and after (cosine 0.93 both); zorb with hashed names R@1 28% before, 30% after (cosine 0.46 to 0.37).

**Reading.**
- *Alien syntax is processed correctly, before and after.* Outputs are finite, the invented syntax retrieves almost as well as C (MRR 0.85 vs 0.88), and a function and its zorb rewrite always match each other. Syntax is not what the model relies on.
- *Names carry the meaning.* Hashing identifiers drops MRR to 0.27 and pair matching to about 30%. So where names are alien or meaningless, this model fails, finetuned or not. This is the actual limit for "intent from code alone".
- *The finetune changed little.* Differences are +0.026 to -0.02 MRR, all inside the noise for sets of 46 to 200 items. The loss was already near zero in early steps, i.e. the base model already solves this task with 16-way batches, so there was little to learn. Mean cosine between unrelated functions fell from about 0.39 to 0.23, so the space is more spread out, but no downstream metric showed a benefit. No evidence of forgetting on unseen languages either.
- Caveats: one seed, one epoch, small pools (n=46 for Haskell), invented syntax is a mechanical rewrite and not a real language, and the task (comment to code) is not the project's goal (style/paradigm fit). A finetune aimed at that goal would need different labels, e.g. pairs of same-intent functions in different styles, with hard negatives of the same topic in a wrong style.

## 19. Pilot: a category × style matrix next to the intent embedding (2026-10-21)

**Why this section exists.** Sections 16 to 18 asked what an embedding says about *what code does* (intent) and found it reads names far more than structure. This section asks the complementary question: *how the code is written* (programming style), and whether style can be placed in the same embedding space as a coordinate, without calling any style better. The design follows ひなた's two requests: (1) style axes must not be hand-defined; like word2vec they should come from offsets between examples that mean the same thing but differ in form, and (2) rows of the matrix are *role categories* (IO with sub-categories such as filesystem and network, mathematical logic, glue code), so intent and style can be read together. Everything is in `pilot/style/`.

**Data.** 20 intents, each written by hand in 5 styles (procedural P, object-oriented O, functional F, data-oriented D with flat columns/numpy, declarative idiom G with comprehensions and stdlib one-liners) = 100 Python snippets (`dataset.py`, `dataset2.py`). Every intent's five versions were run against one shared test and behave identically (`test_dataset*.py`, IO checked with temp files and a mocked `urlopen`). Categories (`CATEGORY` in `dataset2.py`): compute (numeric 4, collections 6, logic 2 intents), io (filesystem 3, network 2), glue (compose 3). In addition, 210 real functions from the Python stdlib/numpy/networkx (statistics, numpy lib, networkx paths, collections, argparse, shutil/glob/filecmp, urllib.request/ftplib/smtplib) serve as out-of-sample code. Docstrings and comments are stripped, and all code is passed through `ast.unparse` so formatting cannot leak. A name-hashed variant replaces every user-chosen identifier (functions, classes, arguments, locals, new attributes) by a hash and keeps keywords, builtins, imported names and std method names, matching the identifier-hashing test of section 18.

**Method.** Models are the same as before (UniXcoder, Qwen3-Embedding-0.6B, and Qwen3 with the LoRA adapter from section 18; `embed_all.py`). The model is `z[intent, style] = mu + a[intent] + v[style] + interaction`. The style vector `v[s]` is the mean over intents of (z[i,s] minus the mean of z[i,.] over styles), i.e. the word2vec offset idea; its rank is 4, so a style coordinate is 4-dimensional. The matrix analysis is written in Julia 1.13 (`matrix.jl`, standard library only; Julia came from conda-forge because julialang.org and the Julia package server answer 403 from this sandbox, so no packages beyond the stdlib were usable). All tests leave one intent out. Numbers: `out/summary.txt`, per-run files `out/<model>_<raw|hashed>.txt`, figures `out/fig_*.png`.

**Results (chance in brackets).**

| Test | UniXcoder raw / hashed | Qwen3 raw / hashed | Qwen3+LoRA raw / hashed |
|---|---|---|---|
| Variance share: style | 0.05 / 0.07 | 0.03 / 0.04 | 0.03 / 0.03 |
| Variance share: top category / sub-category / intent / interaction | .10/.12/.43/.29 / .10/.11/.32/.39 | .12/.15/.57/.12 / .12/.15/.45/.24 | .12/.16/.57/.12 / .12/.15/.45/.24 |
| Top category of a held-out intent (3 classes; permutation mean 0.43) | 0.66 / 0.72 | 0.64 / 0.70 | 0.65 / 0.69 |
| Sub-category of a held-out intent (6 classes; permutation mean 0.16) | 0.40 / 0.51 | 0.38 / 0.49 | 0.46 / 0.51 |
| Style of a held-out intent, nothing known [0.20] | 0.77 / 0.68 | 0.55 / 0.60 | 0.54 / 0.54 |
| Style, intent's other four styles known | 0.83 / 0.84 | 0.87 / 0.77 | 0.88 / 0.74 |
| Style, true sub-category centroid subtracted | 0.70 / 0.66 | 0.52 / 0.54 | 0.52 / 0.46 |
| Style analogy z(b,r)+offset, same sub-category / other category [0.25] | 0.45 / 0.34 | 0.41 / 0.34 | 0.39 / 0.34 |
| Cosine of one style's offset between top categories (compute-io) | 0.37 | 0.48 | 0.46 |

Non-neural baselines (`baselines.py`, same protocol): snippet length alone identifies style 0.53 to 0.61; bag of tokens on hashed code 0.91; keywords and punctuation only 0.87.

Real code (nearest category centroid, then nearest top-level category × style cell; one outcome per corpus, `out/summary.txt`): top category correct for statistics, numpy, networkx, collections at 0.82 to 1.00 with names (0.81 to 1.00 for Qwen3 raw), IO code is weaker (stdlib fs 0.25 to 0.65, net 0.25 to 0.80) and hashing hurts it most. Nearest style cell: numpy lib is D for 0.85 to 0.90 of functions in UniXcoder and Qwen3 raw (0.55 hashed), collections mostly O (0.38 to 0.73), statistics mixes P/D/G with models disagreeing (UniXcoder P 0.70, Qwen3 D/G 0.39 each). "Does a new function belong to its own corpus" (AUROC of distance to the corpus centroid in the 4-d style space, 0.5 = no signal): 0.61 to 0.95 for statistics, numpy, networkx; collections 0.81 to 0.87 with names but 0.45 to 0.53 hashed; argparse and stdlib fs/net 0.47 to 0.67.

**Reading.**
- *The matrix is real but the style column is thin.* Style explains only 3 to 7% of embedding variance; intent (leaf) explains 32 to 57% and category 22 to 28%. Categories do cluster for unseen intents (top 0.64 to 0.72 against 0.43 by permutation, p about 0.01 to 0.04; sub-category 0.38 to 0.51 against 0.16), and hashing identifiers did not remove this, because imported names (`urllib`, `open`, `np`) were kept. So category clusters are carried by API names more than by identifier names.
- *Style is partly additive, partly not.* An offset learned on other intents identifies the style of an unseen intent far above chance (0.54 to 0.77 vs 0.20), and the analogy test beats chance (0.34 to 0.45 vs 0.25) but is weaker across categories than within one (0.29 to 0.34 vs 0.35 to 0.45). Style vectors computed inside different categories have cosine only 0.1 to 0.5 with each other, and the interaction term holds 12 to 39% of variance. A single global "style direction" is an approximation; the matrix (category × style cell) is the better unit than two independent axes.
- *A negative result.* Subtracting the category centroid before reading the style did not help (0.46 to 0.70 against 0.54 to 0.77 without it), so "category and style combine by simple subtraction" does not hold here with only 20 intents.
- *These embeddings are not good style encoders.* Style needs the intent's other versions to reach 0.83 to 0.88 and without that falls to 0.54 to 0.77, while a bag of keyword tokens, with no neural model, reaches 0.87 to 0.91, and length alone reaches 0.53 to 0.61, which explains a good part of the embedding's result. The LoRA adapter from section 18 behaves like the base model (differences at most 0.06), as in section 18. Consistent with sections 16 and 17: these models encode topic and names; structure is a weak secondary signal.
- *Codebase identity works only coarsely.* Corpus fingerprints are sensible where the code is homogeneous (numpy as D, collections as O), models disagree where it is mixed, and the "is this function out of place" check is useful for some corpora and at chance for others; it needs names for collections.
- *Complementarity with intent.* Intent coordinates come from the description (intent) side; the style coordinate is the within-intent offset. They are not orthogonal in these models: style effects do depend on category (see interaction share), which is the argument for a matrix and not two separate axes.

**Limits.** All 100 training snippets were written by one author (me), five styles are my reading of the paradigms (data-oriented means flat columns / numpy here, and "DOP" in the sense of generic data structures plus pure functions would be closer to F or G), snippets are short and Python only, 20 intents with 2 to 6 per sub-category, one run, no seeds to vary (no training involved), and the real-code labels are expectations from module names, not manual annotation. D versions use numpy, so part of "style" is library choice. The category correction test used true sub-categories of at most six values. Julia ran on stdlib only; plots were made in Python from the embeddings.

**Next steps.** Compare with a style space learned directly from structure (AST or keyword tokens, name-free), since that baseline beat the pretrained embeddings; train a contrastive model with same-intent/different-style positives and same-style/different-intent negatives (the objective suggested at the end of section 18); grow the dataset with more authors/languages and annotate the real-code labels by hand.

## 20. Pilot: AST tokenizer that resolves calls down to OS/platform API leaves (2026-10-21)

**Idea (from ひなた).** Instead of reading names with a text embedding, tokenize the AST recursively and follow every call, through local helpers, to its platform leaf (`os.listdir`, `urllib.request.urlopen`, builtin `open`, ...). The category then comes from which leaves a function reaches, and the structure tokens carry the style. Code: `pilot/style/asttok.py` (tokenizer, call-graph closure, category rules, platform table) and `eval_asttok.py` (evaluation); numbers in `out/asttok.txt` and the `asttok` columns of `out/summary.txt`. It complements section 19: same 100 snippets and 210 real functions, same leave-one-intent-out protocol.

**What the tokenizer does.** (1) Pre-order node-type tokens with no identifiers; binary operators, comparison operators and constant types are kept. (2) Each call is tagged by what it resolves to: `CALL:api:<qualified name>` (platform leaf via an import alias table, builtin `open`/`print`/`input`, or a method such as `.urlopen`), `CALL:local` (followed by the callee's reachable leaves, computed as a fixed point over the call graph so recursion is safe), `CALL:builtin:<name>`, `CALL:lib:<module>` (non-platform library such as numpy), `CALL:opaque` (a function that is neither defined, imported nor builtin). (3) Category rule: any platform leaf reached means io, with sub-category network if network leaves are at least as many as filesystem ones; otherwise glue if the code only delegates calls and has no loops, comprehensions, arithmetic or non-constant comparisons; otherwise compute.

**Results.**

| Test | AST tokenizer + rules | Section 19 best embedding |
|---|---|---|
| Top category, 100 snippets (3 classes) | 0.95 (compute 1.00, io 1.00, glue 0.67) | 0.64 to 0.72 held-out intents |
| Real stdlib IO functions, top category: shutil/glob/filecmp (fs) | 0.82 (sub-category correct 0.80) | 0.25 to 0.65 |
| urllib.request/ftplib/smtplib (net) | 0.85 (sub-category correct 0.82) | 0.25 to 0.80 |
| statistics, numpy, networkx, collections as compute | 0.91, 0.95, 1.00, 0.73 | 0.82 to 1.00 |
| Style from structure tokens, held-out intent, 5 styles [0.20] | 0.91 with API tokens, 0.83 structure only | 0.54 to 0.77 (keyword tf-idf baseline 0.87) |

All five glue misses are in glue samples (compute predicted): glue_adults D and F, glue_dispatch P, glue_report F and P. Those use a comprehension, a numeric comparison, or builtin-only calls, which my "delegation only" rule treats as work.

Putting the tokenizer vectors (tf-idf of token bigrams, 64-d SVD) into the Julia matrix (`matrix.jl`, model name `asttok`): style explains 21% of variance (embeddings 3 to 7%), style of an unseen intent is identified 0.91 (0.95 when the intent's other styles are known), the analogy test reaches 0.64 to 0.68 (embeddings 0.30 to 0.45), and style offsets are more shared between categories (cosine 0.46 to 0.71, embeddings 0.1 to 0.5). Top category of a held-out intent from nearest centroid: 0.88, sub-category 0.51 (the same as the embeddings). Subtracting the category centroid still does not help style (0.90 against 0.91).

**Reading.**
- *The leaf resolution is what helps the category, not the learned vector.* The rule-based category (follow calls to platform leaves) reaches 0.82 to 0.85 on real IO code, where the embeddings were often at 0.25 to 0.65 and collapsed when names were hashed. The same tokenizer's tf-idf vectors, used with nearest-centroid classification as in section 19, give only 0.35 (fs) and 0.07 (net) on real IO code, since a centroid of my 100 short snippets does not transfer; the explicit API table does. So ひなた's idea works as a symbolic classifier; as an embedding it still needs real training data.
- *It is name-free by construction.* The `raw` and `hashed` columns of `asttok` are identical, and the category did not need any identifier. Library names do matter here: API leaves are names, but they are the platform's names, not the author's, which is exactly what makes them trustworthy as category evidence.
- *Structure tokens are a much better style signal than pretrained embeddings*, as the keyword baseline in section 19 hinted (0.91 vs 0.54 to 0.77), and they give the matrix a clearer style column (21% of variance, analogies about twice as accurate). They still separate style from category only partially (interaction share 34%).
- *Misses on real IO code are partly right.* shutil/glob/filecmp include pure helpers (string and path-pattern work) that never reach a platform call; calling those compute is arguably correct, and my expected label (module name) is the cruder one. I did not hand-annotate, so 0.82/0.85 is a lower bound against a better label, not a measured accuracy.

**Limits.** The glue rule and the platform table were written by me after seeing the 20 intents, so 0.95 on the snippets is partly tuned; the stdlib results are the out-of-sample part and were obtained with one pass (no tuning on them). Methods are resolved by bare name within a module (first definition wins), receiver types are not inferred, `.read`/`.write` on unknown objects are not counted, indirect calls (callbacks, `getattr`, dispatch tables) are not followed, dynamic imports are invisible, and only Python is covered; other languages would need a tree-sitter front end and their own platform tables (libc/syscalls, Win32, Node `fs`/`net`). Glue is the weakest class: it is defined by what code does not do, and there are only 3 glue intents.

**Next.** Evaluate on a larger hand-labelled set of functions from a real application repository (including glue); add a tree-sitter front end for C/Rust/Julia/JS with per-language platform tables; use the tokenizer's tokens (API leaves as category evidence, structure n-grams as style evidence) as the input of a contrastive model trained with same-intent/different-style positives, so that the learned coordinate no longer depends on my hand-written rule.

## 21. Pilot: a category preset generated from a small OS-API tag set (Python stdlib) (2026-10-21)

**Idea (from ひなた).** Do not hand-list the platform API of each language (section 20's `PLATFORM` table). Predefine the *OS API categories* once, tag only the OS-level seeds, tokenize the language's stdlib, and let the tags propagate through the stdlib's own call graph. The result is a per-language **preset**: for every stdlib function, the set of OS categories it reaches. User code is then categorized by looking up the functions it calls. Code: `pilot/style/build_preset.py` (seeds, propagation, preset), `check_preset.py` (independent check), `eval_preset.py` (category tests), output `preset_python.json`, `out/check_preset.txt`, `out/preset_eval.txt`.

**Seeds (the only hand-made part).** 8 tags: `fs`, `net`, `proc`, `console`, `clock`, `env`, `random`, `thread`. Seed names: POSIX syscall families by name (open/read/stat/listdir/mkdir/rename/... as `fs`, system/fork/exec*/kill/wait* as `proc`, getenv/uname/... as `env`, urandom as `random`), whole native modules (`_socket`, `select`, `_ssl` as `net`, `_posixsubprocess` as `proc`, `time` as `clock`, `_io` as `fs`, `_thread` as `thread`), builtins `open`/`print`/`input`, `sys.stdout/stderr/stdin`, `os.environ`, and 17 socket method names for receivers of unknown type; 112 names in all. Only `fs`, `net`, `proc` make code "IO" in the category rule; `console`, `clock`, `env`, `random`, `thread` are tags but do not (a `print` or a lock is everywhere). Calls into `warnings`, `traceback`, `logging` and similar diagnostic modules are cut from the graph.

**Propagation.** 468 stdlib modules (including frozen ones such as `os`) are parsed; calls are resolved across modules through imports, `from x import *` re-exports (`os` gets `listdir` from `posix`), simple `X = module.func` aliases, `self`/`cls` methods and `Cls(...).method()` receivers; tags flow to callers as a fixed point. 11,477 functions, of which 1,656 public ones carry a tag (fs 735, net 313, proc 254, thread 267, console 819, clock 258, env 253, random 27).

**Independent check.** 54 well-known stdlib functions with the tags I expected, written before seeing the output (`check_preset.py`): 28 of 34 expected-tagged functions got at least one expected tag, 19 of 20 expected-pure functions got no IO tag (the miss, `os.getpid` as `proc`, is a label I would now argue either way). Misses of expected tags: `urllib.request.urlopen` (dynamic dispatch through `opener.open`), `fileinput.input` (module-global instance), `getpass.getpass`, `tarfile.open` (name rebinding), `ssl.create_default_context` (native base class), `logging.info` (diagnostic cut by design).

**Category tests: generated preset against the hand table of section 20** (same snippets and same real code; "+import prior" lets a function with no tag inherit the IO tag of the modules its module imports, e.g. urllib.request imports http.client imports socket):

| Test | Hand table | Preset | Preset + module prior | Preset + module + import prior |
|---|---|---|---|---|
| Snippets, IO top category (n=25) | 1.00 | 0.68 | 0.72 | 1.00 |
| Snippets, IO sub-category | 0.96 | 0.56 | 0.56 | 0.64 |
| Snippets, compute top category | 1.00 | 1.00 | 1.00 | 0.88 |
| statistics (compute) | 0.91 | 0.94 | 0.94 | 0.55 |
| collections (compute) | 0.73 | 0.73 | 0.73 | 0.54 |
| numpy lib (compute) | 0.95 | 0.95 | 0.95 | 0.85 |
| shutil/glob/filecmp (io, filesystem), top / sub | 0.82 / 0.80 | 0.55 / 0.55 | 0.55 / 0.55 | 0.80 / 0.75 |
| urllib.request/ftplib/smtplib (io, network), top / sub | 0.85 / 0.82 | 0.30 / 0.25 | 0.30 / 0.25 | 0.78 / 0.30 |

**Reading.**
- *The mechanism works and generalizes.* From 112 hand-made OS-level seeds it tags 1,656 stdlib functions with no per-function listing, and it was right on 28/34 independent IO cases and 19/20 pure ones. It is language-agnostic in design: the same pipeline, with a tree-sitter front end and the language's own native/FFI seeds (libc, Win32, Node `fs`/`net`, Rust `std::fs`), would give a preset per language.
- *As a classifier it beats neither the hand table nor the embeddings on IO recall* (net 0.30 vs 0.85 hand table, fs 0.55 vs 0.82) because real stdlib code reaches the OS through dynamic dispatch, instance attributes holding functions (`self._create_connection = socket.create_connection`), and handler tables, none of which a static call graph follows. It is *more precise* on compute code (statistics 0.94 vs 0.91): functions that the hand table calls IO by prefix (any `os.*`) are not, if they never reach a syscall.
- *The import prior recovers recall but costs precision.* It lifts fs/net to 0.80/0.78 and snippets IO to 1.00, but turns pure modules that import `os` or `socket` into IO (statistics 0.55, collections 0.54) and confuses filesystem with network (sub-category 0.30 for network). The trade-off is real; I report all three settings and picked no winner on my own test data.
- *Practical use.* The preset is best used as evidence with a confidence (which seeds were reached, by how long a path) next to the embedding, not as a final label; "which stdlib API does this code reach" is cheap and explainable, "is this function IO" needs the dynamic cases handled.

**Limits.** Python only; static resolution by names (first definition wins, no type inference except `Cls(...).method()`), module prior threshold 0.4 and the import-prior rule were set once and not tuned, the diagnostic-module cut and the `console` exclusion are my design choices (they change results), expected labels for real code come from module names, `argparse` has no label (62 to 68% of its functions are IO by the preset against 30% by the hand table; mostly help printing and `sys.argv`), and 112 seed names are more names than the 35 prefixes of the hand table, so "small tag set" holds for the 8 tags, not for the seed list. Julia, C and other languages were not attempted here.

**Next.** (1) Add inter-procedural dynamic cases cheaply: record "attribute assigned from a platform function" (`self.x = socket.create_connection`) and class-hierarchy dispatch (`handler.http_open`); (2) per-tag confidence from path length and share of paths; (3) build the same preset for Julia (the language ひなた prefers for the matrix work) from its Base/Sockets/Filesystem stdlib with `ccall` and libuv as the native seeds, to test the language-agnostic claim.

## 22. Pilot: instance-aware AST analysis for the preset (Python) (2026-10-21)

**Why.** Section 21 found that the generated preset missed IO that is reached through object semantics: `urlopen` calls `opener.open`, `HTTPConnection` stores `socket.create_connection` in an attribute, handlers are classes passed as arguments. ひなた's point: instance creation must be related correctly by the language-specific AST analysis. Code: `pilot/style/build_preset2.py` (analysis), `eval_preset2.py` (tests), `disagree.py` (manual review of disagreements); numbers in `out/preset2_eval.txt`, preset in `preset_python2.json`.

**What the analysis tracks (Python-specific).**
- *Local typing:* `x = Cls(...)`, `with Cls(...) as x`, `x = factory(...)` give `x` the class, so `x.method()` resolves to `Cls.method` through base classes.
- *Return types:* a function returning `Cls(...)` or a variable of that class is a factory (`build_opener()` returns an `OpenerDirector`).
- *Instance attributes:* `self.a = Cls(...)` or `self.a = some_function` in any method types `self.a.m()` and `self.a(...)`; overridden methods in subclasses are added as possible targets.
- *Parameter binding:* classes and functions passed as arguments are what a call on that parameter may reach (context-insensitive), e.g. `do_open(http.client.HTTPConnection, req)`.
- *Escape rule (switchable):* an instance passed to another call may have its public methods called back; this is what links a constructed handler to the opener that dispatches to it by name.
- Constructors are edges to `__init__`; user snippets are added to the graph as one more module, so they use the same machinery.

**Results** (same 100 snippets, 210 real functions, labels from module names for real code; "v1" = section 21 preset without priors):

| Test | Hand table (sec. 20) | v1 preset | v2 no escape | v2 with escape |
|---|---|---|---|---|
| Independent 54-function check: expected tags found / pure kept pure | n/a | 28/34, 19/20 | 29/34, 19/20 | 30/34, 19/20 |
| Public stdlib functions tagged | n/a | 1,656 | 1,882 | 1,925 |
| Snippets IO top / IO sub-category (n=25) | 1.00 / 0.96 | 0.68 / 0.56 | 0.72 / 0.56 | **0.96 / 0.96** |
| Snippets compute top | 1.00 | 1.00 | 1.00 | 1.00 |
| shutil/glob/filecmp, top / sub | 0.82 / 0.80 | 0.55 / 0.55 | 0.50 / 0.50 | 0.50 / 0.50 |
| urllib.request/ftplib/smtplib, top / sub | 0.85 / 0.82 | 0.30 / 0.25 | 0.65 / 0.53 | 0.65 / 0.53 |
| statistics / collections / numpy / networkx as compute | .91/.73/.95/1.00 | .94/.73/.95/1.00 | .94/.88/.95/1.00 | .94/.88/.95/1.00 |

Without any import-based prior, which in section 21 cost compute precision, the instance-aware analysis lifts snippet IO from 0.68 to 0.96 (sub-category 0.56 to 0.96) and network stdlib code from 0.30 to 0.65, while compute stays clean (collections even improves, 0.73 to 0.88).

**Reading.**
- *Instance creation was the missing piece for IO that goes through objects.* The escape rule matters for snippets that build a client object and call it (`JsonClient().get(url)`, `Downloader().save(...)`): 0.72 to 0.96. It added only 43 more tagged stdlib functions, so its effect on library code is small.
- *The low fs/net numbers against the hand table are mostly a labelling effect, not a miss.* Of 20 functions where the hand table says IO and the preset does not, I read a random 14 (`disagree.py`): about 12 are pure helpers (`glob.escape`, `glob.translate`, `url2pathname`, `reduce_uri`, `dircmp.phase4` which only joins paths, `get_cnonce`, `ProxyHandler.__init__`) or console-only (`dircmp.report`, `demo`), 2 are truly IO that the preset misses (`_Globber.wildcard_selector` and `special_selector`: scandir through an overridden method on a user-supplied path object). The two the preset calls IO and the hand table does not (`SMTP.__init__`, `FTP.close`) are correct. So module-name expectations (every function of shutil is IO) understate the preset and overstate the hand table, which treats any `os.*` prefix as IO. A hand-annotated sample is needed for a real accuracy figure; this is a manual reading of a sample of 16, one reader.
- *Still not followed:* dispatch by method-name convention (`getattr(handler, 'http_open')`), globals mutated in other functions, duck-typed arguments (`path.iterdir()` on whatever the caller passes), nested classes, and anything built at runtime. Python-specific rules (`self`/`cls`, `with ... as`, class attributes, MRO by DFS) mean each language needs its own front end; the seed tags and the preset format stay the same.

**Julia.** ひなた reports julialang.org and julialang.net are now allowed. I checked: `Pkg.add("JSON3")` installs and runs, so Julia packages can be used from now on for the matrix work. A Julia preset (Base/Sockets/Filesystem with `ccall` and libuv as seeds, multiple-dispatch call resolution instead of `self`-based method lookup) has not been built yet; multiple dispatch makes "which method does this call reach" depend on argument types, which is a harder version of the instance problem solved here.

**Limits.** One run; Python only; manual review is a sample of 16 by one reader (me); real-code labels are by module name; escape rule over-approximates (any instance passed to a call may run its public methods), measured only through compute code staying clean on 4 corpora; user snippets are mine and fit the machinery (constructor, factory, attribute) by construction, so 0.96 is an upper bound for "typical" code.

## 23. Pilot: linking C++ and JS in Firefox by XPCOM method names, with real word2vec on identifier words (2026-10-21)

**Question (ひなた).** In Firefox the C++ side and the JS side of an XPCOM interface share almost nothing but the function name (`nsIFoo::doThing` in the IDL, `nsFoo::DoThing` in C++, `foo.doThing()` in JS). Does the style/intent embedding connect same-intent C++ and JS functions by names alone, and what happens when names are hashed or mismatched? Follow-up: use real word2vec on the words inside identifiers. Code and data: `pilot/xpcom/` (`extract.py`, `variants.py`, `embed.py`, `evaluate.py`, `w2v_*.py`, `fuse.py`; numbers in `results.txt`, `w2v_results.txt`, `fusion_results.txt`).

**Data.** Shallow sparse clone of `mozilla/gecko-dev` (netwerk, toolkit/modules, toolkit/components/places etc., browser/components, browser/base, dom/base, xpcom/ds, xpcom/io, uriloader: 328 IDL files). 1,512 IDL method names; 1,270 are camel-case multiword names unique to one interface; 829 of those have a C++ implementation `Cls::Name` and 263 have a JS function (4 to 60 lines, tree-sitter) calling `.name(` as its only IDL call. 129 names have a JS caller outside test paths (JS: browser 82, toolkit 41, netwerk 5; C++: netwerk 46, xpcom 23, toolkit 22, browser 15, dom 12). One pair per name: the C++ implementation (first one found) and one random non-test JS caller. C++ impls per name: median 1, 36% have more than one; JS callers per name: median 3. The link is many-to-many in reality; the pool here is one-to-one.

**Test.** Given a JS function, rank all 129 C++ functions by cosine; pair is correct if its own C++ implementation ranks first (R@1; chance 0.8%, MRR chance 0.04). Controls, all on the same pairs:
C0 raw. C1 the method name masked (replaced by a hash) in JS only; C2 in C++ only; C4 in both with different hashes; C3 both with the same hash (name as opaque ID). C5 every identifier hashed consistently on both sides (same name, same hash), C6 hashed with a different salt per language. C7 the names alone. C8 JS where the method name is replaced by another interface's method name (decoy), checking whether retrieval follows the name.

**Results (R@1 / MRR, N=129, 95% bootstrap CI for R@1 about ±0.08).**

| Condition | UniXcoder | Qwen3 | TF-IDF of identifier words | word2vec Firefox (idf bag) | word2vec GoogleNews (idf bag) |
|---|---|---|---|---|---|
| C0 raw | 0.29 / 0.42 | 0.50 / 0.58 | 0.44 / 0.60 | 0.33 / 0.46 | 0.32 / 0.39 |
| C1 JS name masked | 0.25 / 0.37 | 0.42 / 0.52 | 0.36 / 0.49 | 0.25 / 0.38 | 0.19 / 0.28 |
| C2 C++ name masked | 0.22 / 0.34 | 0.40 / 0.51 | 0.37 / 0.52 | 0.27 / 0.40 | 0.25 / 0.33 |
| C3 same hash both sides | 0.21 / 0.33 | 0.37 / 0.49 | n/a | n/a | n/a |
| C4 different hashes | 0.19 / 0.29 | 0.36 / 0.47 | 0.31 / 0.44 | 0.23 / 0.36 | 0.19 / 0.27 |
| C5 all identifiers hashed, consistent | 0.02 / 0.06 | 0.00 / 0.04 | 0.06 / 0.10 | 0.01 / 0.04 | 0.01 / 0.04 |
| C6 hashed, salted per language | 0.00 / 0.04 | 0.02 / 0.05 | n/a | n/a | n/a |
| C7 names only | 0.74 / 0.77 | 0.98 / 0.99 | 1.00 | 1.00 | 1.00 |
| C8 decoy name: top-1 is original C++ / is the decoy's C++ | 0.22 / 0.04 | 0.39 / 0.04 | n/a | 0.22 / 0.02 | 0.18 / 0.03 |

Word2vec: Firefox model = skip-gram, 100-d, trained on 79,992 Firefox functions (19.8k C++, 60.2k JS, 6.2M identifier-word tokens; the 129 evaluation functions removed), 12,509 words; neighbours are sensible (`channel`: chan, request, load, redirect; `cookie`: cookies, partitioned, jar, expiry; `cache`: entry, disk, evict, storage). GoogleNews: pretrained 300-d. Function vector = idf-weighted mean of word vectors over all identifier words of the function.

Fusion (z-scored similarity sums): Qwen3 + TF-IDF raises C0 MRR from 0.58 to 0.65 and R@10 from 0.73 to 0.86, while R@1 only moves 0.50 to 0.52; adding word2vec does not help (0.63 to 0.65).

Language offset (mean C++ minus mean JS vector estimated on one half of the pairs, applied to the other): word2vec half-pool MRR 0.53 to 0.55, UniXcoder 0.51 to 0.51, Qwen3 0.65 to 0.69; small gains, not consistent across conditions (UniXcoder C1 0.47 to 0.43).

**Reading.**
- *Names alone do connect the two sides, but most of the link in real code is not the method name.* Names-only retrieval is perfect for word2vec/TF-IDF (case folding makes `GetFoo` and `getFoo` identical) and 0.74 (UniXcoder) to 0.98 (Qwen3) for the neural models. In context, masking the method name costs only 0.05 to 0.10 R@1, and masking it on both sides with different hashes still leaves 0.19 (UniXcoder) to 0.36 (Qwen3), because the other identifiers (class name words like `channel`, argument words) are shared: 60% of the JS callers contain a word of the C++ class name.
- *When every identifier is hashed, the link is gone for every method, including with the same hash on both sides* (C5 equals chance for Qwen3, UniXcoder and word2vec, 0.06 for TF-IDF). The embeddings do not exploit an identical opaque token: they read words. So an exact symbolic bridge (an IDL index: method name to interface to C++ implementation) is the right link; the embedding can add a soft signal only where words are readable.
- *Real word2vec on words in names helps less than exact word overlap here.* A word2vec bag (0.33 R@1) is below plain TF-IDF over the same words (0.44) and below Qwen3 (0.50); the Firefox-trained model beats GoogleNews (0.33 vs 0.32 raw, 0.25 vs 0.19 with a masked name), so domain words (`nsresult`, `chan`, `uri`) matter. These pairs share the exact words, which is the case where exact overlap is best; word2vec's strength (related but different words, e.g. `evict`/`doom`/`remove`) would need pairs whose names differ, which XPCOM links do not give. The test that would show a benefit is a rename or synonym test, not run here.
- *A mismatched name is not followed.* With a decoy method name in JS the top retrieval is the decoy's C++ implementation only 2 to 4% of the time; most of the signal comes from the rest of the body. So name mismatch is weak evidence against a pair in these models; a mismatch detector would need to look at the name explicitly.
- *Style space note.* C++ and JS are far apart in the embedding (matched cosine 0.5 vs 0.3 for unmatched pairs, Qwen3), but the gap is mostly shared between matched and unmatched pairs: subtracting a language offset improves MRR a few points at most. In the terms of section 19, language behaves like another offset vector, but a weak one compared with the content.

**Limits.** 129 pairs from a sparse subset of the tree, one JS caller and the first C++ implementation per name (many-to-many reality not tested), method names restricted to unique multiword names, masking replaces exact name tokens only (substrings of longer identifiers, strings, comments and `Cls::Name` forms other than `Name`/`name` remain), "hashing" keeps keywords so structure survives, the C++ test is raw text with no AST/API-leaf analysis (those are Python-only, sections 20 to 22), word2vec was trained once (seed 1, 15 epochs, no tuning), no XUL/XBL/`.xhtml` markup was used (only IDL, C++ and JS), and the link direction is JS to C++ only.

**Next.** Build the explicit bridge: IDL index (method to interface to implementing C++ class to JS call sites) with a soft embedding score for ranking among many implementations; a rename/synonym test to see whether word2vec beats exact overlap when words differ; a tree-sitter C++ front end with the OS-API tags of sections 21 and 22 so the category of a C++ implementation comes from what it calls rather than its words.

## 24. Pilot: an exact XPCOM bridge index between IDL, C++ and JS (2026-10-21)

**Why.** Section 23 showed that names connect the two sides only through readable words, that an exact name beats word2vec and that opaque hashes break every embedding, so the link should be an explicit index with embeddings used only as a soft ranking. ひなた asked for the index. Code: `pilot/xpcom/build_index.py` (index), `lookup.py` (query), `make_eval.py`, `embed_index.py`, `eval_index.py` (disambiguation test); data `index.json` (0.7 MB), `js_sites.jsonl` (27,055 call sites with code), numbers `index_results.txt`.

**What the index contains** (built in 25 s from the same sparse gecko-dev checkout as section 23):
- *IDL layer:* 511 interfaces (name, file, base interface, first doc sentence, methods), 1,511 method names; 1,376 are declared by one interface, 135 by several (`init`, `get`, `asyncOpen`, `cancel`, `create`, ...).
- *C++ layer:* classes mapped to interfaces from `NS_IMPL_ISUPPORTS(Class, nsIA, nsIB)`, class base lists and `NS_DECL_NSIFOO` inside the class body (670 classes), joined to the tree-sitter method definitions `Cls::Name` through the interface inheritance chain (a method declared in a base interface is found for classes implementing a derived one). 1,166 (interface, method) pairs have at least one implementing class (median 1 class, mean 2.2, 28% have more than one); 291 of the 511 interfaces have at least one implemented method.
- *JS layer:* 27,055 call sites (innermost function containing `.method(`, 3 to 80 lines) with the receiver expression, the file and line, and every `nsI*` name mentioned in the function (19% of sites mention one).
- `lookup.py <method>` returns declaring interface(s), IDL file, base, and the implementing classes with `file:line`, e.g. `asyncGetDiskConsumption` -> `nsICacheStorageService` (netwerk/cache2/nsICacheStorageService.idl) -> `CacheStorageService` (netwerk/cache2/CacheStorageService.cpp:954).

**Coverage.** Methods with at least one C++ implementation in this checkout: 67% of unique-name methods, 75% of ambiguous ones; JS call sites on unique names with an implementation: 61% (the rest are implemented outside the sparse directories or in JS/Rust, so this is a lower bound). Many call sites are not XPCOM calls at all: the most frequent names are `get`, `remove`, `sendMessage`, `set`, `clear`, `newURI`, `close`, `add`, which also exist on Map/Set/DOM objects, so a name match is a candidate, not a fact.

**Test: resolving ambiguous names.** For a method declared by several interfaces, which interface does a JS call site use? Ground truth: the function itself mentions the interface (`Ci.nsIFoo`, `nsIFoo`, or a derived interface whose chain contains the declaring one); exactly one candidate matches. The `nsI*` mentions are then masked in the code the resolvers see. 412 sites over 62 methods (at most 15 sites per method), median 3 candidates, chance accuracy 0.36. Resolvers: receiver words (words of the receiver expression such as `channel` against the words of the candidate interface and its ancestors), C++ class words (same against the implementing class names, from the index), Qwen3 similarity between the masked JS function and the interface text (name, doc sentence, method list), and a frequency prior (the method's most common interface in other files, from the labelled hints; this needs labels).

| Resolver | All | 2 candidates (180) | 3 to 4 (168) | 5+ (64) |
|---|---|---|---|---|
| chance | 0.36 | 0.50 | 0.30 | 0.13 |
| frequency prior (leave-file-out, uses labels) | 0.72 | 0.80 | 0.80 | 0.33 |
| receiver words | 0.59 | 0.72 | 0.56 | 0.34 |
| C++ class words (from the index) | 0.58 | 0.71 | 0.55 | 0.31 |
| Qwen3 (JS function vs interface text) | 0.69 | 0.91 | 0.55 | 0.47 |
| receiver + C++ class words | 0.76 | 0.93 | 0.67 | 0.56 |
| Qwen3 + receiver + C++ class words | 0.76 | 0.93 | 0.64 | 0.58 |
| prior + Qwen3 + receiver + C++ class | **0.82** | 0.94 | 0.77 | 0.64 |

95% bootstrap intervals: receiver words [0.56, 0.63], Qwen3 [0.65, 0.74], Qwen3 + receiver + class words [0.72, 0.80].

**Reading.**
- *The exact index gives the candidate set for free and exactly; the embedding only ranks inside it.* Without the index the question "which of 511 interfaces" has chance 0.2%; with it the set has a median of 3 and a label-free combination reaches 0.76 (0.82 with a prior learned from labelled sites). That matches the division of labour suggested by section 23: symbolic bridge, soft score on top.
- *Words still carry the disambiguation.* The C++ class names that the index adds (`nsHttpChannel` for `channel.asyncOpen`) help about as much as the receiver words alone (0.58 vs 0.59) but are complementary to Qwen3 on larger candidate sets (5+ candidates: 0.47 for Qwen3 alone, 0.58 to 0.64 combined).
- *The frequency prior is strong and partly an artefact.* The labelled eval set contains only sites with an interface mentioned, one interface tends to dominate per method, and sites from one file cluster; leave-file-out reduces the prior from 0.77 to 0.72 but I cannot tell how much remains selection effect.
- *Limits of the test.* Truth comes from a mention in the same function, so it covers the 19% of call sites where JS names the interface (often QueryInterface/Ci boilerplate); masking replaces `nsI*` tokens only, so other hints (variable names like `httpChannel`, `Services.io.newChannel` forms) remain and help receiver words, which is realistic but not a clean ablation; 62 methods, up to 15 sites each, one run, no tuning of the fusion (equal z-score weights); the Qwen3 interface text includes the interface name, whose words overlap with receiver names.
- *Index limits.* Static, name based: JS implementations of XPCOM interfaces, Rust/Java implementations, `getService`/`createInstance` contract IDs, `QueryInterface` chains at runtime, `Cu.import`/ES module aliasing and attribute accessors (readonly attribute `foo` becomes `GetFoo`/`SetFoo` and `.foo` in JS) are not yet in the graph; interface inheritance follows `: nsIBase` only; the class-to-interface mapping misses classes declared through other macros.

**Next.** Add attributes (`GetFoo`/`SetFoo` to `.foo`), contract IDs (`@mozilla.org/...;1` to class to interface, which resolves `getService(Ci.nsIFoo)` receivers exactly), JS implementers of interfaces, and include the Rust implementers; then re-run section 23's link test through the index (name, then interface, then class, then rank by embedding) to see how much of the 0.36 to 0.50 R@1 gap to 1.0 an exact route closes. For a language-agnostic version, the same layers exist for Windows (COM IDL, WinRT), Java (JNI) and Node (N-API) bindings.

## 25. Pilot: index v2 (attributes, contract IDs, JS receiver typing) and the link test routed through the index (2026-10-21)

**Added to the index** (`pilot/xpcom/build_index2.py`, outputs `index2.json`, `typed_sites.json`, `index2_stats.json`; stats below from this run).
- *Attributes:* 233 interfaces declare 1,062 attributes (`readonly attribute T foo` becomes `GetFoo`/`SetFoo` in C++ and `.foo` in JS); 739 have at least one C++ accessor implementation found through the class-to-interface map.
- *Contract IDs:* parsed all 169 `components.conf` files in the tree (read from git objects, so outside the sparse checkout): 195 contract IDs, 109 with a C++ class (`type`), 83 with a JS module (`esModule` + constructor); 32 have an interface list (explicit or derived from the class map).
- *JS receiver typing* (regexes, file-level names, no scoping): `XPCOMUtils.defineLazyServiceGetter(obj, "name", contract, "nsIFoo")`, `Cc[contract].getService(Ci.nsIFoo)` / `createInstance`, `x = y.QueryInterface(Ci.nsIFoo)`, and `Services.<name>` through the eslint plugin's `services.json` (interface to `Services` name). 4,472 of 27,055 call sites (16.5%) get a receiver interface; for 3,241 of them the typed interface (or an ancestor) declares the method called.

**Validation of the typing.** Where a site has both a typed receiver and exactly one candidate interface mentioned in the function (799 sites), they agree 793 times (99.2%); the two come from related declarations in the same file, so this is a consistency check, not independent evidence. For methods declared by several interfaces, 11.2% of 16,729 call sites are resolved exactly (typing 1,469, interface mention 782, either 1,872); the rest are mostly generic names (`get`, `set`, `remove`, `close`) that are not XPCOM calls at all.

**Link test through the index.** Section 23's 129 pairs, routed as: JS method name, then declaring interface, then the implementing classes in the index, then rank by Qwen3 similarity of the JS function with each implementation.
- *The index acts as a precision filter on the pairs themselves.* For 102 of the 129 pairs the C++ function paired in section 23 is an implementation the index knows; for 27 it is not. In the 14 of those I read, about 11 are spurious name collisions (`nsINode::getProperty`, `nsContentUtils::schemeIs`, `nsHistory::getState`, `nsHttpResponseHead::setHeader`, `nsIOService::recheckCaptivePortal` against unrelated interfaces) and about 3 are index misses (`CacheEntry::setMetaDataElement`/`getMetaDataElement`, whose `NS_DECL_NSICACHEENTRY` is not captured, and `SubstitutingProtocolHandler`). So the section 23 numbers were computed with roughly a fifth of the positives not being real XPCOM links.
- *Routing by exact name is enough when the implementation is unique.* On the 102 confirmed pairs the exact route returns the paired implementation 0.80 of the time with embedding ranking, against 0.82 for picking at random inside the set; 84 of 129 sets contain a single class, so the route is trivially right there. Global 129-way Qwen3 retrieval on the same 102 pairs reaches 0.53 (0.45 with the JS method name masked).
- *Embedding rank inside a set of several implementations is no better than chance.* For the 35 pairs with 2 or more candidates (24 confirmed) Qwen3 is at 0.27 (2 candidates), 0.15 (3) and 0.29 (4+) against 0.33, 0.28 and 0.17 by chance; JS words against class-name or file-path words give 0.34 to 0.40 against 0.33 (24 pairs, within noise). The JS caller does not contain what decides which class receives the call; only a runtime receiver (contract ID, factory, argument) does, which is what receiver typing adds when available (109 contracts name a C++ class).

**Reading.** The exact index is the right backbone: it is cheap to build (about 25 s for the first layer, a minute with typing), exact where names are unique, it removes false pairs, and it gives candidate sets of median size 1. It does not remove the many-to-many ambiguity (several implementations, generic names, runtime receivers), and neither embeddings nor word overlap resolve it statically. Resolution has to come from receiver typing and contract IDs, which cover about a sixth of call sites in this sparse tree. The comparison "embedding 0.50 against the index 0.80" is not a measure of the embedding being worse, because without the name the index is unavailable; with a masked name the fallback is the embedding (0.42 overall, 0.45 on confirmed pairs).

**Limits.** Same sparse subset of the tree for classes and call sites (contracts from the whole tree), 129 pairs and 24 multi-candidate pairs, one run; typing is regex-based and file-level (shadowed names, `this.x` fields set elsewhere, destructuring and ES-module re-exports are not followed); 11/14 and 3/14 are my reading of a sample of the 27 unconfirmed pairs; the class-to-interface map still misses classes whose interface macro is outside a 4,000-character window; JS and Rust implementers are not indexed; attributes are in the index but not yet used by the link test.

**Next.** Use contract IDs and typed receivers as the primary route (`getService(Ci.nsIFoo)` gives interface plus contract plus class), add JS and Rust implementers, widen the checkout (js/xpconnect, xpcom/base, dom) so coverage is not an artefact of directories, and put the section 23 test on a clean pair set built from the index (confirmed implementations only, many-to-many ground truth from typed receivers).

## 26. Pilot: full-tree index (depth=1 clone), JS and Rust implementers, clean-pair link test

Date: 2026-10-21. Request (ひなた): "Test on full file clone with depth=1, and index the JS and Rust too!" Code: `pilot/xpcom/build_index3_base.py`, `build_impls3.py`, `build_index3.py`, `link_v3.py`; outputs `index3.json`, `typed_sites3.json`, `index3_stats.json`, `impls3.json`, `link_v3.json`.

**Setup.** mozilla/gecko-dev, depth=1, all blobs (sparse checkout disabled): 4.1 GB working tree, 1,218 IDL, 92,835 .js, 2,764 .mjs, 12,413 .rs files.

**Index on the full tree** (section 24/25 numbers in brackets):
- 2,390 interfaces [511], 4,899 method names [1,511], 569 ambiguous [135], 3,208 (interface, method) pairs with a C++ implementation [1,166].
- 5,521 attributes in 1,353 interfaces [1,062], 2,134 with a C++ accessor [739]. Contract IDs unchanged at 195 (the earlier checkout already had all 169 components.conf).
- JS call sites 208,633; 23,407 typed by receiver (11.2%); typed agrees with the interface named in the code in 3,999 of 4,029 checkable sites (99.3%).
- JS implementers: 878 classes/objects declaring `generateQI([...nsIFoo])` (332 outside tests). Rust implementers: 62 `#[xpcom(implement(...))]` structs. Their methods matched to IDL members: 2,290 JS and 270 Rust (interface, member) implementations.

**Coverage of typed non-test call sites** (4,091 with a declaring interface): C++ only 3,024; JS/Rust only 638 (16%, invisible before); both 78; none 351 (9%). Candidate-set size: 1 → 2,324, 2 → 1,069, 3 → 231, 4+ → 116.

**Link test A: clean pair set** (typed non-test JS caller <-> its unique implementer, any language; 1 candidate means the index route is exact by construction). Retrieval by Qwen3 over the pool of 177 sampled pairs: R@1 0.43 raw, 0.34 with the method name masked on both sides (chance 0.006). By language: C++ 0.42/0.33 (n=150), JS 0.43/0.39 (n=23), Rust 0.75/0.50 (n=4).

**Link test C: multi-implementation sets with contract-ID truth.** Only 13 sets had a contract ID that picks a class: Qwen3 picks it in 11 (0.85) versus random 0.47. Too small to conclude.

**Limits.** (1) Pair extraction dropped most JS and Rust implementers: 554 JS and 40 Rust unique-implementer sites were available, but only 23 and 4 yielded a method body, so those language rows are anecdotal. (2) Rust/JS matching is by method name, no typing of Rust callers; Rust-to-JS calls and C++ callers were not indexed. (3) Contract truth covers few sites. (4) Test paths and third_party excluded by a path regex. (5) Sample is random with seed 0, not the section 23 set, so numbers are not directly comparable with 0.50/0.36.

**Reading.** The wider tree changes coverage a lot (index size ×4.7, JS/Rust-only implementers 16% of typed sites), but on pairs where the index already picks exactly one implementer, the embedding alone still finds the right one only 43% of the time (34% without the name). That is in line with section 23 (0.50/0.36): the index supplies the link; the embedding stays a weak, name-dependent score.


## 27. Pilot: extracting Code Intent from the Misskey source, and which indicators could help authors and fediverse readers

Date: 2026-10-22. Request (ひなた): try to get Intent out of the Misskey source, then think about which indicators would let the author, and people from this domain, write code that is easier to understand. Code: `pilot/misskey/extract.mjs` (TypeScript compiler API, also reads the `<script>` of `.vue`), `pilot/misskey/analyze.py`; outputs in `pilot/misskey/out/` (`results.json`, `units.jsonl`, `files.jsonl`, `log.txt`).

**Setup.** misskey-dev/misskey, depth=1, commit fbd637a. 1,861 non-test `.ts`/`.vue` files in backend, frontend, frontend-embed, misskey-js, sw, frontend-shared; 4,604 units (named functions, methods, Vue setup functions, and the `super(meta, paramDef, async (ps, me) => ...)` handler of each REST endpoint) with at least 3 lines. The repo ships its own declared conventions (`AGENTS.md`, `.claude/skills/working-on-backend|frontend`), which gave a ground truth for convention checks that the Python pilots did not have.

**How Intent is taken here (same recipe as sec. 20, rebuilt for TS).** Per unit: (a) layer, from the path only (be:service = `core/`, be:endpoint, be:activitypub, be:queue-processor, fe:component, fe:page, ...); (b) effect category from reachable "leaves" instead of names: db.read/db.write on `*Repository`, query-builder chains, redis read/write, `globalEventService.publish*`, `queueService.*`, ActivityPub/HTTP calls, `*EntityService.pack`, other service delegation, Vue `ref/computed/emit`, `os.*` dialogs, `misskeyApi`, DOM/local state. Calls are followed through `this.x()` and bare helpers in the same file, to a fixpoint. Category = write > emit > read > delegate > ui > state > pure, so e.g. an endpoint handler becomes "reads DB, packs entities, delegates to services" without looking at a single identifier. (c) style: 7 unsupervised k-means clusters over name-free structure features (loops, array chains, property mutation, let share, await vs then, this/class, switch, ternary, try/throw, nesting, size). The clusters came out mainly as: class-method style (1,329), small function style (1,727), nested/mutating closure style in Vue setup (854), ternary/chain-heavy (360), try/throw/await (180), switch-heavy (135), then-chain (19). They are labelled by their strongest features, not as good or bad.

Category counts: pure 1,960, read 1,083, ui 432, write 392, state 390, emit 202, delegate 145. Backend services are the mixed layer (write 231, pure 224, read 158, emit 85); endpoints are mostly read (239) with 81 writes; entity-pack is almost purely read (108 of 147); frontend components and pages are mostly pure/ui/read.

### What was measured

**1. Declared conventions are followed almost uniformly, so a deviation is a real signal.** Share of files that follow: `<script setup lang="ts">` 592/592; type-only `defineProps` 415/415 and `defineEmits` 196/196; no Options API 592/592; every endpoint file extends `Endpoint` 438/438; SPDX header 1,847/1,861 (99.2%); no `@ts-ignore` 99.2%; Vue files with `<style>` using SCSS modules 425/460 (92.4%); no `any` in backend files 92.3%; no literal text nodes in templates (i18n) 526/592 (88.9%); DI via `@Inject(DI.x)` for repositories 286/292, services by bare type 597/598. The weakest rules (literal text in templates 67 files, SCSS module 35 files, `any` 73 files) are the ones a tool would flag first.

**2. Does the style tell the reader the effect?** Mutual information between style cluster and effect category *within a layer* is 0.180 bits, against 0.042 (mean) and 0.048 (p99) for category shuffled inside the layer (200 shuffles). So style is informative, but only a little. Per layer (observed vs shuffle mean, bits): be:queue-processor 0.98 vs 0.24, be:activitypub 0.51 vs 0.12, be:entity-pack 0.41 vs 0.07, be:server 0.42 vs 0.12, be:service 0.26 vs 0.02, be:endpoint 0.12 vs 0.03, fe:component 0.05 vs 0.01, fe:page 0.06 vs 0.01. Reading: in backend layers a reader can partly infer "writes / emits / reads" from the shape of the function (try/throw/await for emit-and-write work, plain class methods for reads); in the Vue layers the shape says almost nothing about the effect, so there the effect has to be carried by something else (names, a template, or an explicit marker). Caveat: a part of this MI is confounded with size and class-ness.

**3. Name versus structure for the effect category** (5-fold, grouped by file, naive Bayes; macro recall is the fairer number because 'pure' is 43%): majority 0.426 accuracy; layer only macro-recall 0.256; name only 0.353; structure only 0.359; layer+name 0.444; name+structure 0.496; layer+name+structure 0.527. Names alone are no better than structure alone; each adds to the other and to the layer. This repeats the Python result: names are a weak, partly independent channel for effect, so a checker that compares them has something to find.

**4. Name verb versus reachable effect.** Names starting with a read-like verb (get/find/fetch/list/is/has/check/pack/parse/resolve/validate/build/calc ...): 65 of 962 (6.8%) reach a DB/Redis/file write or an event/queue/federation emission. Hand-checked: `PageEntityService.pack` really runs `pagesRepository.update` inside a getter, which is a true hidden write; `ChatService.getRoomReadStateMap` was labelled "write" because my rule treats a Redis pipeline as write, which is a false positive. Verb → category table (share): `get` pure 0.66 / read 0.20 / write 0.04; `is` pure 0.88; `pack` read 0.89; `publish` write 0.84, emit 0.16; `delete` write 0.50; `create` pure 0.31, emit 0.25, write 0.22, read 0.11; `update` pure 0.29, write 0.24, read 0.20; `save` read 0.61 (mostly Vue "save" that posts through the API); `set` pure 0.57; `on` pure 0.48, ui 0.25. The write-like verbs are ambiguous in this code (`create` = construct a value or perform an effect), which is itself a readable fact: a 50% "mismatch" for mutator verbs is not a defect, it shows that these verbs do not say which one.

**5. Intra-layer outliers and file homogeneity.** Distance from the layer median in the structure space lists the units whose shape is unusual for their layer; the top ones are the known large methods (`NoteCreateService.create`, `NoteCreateService.postNoteCreated`, `DriveService.addFile`, `MfmService.toHtml`, endpoints `i/update`, `admin/update-meta`; Vue `MkPostForm.post`, `MkSuspense.process`). Mean within-file style entropy is lower than the layer entropy everywhere (e.g. be:service 1.05 vs 1.69 bits, fe:component 0.76 vs 1.29): files are more consistent than layers, so "a unit that differs from its own file" is the sharper drift signal.

**6. Where intent is written down.** Only 2-16% of units carry a leading comment (ui 2.3%, read 4.2%, delegate 4.1%, state 12.6%, emit 11.4%, pure 14.6%, write 15.8%). Of units with cyclomatic complexity of 12 or more, 83% in services, 97% in endpoints, 97% in components and 93% in entity-pack have no comment at all.

**7. Domain vocabulary.** Counts of unit-name words (not synonym-resolved, so rough): user 111 vs account 34 vs actor 4 vs person 5; note 77 vs post 26 (post is often the UI verb); reaction 16 vs like 11; emoji 39, emote 0; follow 32, following 16; instance 21, server 17, host 15; remote 17, foreign 0; drive 24, file 55, media 10; no `boost/reblog/toot`. Across 431 words used by 5 or more units, 87 occur in both backend and frontend; Misskey-specific words (`renote`, `antenna`, `channel`, `clip`, `flash`, `role`, `drive`) have no direct Mastodon equivalent; only some of them were counted above. Short receivers dominate the chains where names carry no meaning: `os` (1,014 call sites; this is a real module name), `qb` 241, `gl` 210, `q` 115, `ps` 68.

### Candidate indicators (what would help the author, what would help a fediverse reader)

Offered as placement and consistency information; none of them ranks a style.

For the author, while writing:
1. **Layer × style × effect card for the unit being edited**, built as above: "in this layer 82% of units that write DB use style cluster X; this one is in cluster Y". Measured basis: items 2 and 5. Cheap, symbolic, no model needed.
2. **Name/effect agreement flag**: show the effect set next to the name when a read-verb name reaches a write/emit (6.8% here, about 65 units) and the effect list when a verb is known to be ambiguous (create/set/save/update/on). Basis: item 4. Needs a leaf table that is right; the Redis pipeline error above shows the table has to be tuned per codebase.
3. **Convention drift against the repo's own declared rules**, with the rule text (item 1): literal text nodes in templates, SCSS non-module styles, `any`, SPDX; these come from the repo's `AGENTS.md`/skills, so a checker can cite them instead of inventing rules.
4. **Within-file style deviation** (item 5), which is more sensitive than layer deviation.
5. **Undocumented-complexity list** (item 6) as "intent not written anywhere": complexity 12 or more, no comment, name does not agree with the effect.
6. **Naming collisions with domain terms**: two names for one concept in the same layer (user/account, instance/server/host) as a prompt to pick one; word counts alone are not enough, so this needs context (not measured).

For people from the fediverse domain, while reading:
7. **Concept glossary generated from the code**: every domain word (note, renote, antenna, channel, clip, drive, role, remote/local) with its entity, the layers that mention it, and the effect categories of the units using it, so that a Mastodon person finds where "boost" is called `renote` (measured only as word counts here).
8. **Protocol-boundary view**: units that reach `federation.ap`/`net.http` (the emit category, 202 units) versus those that stay local, so a reader sees which code is observable by other servers; ActivityPub layer already has the strongest style/effect signal (MI 0.51).
9. **Server vs client twin view**: the same noun (note) appears as endpoint → service → entity-pack on the backend and as component → page on the frontend; linking them by name plus misskey-js types is the Misskey analogue of the XPCOM bridge index in sec. 24 (not built).

### Limits
(1) Single snapshot, no git history, so "drift" is cross-sectional only. (2) The leaf table was written by Claude after looking at the top callees of three layers; coverage is partial (e.g. mail via `nodemailer`, Redis pipeline reads, `service.call` hides what the other service does) and the category 'pure' includes units whose effects are not in the table. (3) Style clusters are k-means with k=7 on 17 hand-picked structural features, not learned offsets as in sec. 19; MI is partly size/class confounded. (4) The verb lists are hand-made. (5) No embedding model was run (nothing new would be tested without the AST leaf table; the embedding route from sec. 16-18 would be the next comparison). (6) Not hand-verified: only two of the flagged units were opened in the source.

### 27.1 Worked example: a high-complexity, long-untouched unit refactored (2026-10-22)

Selection: full history fetched (29,026 commits); for the 251 units with cyclomatic complexity 12 or more and 25+ lines, `git blame -w -M` on the unit's line range gave the newest line date. Oldest (not touched for 4.1, 3.4, 3.3 ... years): `getNoteSummary`, `ImportMutingProcessorService.process`, endpoint `hashtags/list`, ... ; `searchEmoji` (frontend/utility/search-emoji.ts, cyc 33, 88 lines, untouched 2.7 years, no comment) was chosen because it is pure, so equivalence can be proven mechanically.

Change: the five hand-copied match passes (exact, exact+alias, prefix, prefix+alias, substring) become a table of `{bonus, skipIfMatched, byAliasTarget, test}`, run by one `collectMatches`; `searchEmojiExact` reuses the first two rows instead of a copy; the fuzzy part is its own `fuzzyHits`. Structure metrics (extract.mjs): max cyclomatic 33 → 8, longest function 88 → 25 lines, the duplicated block is gone. Equivalence: 40,000 random cases (duplicate names, aliases, max in 0/1/2/5/30, empty/null query) against the old file, 0 differences; the 5 new unit tests pass on both old and new code. Not run: ESLint and the repo's vitest (dependencies not installed). Patch: `pilot/misskey/patches/0001-search-emoji-table-driven.patch`, not pushed anywhere.

Revision (same day, ひなた: aim for code that reads without comments; comments only for background, never logic): all comments that narrated logic were removed. What they said moved into names: `exactRules`/`partialRules`, `scoreBonus`, `ignoreIfAlreadyMatched`, `keyedByAliasTarget`, `isAlias`, `countQueryCharsFoundInOrder`, `FUZZY_MIN_QUERY_LENGTH`, `AUTOCOMPLETE_POPUP_SIZE`. One comment remains, a background one (why the fuzzy hits are capped: all hits make the list noisy, the cap is the autocomplete popup size). Same 40,000-case equivalence check, 0 differences.

Revision 2 (ひなた: put the refactored code through the code-style + Intent view; "it should be possible to make it more intuitive"). The Intent of `searchEmoji` is pure ("rank emoji by closeness of the name to the query"), and the fe:util layer is mostly small plain functions (cluster share 40%) and nested closures that mutate a Map (29%); the original 88-line function sat in the rare chain-and-branch cluster (5% of the layer), and the v1 table-of-rules version needed rule objects that no neighbour uses. v2 mirrors the intent directly: `nameMatchScore(x, query)` gives one number (exact 3/2, prefix 1/0, partial -1 plus query length; alias is weaker), `rankByNameMatch` keeps the best score per original emoji and sorts, `searchEmojiExact` is the same ranking on the exact-name subset. All units are in the layer's two common clusters; max cyclomatic 7, longest function 18 lines. Equivalence vs the original: 40,000 random cases with dense name collisions and aliases, 0 differences when non-alias names are unique. One deliberate preservation: when two non-alias emoji share a name, the original lets the later one win unless the result list is already full at that point (an accident of its early stop); v2 lets the later one win always (`replacesSameNamedEmoji`), and differs from the original only in the full-list case (476 of 40,000 in a dense-duplicate stress test, e.g. query "c", max 1). Dropping that line would make the first one win instead; which one is intended is a question for the Misskey authors.

Note on duplication (ひなた, 2026-10-22: copy-paste inside one file is fine because a reader filters the repeated part and sees only what differs; the same text across files is the problem). Measured on Misskey (frontend, backend, embed, js; 6 consecutive non-trivial lines, whitespace-normalised, comments and imports ignored): 566 duplicated windows sit inside a single file, 2,594 are shared across files. The cross-file ones concentrate in the sibling note endpoints (`notes/drafts/create` 74 windows, `notes/hybrid-timeline` 70, `notes/timeline` 70, `drafts/update` 66, `notes/create` 57, `user-list-timeline` 49) and in a few Vue files (`MkNote.vue` 48, `admin/federation.vue` 45). So the proposed indicator is "repeat across files" rather than "repeat"; within-file repeats should be shown as aligned diffs, not flagged. By this view the original `searchEmoji` was not hard to read because its five passes repeated, but because it was 88 lines at nesting depth 5.

Variant 3 (ひなた: try the `addFilter` form): `NameFilterChain` (immutable; `addFilter(bonus, test)` returns a new chain; `scoreOf` = query length + bonus of the first filter that passes). `exactNameFilters` has two filters, `partialNameFilters` extends it with three more, so `searchEmojiExact` and `searchEmoji` share the first two lines instead of copying them. Same equivalence results as v2 (0 differences with unique non-alias names; the same 476/40,000 only in the duplicate-name + full-list case). Files: `pilot/misskey/patches/0002-search-emoji-addfilter.patch`, `search-emoji.addfilter.ts`. On "refer to Perl search code": not looked up; if meant as a source of ranking ideas (e.g. exact > prefix > substring > fuzzy tiers) that is already the shape here, and copying code would have to respect each module's licence next to Misskey's AGPL.

Variant 4 (ひなた: `addScore((emoji, q) => { if (emoji.name == q) return 3 })`, then "that is priority rather than score", so renamed to `addPriority`; `EmojiPrioritizer`, `priorityOf`; the fuzzy pass still produces a real score, a count of matched characters, and is compared with the priority-based number, which is the one place the two scales meet): `EmojiScorer.addScore(scorer)`; each scorer returns a number when it matches and null when not, and the emoji's score is query length plus the best score any scorer gave. One scorer per tier (exact, prefix, substring), with the alias nuance written inside it (`isAlias(x) ? 2 : 3`). 5 filters become 3 scorers, and because the result is the maximum, the order of `addScore` calls no longer matters. Equivalence as before (0 differences for unique non-alias names; 476/40,000 only in the duplicate-name + full-list case). `noImplicitReturns` is on in the frontend tsconfig, so the scorers end with `return null` instead of falling off the end as in the sketch; `tsc --strict --noImplicitReturns` passes on the file. Files: `0003-search-emoji-addpriority.patch`, `search-emoji.addpriority.ts`.

Variant 5 (ひなた: `EmojiScorer.run([...])` should keep the behaviour; and the split into `setScoreIfNull` / `addScore` from the previous message): `EmojiScorer.run(steps, query, emojiDb, max)` runs an ordered list of steps over one shared result map. `setScore` overwrites, `setScoreIfNull` only writes where the emoji has no score yet (the original `!matched.has`), `addFuzzyHits` is the last step; `searchEmojiExact` runs only the first two steps. Because order is explicit and the early stop is kept, this variant matches the original exactly: 0 differences in 40,000 cases, including the dense duplicate-name stress test that variants 2-4 failed in 476 cases. Files: `0004-search-emoji-run-steps.patch`, `search-emoji.run-steps.ts`.

### 27.2 Reverse lookup: from an Intent to the distribution of styles that exist for it (2026-10-22)

Request (ひなた): using the search code as the model, make it possible to look up the style distribution from an Intent, so one can see whether a better style might exist. Code: `pilot/misskey/intent_to_style.py` (reads `out/unit_styles.jsonl`, which `analyze.py` now writes: per unit layer, effect category, reachable leaves, style cluster, size, complexity); examples in `out/intent_to_style_examples.txt`.

Design. An Intent is (layer, effect category, name verb). Matching reuses the shape of variant 5: ordered steps, each unit keeps the first step that matches (set-score-if-null), and steps run until enough units were found (`--min`, default 15): layer+category+verb, then layer+category, then category+verb in any layer, then category alone. The answer is a table of style clusters, each with its share, median size and complexity, share of async units and one small example, shown twice: in this layer, and elsewhere in the code base, plus the styles that serve the same intent elsewhere but never in this layer. It shows what exists; it does not say which is better.

Examples (4,604 units). `fe:util / pure / search` has only 2 exact units, so the lookup widens to all 217 pure fe:util units: small plain functions 46%, class methods 26%, nested mutating closures 21%, ternary/chain-heavy 4% (median 46 lines), switch-heavy 2%; the original `searchEmoji` sat in the 4% group, the refactored versions in the first or third. `be:service / write / create` (19 units): small class methods 74% (median 27 lines, complexity 2), ternary/chain 16%, and two units at 184 and 202 lines with complexity 55 and 77 (`ReactionService.create`, `NoteCreateService.create`): the same intent is mostly served by one short shape, and the two long ones are the visible alternatives. `be:endpoint / read`: class-handler 64% (median 11 lines), ternary/chain 23%, try/throw 8%, switch 5%.

What it can and cannot say. It can say "for this Intent, 74% of existing units use shape X, yours uses Y", and which shapes appear only elsewhere. It cannot suggest a style that Misskey does not already contain, because the 7 clusters are k-means over structure counts (loops, chains, mutation, try, switch, size) and do not see paradigm-level shapes such as a table of rules, a step pipeline or a builder (the variants of 27.1 would all fall in the same two clusters). So "a better style may exist" is only answerable inside the observed distribution here; the next step is to pool other codebases (the Python pilot data, other TS apps) and add paradigm features (rules-as-data, higher-order composition, builder chains) so that the distribution for an Intent includes shapes this repository never used.


## 28. Preparing a multi-language corpus for the Intent/style index (2026-10-22)

Request (ひなた): find large projects in each major language and get ready to build an index. Files: `pilot/corpus/repos.tsv` (selection with domain and reason), `sizes.tsv` (measured file counts), `summarize_trees.py`, `probe_tree.sh`, `fetch_corpus.sh`.

**Selection.** 35 repositories in 15 languages (Python, TypeScript/JavaScript, Java, C#, C, C++, Go, Rust, PHP, Ruby, Kotlin, Swift, Perl, Scala, Elixir, Haskell). Each language gets a large framework or application plus a different kind of project (compiler, runtime, database, search engine). Fediverse servers are included where a GitHub copy exists, so that one Intent (ActivityPub inbox, note delivery) can be compared across language styles: Misskey (TypeScript, done), Mastodon (Ruby), Lemmy (Rust), owncast (Go, substitute: GoToSocial and Pleroma are not hosted on GitHub; there is no Elixir fediverse server on GitHub, so phoenix stands in for Elixir). Also in: Elasticsearch (real search ranking), Laravel (fluent builders, close to the `addFilter` form), Perl 5 and Mojolicious (the Perl request), gecko-dev (already indexed in sec. 24-26).

**Measured without downloading contents.** Blobless depth=1 clones give the whole tree; non-test source file counts (vendored, generated, test and doc paths excluded): dotnet/runtime 17,952 (C# 15,876), elasticsearch 19,831, llvm 15,183 (C++ 14,179), gecko-dev 23,754, kotlin 14,830, apple/swift 11,621, discourse 10,350, home-assistant 10,964, vscode 9,403, kubernetes 7,491, aspnetcore 7,026, nextcloud 7,271, rust 6,467, spring 5,134, apache/spark 4,675, kafka 4,015, mastodon 2,966 (Ruby 2,059), misskey 2,385, gitea 2,321, WordPress 2,218, laravel 1,825, rails 1,621, postgres 1,602 (C 1,403), perl5 1,318 (Perl 1,205), django 946, node 866, lemmy 539, tokio 486, pandas 337, pandoc 295, elixir 267, redis 166, mojolicious 154. `sizes.tsv` has the full table. Total 200,900 source files over the 35 repositories (owncast has only 325 Go files, most of its source is JavaScript; it is a weak Go sample).

**Two things learned.** (1) `git ls-tree -l` (sizes) on a blobless clone downloads every blob, i.e. costs as much as a full clone; the first probe hung on the big repos and left truncated listings that looked complete (aspnetcore 3,712 instead of 17,745 files, dotnet/runtime 2,430 instead of 58,550), so only name listings are used and byte sizes will come from the real checkout. (2) The GitHub API is not enabled for repositories that are not attached, so stars, licences and pushed dates are not collected; licences must be checked per repository before any code is quoted.

**Tooling check.** `tree-sitter` with `tree-sitter-language-pack` installs through pip here and parses a sample function in all 15 languages without error, so one front end can replace the TypeScript compiler API of sec. 27. Disk: 15 GB free in this container, so `fetch_corpus.sh` clones depth=1 in the listed order and stops below 3 GB free; the largest ones (gecko-dev is 4.1 GB, llvm, kubernetes, rust, linux-class trees) will not all fit at once, so a first run should take the middle-sized set and extract per repository, deleting each checkout after its units are written.

**Index plan (not built).** One record per function or method: repository, language, path-derived layer, name verb and words, effect category from reachable platform/library leaves, structure features (loops, higher-order chains, mutation, try/throw, switch, nesting, size, async), and paradigm features that sec. 27.2 said the structure clusters lack (rules-as-data tables, builder chains, higher-order composition, trait/interface use). Per language, a small leaf table (database, network, filesystem, UI, queue/event, federation) has to be written, since the Misskey table cannot be reused; style clusters should be learned per language first and aligned across languages afterwards. Query interface = sec. 27.2 `intent_to_style.py`, with a language filter added.


## 29. Training code in Julia: an Intent-conditional style prior (2026-10-22)

Request (ひなた): write the training code in Julia. Code: `pilot/julia/export_intent_style.py` (tables for Julia), `pilot/julia/train_intent_style.jl` (stdlib only: LinearAlgebra, Statistics, DelimitedFiles, Random; run with `julia train_intent_style.jl <data> <out> [--check] [--epochs N] [--hidden H]`), data in `pilot/julia/data/`, outputs in `pilot/julia/out/` (`results.txt`, `unit_scores.tsv`, `model_*.tsv`). Julia 1.13 from conda-forge through micromamba, as in the earlier Julia notes.

**What is learned.** A one-hidden-layer MLP (48 tanh units) maps the Intent of a unit to a diagonal Gaussian over its 17 name-free, standardized style features (loops, array chains, mutation, let share, await, then, uses-this, in-class, switch, ternary, try, throw, nesting, size, complexity, optional chaining, non-null): the mean head and a log-variance head. Intent inputs are 97 binary features: layer (18), effect category (7), the name's first verb (top 40 + other), reachable leaves (21), language (1; more languages plug in as extra columns when the corpus of sec. 28 is exported). Loss is the Gaussian negative log-likelihood with L2, Adam, hand-written backprop; the gradient matches finite differences (worst relative error 7.5e-8). The score of a unit is its held-out NLL under the prior: how surprising its style is *for its Intent*. It is a map of the typical, not a quality score.

**Two failure modes found while writing it.** (1) With an unconstrained variance head the model collapses the variance of rare features (a unit almost never uses `.then` or `switch`) and every real occurrence then scores as an outlier of thousands of sigmas; held-out NLL 36.3 against 8.6 for a global Gaussian. A variance floor (standard deviation at least 0.25 of the feature's overall deviation) fixes this. (2) Even then the result depends on the number of epochs by a factor of four (12 epochs: 3.3; 60 epochs: 12.7), so the trainer keeps the best epoch on a validation fold.

**Result** (5 folds grouped by file, 4,604 Misskey units; mean held-out NLL per unit, sum over 17 features; lower is better): global Gaussian 8.58, per layer 7.19, per layer+category 6.65, MLP prior 3.67 (per fold 2.4 to 6.2; in every fold it is below all three baselines). R² of the MLP's mean per feature: in-class 0.74, uses-this 0.70, await 0.60, size 0.33, throw 0.26, nesting 0.21, complexity 0.18, try 0.10, chain 0.08, ternary 0.09; near zero for loops, let share, then, switch, optional and non-null. So Intent explains most of "class-method or not" and "async or not", part of size and nesting, and almost nothing of the micro-habits. The baselines get the same variance floor; the MLP gains partly by modelling the variance per Intent, not only the mean.

**Most surprising styles for their Intent** (held out): `MkSuspense.vue:process` (promise `.then` chain in a Vue component, +68 sigma on then), `admin-lookup.ts:lookupUser` and `NoteCreateService.postNoteCreated` (then-chains where await dominates), `update-meta.ts` handler (property mutation and array chains), `MfmService.toHtml` (try/switch/ternary in a pure converter). These are style outliers, not defects. The ranking is dominated by rare features (then, switch), because standardized rare features have a huge scale; a rank-based score would be fairer.

**Limits.** One codebase and one language; the style side is structure counts (the same features as the k-means clusters, so paradigm shapes like rule tables or builders are invisible); the Intent side has no embedding of names or docs; no seeds repeated, no confidence intervals; NLL is a heavy-tailed average (a few units move it). Next: export the multi-language corpus with the same script, add language as an Intent input and as a held-out axis (train on N languages, test on the rest), add paradigm features, and score by rank.


## 30. Learning the derivation of Intent (category) and a few clear styles (2026-10-22)

Request (ひなた): also learn how Intent and category are derived, with a few clear styles carrying the power. Code: `pilot/julia/export_tokens.py`, `pilot/julia/latent_intent_style.jl` (stdlib only); results `pilot/julia/out/latent_results.txt` (main run, 12 categories, up to 10 styles), `latent_results_kc1.txt`, `latent_results_kc30.txt`, per-unit labels `latent_units.tsv`.

**Model.** No leaf table and no hand categories on the input side. Per unit: callee tokens (receiver head + method, method alone, bare function names; for example `usersRepository.findOneBy`, `os.confirm`) and the words of its own name, 1,297 tokens with document frequency of at least 5. A latent *category* c is drawn from a per-layer distribution and emits the tokens (a multinomial topic); a latent *style* s is drawn from a per-(layer, category) distribution and emits the 17 name-free structure features as a diagonal Gaussian. EM, with a Dirichlet(0.5) MAP update on the style mix of each (layer, category) so rows can drop styles, back-off to the layer's own style mix, and pruning of styles that carry less than 2% of the units. Category is *derived* as the posterior from tokens and layer; the hand category of sec. 27 is used only for evaluation.

**Fix needed on the way.** Rare habits (one `.then`, one `switch`) sit hundreds of sigmas out in a standardized feature, so a plain mixture scored worse than one global Gaussian (8.98 against 8.58). Each style density is therefore a per-feature contamination model, 98% N(mu, sigma²) plus 2% a wide Gaussian. That changes the scale of the NLL, so the baselines were recomputed with the same density; numbers below are not comparable with sec. 29.

**Held-out NLL** (5 folds grouped by file, 17 features, lower is better): global Gaussian 22.32; per layer 17.19; per layer + hand category 15.63. Learned model with 12 categories: 10 styles 13.70, 8 styles 14.32, 5 styles 15.35, 3 styles 16.95; with the sparse prior it keeps 4.8 to 6 styles at 16.5 to 16.7. So the learned categories and styles beat the hand-made category from 5 styles up, and the likelihood keeps improving up to about 10 styles; "few" costs likelihood.

**What carries the power.** Ablation: no category at all (1 category, layer and styles only) 13.86; 12 categories 13.70; 30 categories 13.42. The learned category adds only 0.2 to 0.4 nats over the layer alone; most of the work is done by the layer and the styles. The styles that remain after sparse pruning are few and clear, and they are mostly the class/non-class split: in the sparse run 54.5% of the units sit in one style (plain functions: not in class, no this, small; fe:component, fe:page, fe:util) and 31.1% in another (class methods with this; be:service, be:endpoint, be:entity-pack), then 6.7% throw/await handlers (be:endpoint), 4.9% big await-and-chain service methods, 2.7% large nested mutating functions. The first two styles cover 86%. In the dense run the extra styles are finer: switch/try (4.7%), loops with `let` (4.4%), then-chains with optional chaining (2.8%).

**Learned categories** (topics over tokens; the hand category is in brackets): UI and dialogs (`os.apiWithDialog`, `os.confirm`, `os.alert`, `misskeyApi`: hand read/pure), event and menu handlers (`on`, `emit`, `dispose`, `menuItems.push`: pure/ui), getters and type checks (`get`, `is`, `Array.isArray`, `Object.entries`: pure), endpoint handlers with repositories and moderation log (`handler`, `findOneBy`, `pack`, `idService.gen`, `moderationLogService.log`: write/read), DOM and math utilities (`addEventListener`, `Math.floor`: pure/state), entity packing (`pack`, `packMany`: read), HTTP replies (`reply.code`, `reply.header`: write/emit), WebGL uniforms plus query builders, logging and assertions, and three query-builder topics (`makePaginationQuery`, `where`, `orderBy`, `createQueryBuilder`: read). They agree only loosely with the hand categories (normalized mutual information 0.18 to 0.20): the learned topics split by domain (database query, UI dialog, DOM, WebGL), the hand ones by effect (read, write, emit); neither is the right one, they are two views, and the unsupervised one needs a person to name the topics.

**Limits.** One codebase and one language; the 5-fold numbers come from one seed each; the contamination weight (2%) and the variance floor were set by hand; the number of categories (12) was not tuned (30 is slightly better); tokens come from Claude's callee extractor, which keeps only the first 60 calls per unit; and a style here is still only a cluster of structure counts, so the same blindness to paradigm shapes as in sec. 27.2 applies. The next step stays the multi-language corpus (sec. 28): the same model with the language as a layer-like input would show which learned styles are shared across languages and which are local to one.

## 31. Latent model on the multi-language corpus (GitHub Actions, run 39760355017)

**Setup.** `train-corpus.yml` extracted 35 repositories in parallel (tree-sitter), then trained once on the pooled table: 409,187 function units, 36 repositories, 17 languages, 90 language:role layers, 6,000 tokens (min-df 20). Hold-out is 6 whole repositories never seen in training (46,445 units); 24 categories, 12 styles. Extraction took about 10 minutes, the Julia fits about 9 minutes on one runner.

**Held-out NLL (lower is better).** Global mean 21.54. The per-(language:role) layer baseline 12.34. Dense latent model 15.45. Sparse latent model 17.92 (it pruned 12 styles to 4).

**By language (global / layer / dense / sparse).** c 23.68 / 8.94 / 15.59 / 19.08; go 18.92 / 5.11 / 13.22 / 15.36; perl 21.11 / 6.13 / 14.11 / 16.97; php 22.04 / 15.66 / 18.42 / 21.26; ruby 18.56 / 4.87 / 11.59 / 13.28; javascript 22.89 / 23.24 / 15.98 / 17.94; typescript 26.46 / 27.74 / 19.56 / 21.94; tsx 27.42 / 27.43 / 20.91 / 24.51.

**Reading.**
- This is a negative result for the latent model as built. Where the layer baseline has seen a similar layer in training (c, go, perl, php, ruby) it beats the latent model by 3 to 8 nats. The latent model wins only for javascript, typescript and tsx, where the baseline is no better than the global mean (their held-out layers are mostly unseen roles), so the latent model there is acting as a fallback, not as an improvement.
- The earlier single-codebase result (sec. 30, latent below the layer baseline) does not carry over: with language and role folded into the layer, most of the predictable style is already in the layer. The latent categories add little on top of it.
- Styles are not yet "few and clear". The dense run keeps all 12 but two cover 93% (class methods with `this`, 58%; plain functions outside classes, 35%), and both mix many languages (dominant language 23% and 26%). The small ones are throw/try/cyclomatic-heavy handlers (3.4%, python/typescript/php) and deep, long, let-sharing methods (3.2%, csharp/java/go). The sparse run collapses to 4 styles. So the strong shared styles are the class/non-class split and an error-handling-heavy one; finer paradigm differences are not visible in the 17 structure features.
- Categories split mainly by language and ecosystem, not by purpose. 17 of 24 are at least 80% one language (php `isset/empty/writeln`, go `Errorf/Sprintf`, csharp `ThrowIfNull/Debug.Assert`, elixir `defp/case/unquote`, rust `Some/Ok/unwrap/clone`). The cross-language ones are mostly role-like: accessors `get/set/is/has/type/name` (java 47%, cpp 11%, typescript 7%), tests and assertions (`EXPECT_EQ`, `assertThat`: cpp 53%, java 41%), logging and assertion in C-family code (`serverLog`, `MOZ_ASSERT`, `elog`: c/cpp). Tokens are callee names, so language-specific stdlib names dominate; a shared vocabulary needs the leaf categories (write/emit/read) instead of raw tokens, which is the next thing to try.

**Limits.** One seed; the 6 held-out repositories are not balanced across languages (php 12.5k and ruby 11k units, tsx 295); the NLL is heavy-tailed; the run is capped at 15,000 units per repository; hand-set variance floor and contamination weight as before; tokens are raw callee names.

**Next.** (1) Replace raw tokens by leaf-category counts so categories can be shared across languages; (2) add a language-local style offset to the latent model instead of treating the layer as a separate baseline; (3) add paradigm features (chain/builder shape, pattern match, early return vs steps) so styles can differ beyond the class split.

## 32. Leaf-class tokens, per-language centering, paradigm features (Actions run 39763240944)

**Variants.** Same 409,187 units, 6 held-out repositories, 12 styles; only the export changed. `base`: raw callee tokens, 24 categories (a re-run of sec. 31). `leaf`: callee names replaced by seven language-independent effect classes (write, emit, read, ui, state, pure, delegate, plus none) and the leading verb of the unit name, 1,699 tokens, 8 categories. `leaf-centered`: leaf plus every structure feature standardized inside its language. `leaf-centered-paradigm`: that plus closures, call density, branch density and "returns more than once". The leaf table is a hand-set prefix table over the last segment of the callee (first match in the order write, emit, read, ui, state, pure, else delegate); it is crude, and words such as `to`, `is`, `use` are matched by prefix. NLL is comparable only within a variant, because the features differ.

**Held-out NLL (global / language:role layer / dense / sparse).**

| variant | global | layer | dense | sparse | dense minus layer |
|---|---|---|---|---|---|
| base | 21.54 | 12.34 | 15.45 | 17.77 | +3.1 |
| leaf | 21.54 | 12.38 | 15.27 | 17.74 | +2.9 |
| leaf-centered | 21.60 | 13.59 | 17.49 | 19.65 | +3.9 |
| leaf-centered-paradigm | 27.23 | 19.30 | 22.63 | 26.18 | +3.3 |

**Reading.**
- Leaf tokens do as well as raw callee names with a quarter of the vocabulary and a third of the categories (dense 15.27 against 15.45), so the cross-language vocabulary costs nothing. It does not close the gap to the layer baseline.
- The latent model still loses to the language:role layer baseline in every variant (by 3 to 4 nats), and wins only for javascript, typescript and tsx, where the layer baseline is no better than the global mean. Centering by language does not change that, so the language offset is not what the latent model is missing. A plausible reason, not tested: the layer baseline uses a per-layer variance, while the latent model shares each style's variance across all layers.
- After centering, the styles become shared across languages, which was the point. In `leaf-centered-paradigm` three styles cover everything: plain small functions (83.7%, no language above 15%), long complex functions with many closures and deep nesting (12.8%; java 16%, perl 15%, cpp 8%, rust 8%), and try plus await handlers (3.5%; typescript, python, csharp, javascript). Without the paradigm features the second is "long, loops, deep" (3.7%) and a separate "fewer awaits and optional chains" style (19.7%; typescript, csharp, javascript), which is an async-language marker and probably a feature-definition artefact rather than a style. So the closure and nesting features add one real, language-independent style; they do not add many.
- Leaf categories are now readable across languages: accessors and equality (`k:read k:pure`, php/java/typescript), CRUD (`k:write k:ui`, v:add/create/update/remove), construction and parsing (`k:pure v:new v:parse v:format`, python/rust/go), tests and visitors (`k:delegate v:test v:visit`), logging and assertions (`k:emit k:state v:assert v:print`), and two that are really one codebase (cpp diagnostics `v:diagnose v:mangle`, and C/Ruby/Elixir glue `v:pg v:rm v:exec`). Several mix a domain with a language family; 8 categories is probably too few.
- The sparse fit still collapses to 3 or 4 styles in every variant; the two or three big ones carry over 90%. That is the "few and clear" behaviour wanted, but it also means rare styles are pruned, not found.

**Limits.** One seed; the same 6 held-out repositories; hand-set leaf table and prefix matching; "returns more than once" is a crude early-return signal and does not see guard clauses specifically; no test of the shared-variance explanation.

**Next.** (1) Give each layer its own variance (or a mixture of per-layer scale) in the latent model and see whether the gap to the layer baseline closes; (2) a held-out check that works per language, so the answer to "is this style shared" does not rest on the pooled NLL; (3) replace the prefix table by an evidence-based leaf classification (the reachable-leaf method of sec. 27) for the languages where it can be computed.
