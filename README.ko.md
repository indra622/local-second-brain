# Local Second Brain

[English](README.md) | **한국어**

## AI와 쌓은 지식, 대화 밖에서도 이어서.

**원문과 함께 남기고, 다음 작업에 다시 쓰는 나만의 지식 저장소.**

Local Second Brain은 나 또는 에이전트가 정리한 노트를 원문과 이전 버전까지
내 컴퓨터의 파일로 보관해, 다음 작업에서도 꺼내 쓸 수 있게 합니다.

**[에이전트에게 설치 맡기기 (For agents)](#에이전트에게-설치-맡기기-for-agents)** | **[직접 시작하기](#시작하기)**

### 한 번 정리한 지식을 다시 쓰세요

쓸 만한 조사 결과와 결정을 노트로 남기고, 다음 대화에서 찾아 읽으세요.
새 보고서나 프로젝트를 시작할 때 관련 노트를 에이전트에게 건네줄 수 있습니다.

### 결론의 근거까지 함께 남기세요

노트와 원문 파일을 함께 보관하세요. 어떤 자료를 보고 내린 결론인지 돌아보고,
생각이 바뀌면 이전 버전과 비교할 수 있습니다.

### AI를 바꿔도 파일은 내게 남습니다

노트는 내 컴퓨터에 읽을 수 있는 Markdown 파일로 남습니다.
이 도구나 AI 계정 없이도 열어 보고 보관할 수 있습니다.

## 오늘 조사한 자료로, 다음 주 보고서를

이렇게 활용할 수 있습니다. 아래는 가상의 예입니다.

1. **오늘:** 보관할 조사 자료를 고르고, 나 또는 에이전트가 정리한 노트와 함께 저장합니다.
2. **다음 주:** 그 노트를 찾아 에이전트에게 건네고, 보고서의 출발점으로 쓰도록 합니다.
3. **내용이 달라졌을 때:** 보관한 원문을 다시 열고 새 근거를 확인한 뒤 노트를 수정해 저장합니다. 이전 버전도 남습니다.

## 이런 분에게 맞습니다

AI와 자료를 조사하고, 프로젝트의 방향을 정하고, 반복해서 보고서를 쓰면서
한 작업에서 얻은 지식을 다음 작업에도 쓰고 싶은 분을 위한 도구입니다.
현재는 초기 알파 단계의 명령줄 도구로, 저장할 자료를 고르고 작성과 재사용을 지시하는 일은
사용자가 맡습니다. 에이전트에게 설치를 맡기거나 아래 예제를 직접 따라 해 보세요.

## 에이전트에게 설치 맡기기 (For agents)

에이전트에게 설치와 검증을 맡기려면 아래 지시문을 그대로 전달한다.
직접 설치하려면 아래 [시작하기](#시작하기)를 따른다.

```text
https://github.com/indra622/local-second-brain.git 에서 Local Second Brain을 설치하고 검증해 줘.
새 작업 폴더에 복제하거나, 기존 체크아웃을 확인하고 사용자 변경을 덮어쓰지 않고 재사용해 줘.
먼저 저장소의 README와 지원 요건을 읽어 줘.
프로젝트 안에 .venv를 만들고 문서의 소스 설치 방법인 python -m pip install -e . 를 사용해 줘.
그 환경을 활성화한 뒤 second-brain --help를 확인하고, 체크아웃 폴더에서 README의 합성 예제를
실행해 줘. 지식 폴더는 별도로 새로 만든 임시 폴더를 사용해 줘.
체크아웃, CLI 실행 파일, 데모 폴더의 경로와 실행한 명령, 결과를 알려 줘.
범위는 설치와 합성 데모로 한정해 줘. 개인 vault를 훑거나 데이터를 업로드하거나
전역 설정을 바꾸거나 원격 설치 스크립트를 셸에 바로 넘겨 실행하지 마.
설치만으로 자동 기억이나 모델 연동이 생기는 것은 아니야.
```

이후 실제 노트를 다룰 때는 [에이전트 안내](docs/agent-kit.ko.md)와
[작업 흐름](workflows/AGENT-WORKFLOW.ko.md)을 따른다.

## 시작하기

초기 알파다. macOS 또는 Linux의 쓰기 가능한 로컬 POSIX 파일시스템,
POSIX 셸, `venv`를 지원하는 Python 3.11 이상이 필요하다.
CI는 macOS와 Ubuntu에서 Python 3.11과 3.14를 검사한다.
다른 Linux 환경과 WSL은 별도 검증하지 않았으며 Windows는 지원하지 않는다.

Git으로 소스를 받은 뒤 프로젝트 폴더로 이동한다. 압축파일을 받았다면 압축을
풀고 `pyproject.toml`이 있는 폴더에서 터미널을 연다.
PyPI 배포는 없다. 예제와 안내 문서는 소스에 포함되어 있다.

```text
git clone https://github.com/indra622/local-second-brain.git
cd local-second-brain
```

Python을 확인하고 가상환경을 만든 뒤 설치한다. 설치 시 PyYAML과 빌드 도구를
내려받으려면 보통 인터넷이 필요하다. AI 계정이나 API 키는 필요 없다.
Python이 3.11보다 낮거나 `venv`가 없으면 적합한 Python을 먼저 설치한다.

```sh
python3 --version
python3 -m venv --help > /dev/null
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

다음 예제는 가상의 정원 자료를 물주기 노트로 저장한 뒤 `물주기`라는 정확한
단어로 찾는다. **capture(원문 수집)**는 선택한 파일을 복사하고 출처를 기록한다.
**curate(노트 저장)**는 미리 쓴 글을 원문에 연결해 저장한다.
예제는 준비된 파일을 쓰며 두 명령 모두 글을 생성하지 않는다.

지식 폴더는 코드 폴더 밖에 둔다. 다음 임시 폴더는 실행 후에도 남으므로 직접
살펴볼 수 있다. 아래에서 출력하는 `DEMO_DIR=...` 줄을 저장해 둔다.
이 값은 상위 폴더다. `init`이 출력하는 `/wiki`로 끝나는 지식 폴더 경로와 다르다.

```sh
DEMO_DIR="$(mktemp -d "${TMPDIR:-/tmp}/second-brain.XXXXXX")"
printf 'DEMO_DIR=%s\n' "$DEMO_DIR"
second-brain init "$DEMO_DIR/wiki"
second-brain capture "$DEMO_DIR/wiki" examples/inputs/garden-note.txt \
  --id garden-note --actor human:demo --resource synthetic:garden-note
second-brain curate "$DEMO_DIR/wiki" garden \
  --body examples/inputs/garden-v1.md --source garden-note --actor demo-agent/0.1 \
  --title '달빛 정원의 물주기' --stale-after '2030-01-01T00:00:00+00:00'
second-brain search "$DEMO_DIR/wiki" '물주기' --now '2026-10-27T00:00:00+00:00'
second-brain check "$DEMO_DIR/wiki" --now '2026-10-27T00:00:00+00:00'
```
저장한 노트를 읽는다.

```sh
second-brain show "$DEMO_DIR/wiki" garden --format text
```

검색 결과는 `concepts/garden/r000001.md`이며 `current: true`, 상태 `draft`,
검토 수준 `unverified`를 표시한다. 첫 `check` 결과는 `invalid: []`,
`warnings: []`, `stale: []`, `concepts: 1`이다. 이는 형식 검사이며 사실 확인이 아니다.
지식 폴더의 `index.md`에서 노트 링크를 열 수도 있다.

## 지원 범위와 한계

- **작업은 사용자가 이끕니다.** 자동 기억, 모델을 통한 글 생성, 의미 검색은 없습니다. 미리 작성한 노트를 저장하고 정확한 단어로 검색합니다. GUI와 MCP 서버는 없으며 OKF의 일부만 구현합니다.
- **로컬에서 실행됩니다.** CLI는 실행 중 네트워크를 사용하지 않습니다. 외부 에이전트에는 각자의 네트워크 및 데이터 정책이 적용됩니다.
- **검토 기록은 선언입니다.** 검토 기록과 재확인 기한은 다시 확인할 대상을 고르는 단서이며, 검토자의 신원을 인증하거나 사실을 검증하지 않습니다. 자세한 내용은 [명령과 지원 범위](docs/reference.ko.md)를 참고하세요.
- **Obsidian은 선택 사항입니다.** [뷰어 안내](docs/getting-started.ko.md#obsidian이-있을-때)를 따라 열어 볼 수 있지만 GUI 작업 흐름은 검증하지 못했습니다. Obsidian 없이도 사용할 수 있습니다.

## 이어서 사용하기

- [검토, 수정, 다시 찾기](docs/getting-started.ko.md): 예제를 이어서 세 버전을 남기고 별도 합성 재사용 작업을 실행한다. 선택 사항인 Obsidian 안내도 있다.
- [내 에이전트로 사용하기](docs/agent-kit.ko.md): 출처가 있는 노트를 쓰고 나중 작업에 재사용한다. 파일 인터페이스는 특정 에이전트나 자동 연동을 요구하지 않는다.
- [공개 자료로 실행한 Codex 검증](docs/field-validation.md): 실제 에이전트 작성과 후속 작업, 빈 검색 결과와 GUI 접근 한계를 기록했다. 한 번의 수동 실행이며 모든 에이전트의 연동 시험은 아니다.
- [명령과 지원 범위](docs/reference.ko.md): 정확한 검색 규칙, 검토 선언, 안전과 복구 한계. [개발과 검증](docs/development.ko.md)에는 테스트와 CI 설명이 있다.

이전 버전은 직접 고치지 말고 별도 파일에 수정한 뒤 `curate`로 저장한다.
세부 규칙은 참조 문서에서 확인할 수 있다.

## 라이선스와 출처

이 프로젝트에서 직접 작성한 구현과 문서는 [MIT 라이선스](LICENSE)를 따른다.
저작권 표기는 `Copyright (c) 2026 indra622`다.

이 구현은 LLM Wiki의 작업 흐름과
[Open Knowledge Format(OKF) 명세](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md)를 참고했다.
이 개념과 제3자 자료의 출처는 각 작성자에게 있다. 제3자 코드, 문서와 수집한 원문에는
각각의 라이선스와 이용 조건이 적용된다. 이 프로젝트의 MIT 라이선스가 그 자료의
라이선스를 바꾸지는 않는다.
