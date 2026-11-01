# Synthetic recall ranking and scale evaluation

Run from a checkout with its existing project Python environment:

```sh
PYTHONPATH="$PWD/src" python scripts/benchmark_recall.py > /tmp/recall-benchmark.json
```

The script uses no additional dependencies. It creates disposable synthetic bundles,
prints JSON with every judgment, ranking and timing sample, then removes the bundles.
`--profile /tmp/recall-profile.stats` adds a separate untimed cProfile run at the largest
size. `--sizes 10 100 1000 --runs 5` are the defaults. No private notes or generated
corpora are committed. The textual judgments are in
[recall-ranking.json](../tests/fixtures/recall-ranking.json).

## Quality: limited synthetic evidence

Judgments were declared before scoring. These are examples of desired decisions,
not real-user labels. The corpus has 24 current notes, three revisions per note,
and selects r000002 even though r000003 exists. Cases include the four parent EN/KO
focused-versus-repetition examples, body-only focus, relevant and misleading titles,
unequal term distributions, prefixes, history, ties, repeated queries and a miss.
The latter controls also test the retrieval contract; they are not independent user tasks.

On macOS 26.6.2 / Python 3.14.6, the first desired-note ranks were:

| Case | Frequency | BM25 without title hint | BM25-v1 |
| --- | ---: | ---: | ---: |
| EN report decision | 2 | 2 | 1 |
| KO report decision | 2 | 2 | 1 |
| EN archive policy | 2 | 2 | 1 |
| KO archive rule | 2 | 2 | 1 |
| Body-only focus | 2 | 2 | 2 |
| Relevant title vs incidental body | 2 | 2 | 1 |
| Misleading title vs approved body | 1 | 1 | 2 |
| Unequal term distribution EN | 2 | 1 | 1 |
| Unequal term distribution KO | 2 | 1 | 1 |
| Exact-first suppression | 1 | 1 | 1 |
| Explicit EN prefix | 1 | 1 | 1 |
| Explicit KO prefix with unrelated control | 3 | 3 | 2 |
| Indexed earlier revision | 1 | 1 | 1 |
| Equal-score path tie | 1 | 1 | 1 |
| Repeated query terms | 2 | 2 | 1 |

The miss returns no candidates in all variants and is excluded from quality averages.
Over these 15 labeled cases, top-1 is 5/15, 7/15, and 12/15 respectively; mean
reciprocal rank is 0.6556, 0.7222, and 0.9000. Candidate sets match for every variant.
The title hint improves nine ranks, leaves five unchanged, and worsens one compared
with frequency. It does not identify a misleading title or resolve semantic relevance.

BM25-v1 uses k1=1.2 and b=0.75, with one extra IDF unit per distinct query term that
matches a title word. No parameter grid was tuned to these cases. A presence bonus
bounds the extra title influence instead of multiplying every repeated title word.
The no-title ablation shows why the hint was included: saturation alone does not
reverse the four parent repetition examples here. The misleading-title regression
and body-only failure justify keeping the option explicit. These numbers do not
establish general relevance improvement. See the exact formula and corpus rules in
[the reference](reference.md#bounded-current-recall).

## Scale: startup-inclusive wall time and per-child memory

The original study at commit `02dd584` used 10, 100 and 1000 current notes, each with three revisions.
Current bodies vary from 12 to 5000 filler tokens plus the two query words;
current-file bytes total 65,740 / 442,118 / 4,421,162. Short historical bodies also contain
the query. Every sample validates success, indexed/matched counts, current revision,
output budget for recall, and all three revisions for search.

Each method ran once first and five subsequent times as fresh CLI subprocesses.
The method order alternates frequency/BM25/search and its reverse. Times include
interpreter startup through process exit; output parsing/validation is outside the
timed region. Filesystem caches were not controlled: **first is not cold**.
The 10-core machine had background load around 3 when the run began; there was no
CPU isolation. Do not infer small differences from this run.

| Current notes | Method | First ms | Subsequent median ms (min–max) | Peak child RSS range, bytes |
| ---: | --- | ---: | ---: | ---: |
| 10 | frequency recall | 49.54 | 48.41 (47.95–48.69) | 27,099,136–27,508,736 |
| 10 | BM25 recall | 48.26 | 48.40 (47.77–48.68) | 27,262,976–27,557,888 |
| 10 | legacy search | 50.82 | 51.03 (50.42–51.24) | 27,164,672–27,541,504 |
| 100 | frequency recall | 62.88 | 63.44 (63.31–64.40) | 27,738,112–28,065,792 |
| 100 | BM25 recall | 63.54 | 63.47 (63.31–64.29) | 27,967,488–28,065,792 |
| 100 | legacy search | 89.04 | 89.91 (88.02–90.22) | 27,803,648–27,901,952 |
| 1000 | frequency recall | 226.10 | 228.05 (222.54–249.22) | 34,390,016–34,553,856 |
| 1000 | BM25 recall | 229.16 | 226.59 (224.31–245.68) | 34,521,088–34,701,312 |
| 1000 | legacy search | 504.07 | 502.07 (496.08–514.65) | 36,929,536–37,076,992 |

Peak RSS is each child's `wait4().ru_maxrss`, not a cumulative child-process delta.
The script normalizes Darwin bytes and Linux KiB to bytes and emits null on other
platforms. These observations are macOS measurements, not Linux or Windows validation.
The RSS ranges include first and subsequent samples. No rejected or failed sample
is counted as a fast success; this run had zero failures.

Recall returns five results per sample here. Its frequency/BM25 output bytes are
9,011/6,708 at 10 notes, 9,014/4,259 at 100, and 9,017/4,273 at 1000. Different
ranking can select different body lengths. Search retains its separate all-revision,
unbounded-output contract: 30/300/3000 results and 11,523/114,897/1,148,889 output
bytes respectively. It was not changed or bounded by this work.

There is no measured ranking speedup: differences overlap run variation. In a
separate profiled 1000-note BM25 call, read_note consumed 0.290 of 0.369 profiled
seconds, including 0.199 seconds in YAML loading; tokenization and descriptor file
access also contributed. Profiling changes timing and excludes CLI startup, so those
numbers are only evidence of where full-scan work occurs, not comparable latency.
The study supplies no cache necessity threshold. Every recall still reads and parses
current-note bodies; no SQLite, FTS service or persistent cache was introduced.

## Long-query memory correction

Review found that `02dd584` retained a note-by-query-term count matrix, including
for default frequency ranking. A follow-up restores per-note frequency scoring.
BM25 now collects document frequencies in one pass and recomputes each note's
counts while scoring in a second pass. This removes the retained cross-note matrix
without changing BM25-v1 scores, candidate rules, or query limits. It retains the
existing note bodies and token counters; this is not a general RAM or time bound.

The same synthetic memory probe used 3000 distinct query terms and tiny readable
notes. All runs returned zero matches. With 3000 notes, five reviewer trials of
`02dd584` measured peak child RSS of 117,243,904–117,309,440 bytes (median
117,243,904). Five trials after correction measured 30,507,008–30,965,760 bytes
(median 30,638,080). The same rerun's pre-ranking baseline measured
31,522,816–31,997,952 bytes. These are per-child Darwin `wait4` byte measurements
for default frequency, not timing comparisons or universal memory ceilings.

The 10/100/1000-note benchmark was rerun after the correction, with five subsequent
samples per method. Its entire quality and title-ablation result matches the
original, including the misleading-title regression. The original timing table
above remains historical: the follow-up ran alongside local validation, so its
wall times do not support a before/after latency claim. At 1000 notes, subsequent
medians were 245.61 ms frequency, 245.19 ms BM25 and 550.15 ms search. First runs
remain uncontrolled-cache observations. No speedup is claimed. A long-query
allocation regression test covers both modes using Python-traced allocations,
without elapsed-time or host-RSS assertions in CI.
