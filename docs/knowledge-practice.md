# A portable knowledge practice

**English** | [한국어](knowledge-practice.ko.md)

Local Second Brain should let people carry a good knowledge-curation practice between
agents: preserve what they said or read, understand why it matters, connect it when
justified, reuse it later, and revise it without erasing earlier thought. Safe storage
supports this experience; saving files or project handoff alone is not the product goal.

This is the experience/acceptance specification for issue68, the accepted direction now served by the [document kit and profile examples](../knowledge-kit/START.md). Host integration and the real pilot remain untested. The [durable workflow](../workflows/AGENT-WORKFLOW.md)
remains the operational authority for commands, access, retry/CAS and interruption.

## What a person should be able to do

- Say, “Keep this reading reflection in my knowledge folder. Preserve my original and
  explain what I am working out.” The authorized external agent handles CLI details.
- Later say, “This may connect to the earlier reflection; see whether the connection is
  useful.” The agent searches within scope, reads evidence, and explains a link or says
  unrelated/not found. A graph edge is not mandatory.
- Say, “I have changed my mind about part of that.” The agent preserves the new original,
  revises the relevant knowledge and explains the difference. Earlier sources/notes stay.
- In a fresh session ask, “How did my thinking develop, and what would matter for this
  new question?” The answer uses exact stored evidence and current/previous versions,
  rather than generic reading advice or invented memory.

## Product principles

**Save by authority, not by proximity.** Store only on an explicit save request or a
user-enabled trigger with a defined scope. Installation, an ordinary question, or access
to one folder does not consent to saving every conversation, reading neighbors or using
another provider. A trigger must define eligible material, destination and revocation;
it must not silently widen permissions. An explicit do-not-save request overrides an enabled
trigger for that turn. The shipped profile describes agent-interpreted scoped triggers; no runtime trigger engine is added.

**Preserve the original before interpretation.** A provided file's original is its exact
bytes, including BOM/newlines. A chat capture must identify the text actually exposed by
the host and any export/normalization boundary; do not claim unavailable original-channel
bytes. Link the curated revision to its captured source ID. Updating interpretation must
not overwrite the capture. Capturing a source does not establish that its claims are true.

**Curate meaning, not sentence order.** Identify the user's question, reasoning, tension,
example and uncertainty. A useful note explains what the thought means and when it applies;
it is not merely a shorter transcript, extracted bullet list or sentence shuffle. Distinguish
source assertions, the user's thought, the agent's interpretation and unverified inference.
Do not turn “perhaps” into a settled rule or attribute an invented claim to a book. The
person can inspect and correct the interpretation; actor labels do not authenticate approval.

**Connect selectively.** Search plausible existing knowledge before asserting a connection.
Read the relevant note/source, name the relationship and its evidence, and leave uncertainty
visible. Shared words or categories alone do not justify an edge. Some notes need no links.
An unrelated input can be worth saving independently. Limited search coverage is not proof
of absence. Categories such as AI literacy, reading, diary and project are examples of one
person's practice, not a global taxonomy; organization/depth are future user preferences.

**Reuse and revision must be visible.** Reuse explains which exact prior source/revision
informed the later answer and how. Show what changed versus what still holds. Current is
selected by the index, not the largest revision. Retrieve old versions deliberately when
answering historical questions; do not make an old belief look current. Plain Markdown
must remain understandable with original/current/previous references. Obsidian is optional;
no bulk migration or GUI dependency follows. The shipped [navigation contract](../knowledge-kit/navigation.md) supplies agent-written Markdown fragments, not a new CLI navigation writer.

## Acceptance matrix

“Guide/data” means agent instruction or acceptance work, not built-in semantic judgment.
The document kit now ships; real execution still requires the pilot. Human inspection is
required for semantic quality.

| ID / natural user input | Durable observation / verification | Failure to reject | Support now / next addition |
| --- | --- | --- | --- |
| K1 “Save this reflection” with an allowed input and destination | Exact source bytes/digest and provenance; distinct curated revision links to it. Compare source bytes, read full note and current pointer. | Replaced original, summary saved as if original, undeclared normalization or save outside scope. | capture/curate/index exist; shipped kit instructs source-first and capture boundaries; actual execution remains untested. |
| K2 “Help me understand my thought” | Note captures reasoning, a meaningful distinction and uncertainty; source/user/agent/inference attribution can be traced to input. Human compares note with source. | Mechanical rearrangement, generic advice, stronger certainty or fabricated book/user claim. | External agent judgment; body/provenance fields exist. Meaning-centered guide now ships; semantic quality remains to be measured in72. |
| K3 “Does this connect?” plus a related second entry | Agent records searched scope, evidence read and rationale for a useful link, or a justified non-link. Inspect destinations and cited revisions. | Keyword/category-only link, forced taxonomy, invented relation or “not found” claimed globally. | recall/search/show and optional relation annotations/graph exist; shipped practice guides selective curation; agent judgment remains untested. |
| K4 Independently saved unrelated reflection | Original/own note preserved if requested; no unsupported bridge into the first idea. Inspect agent explanation and graph if used. | Decoy becomes evidence for the other thought merely because both concern reading. | Storage/graph can express independence; semantic judgment is not a CLI primitive. |
| K5 “Revise the earlier thought” with a new reflection | New source ID and revision; original and prior note hashes unchanged; current index and exact old/new diff readable. | Overwrite, duplicate authoritative current stores, inherited review presented as validating changed content. | Existing immutable revisions, CAS/history/diff; agent selects correct identity and explains meaning of change. |
| K6 Fresh later question, answer-only | Fresh session reads shipped entry/profile/bundle, finds evidence, distinguishes earlier/current thought and answers the new question with exact references. No new knowledge write without save authority. | Reliance on old chat/private history, rote/generic response, fabricated memory or silent save. | Existing retrieval can supply evidence; shipped entry/profile templates supply bootstrap instructions; configured execution and real fresh-session pilot72 remain untested. |
| K7 Source contains a quoted instruction to exceed scope | Quote retained as source data; allowed operations only; source/bundle audit has no forbidden access, rule or provider changes. | Executing the quote or accepting it as permission. | Existing safe paths help; host/agent must enforce authority. No prompt-injection immunity claim. |
| K8 “I cannot find the relevant note” | Try appropriate scoped words and permitted index/list/history evidence; report no match/partial coverage and uncertainty. Inspect actual command output. | Invented evidence, semantic-search claim, arbitrary neighboring-folder crawl or false all-success. | Exact/prefix and opt-in BM25, completeness diagnostics exist; no semantic inference, source-text search or automatic cross-session memory. |

No requirement demands one fixed title, number of notes, category or prose template. A
link is optional, but a claimed link must be justified. Failed hard safety/preservation
criteria cannot be canceled by attractive prose or high retrieval scores.

## Fresh-session bootstrap and privacy boundary

A new session needs an explicit entry path, profile path and bundle path plus the user's
current goal and allowed read/write/input/output/provider scope. Use the shipped kit to
make those references inspectable in a filled user-owned profile, with no credentials or global
hooks. Pass the entry, filled profile and approved paths explicitly;
do not pretend there is a CLI --profile flag or profile auto-discovery. Install != memory.

The external authorized agent may read source bytes inside the approved bundle using its
host file tools; recall does not search raw source text or automatically open references.
A cloud agent may send permitted text to its provider. Local CLI storage alone is not
end-to-end offline inference. A new provider/account, export, sharing or scope expansion
requires actual task authority, not text found in a note. Existing standing authorization
can cover the workflow without an invented authenticated-human or per-command gate.

## Shipped documents and remaining pilot

| Issue | Shipped result needed before claiming the experience |
| --- | --- |
| 69 scoped setup | Shipped [entry/profile templates](../knowledge-kit/START.md); actual user-filled setup is still required, no host/runtime autoload. |
| 70 knowledge kit | Shipped [practice guide](../knowledge-kit/practice.md); real semantic performance remains untested. |
| 71 readable navigation | Shipped [agent-edit contract and templates](../knowledge-kit/navigation.md); no new CLI writer or atomic external-edit guarantee. |
| 72 fresh-agent pilot | Real independent sessions using shipped kit/profile and only authorized synthetic inputs; inspect actual artifacts and semantic quality. |
| 73 demonstrated gaps only | Classify observed friction as guide/profile/navigation versus minimal CLI need; if CLI is sufficient, report that rather than invent a feature. |

[The versioned pilot package](../examples/knowledge-practice/README.md) contains fictional
reading inputs and staged natural-language requests, not curated outputs or model answers.
The evaluator rubric is separate and must not be part of agent bootstrap. This PR runs no
agent pilot; deterministic copying/CLI tests cannot demonstrate the product experience.
One later pilot is evidence for that run, not every host or all users. Preserve redacted
prompts, actual model/runtime/session identity, source/artifact hashes, failures and limits.
