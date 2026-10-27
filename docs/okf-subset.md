# OKF 참고 기준과 검사 범위

공식 기준은 [GoogleCloudPlatform/open-knowledge-format의 SPEC.md](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md)다.
조회 시각은 `2026-10-27T07:41:18.259947+00:00`이며, GitHub API로 확인한 SPEC.md의
마지막 변경 커밋은 `0b87c52c6ef999286c745e19998fdfcd03d5dbee`다.
[고정 명세](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/0b87c52c6ef999286c745e19998fdfcd03d5dbee/SPEC.md)는 OKF 0.2를 설명한다.
이 프로젝트는 아래의 일부만 구현한다. `check` 통과는 전체 OKF 준수나 사실 확인을 뜻하지 않는다.

## 메타데이터 오류로 보고하는 항목

- 예약 파일을 제외한 모든 `.md`는 UTF-8, 시작과 끝이 `---`인 YAML frontmatter,
  매핑 형식의 메타데이터, 비어 있지 않은 문자열 `type`을 가져야 한다.
- YAML은 PyYAML SafeLoader로 읽는다. 중복 키와 해시할 수 없는 매핑 키는 거부한다.
  알 수 없는 필드와 `type` 값은 허용하고 그 값의 의미를 검사하지 않는다.
- `title`, `description`, `resource`가 있으면 비어 있지 않은 문자열이어야 한다.
  `tags`가 있으면 비어 있지 않은 문자열의 목록이어야 한다.
- `sources`가 있으면 매핑의 목록이어야 한다. 각 항목에는 비어 있지 않은 `resource`가 필요하다.
  범위 설명 문자열도 허용한다. `last_modified`가 있으면 아래 시간 규칙을 적용한다.
- `generated`가 있으면 매핑과 비어 있지 않은 `by`가 필요하다. `at`는 선택 사항이다.
- `verified`는 매핑 하나 또는 매핑의 목록이다. 각 항목에는 비어 있지 않은 `by`와 `at`가 필요하다.
  CLI는 이 필드를 생성하지 않는다. 빈 목록은 검토 기록이 없는 것으로 취급한다.
- `status`가 있으면 `draft`, `stable`, `deprecated` 중 하나다. 없으면 `stable`로 읽는다.
- `generated.at`, `verified.at`, `sources[].last_modified`, `stale_after`,
  `usage_window.from`, `usage_window.to`가 있으면 명시적 UTC 오프셋이 필요하다.
  지원 표기는 `YYYY-MM-DDTHH:MM:SS[.fraction]Z` 또는 `+09:00` 같은 오프셋이다.
  Python `datetime`이 처리하는 달력 범위 안에서 검사한다. 날짜만 있거나 오프셋이 없으면 오류다.
  `usage_window`는 매핑이어야 하지만 시작과 끝의 순서는 검사하지 않는다.
- 하위 `index.md`와 모든 `log.md`의 frontmatter를 거부한다. 루트 `index.md`는
  frontmatter가 없어도 되고 `okf_version: '0.2'`를 선언해도 된다. 알 수 없는 버전은 경고한다.

`index.md`, `log.md`는 개념 문서 수에 포함하지 않는다. 인덱스의 제목과 목록 구조,
로그 날짜 형식과 순서, 계산 개념의 `runtime`, `parameters`, `executor`, `attester`,
출처 신뢰도 필드의 모든 세부 타입, actor 표기 규칙은 검사하지 않는다.
`generated.by`가 `human:`이어도 `verified`가 없으면 `unverified`다.
`verified`가 있으면 `human:` 접두사에 따라 `human-reviewed` 또는 `machine-confirmed`로 표시한다.
메타데이터 오류가 있으면 `invalid-metadata`로 표시한다. 이는 기록의 해석이며 실제 검토의 증명이 아니다.

## 링크 경고와 오래됨

본문의 단순한 `[label](path)` 링크와 이미지 경로를 찾는다. 백틱이나 물결표로 된
fenced code block은 건너뛴다. 공백이나 괄호를 포함한 대상, 링크 제목, reference-style
링크, HTML, inline code 구분, 모든 Markdown 문법은 지원하지 않는다.
footnote 정의 안의 단순한 inline 링크는 검사하지만 footnote ID 대응은 검사하지 않는다.

URL은 접속하지 않는다. 로컬 상대 경로는 해당 문서 위치 기준이며 `/`로 시작하는
경로는 번들 루트 기준이다. URL escape를 한 번 해제하고 경로를 정규화한다.
파일이나 파일을 포함한 디렉터리가 존재하는지만 확인하며 fragment anchor는 검사하지 않는다.
번들 밖을 가리키거나 대상이 없으면 `warnings`에 기록한다. 밖의 파일은 열지 않는다.
`sources[].resource`는 `./`, `../`, `/`로 시작할 때만 같은 방식으로 검사한다.
다른 문자열은 URL이나 범위 설명일 수 있어 존재 여부를 추정하지 않는다.
출처 JSON의 해시 재검증은 하지 않는다.

`stale_after`가 유효하고 평가 시각이 그 순간 이상이면 `stale`에 경로를 추가한다.
`search`와 `check`의 `--now`로 경계 시각을 재현할 수 있다.
링크 경고와 오래됨은 OKF 구문 오류로 처리하지 않는다.

완전한 Markdown 파싱, 계산 attestation, 원문의 사실 확인, LLM 호출, 원격 링크 점검은 하지 않는다.
입출력이나 안전 검사에서 실패하면 검사는 중단되고 종료 코드 2를 반환한다.
