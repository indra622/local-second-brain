# 선언된 지식 그래프

[English](graph.md) | **한국어**

`graph`는 현재 인덱스의 노트 사이에 선언된 관계와 지원되는 Markdown/출처 링크를 보여 준다.
역링크와 방향이 있는 경로로 연결 근거를 확인할 수 있다. 사실 검증, 의미적 모순 탐지나
recall 순위 변경은 하지 않으며 참조를 접속·실행하거나 지시로 승격하지 않는다.

## 관계 작성

`curate --annotations FILE`은 context, relations 또는 둘 다 받는다.
[작은 입력 예시](../examples/graph-relations.json)는 decision 같은 별도 주체에서 reference를
참조하는 경우다. annotate 입력은 wrapper 없이 다음 데이터만 담는다.

```json
{"items":[{"id":"basis","type":"depends_on","target":{"id":"reference"},"expectation":"required","evidence":[]}]}
```

curate 입력에서는 이 값을 `{"version":1,"relations":RELATIONS_DATA}`로 감싼다.

```sh
second-brain --error-format json annotate BUNDLE decision --revision r000001 --section relations --file relations-section.json --actor process:worker --request-id NEW_ID
second-brain graph BUNDLE --scope decision --scope reference
second-brain graph BUNDLE --backlinks reference --relation depends_on
second-brain graph BUNDLE --path decision reference --max-depth 3 --max-chars 12000
```

기존 불변 리비전·현재 대상·원본/입력 해시·시각·영수증·CAS 규칙을 재사용한다. 완료된
재실행은 오래된 현재 조건보다 먼저 원래 결과를 반환한다. 같은 바이트의 다른 파일 이름은
재실행되고 바이트 변경은 충돌한다. 암묵 시각은 식별값에 들어가지 않는다. 새 annotate는
본문·다른 메타데이터를 보존하고 새 리비전의 상속 verified만 제거한다. 대상이나 역방향
관계를 쓰지 않는다. 원래 리비전은 보존한다.

항목은 최대 128개이며 각각 id, type, target, expectation, evidence만 담는다. id는 기존
ASCII 식별자이며 섹션 안에서 중복되면 안 된다. type은 relates_to, depends_on, supersedes,
contradicts, supports다. contradicts를 포함해 모두 호출자의 선언이며 인증이나 사실 확인이
아니다. target은 현재 포인터 `{id:ID}` 또는 고정 `{id:ID,revision:rNNNNNN}`다.
expectation은 required/wanted이고 wanted는 리비전 없는 대상만 허용한다. 자기 개념 관계,
미지원 타입·대상과 중복 id는 intent 전에 거부한다. 근거는 기존 제한된 미검사 참조다.
입력/소유 루트 262144바이트, 저장 섹션 65536바이트, 깊이·방문·필드 한도를 유지하며
escape된 UTF-8 크기를 별칭 확장 전에 검사한다. annotations 생략 시 기존 payload와
메타데이터는 바뀌지 않는다.

## 읽기와 범위

scope는 정확한 인덱스 ID 허용 목록이며 생략하면 현재 노트를 선택한다. 경로 끝점도 선택
범위 안에 있어야 한다. 없는 scope ID는 not_found, 범위 밖 끝점은 invalid_input이다.
최대 리비전 추정, 과거 대체, 제목·별칭·위키링크 해석, 원문 읽기나 대상 파일 확인은 없다.
범위 밖 심볼릭 링크도 열지 않는다. context나 관계의 evidence가 자동으로 edge가 되지 않는다.

필터는 다섯 선언 타입과 파생 link/source를 받는다. markdown/sources 출처는 구분한다.
새 simple-inline-v1 파서는 공백·괄호가 없는 `[label](target)` 및 이미지 대상만 읽는다.
최대 3칸 들여쓴 백틱/물결표 fence에서 같은 문자·이상 길이와 뒤쪽 공백만 있는 닫힘까지
건너뛴다. 닫히지 않으면 나머지를 가린다. 같은 길이 백틱 run의 inline code도 줄바꿈을
포함해 제외한다. 대응하지 않는 run은 일반 문자다. 줄 번호 계산에는 파서 내부 복사본의 LF/CRLF/CR만 정규화하고 저장 본문은 바꾸지 않는다. fence 제거가 span 처리보다 먼저다.
백슬래시 escape 규칙, 들여쓴 코드, 참조형 링크, HTML, 중첩 링크, CommonMark 및 Obsidian
별칭 전체를 지원하지 않는다. 기존 check 파서는 바꾸지 않는다. 상대 경로는 기존 한 번
URL decode·정규화 규칙을 쓰며 fragment는 검사하지 않는다. URL은 접속하지 않는다.
안전하지 않은 앱·영수증·잠금 경로는 진단한다. 참조는 UTF-8 2048바이트까지이며 넘으면
자르지 않고 진단 후 제외한다.

읽은 현재 노트만 순회할 수 있다. resolved, out_of_scope, non_current_reference,
not_indexed, wanted_not_indexed, missing_indexed, unavailable_indexed, invalid_indexed,
unread_indexed를 구분한다. 과거 pin의 실제 존재를 단정하지 않고 not_indexed를 과거/가져온
노트의 부재로 해석하지 않는다. wanted는 명시한 작성 희망 목록이다. 현재가 생기면 정상
해석된다. 원문·파일·자유 출처 설명·URL은 unchecked_resource 말단 참조다. 인덱스가 가리킨
선택 파일이 실제 없으면 missing_indexed로 표시한다.

각 edge는 주체의 정확한 리비전·해시, 해석한 대상의 현재 경로·해시, 선언 주체·시각·근거
또는 Markdown 줄/출처 위치를 담는다. evidence 해시는 여전히 선언이다. 같은 주체·타입·출처·
대상·expectation만 묶고 횟수와 허용된 모든 근거 항목을 남긴다. 출처를 몰래 합치지 않는다.
큰 그룹은 출력 예산에 맞지 않으면 통째로 생략할 수 있다.

역링크는 쓰기 없이 들어오는 연결을 계산한다. 경로는 방향을 지킨 BFS이며 동률은 대상 경로·
타입·근거 순으로 결정한다. 깊이는 기본 3, 범위 1..8이고 --max-depth는 --path와 함께 쓴다.
완전한 그래프의 found만 이 구조 모델 안에서 최단 경로다. 불완전한 양성 결과는 found_partial,
없을 때는 완전하면 no_path_within_depth, 아니면 undetermined다. 읽을 수 있는 자기 노드의
0단계 경로도 허용한다. 순환은 사실적 모순의 증거가 아니다.

## 한도와 부분 결과

노트 최대 1000개, 노트 내용 67108864바이트, 추출 참조 10000회, 보존 진단 1000개다.
파일별 기존 한도도 유지한다. 실패한 읽기는 허용량을 보수적으로 비용 처리하고 실제 크기를
모르면 read_bytes=null이다. 크기 확인의 추가 바이트가 생길 수 있으며 전체 RAM/시간 한도가
아니다. unread_indexed는 missing과 다르다. 잘못된 참조도 허용 횟수에 포함한다.

알려진 섹션 오류는 그 섹션만 건너뛴다. 잘못된 relations가 유효한 context를 지우지 않고
반대도 같다. 진단은 현재 분석에 영향을 주는지 표시한다. 루트 버전·타입·깊이·방문·JSON
바이트 안전 한도는 전체에 적용된다. 쓰기는 후보 루트의 구현된 섹션을 모두 검증한다.
알 수 없는 가져온 섹션은 기존 한도 안에서 보존하고 해석하지 않으며 검사 시 불완전성을
알린다. 다음 이슈의 health/freshness/evaluation은 구현하지 않는다.

scan·analysis_complete·output_complete·partial·omitted와 관측/전체 수를 확인한다.
완전한 전체를 모르면 null이며 0을 만들지 않는다. 처음/마지막 index가 다르면 불완전하다.
같아도 파일시스템 스냅샷이 아니다. 읽기는 잠금·커서·로그·캐시를 만들지 않는다. 유효한
진단 보고서는 종료 0, 치명적 입력/index/루트 오류는 기존 error-format으로 종료 2다.

JSON 문법·escape·마지막 줄바꿈을 포함한 전체 출력이 --max-chars 안에 들어간다.
기본 12000, 범위 2048..1000000 Unicode 코드 포인트다. 경로 설명, 진단, edge, node 순으로
결정적 prefix를 효율적으로 고르고 식별자는 자르지 않는다. found여도 설명 전체가 생략될
수 있으며 path_state/path_length와 omitted.paths로 알린다. 세부 출력 생략은 계산한 수를
바꾸지 않는다. 기존 context 출력은 유지하고 캐시·의미 검색·속도 개선을 약속하지 않는다.
