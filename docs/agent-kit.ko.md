# 허가한 에이전트로 시작하기

[English](agent-kit.md) | **한국어**

이 키트는 에이전트에게 범위가 정해진 로컬 지식 작업을 맡기는 입구다. CLI는 준비된 글과
원문을 저장하고 에이전트가 읽기·종합·판단을 한다. [README 빠른 시작](../README.ko.md#시작하기)으로
설치한 뒤 목적에 맞게 연다.

- [지속 작업 절차](../workflows/AGENT-WORKFLOW.ko.md): 명령 순서, 접근·개인정보, 데이터와
  지시 구분, 재시도/CAS, 선언과 불완전 결과의 정본이다. 정확한 옵션·스키마는 reference로 연결한다.
- [복사할 작업 프롬프트](../templates/task-workflow.ko.md): 목표·허용 경로·안정된 작업 ID·
  저장한 요청/리비전을 채워 선택한 에이전트에게 준다.
- [본문 틀](../templates/concept-body.ko.md): 번들 밖에서 검색 가능한 Markdown을 준비한다.
  recall은 annotation 필드를 검색하지 않는다.

CLI에 호스트 연동·모델·계정·Obsidian은 필요하지 않고 키트는 훅이나 전역 규칙을 설치하지
않는다. 결정적 CLI 예제가 실제 호스트/모델 연동을 증명하지 않는다. 로컬 저장은 런타임
업로드를 하지 않지만 외부 에이전트는 자체 정책에 따라 허용한 입력을 제공자에게 보낼 수
있다. 접근과 전송 권한은 명시한다.

## 합성 재사용 예제

프로젝트 환경을 활성화하고 새 경로나 빈 출력 폴더를 고른다.

```sh
python examples/knowledge_reuse.py --output /tmp/my-new-second-brain-demo
```

예제는 지정된 가상 fixture만 읽고 자체 bundle/prepared/results를 쓴다. 비어 있지 않은
대상·파일·출력 심볼릭 링크는 거부한다. 실패 시 부분 산출물이 남을 수 있지만 이전 출력을
지우거나 덮어쓰지 않는다. 출처 노트 저장·process 검토·후속 체크리스트 재사용 후 내용을
수정하고 다시 현재 지식을 사용한다.

summary.json·transcript.json, reuse-before.json/reuse-after.json과 wiki/에서 정확한 리비전과
원문 바이트를 확인한다. 재사용은 결정적 복사이며 LLM 판단이나 사실 검증이 아니다. 내용
변경은 상속 검토를 초기화한다. demo actor를 인증된 신뢰로 보지 말고 실제 작업은 정본 절차를 따른다.
