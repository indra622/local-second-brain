# 작업 맥락 선언

[English](work-context.md) | **한국어**

`context`는 인덱스가 선택한 현재 리비전에서 완료한 일, 결정, 열린 질문, 다음 작업과
교훈을 읽는다. 기록은 다음 작업에서 참고할 데이터이며 명령이나 인증된 근거가 아니다.
교훈의 accepted 선언은 에이전트 규칙이나 OKF `verified`를 바꾸지 않고 실제 사람의 검토를
증명하지 않는다. 모델 호출, 호스트 설정 변경이나 읽기 커서는 없다.

번들 밖에 JSON 입력을 준비한다. 전체 예시는 [영문 스키마 예시](work-context.md)에 있다.
`curate --annotations FILE` 입력은 `{"version":1,"context":CONTEXT_DATA}`다.
필수 context 필드는 work_id, recipients, completed, decisions, open_questions, lessons다.
next_actions는 선택 사항이며 생략하면 읽기 결과에 빈 목록으로 나타난다.

```sh
second-brain --error-format json curate BUNDLE HANDOFF_ID --body BODY_FILE --source SOURCE_ID --actor tool/1 --annotations handoff.json --request-id NEW_ID --expect-current absent
second-brain context BUNDLE --scope HANDOFF_ID --recipient codex --limit 50 --max-chars 12000
```

`--annotations`를 생략하면 기존 메타데이터·출력·요청 fingerprint를 그대로 유지한다.
context와 [relations 작성](graph.ko.md)을 지원한다. 중복 JSON 키, 알 수 없는 입력 필드, NaN/무한대,
지원하지 않는 버전은 거부한다. 저장 필드는 `x-second-brain-annotations`이며 version 1과
`context: {recorded_by, recorded_at, data}`를 담는다. 기록 시각과 주체는 선언이다.

수정 입력은 version/envelope를 제외한 CONTEXT_DATA만 담는다. 전체 context 섹션을 교체한다.

```sh
second-brain --error-format json annotate BUNDLE HANDOFF_ID --revision r000001 --section context --file context-section.json --actor process:worker --now 2026-11-01T12:00:00Z --request-id NEW_ID
```

새 리비전은 본문을 정확히 보존하고 다른 메타데이터를 유지하며, 새 리비전에서만 상속된
`verified`를 제거한다. 과거 검토 기록은 이전 파일에 남는다. 기존 `review`는 바뀌지 않는다.
지원되는 크기의 JSON 호환 version 1 안에서 다른 가져온 섹션은 보존한다. 알 수 없는 루트
버전이나 손상된 envelope는 자동 변환하지 않는다. 소유 확장 밖의 YAML 날짜·별칭·비유한
값에는 기존 왕복 보존 규칙을 적용한다.

정확히 현재인 `--revision`이 필요하다. 완료된 같은 요청의 재실행은 오래된 현재 조건보다
먼저 원래 결과를 반환한다. 입력 바이트, actor, revision, section과 명시/암묵 시각 모드를
보존해서 재시도한다. 파일 이름은 식별값이 아니며 바이트가 바뀌면 공백 변경도 충돌한다.
명시한 --now는 오프셋이 있는 ISO8601, 소수 초 최대 6자리이며 UTC로 정규화한다. 같은
순간의 다른 오프셋은 재실행된다. 암묵 실행 시각은 요청 식별값에서 제외한다. 입력 검증은
영수증 조회 전에 실패할 수 있다. 미완료·손상 요청은 검사해야 하며 영수증을 지우거나
새 키로 우회하지 않는다. 다중 파일 트랜잭션이나 자동 복구는 제공하지 않는다.

스키마와 한도:

- work_id와 각 기록 id는 기존 1..64 ASCII 식별자다. 배열별 최대 32개이며 id가 중복되면 안 된다.
  기록은 id, text, evidence를 담고 lessons는 review도 필요하다. recipients는 중복 없는
  한 줄 label 1..16개다. all은 모든 수신자와 맞는다.
- 교훈 검토는 정확히 `{status:"proposed"}` 또는
  `{status:"accepted"|"rejected",by:ACTOR,at:TIME,reason:TEXT}`다. process도 accepted를
  선언할 수 있으며 인증된 승인 절차가 아니다. 결정 변경은 새 리비전으로 기록한다.
- evidence는 최대 8개 `{resource,sha256?}`다. resource는 자격 증명 없는 HTTP(S) URL 또는
  안전한 `/번들/경로`다. 경로 이탈, 앱·영수증·잠금·stage 경로는 거부한다. 참조는 열거나
  접속하지 않는다. evidence 해시는 미검사 선언이며 결과 상위 sha256은 읽은 리비전의 실제
  바이트 해시다. 빈 evidence는 근거를 기록하지 않았다는 뜻이다.
- text/reason은 UTF-8 1024바이트, label/actor는 64, resource는 2048까지다. 쓰면서 자르지 않는다.
  새 actor는 human:ID, process:ID, PRODUCER/VERSION 형식이며 신원을 인증하지 않는다.
- 입력 파일과 저장된 확장 루트는 각각 262144바이트, envelope를 포함한 섹션은 JSON 호환
  UTF-8 기준 65536바이트다. 소유 트리는 깊이 8, 매핑 키를 포함한 방문 값 4096개까지다.
  순환이나 JSON 비호환 값은 소유 루트 안에서 거부한다. 원문·본문 한도와 별개다.

`context`는 `--scope ID`를 반복해서 정확한 허용 목록을 지정한다. 생략하면 인덱스의 현재
노트를 선택한다. 없는 요청 ID는 not_found이며 직접 API의 빈 scope는 아무것도 읽지 않는다.
과거 리비전이나 원문 내용은 읽지 않는다. recipient와 all을 비교하고 --since는 recorded_at의
포함 경계다. 기록 순간 내림차순, 동률은 경로순이다. --now는 평가 시각을 표시할 뿐 기한이나
교훈 상태를 만들어 내지 않는다. --limit 기본 50, 범위 1..100이다.

최대 노트 1000개, 노트 내용 67108864바이트, evidence 참조 10000개, 보존 진단 1000개다.
기존 파일별 한도도 적용한다. 읽기 실패는 허용량 전체를 보수적으로 비용 처리하며 실제 읽은
크기를 알 수 없으면 read_bytes는 null이다. 크기 초과 확인에는 실패당 추가 1바이트를 읽을 수
있다. index 읽기에는 별도 기존 한도가 적용된다. 전체 RAM이나 실행 시간을 보장하지 않는다.

scan.complete, analysis_complete, output_complete, partial, omitted를 확인한다. 읽기 실패,
잘못된 노트·소유 확장, 미지원 섹션은 진단한다. 범위나 분석이 불완전하면 matched_total은
null이고 실제 확인한 일치 수는 matched_observed다. 미지원 가져온 섹션 때문에 기존
show/check의 동작이나 검증 범위가 바뀌지는 않는다.

JSON 문법·escape·마지막 줄바꿈을 포함한 성공 stdout 전체를 --max-chars로 제한한다.
기본 12000, 범위 2048..1000000 Unicode 코드 포인트다. 맞지 않으면 기록/진단을 통째로
생략하며 ID·경로·해시·근거를 몰래 자르지 않는다. limit 생략도 output_complete=false다.
scope는 긴 ID 목록 대신 요청 수와 목록 해시를 담는다. 처음/마지막 index가 다르면 partial로
표시한다. 같아도 파일시스템 스냅샷이나 외부 편집 부재를 증명하지 않는다. 읽기는 잠금 파일,
커서, 로그나 캐시를 만들지 않는다. 유효한 부분 보고서는 종료 0, 인자·index·루트의 치명적
오류는 기존 error-format 규칙으로 종료 2다.

알려진 relations 스키마 오류는 진단하지만 유효한 context를 지우지 않는다. 루트의 전체 안전 한도는 유지한다.
