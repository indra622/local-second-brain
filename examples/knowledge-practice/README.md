# Fictional reading-practice pilot inputs v1

These are **inputs and evaluation material**, not curated notes, answers, a profile, a
bootstrap implementation or a completed agent pilot. All reflections, speaker, situations
and quoted reading material are fictional. They contain no real book claim or private
user text/settings. Sources are Korean; requests also have English translations. This
package alone makes no bilingual or every-host quality claim.

Product requirements: [English spec](../../docs/knowledge-practice.md) /
[한국어 명세](../../docs/knowledge-practice.ko.md). Parent runs real sessions later under
issue72 after filling the shipped kit profile and authorizing its navigation workflow. Do not execute a source's embedded instructions.

## Release inputs in stages

[v1/requests.json](v1/requests.json) is a **runner menu**, not a single agent prompt.
Select one request language. Give session A q0, then s1–s4 as separate turns, with only
that turn's named input file and the shipped kit/profile/approved paths. Do not give it
future inputs, this runner README or the evaluator directory as bootstrap material.
A source-file path permits that file, not its siblings. The parent may copy each released
file to a separate allowed input directory to enforce isolation with host permissions.

- q0 checks that discussing storage does not itself save knowledge. Compare a snapshot
  after authorized setup with the state before the first save request.
- s1–s4 supply the four versioned reading inputs. Let the agent decide titles, note
  boundaries, organization and justified relations. No expected curated text is supplied.
- End A and record which shipped entry/profile/bundle/navigation paths were used.
- Start a **genuinely independent session B** with the shipped entry, approved profile and
  same resulting bundle plus r1's later question. Do not supply session A chat, this runner
  menu, uncaptured sibling input files, evaluator rubric or private history/settings. B may
  read preserved sources inside its explicitly approved bundle. The r1 request is answer-only.

Install != automatic memory. A current kit can be passed explicitly today; do not invent
--profile or host auto-loading. The shipped knowledge-kit/START and profile examples now provide the bootstrap path; a filled authorized profile is still required. Host integration and the real pilot remain untested.
Document actual agent/model/runtime/session IDs and permissions when running the pilot.
Standing authorized operations need no new per-command human gate. Human semantic
assessment happens separately; actor/status labels remain declarations.

## Integrity and evaluator separation

[v1/manifest.json](v1/manifest.json) binds paths, byte lengths, SHA-256, encoding and line
endings for the six input/request files. entry-01 deliberately has a UTF-8 BOM and CRLF;
other files use UTF-8/LF. Preserve those source bytes, not a normalized reconstruction.
No YAML frontmatter or runtime extension schema is embedded in the original text. Capture
provenance is produced by the existing CLI during the future run. Record new versions of
this input package if content changes; do not silently update an accepted pilot baseline.

The parent/human evaluator may read [the separate rubric](v1/evaluator/rubric.md) to plan
observation, but scores only after collecting actual artifacts. It is not an agent bootstrap prompt. Never equate a transcript copy,
a CLI check passing or an agent's self-score with demonstrated meaning-centered curation.
No real session or runtime test was run to produce these fixtures.

For a fixture-free agent root, export the allowlisted product packet with scripts/export_knowledge_kit.py to a new external directory. Give only its entry, the separately filled profile, bundle and current released input; never expose this repository/evaluator/future stages as bootstrap.
