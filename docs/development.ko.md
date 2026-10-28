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
