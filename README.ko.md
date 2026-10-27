# Local Second Brain

[English](README.md) | **한국어**

**초기 알파: macOS에서 검증. Windows 미지원. Linux 미검증.**

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

- **운영체제:** macOS 또는 Linux의 로컬 POSIX 파일시스템. 실제 검증은 macOS에서만 했다.
  Windows는 POSIX 전용 파일 API 때문에 지원하지 않는다. WSL도 미검증이다.
- **Python:** 표준 `venv` 모듈을 사용할 수 있는 Python 3.11 이상. 테스트 환경은 3.14.6이며,
  최소 버전인 3.11은 별도로 검증하지 않았다.
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
새 리비전의 기본 상태는 `draft`, 검토 수준은 `unverified`다. 두 번째 글을 저장하면
첫 파일은 그대로 남고 `index.md`가 두 번째 파일을 가리킨다.

```sh
second-brain curate "$DEMO_DIR/wiki" garden \
  --body examples/inputs/garden-v2.md --source garden-note --actor demo-agent/0.1
second-brain search "$DEMO_DIR/wiki" '물주기'
second-brain check "$DEMO_DIR/wiki"
```

명령 출력은 JSON이다. `second-brain --help`와 `second-brain curate --help`로 옵션을 확인한다.
`--actor`는 실행 주체를 명시하는 입력이며 로그인 인증이나 신원 증명이 아니다.

## 저장된 지식 확인하기

### Obsidian이 없을 때

애플리케이션 소스가 아니라 **지식 폴더**를 파일 탐색기나 편집기로 연다.
`index.md`부터 읽으면 현재 버전의 노트로 이동할 수 있다. 링크된 Markdown을 열어 본문과
YAML 메타데이터를 확인한다. Markdown 미리보기가 있는 편집기를 쓰면 보기 편하고,
일반 텍스트 편집기로 읽어도 된다. 현재 버전에는 자체 그래픽 뷰어가 없다.

위 예제를 끝낸 뒤 다음 명령으로 현재 링크, 두 번째 노트 버전과 원문 수집 기록을 확인한다.

```sh
cat "$DEMO_DIR/wiki/index.md"
cat "$DEMO_DIR/wiki/concepts/garden/r000002.md"
python -m json.tool "$DEMO_DIR/wiki/sources/garden-note/provenance.json"
second-brain search "$DEMO_DIR/wiki" '물주기'
second-brain check "$DEMO_DIR/wiki"
```

`search`는 본문 전체가 아니라 파일 경로와 메타데이터를 반환한다. 반환된 경로를 편집기로 열면 된다.
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
설정 폴더는 지식 출처가 아니다. 현재 검사는 앱 폴더를 자동 제외하지 않아서 플러그인이나 설정 폴더에
추가된 Markdown도 검사할 수 있다. 처음에는 커뮤니티 플러그인 없이 사용한다.
버전 이력을 지키려면 기존 리비전을 직접 고치지 말고, 별도 본문 파일을 준비해 `curate`로 저장한다.

폴더를 볼트로 여는 절차는 [Obsidian 공식 가이드](https://help.obsidian.md/vault)를 기준으로 썼다.
이 프로젝트에서 그래픽 화면의 실제 동작까지 독립 검증한 것은 아니다.

## 명령과 파일

| 명령 | 동작 |
| --- | --- |
| `init BUNDLE` | 새 경로나 빈 디렉터리에 `index.md`를 만든다. 비어 있지 않으면 거부한다. |
| `capture BUNDLE FILE --id ID --actor ACTOR --resource ORIGIN` | 원문 바이트와 출처, 수집 주체, 시간, SHA-256을 보존한다. ID 재사용을 거부한다. |
| `curate BUNDLE ID --body FILE --source SOURCE_ID --actor ACTOR` | 준비한 UTF-8 본문을 새 개념 리비전으로 저장한다. `--source`는 반복할 수 있다. |
| `search BUNDLE QUERY` | 모든 개념 리비전의 제목과 본문을 단어로 검색한다. |
| `check BUNDLE` | 메타데이터 일부를 검사하고 링크 경고와 오래된 문서를 별도로 보고한다. |

ID는 영문 소문자나 숫자로 시작하는 1~64자의 영문 소문자, 숫자, 하이픈이다.
`curate`는 `--type`, `--title`, `--status`, `--stale-after`도 받는다.
원문을 직접 해석하거나 준비한 글의 사실을 확인하지 않는다. `verified`는 추가하지 않는다.
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
```

원문은 확장자나 인코딩에 관계없이 바이트 그대로 저장한다. 줄바꿈과 BOM도 바꾸지 않는다.
원문 Markdown도 `.raw`로 보존하므로 개념 문서로 잘못 검사하지 않는다.
원문 검색, PDF 추출, 인코딩 추측은 없다. 본문과 개념 문서는 UTF-8이어야 한다.
다른 인코딩은 에이전트가 별도 작업 파일에서 변환하고 원문과 구분해야 한다.

검색은 Unicode `\w+` 토큰을 `casefold`한 뒤 모든 검색어가 정확히 있는 문서를 찾는다.
점수는 중복을 제거한 검색어의 출현 횟수 합이며, 점수 내림차순과 경로 오름차순으로 정렬한다.
형태소 분석, 부분 문자열 검색, 의미 검색은 없다. 이전 리비전도 결과에 남는다.
`current`는 이 CLI의 현재 링크 여부이며, 가져온 일반 번들에서 판단할 수 없으면 `null`이다.
`status`, `trust`, `stale`, 생성과 검토 기록, 메타데이터 오류를 함께 출력한다.
`stale: null`은 기한이 없거나 잘못되어 판단할 수 없다는 뜻이다. 검토 수준은 기록에서
계산한 참고 정보다. CLI가 사실이나 검토자의 신원을 확인했다는 뜻이 아니다.

검사는 번들 안의 모든 `.md`를 읽는다. `index.md`와 `log.md`는 예약 파일로 구분한다.
깨진 링크와 오래된 문서는 형식 오류와 별도이며, 이것만 있으면 종료 코드는 0이다.
메타데이터 오류가 있으면 1, 입출력 실패나 안전상 거부, 잘못된 인자는 2다.
정확한 검사 범위와 생략한 항목은 [검사 범위](docs/okf-subset.md)에 적었다.

## 작업 방법과 한계

에이전트에는 [공통 작업 절차](workflows/AGENT-WORKFLOW.md)를 전달한다.
[본문 템플릿](templates/concept-body.md)과 [합성 예제 번들](examples/bundle/index.md)을 참고할 수 있다.
이 지침과 템플릿은 번들 밖에 둔다. 특정 vault 구조나 에이전트 설정을 가정하지 않는다.

쓰기 명령은 번들의 배타 잠금을 사용하며 파일 생성 시 기존 파일을 덮어쓰지 않는다.
`index.md`의 관리 표식 사이에는 생성된 현재 링크만 둔다. 그 밖에 쓴 글은 보존한다.
관리 구역의 구조를 바꾸면 `curate`는 거부한다. 파일을 직접 편집하는 프로그램은 잠금을
따르지 않으므로 쓰기 명령과 동시에 편집하지 않는다. 장애 후 남은 잠금이나 미연결
리비전은 자동 삭제하지 않는다. [구조와 복구 범위](docs/architecture.md)를 먼저 확인한다.

웹 UI, 서버, 벡터 DB, 클라우드, MCP, 계산 실행과 attestation은 이번 범위에 없다.
라이선스는 아직 선택하지 않았으며, 이 저장소에서 재사용 라이선스를 부여하지 않는다.
PyPI 배포는 아직 없으므로 프로젝트 소스로 설치한다.

## 개발 확인

```sh
python -m unittest discover -s tests -v
python -m compileall -q src tests
python -m pip check
```

`python tests/verify_quickstart.py`는 두 README의 셸 블록을 각각 임시 프로젝트 복사본과 새 venv에서 그대로 실행한다.
검증 항목은 설치, 원문 바이트 보존, 이전 버전 유지와 문서의 열람 명령이다.

Obsidian 화면 절차는 공식 도움말 기준이며 실제 GUI 조작은 독립 검증하지 않았다.
