# Local Second Brain

[English](README.md) | **한국어**

원문과 다시 쓸 노트를 로컬 폴더에 보관한다. Local Second Brain은 나중에 노트를
찾고, 출처를 확인하고, 수정 전 버전도 남기려는 사람과 에이전트를 위한 작은
Python 명령줄 도구다.

글은 사람이나 에이전트가 쓴다. CLI는 원문 바이트 복사, Markdown 버전 저장,
정확한 단어 검색과 메타데이터 검사를 맡는다. 실행 중 모델이나 네트워크를
호출하지 않는다. 일반 텍스트 편집기로 읽을 수 있고 Obsidian은 선택 사항이다.

초기 알파다. macOS 또는 Linux의 쓰기 가능한 로컬 POSIX 파일시스템,
POSIX 셸, `venv`를 지원하는 Python 3.11 이상이 필요하다.
CI는 macOS와 Ubuntu에서 Python 3.11과 3.14를 검사한다.
다른 Linux 환경과 WSL은 별도 검증하지 않았으며 Windows는 지원하지 않는다.

## 시작하기

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

## 이어서 사용하기

- [검토, 수정, 다시 찾기](docs/getting-started.ko.md): 예제를 이어서 세 버전을 남기고 별도 합성 재사용 작업을 실행한다. 선택 사항인 Obsidian 안내도 있다.
- [내 에이전트로 사용하기](docs/agent-kit.ko.md): 출처가 있는 노트를 쓰고 나중 작업에 재사용한다. 파일 인터페이스는 특정 에이전트나 자동 연동을 요구하지 않는다.
- [공개 자료로 실행한 Codex 검증](docs/field-validation.md): 실제 에이전트 작성과 후속 작업, 빈 검색 결과와 GUI 접근 한계를 기록했다. 한 번의 수동 실행이며 모든 에이전트의 연동 시험은 아니다.
- [명령과 지원 범위](docs/reference.ko.md): 정확한 검색 규칙, 검토 선언, 안전과 복구 한계. [개발과 검증](docs/development.ko.md)에는 테스트와 CI 설명이 있다.

검토자 표시는 신원 인증이 아닌 선언이다. 검색은 의미가 아닌 정확한 단어를
사용한다. 이전 버전은 직접 고치지 말고 별도 파일에 수정한 뒤 `curate`로 저장한다.
세부 규칙은 참조 문서에서 확인할 수 있다.

## 라이선스와 출처

이 프로젝트에서 직접 작성한 구현과 문서는 [MIT 라이선스](LICENSE)를 따른다.
저작권 표기는 `Copyright (c) 2026 indra622`다.

이 구현은 LLM Wiki의 작업 흐름과
[Open Knowledge Format(OKF) 명세](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md)를 참고했다.
이 개념과 제3자 자료의 출처는 각 작성자에게 있다. 제3자 코드, 문서와 수집한 원문에는
각각의 라이선스와 이용 조건이 적용된다. 이 프로젝트의 MIT 라이선스가 그 자료의
라이선스를 바꾸지는 않는다.
