# 구조와 범위

`cli.py`는 명령의 인자, JSON 출력, 준비된 본문의 리비전 저장과 단어 검색을 맡는다.
`storage.py`는 번들 안의 파일 접근, 배타 잠금, 새 파일 생성, 인덱스 교체를 맡는다.
`format.py`는 PyYAML 기반 frontmatter 읽기, 문서화한 메타데이터 검사, 링크 경고와
오래됨 판정을 맡는다. 모델 런타임과 플러그인 계층은 없다.

에이전트가 원문을 읽고 준비 파일을 만드는 단계는 CLI 밖에 있다.
원문과 그 수집 기록은 `sources/<id>/`에, 개념은 `concepts/<id>/rNNNNNN.md`에 둔다.
이 배치는 이번 CLI의 로컬 저장 규칙이다. OKF 전체의 필수 디렉터리 규칙이 아니다.
일반 Markdown 상대 링크로 읽을 수 있으며, 검색과 검사는 다른 배치의 개념도 읽는다.
새 리비전을 쓰는 명령은 이 CLI가 만든 현재 링크 관리 구역이 있는 번들을 요구한다.

리비전 번호는 해당 ID의 기존 파일 중 가장 큰 번호 다음을 사용한다. 과거 파일은 고치지 않는다.
`curate`는 이전 `verified`, 상태, 기한이나 사용자 정의 메타데이터를 새 문서로 암묵적으로 복사하지 않는다.
`review`는 [검토 규칙](review-contract.md)에 따라 본문과 기존 메타데이터 값을 보존한 새 리비전에
검토 선언을 덧붙인다. 원래 생성 주체·시각과 상태도 유지한다.
각 리비전은 별개의 OKF 개념 경로다. 현재 리비전은 루트 인덱스의 링크로 표시하며,
과거 문서의 `status`를 자동으로 `deprecated`로 바꾸지 않는다.
검색은 과거 기록도 반환하고 `current`로 구분한다.

## 쓰기와 복구

`.lkw.lock`은 정확한 `lkw:flock:v1`+LF를 가진 영구 일반 파일이다. 비차단 native flock으로
협력 작성자를 배제하며 종료 시 descriptor만 닫는다. 기존 파일을 지우거나 다시 초기화하지 않는다.
구형/빈/부분/알 수 없는 표식은 flock 가용성과 관계없이 검사 필요로 거부한다. 구형 작성자와의
혼용/자동 이전은 없다. 보유 중 fork하지 않으며 상속 descriptor는 프로세스 종료 뒤 잠금을 유지할 수 있다.

수집은 새 출처 디렉터리를 먼저 확보하고 원문과 JSON을 만든다. 리비전 쓰기는 소유한 무작위 이름의
index stage를 배타 생성/동기화한 뒤 리비전을 생성한다. 인덱스와 stage 바이트/inode를 확인한 후
인덱스 한 파일을 os.replace하고 루트를 fsync한다. 정리 시 소유한 stage inode만 지우며 리비전은
삭제하지 않는다. rename 뒤 오류면 새 파일이 이미 현재일 수 있다. 고정/기존 임시 파일은 보존한다.

키가 있는 작업의 stage는 intent 뒤에서만 시작한다. 중단으로 부분 출처, stage, 미연결 리비전이나
현재 리비전과 미완료 요청이 남을 수 있다. 초기화된 유일 보유자 종료는 커널 잠금을 풀지만 데이터
완료를 증명하지 않는다. 읽기 전용 inspect-storage는 공유 잠금이 가능하면 유지하고, 아니면
best_effort로 표시한다. 정상 과거 기록을 orphan으로 단정하지 않는다. 자동 복구/삭제/재실행은 없다.

Persistent marked flock and owned staging provide cooperating-writer exclusion and one-index
replacement, not atomic revision/index/receipt visibility or power-loss recovery. Directory sync
of the index does not order all other directories. Inspection is bounded and read-only;
see the bilingual [reference](reference.md#storage-interruption-and-read-only-inspection) for
upgrade rules, limits, diagnostic states and inherited-descriptor caveats.

잠금은 이 CLI끼리 협력할 때만 유효하다. 편집기는 쓰기 명령과 동시에 실행하지 않는다.
검사와 검색도 쓰기 도중의 일관된 스냅샷을 보장하지 않는다. 적대적인 프로세스가
디렉터리나 hard link를 동시에 바꾸는 환경, 네트워크 파일시스템은 이번 지원 범위 밖이다.

## 경로 경계

번들과 명시한 입력 파일의 마지막 경로 요소에 대한 심볼릭 링크를 거부한다.
번들 내부는 디렉터리 descriptor를 기준으로 각 경로 요소를 `O_NOFOLLOW`로 연다.
스캔 중 심볼릭 링크나 일반 파일이 아닌 항목을 발견하면 중단한다.
ID는 제한된 ASCII 패턴만 허용하고 내부 파일 API는 절대 경로와 `..`를 거부한다.
본문의 번들 밖 링크는 열지 않고 경고로만 보고한다.

사용자가 지정한 번들과 입력 경로의 상위 디렉터리는 운영체제가 해석하는 신뢰 경계다.
시스템의 `/tmp` 같은 상위 별칭을 모두 금지하는 샌드박스는 아니다.
임의의 다른 로컬 파일을 읽는 기능은 없지만 명시한 입력은 번들 밖에 있어도 된다.
큰 원문도 메모리에 한 번에 읽으므로 크기 제한과 스트리밍은 후속 검토 대상이다.

POSIX 파일 API가 필요하다. 로컬 macOS와 호스팅된 macOS/Ubuntu CI에서 검증했으며 Windows에서는 실행하지 않았다.
Windows는 현재 지원하지 않는다. 이 프로젝트의 구현과 문서는 [MIT 라이선스](../LICENSE)를 따른다.
제3자 자료에는 각각의 라이선스가 적용된다. 패키지 배포는 후속 결정 사항이다.
