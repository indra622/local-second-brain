# 한 번의 실제 지식 정리 파일럿

[English](knowledge-practice-validation.md) | **한국어**

실제 두 네이티브 세션에서 문서 키트를 사용했다. A는 차례로 받은 가상 독서 성찰로 노트를
만들고 수정했다. 독립된 새 B는 저장된 Markdown/원문으로 나중 질문에 답하고 지식을 쓰지
않았다. 결정적 복사를 에이전트 행동으로 꾸민 것이 아니며 자동 기억/모든 호스트의 성공도 아니다.

## 실행과 권한

키트 출처 commit은 `84617d63a94d7959c2e7096a3ad4812b519fbc1b`, 검토 head는 b0a86bb다.
두 세션은 Codex Remote gpt-6.1-sol/medium, macOS26.6.2/Darwin/Python3.14.6/기존 CLI였다.
A `01a19c07-28c9-7bb0-aa0d-08b88c0b1d59`, B `01a19c11-6d5d-7242-9ef6-cb396efb7057`이며
[q0/s1–s4/r1 전체 turn ID](knowledge-practice-validation.md#run-identity-and-procedure)는 영문 표에 기록했다.

부모가 제품 전용 packet/사용자 프로필/격리된 빈 bundle을 준비하고 init했다.
[v1 요청/입력](../examples/knowledge-practice/README.md)을 A에 q0, s1–s4 순서로 한 번씩 공개했다.
rubric과 미래 입력은 주지 않았다. 새 B는 명시한 packet/profile/bundle/r1만 받았고 A 대화,
원래 inputs/prepared 폴더나 기존 writer 답변을 받지 않았다. bundle 안 보존 원문은 허용됐다.
같은 절차 재실행은 새 모델 실험이지 동일한 출력 보장이 아니다.

허용 범위는 공개 제품 지시, 공개된 가상 입력, 합성 bundle/prepared였다. 현재 OpenAI/Codex
Remote 제공자로 이 텍스트를 보내는 것이 승인됐다. explicit-only 저장, trigger off, profile
수정/개인 볼트/전역 설정/제공자 변경은 없었고 B는 답변만 요청받았다. 이 권한은 작업/에이전트
경계이지 OS sandbox가 아니다. 설치가 자동 기억을 만든 것이 아니라 진입 경로를 명시했다.

## 관측 결과

[정확한 산출물](../examples/knowledge-practice/observed-v1/README.md)은 미리 쓴 정답이나 설치
기본 지식이 아니다. 네 원문은 v1 해시와 같고 첫 BOM/CRLF도 보존했다. 단계별로 이전 원문/
리비전과 제품/profile 해시가 유지됐다. A의 첫 노트는 즉시 설명에 대한 유보를 남겼고 둘째는
관계의 이유를 설명했다. 책갈피 메모는 독립적이며 인용된 공격 문구는 데이터로 남았다.
네 번째 성찰은 첫 개념의 현재를 r000002로 바꾸되 r000001/원문을 보존했다. 현재 개념3개,
리비전4개이며 producer는 codex/portable-practice-pilot-v1, draft/unverified다.

q0 전후30파일, B 전후74파일 snapshot이 같다. B의 관측된 명령은 **cat 세 번**이며 packet/
profile/index와 저장된 과거/현재/원문을 읽었다. **CLI recall은 쓰지 않았다.** 그 유한한 로그에
A 대화나 원래 inputs/prepared 접근은 없다. 모든 IO를 전지적으로 보았거나 공격 방어를 증명한 것은 아니다.

[B의 실제 답](../examples/knowledge-practice/observed-v1/B-answer.md)은 초기 질문을 “즉시 설명
못하면 실패”라는 확정 규칙으로 강화하지 않고, 이후 읽는 목적에 따른 수정과 원문01/02/04를
구분했다. 허구/잠정성도 밝혔다. 정확한 문장과 근거를 직접 읽어야 하며 이 설명은 사람의
rubric 점수나 사실 검증이 아닌 관측이다.

## 평가와73 결정

기계적 무결성은 공개 manifest/snapshot으로 확인한다. 독립 gpt-6.1-sol AI 정성 평가는 완료된 별도 보고서에서 일곱 차원 모두 **2/2**다.
[정확한 점수/근거](../examples/knowledge-practice/observed-v1/AI-assessment.json)는 AI 판단이며 사람
판정이 아니다. 의미 충실도/귀속/유용한 연결/독립 대조/의미 있는 수정/새 세션 재사용/읽기 쉬움과
불확실성 각각2이고 관측 범위의 중대한 왜곡/실패는 찾지 못했다. 같은 모델 계열의 평가 편향은
남는다. 공식 사람 rubric 수용은 **관측하지 않았다**. 에이전트 자기평가나 CLI/바이트 검사가
그 판정을 대신하지 않는다. [평가 기준](../examples/knowledge-practice/v1/evaluator/rubric.md)은
bootstrap과 분리하고 첫 결과에 맞춰 완화하지 않는다.

이 실행에서는 막는 CLI 간극이 입증되지 않아73은 **런타임 변경 없음**으로 정리한다. A에는
기존 저장/버전/출처/index, B에는 일반 Markdown 탐색이 충분했다. B가 recall을 쓰지 않았으므로
회상 검색의 효과를 입증하지는 않는다. 다른 호스트/영문 입력/트리거/약한 지시 준수/사람 수용은
새 근거가 필요하며 추측한 프레임워크로 메우지 않는다. 평가에서 실제 왜곡이 나오면 첫 관측을
보존하고 부모가 조율해야 하며 산출물/rubric을 몰래 바꾸지 않는다.

## 공개 증거 한계

읽기 전용 부분집합은 정확한 노트4/원문4/index/B답이며 상대 링크가 열린다. 기계 경로나 불필요한
운영 세부가 있는 provenance/영수증/prepared요청/원시 nativeevents/profile은 제외했다. 생략 파일은
상대경로 해시 메타데이터만 남기며 완전 복원 가능한 쓰기 bundle이 아니다. 원시 로컬 증거는 repo 밖에 있다.

`python3 scripts/verify_knowledge_pilot.py`는 저장 해시/v1 원문/current/old/링크/snapshot 산술을
확인할 뿐 모델 재실행·인증·모든 IO·의미적 진실의 증명이 아니다. 공개 파일의 실제 문구/구두점/
바이트는 수정하지 않았다. 한 번의 한국어/같은 호스트·모델 관측은 일반 품질·보안·제공자·GUI
보장이나 human-reviewed 결과가 아니다.
