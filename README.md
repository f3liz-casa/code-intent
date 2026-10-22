# Code Intent

Research notes and small pilots for **Code Intent**: a language-agnostic layer, like LSP but for the purpose of code, so that AI writes code that is both *working* and *familiar* (it matches the conventions and the style of the codebase), and so that people can read the intent of code from its style.

Core idea: the *style / paradigm* in which a piece of logic is written is part of how its intent is communicated. Wrong style for an intent hides the intent. The project tries to place code in a map of **intent (what it does, from platform-API leaves, not names) × style (how it is written)**, without ranking styles as better or worse.

## Layout

| Path | What |
|---|---|
| [`docs/terms.md`](docs/terms.md) | The running research log (sections 1-28): terms and name check, embedding survey, goals, every pilot with its numbers and limits |
| `pilot/` | Pilot code and small results (large data, model weights and embeddings are not in the repo) |
| `pilot/style/` | Category × style matrix, AST/API-leaf tokenizer, Python stdlib preset (sec. 19-22) |
| `pilot/xpcom/` | Firefox C++ ↔ JS link test and the exact XPCOM bridge index (sec. 23-26) |
| `pilot/misskey/` | Intent extraction from Misskey (TypeScript/Vue), indicators, reverse lookup Intent → style distribution, and refactor examples (sec. 27) |
| `pilot/corpus/` | Multi-language corpus selection (35 repositories, 15 languages) and tree-size probe (sec. 28) |

## Findings so far (short)

- Pretrained code embeddings separate *categories* of intent for unseen intents but are weak style encoders; a name-free structure tokenizer beats them for style (sec. 16-20).
- Category should come from platform/library API leaves reached through the call graph, not from names (sec. 20-22).
- Exact symbolic bridges (IDL index) beat embeddings for cross-language links; embeddings stay a soft score (sec. 23-26).
- On Misskey: effect category from leaves works without names; style carries the effect only weakly (strong in backend queue/ActivityPub layers, almost none in Vue); names and structure are separate, complementary channels; the repo's own declared conventions are followed 89-100%, so deviations are real signals (sec. 27).
- Indicators proposed for authors and domain readers (sec. 27), and a reverse lookup from an Intent to the styles that already exist for it (sec. 27.2).

## Status and caveats

Pilots, not a product. Datasets are small or single-author in places, leaf tables were tuned by hand on a few layers, style clusters are unsupervised k-means over structure counts and do not see paradigm-level shapes (tables of rules, builders, pipelines). Each section of `docs/terms.md` ends with its own limits.

## Licensing note

`pilot/misskey/patches/` contains refactoring examples of code from [misskey-dev/misskey](https://github.com/misskey-dev/misskey), which is AGPL-3.0-only; those files stay under that licence. The repository itself has no licence file yet. Licences of the corpus repositories in `pilot/corpus/repos.tsv` were not checked.
