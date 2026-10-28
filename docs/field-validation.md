# 공개 자료로 실행한 Codex 검증

2026-10-28, macOS와 Python 3.14.6에서 Codex가 공식 Python 문서를 읽고
새 지식 폴더에 원문과 직접 작성한 노트를 저장했다. 이후 별도 질문에서 검색과
본문 열람으로 노트를 재사용했다. CLI는 글을 생성하지 않았으며 사람 검토나
인증된 검토를 기록하지 않았다. 이 결과는 한 번의 수동 에이전트 실행이며
자동 Codex 연동이나 다른 에이전트의 동작을 검증하지 않는다.

## 자료와 보존

[Python 3.14 pathlib 공식 문서](https://docs.python.org/3.14/library/pathlib.html)를
2026-10-28T07:20:22.972631+00:00에 가져왔다. HTML은 272,063바이트이며 SHA-256은
`1b3d89cafd8822dc15680ae0376139ad14453f9154a7148e490b804d40cefd5b`다.
전체 HTML, 응답 헤더, 수집 시각, 명령별 stdout/stderr, 해시, 원본 답변은
저장소 밖의 로컬 검증 로그에만 보관했다. 원문 전체와 기기별 경로는 커밋하지 않았다.
이는 해당 시점의 바이트 식별이며 현재 웹 문서와 같다는 보장은 아니다.

## 실제 실행과 결과

아래에서 `RUN`은 새 검증 폴더, `BUNDLE`은 그 안의 새 지식 폴더다.
`note-v1.md`는 Codex가 문서를 읽고 쓴 짧은 설명이며 미리 작성된 데모가 아니다.
명령은 설치된 `second-brain`으로 실행했고 모두 종료 코드 0이었다.

```text
second-brain init "$BUNDLE"
second-brain search "$BUNDLE" archive
second-brain capture "$BUNDLE" "$RUN/pathlib.html" --id python-pathlib --actor codex/field-validation --resource https://docs.python.org/3.14/library/pathlib.html
second-brain curate "$BUNDLE" archive-names --body "$RUN/note-v1.md" --source python-pathlib --actor codex/field-validation --title 'Archive naming with pathlib'
second-brain search "$BUNDLE" rename
second-brain search "$BUNDLE" archive --current-only
second-brain show "$BUNDLE" archive-names
```

초기 `archive` 검색은 빈 목록이었다. 저장 뒤 `rename` 검색도 빈 목록이었다.
본문에는 `renames`가 있지만 `rename`은 없었다. `archive`는 현재 노트 하나를 찾았다.
이는 정확한 단어 검색의 관측 결과이며 검색 구현을 바꾸지는 않았다.

노트는 `with_suffix`가 마지막 확장자만 바꾸므로 알려진 두 겹 확장자의 전체
파일명을 정하려면 `with_name`으로 이름을 명시하자는 설명이다.
별도 질문은 `exports/metrics.tar.gz`의 이웃 경로 `metrics.zip`을 파일 접근 없이
계획하는 것이었다. 저장된 `r000001`과 원문을 인용한 답변은
`PurePosixPath('exports/metrics.tar.gz').with_name('metrics.zip')`을 선택했다.
직접 Python으로 확인한 결과는 `exports/metrics.zip`이며 `with_suffix('.zip')`의
결과는 `exports/metrics.tar.zip`이었다. 입력 객체는 변하지 않았다.
경로 이름 계산일 뿐 파일 이름 변경이나 압축 형식 변환은 아니다.

이후 후속 질문의 설명을 `note-v2.md`에 덧붙여 다음을 실행했다.

```text
second-brain curate "$BUNDLE" archive-names --body "$RUN/note-v2.md" --source python-pathlib --actor codex/field-validation --title 'Archive naming with pathlib'
second-brain history "$BUNDLE" archive-names
second-brain search "$BUNDLE" archive --current-only
second-brain show "$BUNDLE" archive-names
second-brain check "$BUNDLE"
second-brain diff "$BUNDLE" archive-names r000001 r000002
```

`r000001`과 `r000002`의 현재 표시는 각각 false, true였다. 현재 검색은 두 번째
리비전 하나를 반환했다. 두 리비전 모두 `draft`, `unverified`이며 유효 기한이 없어
신선도는 알 수 없었다. `review`는 실행하지 않았다. `check`는
`invalid: []`, `warnings: []`, `stale: []`, `concepts: 2`를 반환했다.
형식 검사가 사실을 확인했다는 뜻은 아니다.

수정 전후 원문 해시는 위 HTML 해시와 같았다. 첫 리비전의 SHA-256도
`60bf4770452d96b488ac2306195921c04384b2447df54604ab27794e6a238b94`로 유지됐다.
로컬 비교는 수집 파일과 `content.raw`가 바이트 단위로 같음을 확인했다.

## Obsidian GUI 한계

공식 Remote Computer Use의 `cua.getApp("Obsidian")`과
`cua.getApp("md.obsidian")`가 모두
`Computer Use server error -10005: cgWindowNotFound`를 반환했다.
따라서 GUI의 인덱스 열기와 노트 링크 이동은 검증하지 못했다.
개인 vault를 열거나 설정과 권한을 바꾸지 않았고 스크린샷도 만들지 않았다.
CLI와 파일 검증 결과를 GUI 검증으로 해석하면 안 된다.

검색어 차이에 따른 빈 결과와 GUI 접근 실패가 이번에 관측한 한계다.
제품 결함으로 확인된 항목은 없으며 GUI 재검증은 창에 접근 가능한 환경이 필요하다.
[에이전트 안내](agent-kit.ko.md)에서 일반 절차와 합성 데모의 범위를 확인할 수 있다.
