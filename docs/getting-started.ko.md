# 다음 단계: 검토, 수정, 다시 찾기

[English](getting-started.md) | **한국어**

[README 시작하기](../README.ko.md#시작하기)를 먼저 실행한 같은 셸에서 이어서 실행한다.
새 터미널에서는 프로젝트 폴더로 돌아와 가상환경을 활성화한다.
README에서 저장한 `DEMO_DIR=...` 줄로 상위 폴더 경로를 복원한다.
`/wiki`로 끝나는 지식 폴더 경로가 아니다. 아래 명령이 `/wiki`를 덧붙인다.

## 검토와 수정

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

## 합성 재사용 예제

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
[사용 안내](agent-kit.ko.md)에서 각 결과를 설명한다.
예제는 미리 작성한 영어 합성 노트와 결정적인 CLI 실행을 쓰며 LLM 합성이나 사실 검증기가 아니다.
`process:synthetic-demo` 검토는 예제 선언이며 신원 인증이나 사람의 검토가 아니다.
이후 내용 수정은 `unverified`다. Claude, Codex, Grok의 자동 연동은 시험하지 않았다.
별도의 [공개 자료 Codex 실행 기록](field-validation.md)은 수동 CLI 사용과 한계를 다룬다.
필수 모델, 업체, 계정이나 API 키는 없다. CLI는 오프라인에서 실행되지만 외부 에이전트는
자체 정책을 따르며 외부 전송에는 별도 허가가 필요하다. 예제와 문서는 체크아웃 자료이며
배포된 독립 패키지가 아니다.
