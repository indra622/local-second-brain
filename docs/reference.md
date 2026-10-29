# Commands and support reference

**English** | [한국어](reference.ko.md)

## Prerequisites

**To read existing knowledge:** a file browser and any UTF-8 text or Markdown editor are enough.
Python, the CLI, an AI account, and Obsidian are not required just to read the files.

**To install and run the CLI:**

- **OS:** a local POSIX filesystem on macOS or Linux. CI-tested on hosted macOS and Ubuntu runners; other Linux environments are not separately validated.
  Windows is not supported because file access uses POSIX-specific APIs. WSL is not tested.
- **Python:** Python 3.11 or newer with the standard `venv` module. CI covers Python 3.11 and 3.14; local validation used Python 3.14.6.
- **Shell:** a terminal with a POSIX shell, such as bash or zsh, for the commands below.
- **Source files:** a local copy of this project, including `pyproject.toml`. Git is optional if you have an archive or copied source.
- **Install dependencies:** `pip` in the virtual environment. It installs PyYAML and build tools automatically.
  Package downloads normally need internet access; CLI operations do not.
- **Storage:** a writable local folder. `init` requires a new or empty target. Keep knowledge outside the code checkout and `.venv`.

Check your Python installation before you start:

```sh
python3 --version
python3 -m venv --help > /dev/null
```

If Python is older than 3.11, select a newer interpreter for `python3` in the commands below.
If `venv` is missing, install your OS distribution's Python venv support first.
No GPU, database, server, API key, Obsidian plugin, or required AI service is needed.
An agent is optional for writing the prepared text; you can write it yourself.

## How it works

1. **Capture:** Copy an explicitly selected source file without changing its bytes.
2. **Prepare:** Read that source and write a Markdown body, yourself or with your chosen agent.
3. **Curate:** Store the prepared body as a new concept revision with source references.
4. **Recall:** Search notes and inspect their current-version, review, and freshness context.
5. **Check:** Report metadata errors, local-link warnings, and stale notes separately.
6. **Review:** Deliberately compare the current body with evidence, then record the declared reviewer and reference.

There is no background learning loop or built-in LLM synthesis.
`curate` stores prepared text; it does not summarize or verify it.

| Command | Purpose |
| --- | --- |
| `init BUNDLE` | Create an index in a new or empty directory. Refuse nonempty targets. |
| `capture BUNDLE FILE --id ID --actor ACTOR --resource ORIGIN` | Preserve source bytes, origin, actor, capture time, and SHA-256. Refuse reused source IDs. |
| `curate BUNDLE ID --body FILE --source SOURCE_ID --actor ACTOR` | Store a prepared UTF-8 body as a new revision. Repeat `--source` for multiple sources. |
| `review BUNDLE ID --revision rNNNNNN --actor ACTOR --evidence RESOURCE` | Append a declared review in a new revision of the current body. |
| `recall BUNDLE QUERY` | Bounded indexed-current context with explicit match diagnostics (JSON). |
| `search BUNDLE QUERY` | Search titles and bodies across all concept revisions. |
| `list BUNDLE` | List all CLI revision summaries, sorted by path. |
| `show BUNDLE ID [--revision rNNNNNN]` | Read the indexed current revision, or an explicit revision. |
| `history BUNDLE ID` | List revision summaries from oldest to newest. |
| `diff BUNDLE ID BEFORE AFTER` | Compare two explicit revisions, including metadata and body. |
| `inspect-storage BUNDLE` | Read-only bounded storage inventory with lock/receipt consistency qualifications. |
| `check BUNDLE` | Check the supported metadata subset and report links and freshness. |

IDs are 1–64 lowercase ASCII letters, digits, or hyphens, starting with a letter or digit.
`curate` also accepts `--type`, `--title`, `--status`, and `--stale-after`.
New `curate` titles, types and actors, and `capture` actors must be single-line strings,
including through the Python functions. LF, CR, CRLF, vertical tab, form feed, file/group/record
separators, NEL, and Unicode line/paragraph separators are rejected as `invalid_input` before
writes or request reservation. Ordinary spaces and Korean/English text are allowed.
This writer policy does not reject multiline fields in imported historical metadata.
Revision serialization double-quotes strings containing NEL to preserve its value;
ordinary Korean and other Unicode text remain readable.

Frontmatter delimiters are exact, unindented `---` lines with LF or CRLF; a closing `---`
at EOF is also accepted. Spaces, lone CR and Unicode line separators do not delimit frontmatter.
Indented separators inside valid YAML scalars remain metadata; body fences remain body text.
Before a revision is created, its UTF-8 serialization is parsed and validated with exact body
and metadata meaning checks. Curate/review prepare these bytes before request reservation;
a failed check creates no revision, index change or pending intent. Existing files are not repaired.

`--actor` is a declared identity, not authentication. Only an explicit `review` adds `verified`; format validation never does.
Relative body links resolve from the final revision file, not the prepared input file.

```text
wiki/
  index.md
  sources/garden-note/
    content.raw
    provenance.json
  concepts/garden/
    r000001.md
    r000002.md
    r000003.md
```

Sources retain their encoding, BOM, and line endings. Even Markdown sources are stored as
`.raw`, separate from concept documents. There is no source-text search, PDF extraction,
or encoding detection. Prepared bodies and concept documents must be UTF-8.

`list`, `show`, `history`, and `diff` are read-only. They use CLI files at
`concepts/ID/r000001.md` through `r999999.md`. Revision arguments must be exactly `rNNNNNN`;
IDs follow the same rules as `curate`. `show` never guesses the current revision from the highest number.
If the current index is unavailable, use `--revision`. Summaries include the current marker, lifecycle,
trust, freshness, and metadata errors. `show` also includes the full body and metadata.
`diff` emits a unified diff of the complete stored Markdown, including metadata, with three context lines;
equal revisions produce an empty JSON `diff` or `No differences.` in text mode.
Imported generic OKF notes remain readable through search/check and a text editor; these commands do not
infer revision history for them. Missing concepts/revisions and unsafe paths return exit `2`.
Malformed note metadata is reported in `metadata_errors` (text mode labels each error); browsing still
returns available content. Invalid UTF-8 is reported with an empty body. Diff refuses invalid notes.
Non-string YAML mapping keys are converted to strings in output only. Stored notes are unchanged.
Mappings with colliding converted keys or cyclic values return a deliberate error instead of losing data.
Read-command operational errors are a JSON `{"error": "..."}` object on stderr in JSON mode, or a
`second-brain:` message in text mode. Argument syntax errors use argparse's text diagnostic.

`review` requires the exact indexed current revision and refuses historical targets under the write lock.
Actors must be `human:ID`, `process:ID`, or `PRODUCER/VERSION`, with nonempty components and no
whitespace, controls, colon, slash or backslash inside a component. These are declarations.
Review defaults to the actual UTC clock. Optional `review --now TIME` instead declares an
explicit-offset ISO8601 event time, validated before locking/reservation and normalized to
UTC isoformat. It does not prove the actual review time. Read-command `--now` keeps its
freshness-evaluation meaning. Equivalent Z/offset instants share a canonical event value.
Evidence must be an absolute HTTP(S) URL with a host (no credentials, invalid ports/escapes or whitespace),
or an existing nonempty regular artifact at a literal bundle-root path, optionally starting with `/`.
Local spaces are allowed, but query/fragment syntax, traversal, backslashes, application directories
and symlinks are refused. Unsupported URL schemes are refused. URLs are never fetched and evidence
is never executed. References are declarations, not proof of truth.

The new event uses standard OKF `by`/`at` and project extensions `x-second-brain-target`
(`resource` and SHA-256 of the complete target file) and `x-second-brain-evidence`
(`resource`, plus SHA-256 for local evidence). Digests identify observed bytes; they do not authenticate
reviewers. The original file stays byte-for-byte intact. The new body and metadata values, including
unknown YAML keys and original generation records, are preserved; new YAML formatting may differ.
Existing mapping/list review events are retained in a list. Status is unchanged, and a later `curate`
does not inherit reviews. See the bilingual [review contract](review-contract.md) for details and failure limits.

## Bounded current recall

`recall BUNDLE QUERY [--match auto|exact|lexical] [--limit N] [--max-chars N] [--now TIME]`
is read-only and JSON-only. It has no `--format` option. Other commands retain their formats.
It reads only CLI revisions selected by the current index, never the highest revision or
historical substitutes. Imported generic notes remain accessible with search/check.

Default `auto` tries exact Unicode `\w+` words after `casefold`, then lexical matching
only if no current exact result exists. `exact` never expands; `lexical` explicitly allows
each query word to match the start of a note word if it has at least three code points,
or at least two characters consisting entirely of precomposed Hangul syllables (`가`..`힣`).
Shorter terms still require equality. Every distinct query word must match the title or body.
Scores sum matching word occurrences per query term; ties sort by path. No stemming,
Unicode normalization, morphology, semantic search or source-text search occurs.
`rename` matches `renames` and `보고서` matches `보고서를` with lexical matching;
`xrename` and `중간보고서` do not match those queries. `port` can match unrelated
`portable`. Two-syllable `규칙`/`결정` match `규칙을`/`결정을`, but also potentially
unrelated `규칙성`/`결정체`; `불규칙한`/`미결정` do not match. One-syllable prefixes
do not expand. Prefix matching is a candidate lookup, not proof of relevance.
Exact-first can omit useful prefix candidates when an exact hit exists; request lexical deliberately.

The default limit is 5 (allowed 1..100). The default budget is 12000 (allowed 2048..1000000).
`--max-chars` bounds the **entire successful stdout**, including JSON syntax, escaping,
diagnostics and final newline, counted as Python Unicode code points, not bytes,
grapheme clusters or tokens. Surrogate code points decoded from YAML escapes are
serialized as JSON `\uXXXX` escapes; Korean and other valid Unicode remain readable.
Each six-character escape counts toward the budget. The command may return fewer results than the limit.
It clips body context, then omits results that cannot fit. `matched` counts all selected-mode
matches before bounds; `omitted_results` counts matches not returned. A result has `id`,
`revision` and `path` for explicit `show`. `body_start`/`body_end` are original body code-point
offsets; `body_chars` is its full length. The initial window starts up to 120 characters before
the first matching body word, at most 1600 characters long, and can shrink under budget.
It need not contain every query term; `body_truncated` indicates omitted body content.

Selected fields include title, lifecycle, trust, freshness/deadline, metadata errors,
generation/review declarations and source references. Nested declarations select only
`id`, `resource`, `last_modified`, `by`, `at`, `sha256` and review target/evidence fields.
Each selected string is limited to 240 characters, lists to 8 items, nesting to 4 levels.
`selected_fields_truncated_or_omitted` reports these reductions. Non-finite YAML floats
become JSON `null` with this flag set; metadata validation errors remain visible. `metadata_omitted` is always
true: full metadata and unknown extensions are intentionally omitted. Use `show` for full evidence.
Clipped references are not usable full paths. Source references are unvalidated declarations;
recall does not resolve, fetch, authenticate or execute them. Keep path access within the
separate task authority, and run `check` for supported link checks. Draft, deprecated,
stale, unverified and invalid metadata notes can match; they are not silently promoted.
Trust comes from stored declarations, not authenticated review. `stale: null` means unknown.

Read `requested_match`, `match_mode` and `fallback_used` before interpreting results.
`state` distinguishes `matches`, `no_match`, `empty_index`, `invalid_index`, `partial`
(matches plus exclusions), `incomplete` (no match plus exclusions), and `budget_omitted`
(matches exist but none fit). Exclusion counts identify unavailable/unsafe revisions,
unsupported revision names and invalid UTF-8. `invalid_metadata_notes` counts inspected
invalid notes even when they did not match. An invalid index never falls back to history.
Diagnostics offer a next action; a miss does not establish absence. States return exit 0;
I/O/argument failures return 2 (operational errors are JSON on stderr; argparse syntax
errors are text). The successful-output budget does not bound stderr, input size, parsing
memory or runtime. Recall does not lock a bundle snapshot; avoid concurrent edits during recall.

## Search and trust signals

Search uses exact Unicode `\w+` tokens after `casefold`. All query words must match.
Scores sum occurrences of distinct query words; ties sort by path. There is no semantic,
substring, or morphological search. Older revisions remain searchable by default; existing JSON keys
and scoring are retained. `snippet` adds the first 160 Unicode characters of the body after whitespace
is collapsed (the final character is `…` when truncated). `title` is also included.

Use `--current-only` to require an indexed current revision; unknown current status is excluded.
`--status draft|stable|deprecated` filters lifecycle status and excludes invalid metadata. An omitted
status on an otherwise valid OKF note means `stable`, as before. `--freshness fresh|stale|unknown`
uses only `stale_after`: fresh means a valid deadline later than `--now`, stale means that deadline
has been reached, and unknown means an absent or invalid deadline, including one without a UTC offset.
Unrelated metadata errors remain visible but do not change freshness. Filters combine with AND and
apply to individual revisions; a matching older revision is never substituted for the current one.
Use `--now` for reproducible evaluation and `--format text` for readable Unicode output.

Each result includes `current`, `status`, `trust`, `stale`, generation and verification records,
and metadata errors. `current: null` means the CLI cannot identify a current-version index.
`stale: null` means no usable expiry date is available. Review tiers interpret stored records;
they do not prove that a reviewer checked the facts or that their identity is authentic.

`check` scans Markdown files outside `.obsidian` and `.git` and recognizes reserved `index.md` and `log.md` files.
Broken links and stale documents are separate from metadata errors:

- Exit `0`: no metadata errors; link warnings or stale notes may still be present.
- Exit `1`: metadata errors.
- Exit `2`: I/O failure, unsafe operation, or invalid arguments.

This is not a complete OKF validator or a factual-verification service.
See the exact [OKF subset](okf-subset.md) and [architecture and recovery limits](architecture.md).
These detailed documents are currently in Korean.

## Agent errors and write requests

All commands accept global `--error-format json` **before the command**. It changes only
failures on stderr, including argparse failures; successful stdout and exits remain the
same. `--error-format=json` also works. If repeated before the command, the last value
(`json` or `legacy`) wins for parser and runtime failures. After-command placement is
unsupported. Default `legacy` preserves existing error shapes/messages and argparse text.
Help remains text. Exit 2 means failure; `check` still emits its report on stdout and
returns 1 for invalid metadata, not a structured error.

Structured stderr is one ASCII-escaped, strict JSON object:

```json
{"error":{"code":"precondition_failed","message":"...","message_truncated":false,"action":"reread_then_new_request"}}
```

Messages are descriptive and limited to 1000 code points; use codes rather than matching
message text. ASCII escaping handles surrogate values; non-finite values in exception
messages are strings. Unexpected runtime exceptions become `internal_error`, without a
traceback, in this mode. Guidance is not a promise that retrying is safe.

| Code | Action |
| --- | --- |
| `arguments` | Correct command syntax. |
| `invalid_input` | Correct IDs, metadata, query, timestamp or other domain input. |
| `invalid_index` | Inspect the unavailable/malformed managed current index. |
| `not_found` | Inspect missing input files or concepts/revisions. |
| `already_exists` | Inspect existing target; do not overwrite it. |
| `unsafe_path` | Inspect rejected path, symlink or nonregular file. |
| `locked` | Wait for the active recognized holder; the persistent marker remains when idle. |
| `precondition_failed` | Re-read current, assess changes, then use a new authorized request. |
| `request_conflict` | Restore original request payload, or assess a separate new operation. |
| `recovery_required` | Stop and inspect receipts and bundle; do not re-execute blindly. |
| `concurrent_change` | Stop and inspect; an external edit may have left an orphan revision. |
| `io_error` | Inspect I/O and possible partial state. |
| `internal_error` | Stop and inspect unexpected failure. |

### Request identity and current-version preconditions

`capture`, `curate` and `review` accept optional `--request-id ID`. IDs use the same
1–64 lowercase ASCII letter/digit/hyphen rules as source IDs and are unique across all
three commands **within one bundle**. Choose/persist a new ID and original payload before
authorized execution. Without a request ID, writes retain their old behavior: an identical
curate body still creates a new revision. Review declarations remain unauthenticated.

`curate --expect-current rNNNNNN` requires that exact indexed revision; `absent` requires
no current index entry for this concept, not absence of historical/orphan files. Omit it
for ordinary unconditional curate. `review --revision` keeps its existing current-version
precondition. Index read, receipt lookup, comparison and mutation occur under one bundle
write lock. The lock refuses contention rather than waiting internally.

A completed request with the same fingerprint returns its original successful result
before testing the now-stale current precondition. It creates no new source, provenance,
revision or review and never rolls the current index back. A later unrelated revision is
allowed. Changing the command or payload with the same ID gives `request_conflict`.
The generated capture/curate/review clock is excluded from identity. Implicit review keeps
the exact previous v1 payload without a time field; only explicit review `--now` adds canonical
`declared_at`. Switching implicit/explicit mode or changing the instant conflicts; equivalent
offset forms replay. Recorded event `at` equals that canonical value. Fingerprints include:

- Capture: source byte SHA-256, original basename (stored provenance), source ID, actor and origin.
- Curate: prepared body byte SHA-256, ordered source IDs plus content/provenance byte hashes,
  concept ID, actor, type, effective title, status, stale-after argument and expected-current argument.
- Review: exact target revision byte hash, concept/revision, actor, supplied evidence argument
  and resolved evidence reference, including local evidence byte hash. URLs are declarations, never fetched.

File paths alone are not identity. Moving a prepared body with identical bytes is allowed;
capture basename changes matter. Preserve the original inputs, source artifacts, review target
and evidence for replay: they are read/validated again to identify the payload. Missing or invalid
inputs can therefore fail before receipt lookup. The managed index must remain readable.
Defaults are canonicalized for title; source order and exact deadline/evidence arguments matter.
Do not change expected-current to the latest revision when replaying an old successful request.
For a new decision, re-read and assess current, then save a new request ID and payload.

### Receipt and failure limits

Create-only records live in reserved root `.lkw-requests/ID/intent.json` and `result.json`.
This root namespace is excluded from normal note enumeration/search/check/browsing;
receipt access still uses descriptor-relative regular-file/no-symlink checks. Do not store
knowledge or use receipts as review evidence. Do not edit or delete receipts to enable retries.
Records contain a version, command/fingerprint, JSON result, result checksum and effect-file
SHA-256 hashes. Replay validates canonical receipt shape/checksum and the exact created
source/provenance or revision bytes. It does not require that revision to remain current.
These are local integrity checks, not authentication or protection against deliberate tampering.

Validation and clean CAS rejection precede intent reservation where possible. A request
directory is reserved before creating/syncing the intent; mutation follows intent sync.
The result record is created only after the mutation returns and its effect files are read.
An existing request directory without intact matching completed records fails closed.
Any failure after reservation conservatively returns `recovery_required`: there may be no
knowledge effect, a source directory alone, content without provenance, a complete captured
source, an orphan revision, or a revision already selected by the index. Result-write failure
can leave a partial record. If final sync fails but a valid result and effect files are still
present, a later replay can prove process-observed success and return it without another write.

Do not infer rollback or retryability from exit 2. An invalid/pending receipt must not be
bypassed with a new ID; stop for manual inspection of the request directory, sources,
revisions, index and lock. No recovery/receipt/lock deletion command is provided. Lock
contention itself reserves no request. Legacy unkeyed failures can also leave partial state.
Receipt JSON has an 8 MB read/write limit; oversized review records are refused early where
possible, but an unexpectedly oversized completion can still leave a pending request.
There is no complete transaction, automatic reconciliation, crash rollback or power-loss
recovery guarantee. Editors do not honor the lock; do not edit concurrently. Input parsing
and hashing remain in memory. External permissions still govern file access and review.

## Storage interruption and read-only inspection

`inspect-storage BUNDLE` returns JSON without creating a lock or modifying any artifact.
It never replays requests, promotes revisions, fetches references or deletes files.
Use global `--error-format json` before the command for structured operational/parser errors.
A useful inventory returns exit 0 even with diagnostics; an inaccessible bundle is an error.

New writers use a permanent regular `.lkw.lock` containing exactly `lkw:flock:v1` plus LF.
Native exclusive nonblocking `flock` serializes cooperating writers on supported local
macOS/Linux filesystems. The marker's presence is normal: exit closes the descriptor,
not the pathname. Its bytes/inode are never rewritten, truncated or unlinked after
initialization. Killing the sole initialized holder releases its kernel lock; this does
not prove that pending receipts or bundle artifacts are complete. Busy recognized locks
return `locked`. Empty, partial, legacy or unknown markers return `recovery_required`
without conversion, even if their advisory lock is available. Unsafe/nonregular,
hard-linked or substituted lock paths are refused. Unsupported locking never falls
back to an unprotected write. Initial marker creation can fail and need inspection.

This is a writer-format upgrade, not mixed-version interoperability. The permanent
marker intentionally blocks old O_EXCL writers, including when idle. Before an offline
operator considers retiring a legacy sentinel, stop all old writers and inspect partial
state. There is no migration/removal command; never blindly delete either marker to
retry or downgrade. Do not fork while holding a Store lock: close-on-exec does not stop
fork/dup inheritance, and another inherited descriptor may keep the lock after a death.
Only local cooperative locking is supported; editors and hostile filesystem changes
are outside this guarantee. `init` refuses nonempty targets before installing a lock.

Revision writes now create a unique `.lkw-index.<32 lowercase hex>.tmp` before creating
the revision. Ten exclusive-name attempts bound collisions. Existing fixed
`.lkw-index.tmp` and other random artifacts are preserved. The owned stage is written
and synced, then the revision is created/synced. Before one-index rename, original index
bytes and stage inode/bytes are checked. The root directory is synced after rename.
Cleanup removes only the invocation's still-present owned staging inode, never a revision.
A failure after actual rename may mean the new revision is already current. Keyed staging
starts after request intent, so an interrupted stage remains conservative
`recovery_required`, even if no revision was created. A killed process may leave a temp.
No multi-file atomicity, rollback or power-loss recovery is promised; index directory sync
does not durably order every source/revision/receipt directory. Identity checks do not
provide atomic conditional unlink against hostile concurrent entry replacement.

Inspection takes a shared nonblocking lock on an existing recognized marker when possible.
`consistency: shared_lock_held` excludes cooperating writers during the inventory;
`best_effort` with absent/legacy/busy/unavailable lock does not establish a snapshot.
A busy writer can legitimately have a pending receipt. Diagnostics retain useful partial
results for unsafe or inaccessible entries and never follow symlinks/receipt URLs.
`scan.complete: false` qualifies counts as observed partial totals, not complete totals.

The report exposes `receipts.namespace`: absent, directory, invalid, unavailable, or unchecked.
A non-directory reserved root has its actual type and a diagnostic; unavailable receipt totals
are `null`, not a healthy zero. Useful inventory continues without following that entry.
The report contains managed-index validity and missing/unavailable current targets,
current versus non-current CLI revision counts, staging type/size and unknown ownership,
lock state, and receipt states: `self_consistent`, `pending`, `incomplete`, `corrupt`, or
`effects_unchecked`. Non-current includes ordinary history. Completion evidence can
identify a previously completed operation; an unclassified file is not a proven orphan.
A self-consistent receipt has canonical v1 schema/checksum and matching permitted effect
bytes; without original payloads inspection does not certify replay eligibility.
Intent v1 has no planned revision path, so pending requests cannot be reliably assigned
to individual non-current files. Strict result/effect grammars precede artifact reads.

Inspection bounds: 100 details per section, 240 code points per text field (with a
truncation flag), 10000 visited entries, 16 directory levels, 100 receipts checked,
8 MB per receipt/index read (size checked before allocation), 64 MB per effect hash
and 128 MB total hashing. Receipts above the check cap remain unchecked. Oversized effects
produce `effects_unchecked`; the report does not treat that as verified consistency.
Details have omission counters; index targets beyond 10000 have a separate unchecked count.
These are inspection limits, not new input limits on ordinary commands. A filename pattern
never proves temp ownership or permission to remove it. Stop and inspect ambiguous state;
there is no automatic recovery, lock deletion, receipt finalization or orphan cleanup.

## Explicit directory aliases and internal links

The directory root explicitly supplied by the caller is resolved once before opening its
descriptor. Bundle aliases and source/body parent-directory aliases, including macOS `/tmp`,
are supported. The final resolved directory still opens with `O_DIRECTORY | O_NOFOLLOW`;
subsequent bundle paths remain descriptor-relative and no-follow. No `~` expansion or
allowed-root policy is added. Loops, missing targets and non-directories fail with the
existing structured error interface, including loop handling on Python 3.11/3.12.
This resolution is not protection against hostile concurrent root or ancestor changes.

Only the explicit directory is resolved. A final source/body file symlink is refused;
original supplied basenames, source bytes and request fingerprints are preserved.
Internal concept/source/evidence/receipt/staging/lock links are not resolved or followed.
Full list/search/check/write scans still reject arbitrary internal symlinks rather than
silently hiding them. Indexed recall retains its narrower behavior: unrelated links do
not add a scan, and an indexed linked revision is excluded rather than followed.
Use `inspect-storage` for a qualified useful inventory of an unsafe bundle.

Aliases share the same target index, receipts and permanent lock inode. Replay-before-CAS
and expected-current checks are unchanged. `init` can initialize an existing empty directory
through an explicit alias; it refuses a nonempty target without changing it. Directory
aliases are a caller-selected location, not permission to follow references from notes.

## Agent and storage limits

Start with the [portable agent guide and task template](agent-kit.md), then give your
chosen agent the [English workflow](../workflows/AGENT-WORKFLOW.md) and
[body template](../templates/concept-body.md). Each has a Korean counterpart.
The older [synthetic bundle](../examples/bundle/index.md) remains in Korean.
Keep instructions and templates outside the knowledge bundle.

CLI writes use an exclusive lock and refuse to overwrite existing sources or revisions.
Only the marked current-version block in the root index is managed; surrounding human text stays intact.
Editors do not honor this lock. Do not edit concurrently with a write command.
Crash leftovers are preserved for manual inspection, not automatically deleted or repaired.

There is no web UI, daemon, vector database, cloud backend, MCP server, computation execution,
or attestation in this version.
No PyPI package release is available. Install from the source checkout.

## File interface

The internal Python module remains `local_knowledge_wiki`; existing bundles need no migration.
