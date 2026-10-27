# Review contract

`second-brain review BUNDLE ID --revision rNNNNNN --actor ACTOR --evidence RESOURCE`
records a declared content review. JSON output contains `revision` and the resulting `verified` list. All three options are required. It does not check
facts, authenticate the actor, or sign a document. `check` validates the documented
format subset; reading, capturing, curating, and checking never add review events.

The command requires the exact indexed current revision. Under the existing exclusive
write lock it validates the managed index, target path, metadata, and evidence before
creating a new revision. Historical or missing targets are refused. Revision allocation
uses the largest existing number, including unindexed revisions; it does not guess the
current target from that number. The original target bytes remain unchanged.

The new revision has the identical UTF-8 body and preserves all existing metadata values,
including unknown fields, `generated.by`, `generated.at`, status and freshness deadlines.
YAML formatting and comments can change in the new file. A mapping-form `verified` becomes
a one-element list; a list retains its entries. A new event is appended. A later normal
`curate` creates fresh metadata without any inherited verification, even if its body is
identical. Review never promotes a draft to stable.

Each new `verified` event contains standard OKF `by` and `at`, plus these local extensions:

- `x-second-brain-target`: `{resource: /concepts/ID/rNNNNNN.md, sha256: HEX}` binds the event to
  the complete original revision bytes (frontmatter and body).
- `x-second-brain-evidence`: `{resource: RESOURCE}` records an absolute HTTP(S) URL without
  accessing it. For a local artifact it records `{resource: /bundle/path, sha256: HEX}`,
  with a digest of the observed file bytes. Local references start at the bundle root,
  with an optional leading `/`; they are not relative to the new note or shell directory.

`at` is the offset-aware UTC time observed by the local CLI while recording the event.
There is no historical timestamp input. Actors must be `human:ID`, `process:ID`, or
`PRODUCER/VERSION`; components are nonempty and contain no whitespace, control characters,
colon, slash or backslash. This input convention does not authenticate identity.
`human-reviewed` and `machine-confirmed` remain advisory labels derived from the declared
`verified.by` values, not proof that anyone performed a check.

Evidence must be a syntactically valid absolute HTTP(S) URL with a host, or an existing nonempty
bundle-local regular file. Empty strings, unsupported schemes, URL credentials, invalid
ports/escapes, whitespace/control characters in URLs, local query/fragment syntax,
backslashes, traversal components and symlinks are refused. Local files may contain spaces;
paths are literal, not percent-decoded. Application directories `.git` and `.obsidian`
are not evidence stores. URLs are never fetched; evidence is never executed. Evidence
references are declarations, not proof of truth. Digests identify observed bytes and are
not cryptographic authentication. Evidence can later change or disappear.

Concurrent CLI writers are serialized. The target and index are rechecked before the new
file is created, and the existing index replacement checks still apply. Noncooperating
editors must not run concurrently. An I/O failure or concurrent index change after file
creation can leave an unindexed revision, as with `curate`; there is no crash transaction
or automatic recovery. Validation failures leave no revision or index changes.

These choices follow [OKF 0.2 §§4.1, 5.2, 5.3 and 7](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md),
checked on 2026-10-28: preserve unknown fields, accept mapping/list review events, and
separate generated and verified records. The `x-second-brain-*` fields are project extensions.

## 검토 규칙

`second-brain review BUNDLE ID --revision rNNNNNN --actor ACTOR --evidence RESOURCE`는
내용을 검토했다는 선언을 기록한다. JSON 출력에는 `revision`과 최종 `verified` 목록이 들어 있다. 세 옵션은 모두 필수다. 사실 확인, 신원 인증이나
전자서명을 하지 않는다. `check`는 문서화한 형식 일부를 검사할 뿐이며, 열람·수집·정리·검사는
검토 기록을 자동으로 만들지 않는다.

기존 배타 잠금 안에서 인덱스와 정확히 일치하는 현재 리비전, 메타데이터와 근거를 검사한다.
과거 리비전이나 없는 대상은 거부한다. 새 번호는 미연결 파일을 포함한 기존 최대 번호 다음이다.
최대 번호로 현재 대상을 추정하지 않는다. 원본 바이트는 그대로 두고 새 리비전을 만든다.
새 파일은 UTF-8 본문과 기존 메타데이터 값을 보존한다. 알 수 없는 필드, 원래 생성 주체와 시각,
상태와 유효 기한도 유지한다. 새 파일의 YAML 서식과 주석은 바뀔 수 있다.
기존 `verified` 매핑은 목록으로 바꾸고, 기존 목록은 항목을 유지한 뒤 새 이벤트를 덧붙인다.
`draft`를 `stable`로 올리지 않는다. 이후 일반 `curate`는 본문이 같아도 검토 기록을 물려받지 않는다.

새 이벤트의 표준 필드는 `by`와 `at`다. 프로젝트 확장 `x-second-brain-target`에는 원본 리비전의
번들 기준 `/concepts/ID/rNNNNNN.md` 경로인 `resource`와 전체 바이트의 `sha256`을 넣는다.
`x-second-brain-evidence`에는 URL인 `resource`, 또는 로컬 파일의 번들 기준 `/경로`와 관측한 바이트의
`sha256`을 넣는다. 로컬 경로는 번들 루트 기준이며 앞의 `/`는 생략할 수 있다.
`at`는 기록 시 CLI가 관측한 UTC 오프셋 포함 시각이다. 과거 시각을 입력하는 옵션은 없다.

actor는 `human:ID`, `process:ID`, `PRODUCER/VERSION` 중 하나다. 각 구성요소는 비어 있지 않아야 하며
공백, 제어 문자, 콜론, 슬래시나 역슬래시를 포함할 수 없다. 이 규칙은 신원을 인증하지 않는다.
`human-reviewed`와 `machine-confirmed`는 선언한 `verified.by`로 계산한 참고 표시다.

근거는 호스트가 있는 절대 HTTP(S) URL 또는 번들 안에 실제로 있는 비어 있지 않은 일반 파일이어야 한다.
빈 값, 다른 URL scheme, URL 자격 증명, 잘못된 포트·escape, URL 공백·제어 문자,
로컬 query·fragment, 역슬래시, 경로 순회 요소와 심볼릭 링크는 거부한다.
로컬 파일명에는 공백을 허용하며 percent decoding은 하지 않는다. `.git`과 `.obsidian`은
근거 저장 위치로 쓰지 않는다. URL에 접속하거나 근거를 실행하지 않는다.
근거 참조는 선언이며 진실의 증거가 아니다. 해시는 관측한 바이트를 식별하며 신원 인증이 아니다.
근거는 나중에 바뀌거나 없어질 수 있다.

새 파일 생성 전에 대상과 인덱스를 다시 확인하며 기존 인덱스 교체 검사도 적용한다.
잠금을 따르지 않는 편집기를 동시에 실행하지 않는다. 생성 뒤 I/O 오류나 인덱스 변경이 있으면
`curate`처럼 미연결 리비전이 남을 수 있다. crash transaction이나 자동 복구는 없다.
검증 실패 시 리비전이나 인덱스를 바꾸지 않는다. 위 OKF 0.2 절을 2026-10-28에 확인했으며
`x-second-brain-*`는 표준 필드가 아닌 프로젝트 확장이다.
