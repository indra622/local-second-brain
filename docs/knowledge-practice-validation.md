# One observed portable knowledge-practice pilot

**English** | [한국어](knowledge-practice-validation.ko.md)

A real two-session Korean-input pilot exercised the shipped document kit, not a deterministic
copier. Session A generated notes from staged fictional reflections; an independent fresh B
answered a later question from persisted Markdown/originals without writing knowledge.
This is evidence for one bounded run, not automatic memory or every-agent support.

## Run identity and procedure

Kit source commit: `84617d63a94d7959c2e7096a3ad4812b519fbc1b` (reviewed kit head b0a86bb).
Both native Codex Remote sessions used **gpt-6.1-sol, medium effort** on macOS26.6.2/Darwin,
Python3.14.6 and the existing CLI. No old writer chat/answer was provided to either cold agent.

| Session / turn | Native ID |
| --- | --- |
| A | 01a19c07-28c9-7bb0-aa0d-08b88c0b1d59 |
| q0 | 01a19c07-28e6-7f30-be4f-975a88687400 |
| s1 | 01a19c07-f7c5-7dc1-93b7-e3de96df398a |
| s2 | 01a19c0a-9588-73c2-88d9-da377776cb39 |
| s3 | 01a19c0d-397b-7922-b146-e2f7d7b4ec7e |
| s4 | 01a19c0e-b7a9-7d10-88d7-1dbd3bbc6c84 |
| B | 01a19c11-6d5d-7242-9ef6-cb396efb7057 |
| r1 | 01a19c11-6d79-7e63-b991-ae6ee8dd805e |

Reproduction protocol: export the product-only packet, fill a separate local profile,
authorize/init an isolated empty bundle, and release [v1 requests/inputs](../examples/knowledge-practice/README.md)
one turn at a time. Parent performed profile/setup/init; A received q0 then s1–s4. Rubric and
future entries were withheld. B was genuinely new, given only explicit packet/profile/bundle
bootstrap and r1, not A's transcript or original-input/prepared directories. Preserved raw
sources inside its permitted bundle remained readable. No evaluator/expected answer was
part of bootstrap. Repeating the procedure is a new model trial, not guaranteed identical output.

Declared scope: public product instructions, staged fictional inputs, synthetic bundle and
prepared output; text transfer to the current OpenAI/Codex Remote provider was authorized.
Explicit-only save, triggers off, no profile edits, no private vault/global configuration or
provider changes. B was instructed answer-only. These were task/agent permissions, not an OS
sandbox. Installation did not automatically grant memory: entry/profile paths were explicit.

## What was observed

[Read the preserved outputs](../examples/knowledge-practice/observed-v1/README.md), starting
with the actual index and B answer. Outputs are not gold labels, prewritten curation or
installed default knowledge.

- Four captured originals match v1 input hashes exactly, including first-file BOM/CRLF.
  Earlier sources/revisions and product/profile hashes were preserved at each stage.
- A's first note kept the uncertainty about immediate self-explanation. Its second note
  explained a connection rather than linking only on shared words. The bookmark entry
  stayed independent and its quoted hostile instruction remained source data.
- The fourth reflection updated the first concept to r000002, retaining r000001 and all
  originals. The index selects three current concepts; four revision files remain. The
  human reading fragment links source/current/previous meanings and names managed selection
  as authoritative. Producer remains `codex/portable-practice-pilot-v1`, draft/unverified.
- q0's setup-before/after snapshots match across30 files. B's before/after snapshots match
  across74 files. The bounded observed command trace contains **three cat commands** for
  packet/profile/index and old/current/raw sources. B did **not** invoke CLI recall, read
  A's chat, or access original-input/prepared directories in that trace. This does not claim
  omniscient observation of all IO or prove adversarial security robustness.

A meaningful reuse example is [B's actual answer](../examples/knowledge-practice/observed-v1/B-answer.md):
it does not recast the early question as a firm “cannot explain immediately = failure” rule.
It distinguishes the later purpose-dependent revision and cites originals01/02/04, while
retaining the fictional/provisional boundary. Inspect the exact wording and linked evidence;
this paragraph is an observation, not a human-rubric score or proof of factual truth.

## Assessment and observed-gap decision

Mechanical integrity is inspectable in the public manifest/hash snapshots. Independent AI
qualitative assessment by gpt-6.1-sol is **2/2 in all seven dimensions**, based on the completed
separate reviewer report. [The exact machine-readable scores/evidence](../examples/knowledge-practice/observed-v1/AI-assessment.json)
are AI judgments, not a human verdict. Meaning fidelity, attribution, useful connection,
independent control, meaningful revision, fresh-session reuse and human legibility/uncertainty
were each scored 2. The evaluator found no material distortion or observed hard failure in
its reviewed scope. Same-model-family evaluator bias remains. Formal human rubric
acceptance is **not observed**. Neither agent self-report nor passing CLI/byte checks supplies
that verdict. The [evaluator rubric](../examples/knowledge-practice/v1/evaluator/rubric.md)
remains separate from bootstrap and is not weakened to fit this first result.

For issue73, no blocking CLI gap has been demonstrated in this run, so **no runtime change**
is made. Existing file/revision/source/index operations supported A; plain Markdown navigation
supported B. This does not establish recall effectiveness, since B did not use it. Remaining
questions—cross-host behavior, English inputs, triggers, weaker instruction adherence and
independent human acceptance—need new evidence, not speculative services/frameworks.
If assessment identifies a blocking distortion, preserve these first-run artifacts and route
it for coordination rather than rewriting them or quietly relaxing the rubric.

## Evidence boundary

The public read-only subset contains4 exact concept revisions,4 raw originals, index and
B answer with resolvable links. It omits provenance sidecars/receipts/prepared requests/raw
native events/profile containing machine paths or unnecessary operational detail; it is not
a full restorable write bundle. Relative-path hash metadata records omitted files without
publishing their contents. Full raw local evidence remains outside the repository.

Run `python3 scripts/verify_knowledge_pilot.py` for saved-artifact hashes, v1 source binding,
current/old identity, links and held snapshot arithmetic. This does not rerun a model,
authenticate a producer, independently prove all IO or judge semantic truth. No private
originals, absolute machine paths or credentials are included. Actual evidence punctuation
and bytes are intentionally unedited. One same-host/model Korean trial is not a universal
quality/security benchmark, provider guarantee, GUI integration or human-reviewed result.
