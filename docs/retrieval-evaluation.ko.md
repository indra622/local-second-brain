# 명시한 판단으로 검색 평가하기

[English](retrieval-evaluation.md) | **한국어**

`eval-retrieval`은 사용자가 정답 노트를 판단한 질문에서 recall이 실제로 전달한 결과를
평가한다. 라벨 생성·업로드·외부 엔진 실행·의미 검색은 없다. 작은 합성 점수로 실제 사용자
전반의 관련성 향상을 주장하지 않는다.

```sh
second-brain eval-retrieval BUNDLE --cases cases.json --mode auto:frequency --mode auto:bm25 --k 1 --k 3 --result-max-chars 12000 --max-chars 12000 --now 2026-11-02T12:00:00Z
```

[예시](../examples/retrieval-cases.json)는 관련 결정이 있는 task-report-pilot을 따로 만들었다는
가정이다. 자신의 번들에 맞게 명시적으로 판단해야 하며 기본 정답 집합이 아니다. --cases는
필수이고 개발용 benchmark 라벨을 자동으로 쓰지 않는다.

입력은 정확히 version=정수1, target_mode=current_id|exact_revision, cases다. case는 고유
ASCII id/query/gold를 담으며1..100개다. query는 단어가 있어야 하고 UTF-8 65536바이트까지다.
파일2MiB, 깊이8, 객체 키 포함 방문50000개 한도이며 중복 JSON 키·비유한 값·알 수 없는
필드·잘못된 UTF-8은 거부한다. 기존 recall의 검색어 한도는 바뀌지 않는다.

current_id 정답은 `{id:ID}`, exact_revision은 `{id:ID,revision:rNNNNNN,sha256?:HEX}`다.
최대32개이며 같은 대상 중복은 거부한다. 오래된 pin·다른 해시·없는/읽지 못한/범위 밖 정답은
이 실행에서 무효한 라벨이다. 누락을 일반 검색 실패로 숨기지 않는다. 빈 gold는
expect_no_match=true가 필요하고 별도 대조군이다. 라벨을 자동 수정하지 않는다.

인덱스와 선택된 현재 노트를 한 번씩 읽고 마지막 index를 비교한다. 반복 --scope는 정확한
허용 목록이며 생략하면 현재 전체, 직접 API의 빈 목록은 없음이다. 과거·원문·범위 밖 내용을
열지 않는다. 날짜/set/NaN/별칭과 잘못된 메타데이터도 기존 recall 규칙으로 처리하며 소유
확장/그래프 검증으로 걸러내지 않는다. 모든 모드·질문은 같은 시각과 캡처한 코퍼스를 쓰고
cases/index/경로-내용 manifest 해시를 남긴다. 부분 manifest는 관측한 읽기만 식별한다.
스냅샷·영구 캐시가 아니며 외부 동시 편집을 배제하지 못한다.

노트1000개/64MiB와 기존 파일 한도를 적용한다. 읽기 실패는 허용량을 보수적으로 비용
처리하며 실제 크기를 모르면 null이다. 읽지 못함·미지원 리비전·잘못된 UTF8·index 이동은
코퍼스 불완전이다. 메타데이터 오류만으로는 노트를 제거하지 않는다. 전체 RAM/시간 보장은
없다. per-note/두 단계 BM25를 유지하고 N×Q 행렬이나 모드×질문×문서 캐시는 만들지 않는다.

모드는 auto/exact/lexical × frequency/bm25 여섯 가지다. 기본 auto:frequency, k는1/3/5/10이고
1..100이다. limit=max(k), 명시한 result-max-chars(기본12000,2048..1000000)로 실제 전달된
결과를 평가한다. 출력 예산 때문에 빠진 결과와 horizon 밖/불일치 정답을 구분한다.

case Recall@k는 전달 top k의 고유 정답 수/판단한 전체 고유 정답 수다. macro는 라벨 case
평균이다. MRR@K는 K=max(k) 안 첫 정답 순위의 역수, 없으면0이며 horizon을 명시한다.
빈 gold 대조군은 관련성 분모에서 제외하고 matched=0 여부로 별도 정확도를 계산하므로
예산 때문에 출력이 빈 경우를 성공으로 세지 않는다. case별 순위·빠진 정답·fallback·제외·
생략 원인을 담는다. 첫 모드와 Recall@K, 다음 MRR@K 순으로 비교한다.

코퍼스 불완전·무효 라벨·case 실행 실패가 하나라도 있으면 모든 primary 집계는 null이다.
완료된 case 결과는 남기되 성공 부분집합 평균을 headline으로 내지 않는다. 대조군만 있는
집합은 관련성 집계가 null이고 정확도만 별도다.

계산 후 전체 JSON/escape/마지막 줄바꿈을 max-chars(기본12000,2048..1000000 코드 포인트)에
맞춘다. 모드 집계·진단·case를 통째로 생략할 수 있으며 수를 표시한다. 분모나 ID를 자르지
않는다. 큰 k/모드 행렬은 더 큰 예산으로 집계를 확인한다. 출력 생략과 분석 불완전은 별도다.
유효한 부분 보고서는 종료0, 치명적 입력/index/루트 오류는 기존 형식의 종료2다.

[작업별 워크플로](../templates/task-workflow.ko.md)를 참고한다. 기존 recall은 annotation
필드를 검색하지 않는다. 호스트 훅·스케줄러·전역 규칙·자동 복구는 설치하지 않는다.
