# 지식 상태 선언과 진단

[English](health.md) | **한국어**

`health BUNDLE [--scope ID ...] [--now TIME] [--verify-source ID ...] [--max-chars N]`은
수정 없이 구조적 권고를 보여 준다. 인덱스의 선택된 현재 노트를 한 번 읽고 그래프의
추출·해석 데이터를 재사용한다. 모델 호출, URL 접속, 복구·승격은 없다. 검토, 관측 시각,
현재 정보 포인터, 보존 바이트와 출처 분류를 구분한다.

curate의 선택적 annotations 또는 정확한 현재 대상의 annotate로 freshness/source_evidence를
쓴다. 기존 불변 리비전·verified 제거·해시·CAS·재실행·시각·사전 검증 규칙을 유지한다.
[영문 JSON 예시](health.md)는 섹션 데이터이며 curate는 version1 wrapper로 감싼다.

freshness는 observation(observed_at/evidence 필수), pointer(target/evidence 필수,
last_observed_at/recheck_after 선택), reference(evidence 필수)다. 새 시각은 명시적 오프셋,
소수초 최대6자리이며 UTC로 정규화한다. 오래된 관측은 그 날짜의 선언이며 거짓으로
판정하지 않는다. pointer는 명시한 recheck_after에만 재관측 기한이 되고 기존 stale_after는
별도 노트 기한이다. generated/verified/recorded/mtime으로 관측 시각을 대신하거나 암묵적
7일 정책을 만들지 않는다. reference도 검증·영구 유효를 뜻하지 않는다.

source_evidence는 최대32개의 resource/provenance_basis/retained_scope/rationale/evidence
항목이다. basis는 primary_record/direct_document/derived/unknown, 보존 범위는
complete/excerpt/locator_only/unknown이다. 모두 선언이며 사실 검증이나 등급이 아니다.
resource는 안전한 문서 상대 경로 정규화 또는 정확한 locator 일치로 note.sources와 연결한다.
새 입력의 미연결 항목은 intent 전에 거부하고, 가져온 항목은 진단한다. 상충하는 분류도
판정·순위 변경 없이 드러낸다. 원문과 provenance는 수정하지 않는다. 기존 입력/루트262144,
섹션65536바이트·깊이8·방문4096·별칭 확장 전 escape UTF-8 한도를 유지한다.

```sh
second-brain health BUNDLE --scope TASK_ID --now 2026-11-02T12:00:00Z
second-brain health BUNDLE --scope TASK_ID --verify-source memo --max-chars 12000
```

기본 읽기는 원문/sidecar를 열지 않는다. 명시한 verify-source 최대16개에 대해서만
sources/ID/content.raw와 provenance.json을 검사한다. nofollow/비차단·일반 파일 검사와
청크 해시를 쓰고 URL이나 다른 근거 경로를 열지 않는다. 검증 IO는 sidecar와 실패 중
읽은 바이트를 포함해128MiB다. 원문256MiB/sidecar8000000바이트의 파일별 한도도 적용한다.
남은 예산보다 큰 파일은 손상이 아닌 unchecked_budget, 파일 한도 초과는 unchecked_limit다.
누락·비일반/읽기 실패·잘못된 provenance를 구분한다.

중복 JSON 키, NaN/무한대, bool/음수 바이트 수, 다른 ID/잘못된 해시와 capture 구조는 거부한다.
기존의 일반 한 줄 actor, 불투명 문자열 locator와 예전 시각 정밀도는 허용한다. 새 annotation의
엄격한 actor/HTTP 규칙을 소급 적용하지 않는다. 원문 내용이나 긴 locator는 출력하지 않는다.
matched는 관측 바이트의 해시와 길이 일치일 뿐 인증이나 사실 확인이 아니다. 선언된 근거
해시는 명시적으로 검사한 출처와 정확히 연결될 때만 비교한다. 해시 불일치는 관측 결과이고,
검사 불능과 달리 그 자체로 불완전 스캔은 아니다.

현재 노트의 단일 패스는1000개/64MiB, 그래프 참조10000회/진단1000개다. 별도로 근거 참조와
보존 finding도 각각10000개까지다. 전체 RAM/시간 한도는 아니다. 기한·wanted·미분류·제한된
근거는 정상적인 진단 결과다. 읽기/스키마/예산 때문에 분석할 수 없는 경우와 구분한다.
모르는 전체 수는 null이다. 섹션 오류는 소비자별로 처리하고 루트 안전 검사는 전체에 적용한다.

severity/path/field/kind 순 finding은 실행하지 않는 권고다. wanted/필수 미인덱스/과거 pin/
범위 밖/깨진 현재 파일/미검사 원문을 구분하며 의미적 모순이나 물리적 부재를 단정하지 않는다.
index 변경도 표시하지만 파일시스템 스냅샷은 아니다. JSON·escape·마지막 줄바꿈을 포함해
max-chars 기본12000, 범위2048..1000000 코드 포인트다. 맞지 않는 항목은 통째로 생략하고
ID/해시를 자르지 않는다. 유효한 진단은 종료0, 치명적 입력/index/루트 오류는 기존 형식의
종료2다. 잠금·커서·캐시·로그·규칙을 만들지 않는다. 기존 명령과 다음 평가 기능의 범위는 유지한다.
