# Local Second Brain

[English](README.md) | **한국어**

**초기 알파: macOS와 Ubuntu에서 CI 검증. Windows 미지원.**

**내 파일로 남는 지식. 어떤 에이전트와도 이어서.**

기억을 쌓는 데서 끝내지 않고, 근거와 변화까지 남기는 로컬 세컨드 브레인이다.
LLM Wiki의 자료 수집과 개념 정리 흐름을 바탕으로, Open Knowledge Format(OKF)의
메타데이터 일부를 사용해 출처, 검토 기록, 신선도와 현재 버전을 구분한다.

- **출처가 남는다.** 원문 바이트와 수집 기록을 보존하고 지식 노트에서 연결한다.
- **검토 여부가 보인다.** 작성 주체와 기록된 검토 주체를 구분한다. 형식 검사를 사실 확인으로 취급하지 않는다.
- **오래된 지식을 알아본다.** 생성 시점과 선택적 유효 기한을 읽고 오래됨 여부를 표시한다.
- **수정해도 이전 판단이 남는다.** 새 파일로 리비전을 만들고 인덱스는 현재 버전을 가리킨다.
- **도구를 바꿔도 지식은 남는다.** 일반 파일과 Markdown을 읽으며 특정 모델, 서비스나 에이전트 런타임을 요구하지 않는다.

현재는 작은 Python CLI다. 선택한 에이전트나 사람이 글을 정리하고, CLI는 저장, 리비전,
키워드 검색과 형식 검사를 맡는다. CLI 자체는 모델이나 네트워크를 호출하지 않는다.
Obsidian은 선택적 뷰어다. 특정 에이전트와의 자동 연동은 아직 구현하거나 검증하지 않았다.
CLI 명령은 `second-brain`이다. 내부 Python 모듈은 `local_knowledge_wiki`를 유지하며, 기존 지식 파일은 변환 없이 그대로 사용한다.

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

## 시작하기

`pyproject.toml`이 있는 프로젝트 루트에서 실행한다.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

다음 예제는 모두 지어낸 자료다. `mktemp`로 만든 임시 경로는 셸이 종료되면 변수에서
사라지지만 디렉터리는 남는다. 실행 결과의 경로를 확인해 두면 파일을 직접 살펴볼 수 있다.

```sh
DEMO_DIR="$(mktemp -d "${TMPDIR:-/tmp}/second-brain.XXXXXX")"
second-brain init "$DEMO_DIR/wiki"
second-brain capture "$DEMO_DIR/wiki" examples/inputs/garden-note.txt \
  --id garden-note --actor human:demo --resource synthetic:garden-note
second-brain curate "$DEMO_DIR/wiki" garden \
  --body examples/inputs/garden-v1.md --source garden-note --actor demo-agent/0.1 \
  --title '달빛 정원의 물주기' --stale-after '2030-01-01T00:00:00+00:00'
second-brain search "$DEMO_DIR/wiki" '물주기' --now '2026-10-27T00:00:00+00:00'
second-brain check "$DEMO_DIR/wiki" --now '2026-10-27T00:00:00+00:00'
```

`check`의 예상 결과는 `invalid: []`, `warnings: []`, `stale: []`, `concepts: 1`이다.
새 리비전의 기본 상태는 `draft`, 검토 수준은 `unverified`다. 합성 본문과 원문을 직접
비교한 뒤 검토했다는 선언을 기록한다.

```sh
second-brain review "$DEMO_DIR/wiki" garden --revision r000001 \
  --actor human:demo --evidence sources/garden-note/content.raw
second-brain show "$DEMO_DIR/wiki" garden --format json
```

본문이 같은 `r000002`가 만들어지고 `human-reviewed` 선언이 표시된다. `r000001`은 그대로 남고
상태는 `draft`를 유지한다. CLI는 사실이나 `human:demo`의 신원을 확인하지 않는다.
이어서 본문을 수정하면 다시 `unverified`인 새 리비전이 만들어진다.

```sh
second-brain curate "$DEMO_DIR/wiki" garden \
  --body examples/inputs/garden-v2.md --source garden-note --actor demo-agent/0.1
second-brain search "$DEMO_DIR/wiki" '물주기'
second-brain check "$DEMO_DIR/wiki"
```

세 리비전은 모두 남고 인덱스는 본문을 수정한 `r000003`을 가리킨다. 명령의 기본 출력은 JSON이다. 검색과 읽기 전용 열람 명령은 `--format text`도 받는다. `second-brain --help`, `second-brain curate --help`, `second-brain review --help`로 옵션을 확인한다.
`--actor`는 실행 주체를 명시하는 입력이며 로그인 인증이나 신원 증명이 아니다.

## 저장된 지식 확인하기

### Obsidian이 없을 때

애플리케이션 소스가 아니라 **지식 폴더**를 파일 탐색기나 편집기로 연다.
`index.md`부터 읽으면 현재 버전의 노트로 이동할 수 있다. 링크된 Markdown을 열어 본문과
YAML 메타데이터를 확인한다. Markdown 미리보기가 있는 편집기를 쓰면 보기 편하고,
일반 텍스트 편집기로 읽어도 된다. 현재 버전에는 자체 그래픽 뷰어가 없다.

위 예제를 끝낸 뒤 다음 명령으로 현재 링크, 이전 노트 버전과 원문 수집 기록을 확인한다.

```sh
second-brain list "$DEMO_DIR/wiki" --format text
second-brain show "$DEMO_DIR/wiki" garden --format text
second-brain show "$DEMO_DIR/wiki" garden --revision r000001 --format json
second-brain history "$DEMO_DIR/wiki" garden --format text
second-brain diff "$DEMO_DIR/wiki" garden r000001 r000003 --format text
second-brain search "$DEMO_DIR/wiki" '물주기' --current-only --status draft \
  --freshness unknown --format text
second-brain search "$DEMO_DIR/wiki" '물주기' --status draft --freshness fresh \
  --now '2026-10-27T00:00:00+00:00' --format json
python -m json.tool "$DEMO_DIR/wiki/sources/garden-note/provenance.json"
second-brain search "$DEMO_DIR/wiki" '물주기'
second-brain check "$DEMO_DIR/wiki"
```

`search`는 파일 경로, 메타데이터와 짧은 본문 발췌를 반환한다. 전체 본문은 `show`로 읽는다.
`current: true`는 인덱스가 가리키는 현재 버전이다. 이전 파일은 비교용으로 남는다.
`content.raw`는 원문 바이트를 보존하므로 텍스트 자료임을 알 때만 텍스트로 연다. 바이너리일 수도 있다.
`provenance.json`에는 출처, 수집 시각, 수집 주체와 해시가 들어 있다.
다른 터미널을 열면 `.venv`를 다시 활성화하고 지식 폴더 경로를 지정한다.
`DEMO_DIR`는 값을 설정한 셸에서만 유지된다.

### Obsidian이 있을 때

1. CLI로 **새 지식 폴더**를 먼저 만들고 자료를 넣는다. 기존의 비어 있지 않은 볼트에 `init`을 실행하지 않는다.
2. Obsidian 볼트 전환 화면에서 **Open folder as vault**를 선택하고 그 지식 폴더를 연다.
   위 예제에서는 `init`이 출력한 경로의 `wiki` 폴더다. 프로젝트 소스 폴더를 여는 것이 아니다.
3. `index.md`의 현재 버전 링크로 노트를 읽는다. Source 모드에서 YAML을 보거나 Properties에서
   지원하는 속성을 확인한다. 중첩 메타데이터는 Source 모드에서 읽을 수 있다.
4. `concepts/`의 버전 파일을 비교하고 `sources/`의 원문 기록을 확인한다.
   Obsidian에서 `.raw`나 JSON이 열리지 않으면 외부 편집기로 읽는다.
5. 검색, 검사와 새 버전 작성은 터미널의 CLI로 한다. Obsidian으로 읽었다고 내용이 검증되는 것은 아니다.

커뮤니티 플러그인, Sync 구독이나 Publish 서비스는 필요 없다. Obsidian은 `.obsidian` 설정 폴더를 만든다.
검색, 검사와 리비전 순회는 모든 깊이에서 이름이 정확히 `.obsidian` 또는 `.git`인 항목을 제외한다.
해당 이름의 심볼릭 링크도 따라가지 않으며 파일을 바꾸지 않는다. 그 외 숨김 지식 파일과 폴더는
계속 검사하며, 일반 지식 경로의 심볼릭 링크는 거부한다.
버전 이력을 지키려면 기존 리비전을 직접 고치지 말고, 별도 본문 파일을 준비해 `curate`로 저장한다.

폴더를 볼트로 여는 절차는 [Obsidian 공식 가이드](https://help.obsidian.md/vault)를 기준으로 썼다.
이 프로젝트에서 그래픽 화면의 실제 동작까지 독립 검증한 것은 아니다.

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
검토 기록을 물려받지 않는다. 상세 규칙과 실패 한계는 한영 [검토 규칙](docs/review-contract.md)을 참고한다.

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
정확한 검사 범위와 생략한 항목은 [검사 범위](docs/okf-subset.md)에 적었다.

## 작업 방법과 한계

[에이전트 사용 안내와 작업 템플릿](docs/agent-kit.ko.md)부터 읽고
[한국어 작업 절차](workflows/AGENT-WORKFLOW.ko.md)와
[본문 템플릿](templates/concept-body.ko.md)을 에이전트에 전달한다. 각각 영어 문서도 있다.
기존 [합성 예제 번들](examples/bundle/index.md)은 한국어다.
지침과 템플릿은 번들 밖에 둔다. 특정 vault 구조나 에이전트 설정을 가정하지 않는다.

체크아웃에서 환경을 활성화한 상태로 별도의 합성 재사용 예제를 실행한다.
빠른 시작의 임시 `DEMO_DIR` 아래에 기존 `wiki`와 분리해서 저장한다.

```sh
python examples/knowledge_reuse.py --output "$DEMO_DIR/reuse-demo"
second-brain show "$DEMO_DIR/reuse-demo/wiki" lantern --format text
second-brain history "$DEMO_DIR/reuse-demo/wiki" lantern --format text
```

빈 검색, 원문 수집, 준비 본문, 나중 작업의 검색과 재사용, 수정 원문과 본문,
현재 선택, 바이트 보존, 이력과 비교를 확인한다. `reuse-demo` 아래의
`reuse-before.json`, `reuse-after.json`, `transcript.json`, `summary.json`을 읽어 볼 수 있다.
[사용 안내](docs/agent-kit.ko.md)에서 각 결과를 설명한다.
예제는 미리 작성한 영어 합성 노트와 결정적인 CLI 실행을 쓰며 LLM 합성이나 사실 검증기가 아니다.
`process:synthetic-demo` 검토는 예제 선언이며 신원 인증이나 사람의 검토가 아니다.
이후 내용 수정은 `unverified`다. 실제 Claude, Codex, Grok 연동은 시험하지 않았다.
필수 모델, 업체, 계정이나 API 키는 없다. CLI는 오프라인에서 실행되지만 외부 에이전트는
자체 정책을 따르며 외부 전송에는 별도 허가가 필요하다. 예제와 문서는 체크아웃 자료이며
배포된 독립 패키지가 아니다.

쓰기 명령은 번들의 배타 잠금을 사용하며 파일 생성 시 기존 파일을 덮어쓰지 않는다.
`index.md`의 관리 표식 사이에는 생성된 현재 링크만 둔다. 그 밖에 쓴 글은 보존한다.
관리 구역의 구조를 바꾸면 `curate`는 거부한다. 파일을 직접 편집하는 프로그램은 잠금을
따르지 않으므로 쓰기 명령과 동시에 편집하지 않는다. 장애 후 남은 잠금이나 미연결
리비전은 자동 삭제하지 않는다. [구조와 복구 범위](docs/architecture.md)를 먼저 확인한다.

웹 UI, 서버, 벡터 DB, 클라우드, MCP, 계산 실행과 attestation은 이번 범위에 없다.
PyPI 배포는 아직 없으므로 프로젝트 소스로 설치한다.

## 라이선스와 출처

이 프로젝트에서 직접 작성한 구현과 문서는 [MIT 라이선스](LICENSE)를 따른다.
저작권 표기는 `Copyright (c) 2026 indra622`다.

이 구현은 LLM Wiki의 작업 흐름과
[Open Knowledge Format(OKF) 명세](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md)를 참고했다.
이 개념과 제3자 자료의 출처는 각 작성자에게 있다. 제3자 코드, 문서와 수집한 원문에는
각각의 라이선스와 이용 조건이 적용된다. 이 프로젝트의 MIT 라이선스가 그 자료의
라이선스를 바꾸지는 않는다.

## 개발 확인

```sh
python -m unittest discover -s tests -v
python -m compileall -q src tests examples
python -m pip check
```

`python tests/verify_quickstart.py`는 두 README의 셸 블록을 각각 임시 프로젝트 복사본과 새 venv에서 그대로 실행한다.
이 소스 작업 절차는 의도적으로 체크아웃의 예제를 사용한다. 검증 항목은 설치, 원문 바이트 보존, 이전 버전 유지, 문서의 열람 명령과 별도 재사용 예제 결과다.

Obsidian 화면 절차는 공식 도움말 기준이며 실제 GUI 조작은 독립 검증하지 않았다.

체크아웃에서 `python scripts/verify_wheel.py`를 실행하면 `pip wheel`로 프로젝트 wheel을
빌드하고, 시스템 패키지를 포함하지 않는 새 venv에 wheel과 의존성을 설치한다.
체크아웃 밖에서 `PYTHONPATH`를 비운 채 패키지가 해당 venv에서 import되는지 확인하고,
init, capture, curate, search, check, review와 네 가지 열람 명령을 실행한다.
원문과 이전 리비전의 바이트 보존도 확인한다. 입력은 체크아웃 예제와 별개로 만든 합성
임시 파일이며 HOME과 pip 캐시 쓰기는 임시 디렉터리 안에 둔다. 설치 시 빌드 도구와
의존성을 다운로드할 수 있지만 CLI는 실행 중 외부 API를 호출하지 않는다.
종료 시 임시 검사 결과를 삭제하며 패키지를 배포하지 않는다.

[CI](.github/workflows/ci.yml)는 pull request와 `main` push에 실행하도록 설정했다.
`macos-latest`, `ubuntu-latest`에서 각각 Python 3.11과 3.14를 사용한다.
네 작업 모두 전체 unittest와 wheel 검사를 실행하며, 두 README 소스 작업 절차는
macOS/Python 3.14에서만 실행한다. 권한은 contents 읽기 전용이며 공식 액션을 커밋 SHA로
고정하고 체크아웃 인증 정보를 유지하지 않는다. 예약 실행이나 자동 배포는 없다.

macOS/Python 3.14.6 로컬 검증에서 단위 테스트 50개, 독립 wheel 검사, 두 README 작업 절차,
컴파일과 `pip check`가 통과했다.
[실제 Actions 실행 40599790644](https://github.com/indra622/local-second-brain/actions/runs/40599790644)도
macOS/Ubuntu와 Python 3.11/3.14의 네 작업 모두 통과했다. 두 README의 전체 실행은
macOS/Python 3.14 작업에서 통과했다. 해당 호스팅 환경의 검증이며 모든 Linux 배포판이나
Obsidian GUI 동작을 검증했다는 뜻은 아니다.
