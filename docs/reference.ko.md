# 명령과 지원 범위

[English](reference.md) | **한국어**

## 설치 전 준비 사항

**기존 지식을 읽기만 할 때:** 파일 탐색기와 UTF-8 텍스트 또는 Markdown 편집기면 된다.
파일 열람에는 Python, CLI, AI 계정이나 Obsidian이 필요 없다.

**CLI를 설치하고 실행할 때:**

- **운영체제:** macOS 또는 Linux의 로컬 POSIX 파일시스템. 호스팅된 macOS와 Ubuntu에서 CI를 통과했으며 다른 Linux 환경은 별도로 검증하지 않았다.
  Windows는 POSIX 전용 파일 API 때문에 지원하지 않는다. WSL도 미검증이다.
- **Python:** 표준 `venv` 모듈을 사용할 수 있는 Python 3.11 이상. CI는 Python 3.11과 3.14를 검사하며 로컬 검증은 3.14.6에서 했다.
- **터미널:** 아래 예제를 실행할 bash, zsh 같은 POSIX 셸.
- **프로젝트 소스:** `pyproject.toml`이 포함된 로컬 프로젝트. 압축파일이나 복사본이 있으면 Git은 필수가 아니다.
- **설치 도구와 의존성:** 가상환경 안의 `pip`가 PyYAML과 빌드 도구를 설치한다.
  설치 시 패키지 다운로드에는 보통 인터넷이 필요하지만, CLI 동작에는 필요 없다.
- **저장 공간:** 쓰기 가능한 로컬 폴더. `init`에는 새 경로나 빈 폴더를 지정한다.
  지식 폴더는 프로젝트 코드나 `.venv` 밖에 따로 두는 것이 좋다.

먼저 Python을 확인한다.

```sh
python3 --version
python3 -m venv --help > /dev/null
```

버전이 3.11보다 낮으면 아래 명령의 `python3`를 새 Python 실행 경로로 바꾼다.
`venv`가 없으면 운영체제의 Python venv 지원 패키지를 먼저 설치한다.
GPU, DB, 서버, API 키, Obsidian 플러그인이나 특정 AI 서비스는 필요 없다.
본문은 직접 써도 되고, 원하는 에이전트로 정리해도 된다.

## 명령과 파일

| 명령 | 동작 |
| --- | --- |
| `init BUNDLE` | 새 경로나 빈 디렉터리에 `index.md`를 만든다. 비어 있지 않으면 거부한다. |
| `capture BUNDLE FILE --id ID --actor ACTOR --resource ORIGIN` | 원문 바이트와 출처, 수집 주체, 시간, SHA-256을 보존한다. ID 재사용을 거부한다. |
| `curate BUNDLE ID --body FILE --source SOURCE_ID --actor ACTOR` | 준비한 UTF-8 본문을 새 개념 리비전으로 저장한다. `--source`는 반복할 수 있다. |
| `review BUNDLE ID --revision rNNNNNN --actor ACTOR --evidence RESOURCE` | 현재 본문을 유지한 새 리비전에 검토 선언을 덧붙인다. |
| `search BUNDLE QUERY` | 모든 개념 리비전의 제목과 본문을 단어로 검색한다. |
| `list BUNDLE` | 모든 CLI 리비전 요약을 경로순으로 표시한다. |
| `show BUNDLE ID [--revision rNNNNNN]` | 현재 리비전 또는 지정한 리비전의 본문을 읽는다. |
| `history BUNDLE ID` | 리비전 요약을 오래된 순서로 표시한다. |
| `diff BUNDLE ID BEFORE AFTER` | 두 리비전의 메타데이터와 본문을 비교한다. |
| `check BUNDLE` | 메타데이터 일부를 검사하고 링크 경고와 오래된 문서를 별도로 보고한다. |

ID는 영문 소문자나 숫자로 시작하는 1~64자의 영문 소문자, 숫자, 하이픈이다.
`curate`는 `--type`, `--title`, `--status`, `--stale-after`도 받는다.
`curate`는 원문을 직접 해석하거나 준비한 글의 사실을 확인하지 않는다.
명시적 `review`만 `verified`를 덧붙이며 형식 검사는 검토 기록을 만들지 않는다.
본문의 상대 링크는 준비 파일 위치가 아닌 최종 리비전 위치를 기준으로 쓴다.

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

원문은 확장자나 인코딩에 관계없이 바이트 그대로 저장한다. 줄바꿈과 BOM도 바꾸지 않는다.
원문 Markdown도 `.raw`로 보존하므로 개념 문서로 잘못 검사하지 않는다.
원문 검색, PDF 추출, 인코딩 추측은 없다. 본문과 개념 문서는 UTF-8이어야 한다.
다른 인코딩은 에이전트가 별도 작업 파일에서 변환하고 원문과 구분해야 한다.

`list`, `show`, `history`, `diff`는 파일을 바꾸지 않는 열람 명령이다.
`concepts/ID/r000001.md`부터 `r999999.md`까지의 CLI 파일을 대상으로 한다.
리비전 인자는 정확히 `rNNNNNN` 형식이며 ID 규칙은 `curate`와 같다.
`show`는 가장 큰 번호를 현재 버전으로 추측하지 않는다. 현재 인덱스가 없으면 `--revision`을 지정한다.
요약에는 현재 표시, 상태, 검토 수준, 신선도와 메타데이터 오류가 들어간다. `show`는 전체 본문과 메타데이터도 보여 준다.
`diff`는 메타데이터를 포함한 전체 Markdown의 unified diff를 앞뒤 세 줄과 함께 출력한다.
동일한 리비전이면 JSON의 `diff`는 빈 문자열이고 텍스트는 `No differences.`다.
가져온 일반 OKF 노트는 검색, 검사와 편집기로 읽을 수 있지만 이 명령들이 리비전 이력을 추론하지는 않는다.
없는 개념이나 리비전, 안전하지 않은 경로는 종료 코드 `2`다.
잘못된 메타데이터는 `metadata_errors` 또는 텍스트의 오류 표시로 알리고 읽을 수 있는 내용은 반환한다.
UTF-8이 아니면 오류와 빈 본문을 반환한다. `diff`는 잘못된 노트를 거부한다.
YAML 매핑의 문자열이 아닌 키는 출력할 때만 문자열로 바꾸며 저장된 노트는 바꾸지 않는다.
변환한 키가 충돌하거나 값이 순환하면 데이터를 버리지 않고 명시적 오류를 반환한다.
읽기 명령의 실행 오류는 JSON 모드에서 stderr의 `{"error": "..."}`, 텍스트 모드에서
`second-brain:` 메시지로 출력한다. 인자 문법 오류는 argparse의 텍스트 진단을 사용한다.

`review`는 잠금 안에서 인덱스가 가리키는 정확한 현재 리비전만 받으며 과거 대상은 거부한다.
actor는 `human:ID`, `process:ID`, `PRODUCER/VERSION` 중 하나다. 구성요소는 비어 있지 않아야 하며
공백, 제어 문자, 콜론, 슬래시나 역슬래시를 포함할 수 없다. 이는 신원 인증이 아닌 선언이다.
기록 시 CLI가 관측한 UTC 오프셋 포함 시각을 사용하며 과거 검토 시각은 입력할 수 없다.
근거는 호스트가 있는 절대 HTTP(S) URL 또는 번들 루트 기준으로 실제 존재하는 비어 있지 않은
일반 파일이다. 로컬 경로의 앞 `/`는 생략할 수 있고 파일명 공백은 허용한다.
URL 자격 증명, 잘못된 포트, escape, 공백, 다른 scheme, 로컬 query 또는 fragment, 경로 순회,
역슬래시, 앱 디렉터리와 심볼릭 링크는 거부한다. URL에 접속하거나 근거를 실행하지 않는다.
근거 참조는 선언이며 진실의 증거가 아니다.

새 이벤트는 표준 OKF `by`/`at`와 프로젝트 확장 `x-second-brain-target` 및
`x-second-brain-evidence`를 사용한다. 대상에는 `resource`와 전체 파일 바이트의 SHA-256,
근거에는 `resource`와 로컬 파일일 때만 SHA-256을 기록한다. 해시는 바이트를 식별하며 신원을
인증하지 않는다. 원본 파일 바이트는 유지한다. 새 파일의 본문, 알 수 없는 YAML 키와 원래
생성 기록을 포함한 메타데이터 값도 유지하되 YAML 서식은 달라질 수 있다.
기존 검토 매핑이나 목록은 항목을 보존한 목록이 된다. 상태는 바꾸지 않으며 이후 `curate`는
검토 기록을 물려받지 않는다. 상세 규칙과 실패 한계는 한영 [검토 규칙](review-contract.md)을 참고한다.

검색은 Unicode `\w+` 토큰을 `casefold`한 뒤 모든 검색어가 정확히 있는 문서를 찾는다.
점수는 중복을 제거한 검색어의 출현 횟수 합이며, 점수 내림차순과 경로 오름차순으로 정렬한다.
형태소 분석, 부분 문자열 검색, 의미 검색은 없다. 기본 검색은 이전 리비전도 포함하며 기존 JSON 키와 점수를 유지한다.
`title`과 `snippet`이 추가된다. `snippet`은 본문 공백을 한 칸으로 합친 뒤 앞에서 최대 160 Unicode 문자를
보여 준다. 잘린 경우 마지막 문자는 `…`다.

`--current-only`는 인덱스가 가리키는 현재 리비전만 남기며, 현재 여부를 모르면 제외한다.
`--status draft|stable|deprecated`는 상태로 필터링하고 메타데이터 오류가 있는 문서는 제외한다.
유효한 OKF 노트에서 상태가 생략되면 기존처럼 `stable`이다.
`--freshness fresh|stale|unknown`은 `stale_after`만 사용한다. 유효한 기한이 `--now`보다 뒤면 fresh,
기한에 도달했으면 stale이다. 기한이 없거나 잘못되었거나 UTC 오프셋이 없으면 unknown이다.
다른 메타데이터 오류는 그대로 표시하되 신선도를 바꾸지 않는다. 필터는 AND로 결합하며 리비전마다 적용한다.
이전 리비전이 조건에 맞아도 현재 리비전을 대신하지 않는다.
재현 가능한 시간 판정에는 `--now`, 읽기 쉬운 Unicode 출력에는 `--format text`를 쓴다.
`current`는 이 CLI의 현재 링크 여부이며, 가져온 일반 번들에서 판단할 수 없으면 `null`이다.
`status`, `trust`, `stale`, 생성과 검토 기록, 메타데이터 오류를 함께 출력한다.
`stale: null`은 기한이 없거나 잘못되어 판단할 수 없다는 뜻이다. 검토 수준은 기록에서
계산한 참고 정보다. CLI가 사실이나 검토자의 신원을 확인했다는 뜻이 아니다.

검사는 `.obsidian`과 `.git`을 제외한 번들 안의 `.md`를 읽는다. `index.md`와 `log.md`는 예약 파일로 구분한다.
깨진 링크와 오래된 문서는 형식 오류와 별도이며, 이것만 있으면 종료 코드는 0이다.
메타데이터 오류가 있으면 1, 입출력 실패나 안전상 거부, 잘못된 인자는 2다.
정확한 검사 범위와 생략한 항목은 [검사 범위](okf-subset.md)에 적었다.

## 에이전트와 저장 한계

[에이전트 사용 안내와 작업 템플릿](agent-kit.ko.md)부터 읽고
[한국어 작업 절차](../workflows/AGENT-WORKFLOW.ko.md)와
[본문 템플릿](../templates/concept-body.ko.md)을 에이전트에 전달한다. 각각 영어 문서도 있다.
기존 [합성 예제 번들](../examples/bundle/index.md)은 한국어다.
지침과 템플릿은 번들 밖에 둔다. 특정 vault 구조나 에이전트 설정을 가정하지 않는다.

쓰기 명령은 번들의 배타 잠금을 사용하며 파일 생성 시 기존 파일을 덮어쓰지 않는다.
`index.md`의 관리 표식 사이에는 생성된 현재 링크만 둔다. 그 밖에 쓴 글은 보존한다.
관리 구역의 구조를 바꾸면 `curate`는 거부한다. 파일을 직접 편집하는 프로그램은 잠금을
따르지 않으므로 쓰기 명령과 동시에 편집하지 않는다. 장애 후 남은 잠금이나 미연결
리비전은 자동 삭제하지 않는다. [구조와 복구 범위](architecture.md)를 먼저 확인한다.

웹 UI, 서버, 벡터 DB, 클라우드, MCP, 계산 실행과 attestation은 이번 범위에 없다.
PyPI 배포는 아직 없으므로 프로젝트 소스로 설치한다.

## 파일 인터페이스

내부 Python 모듈은 `local_knowledge_wiki`를 유지한다. 기존 번들은 변환할 필요가 없다.
