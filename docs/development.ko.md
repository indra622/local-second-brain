# 개발과 검증

[English](development.md) | **한국어**

```sh
python -m unittest discover -s tests -v
python -m compileall -q src tests examples
python -m pip check
```

`python tests/verify_quickstart.py`는 각 README와 연결된 다음 단계 안내의 셸 블록을 임시 프로젝트 복사본과 새 venv에서 그대로 실행한다.
검증은 임시 소스 복사본에서 시작하며 GitHub 복제 자체는 검사하지 않는다.
이 소스 작업 절차는 의도적으로 체크아웃의 예제를 사용한다. 검증 항목은 설치, 원문 바이트 보존, 이전 버전 유지, 문서의 열람 명령과 별도 재사용 예제 결과다.

Obsidian 화면 절차는 공식 도움말 기준이며 실제 GUI 조작은 독립 검증하지 않았다.

체크아웃에서 `python scripts/verify_wheel.py`를 실행하면 `pip wheel`로 프로젝트 wheel을
빌드하고, 시스템 패키지를 포함하지 않는 새 venv에 wheel과 의존성을 설치한다.
체크아웃 밖에서 `PYTHONPATH`를 비운 채 패키지가 해당 venv에서 import되는지 확인하고,
init, capture, curate, search, check, review와 네 가지 열람 명령을 실행한다.
원문과 이전 리비전의 바이트 보존도 확인한다. 입력은 체크아웃 예제와 별개로 만든 합성
임시 파일이며 HOME과 pip 캐시 쓰기는 임시 디렉터리 안에 둔다. 설치 시 빌드 도구와
의존성을 다운로드할 수 있지만 CLI는 실행 중 외부 API를 호출하지 않는다.
종료 시 임시 검사 결과를 삭제하며 패키지를 배포하지 않는다.

[CI](../.github/workflows/ci.yml)는 pull request와 `main` push에 실행하도록 설정했다.
`macos-latest`, `ubuntu-latest`에서 각각 Python 3.11과 3.14를 사용한다.
네 작업 모두 전체 unittest와 wheel 검사를 실행하며, 두 README 소스 작업 절차는
macOS/Python 3.14에서만 실행한다. 권한은 contents 읽기 전용이며 공식 액션을 커밋 SHA로
고정하고 체크아웃 인증 정보를 유지하지 않는다. 예약 실행이나 자동 배포는 없다.

이번 문서 재구성 이전의 macOS/Python 3.14.6 로컬 검증에서 단위 테스트 50개, 독립 wheel 검사, 두 README 작업 절차,
컴파일과 `pip check`가 통과했다.
[실제 Actions 실행 40599790644](https://github.com/indra622/local-second-brain/actions/runs/40599790644)도
macOS/Ubuntu와 Python 3.11/3.14의 네 작업 모두 통과했다. 두 README의 전체 실행은
macOS/Python 3.14 작업에서 통과했다. 해당 호스팅 환경의 검증이며 모든 Linux 배포판이나
Obsidian GUI 동작을 검증했다는 뜻은 아니다.

## 2026-10-28 문서 검증

이번 재구성 후 macOS와 Python 3.14.6에서 단위 테스트 50개가 모두 통과했다.
각 README와 다음 단계 안내를 별도의 새 가상환경에서 실행했고 정원 노트의
세 리비전과 합성 재사용 검사를 통과했다. `src`, `tests`, `examples`, `scripts`의
컴파일, `pip check`, 상대 링크와 제목 검사도 통과했다.
이 프로젝트에는 별도 lint나 typecheck 명령이 설정되어 있지 않다.
검증기는 로컬 소스 복사본을 쓰므로 Git 복제 단계 자체는 검사하지 않는다.

이번 문서와 검증기 변경에서는 wheel 검사를 다시 실행하지 않았다.
위 wheel 결과는 이전 검증 기록이다. 패키지 설정과 CLI 코드는 바꾸지 않았다.
[공개 자료 검증 기록](field-validation.md)에 별도 Codex 실행과 Obsidian GUI
접근 실패를 적었다.

## 유지보수 정책

작은 라이브러리와 CLI 규모에 맞게 유지보수한다. 지원 런타임 의존성 범위는
`PyYAML>=6.0,<7`이며 빌드 요구사항도 `pyproject.toml`에 선언되어 있다.
프로젝트 lockfile은 없다. 모든 사용자를 한 개발 환경에 고정하기보다 라이브러리의
호환 범위를 유지한다. 반복 검증에는 소스 commit, Python과 의존성 버전, 명령과 결과를
기록한다. 향후 애플리케이션이나 릴리스 빌드는 이 호환 계약과 별개로 고정된 환경을
쓸 수 있다. `pip check`는 설치 의존성의 일관성 검사이며 재현 빌드 보장은 아니다.

lint와 typecheck 명령은 설정되어 있지 않다. Ruff가 이미 설치된 환경에서는 버전,
설정과 실제 진단을 기록한 뒤 수정 대상을 분류한다. 전역 도구를 암묵적으로 설치하거나
갱신하지 않으며 이전 리뷰의 진단 건수를 재현 결과로 쓰지 않는다. 서식 정리는 정확성
수정과 분리한다. 런타임 변경에는 위의 관련 검사를 쓰고 문서만 바꾸면 변경 링크와
영향받는 예제를 확인한다.

추적된 체크아웃 파일 크기와 Git 이력 또는 전송 크기는 구분해서 측정한다.
2026-11-06의 추적된 `site/` 파일 합계는 4,786,636 bytes이며, 그중 이미지와 영상
7개의 합계는 4,731,773 bytes다. 작업 트리 파일 크기이며 압축된 복제 비용은 아니다.
[자산 목록](../site/assets/README.md)에 적힌 승인된 양언어 영상, 재현 소스,
바이트 manifest와 공개 URL을 보존한다. 측정한 비용이 근거가 되고 URL 보존 계획이
있을 때만 다른 미디어 호스팅을 검토한다. 일반 정리 작업으로 이력을 재작성하거나
자산을 옮기지 않는다. 기존 공개 예제와 자산 계약은 `python scripts/showcase/verify.py`로 확인한다.

[파일 인터페이스](reference.ko.md#파일-인터페이스)에 호환 이름을 설명했다.
이름을 바꾸려면 import, 명령과 번들의 명시적인 이전 계획이 필요하다.
이름이 다르다는 사실만으로 런타임 결함이라고 보지 않는다.
