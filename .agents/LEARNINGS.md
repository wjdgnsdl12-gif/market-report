# 에이전트 영구 학습 메모리 (LEARNINGS.md)

본 파일은 에이전트가 본 프로젝트(`market-report`)를 개발하며 습득한 환경 설정, 버그 트러블슈팅 이력, 사용자 코딩 스타일 선호도를 누적 기록하여 후속 태스크 수행 시 실수를 방지하고 코딩 완성도를 높이기 위해 참조하는 메모리입니다.

---

## 1. 프로젝트 고유 설정 및 지식
* **프로젝트 성격**: Yahoo Finance API(`yfinance`)와 Google Gemini API를 활용하여 시장 지표를 수집하고 AI 분석 코멘트를 생성한 뒤, 모바일용 정적 HTML(`public/index.html`)을 생성하는 프로젝트입니다.
* **로컬 빌드 검증**: `python report.py` 명령어로 전체 빌드 검증이 가능합니다. `GEMINI_API_KEY`가 로컬 환경 변수에 없더라도 에러 없이 템플릿 빌드 자체는 진행됩니다.

## 2. 트러블슈팅 및 꿀팁 (Troubleshooting Log)
* **2026-07-03 | Claude Code 스타일 자동화 적용**:
  * 에이전트의 자동 승인 룰을 정의하기 위해 `.agents/AGENTS.md`, `GEMINI.md`, `CLAUDE.md`를 프로젝트 루트에 구축하였습니다.
  * 빌드가 성공하면 지체 없이 자동으로 `git add/commit/push`를 실행하여 릴리즈를 완결합니다.

## 3. 사용자 코딩 스타일 & 선호도 (User Style Preferences)
* **한국어 대응**: 모든 답변과 아티팩트(`implementation_plan.md`, `task.md`, `walkthrough.md` 등)는 100% 한국어로만 기록해야 합니다.
* **자율성 극대화**: 에러나 빌드 오류가 있을 때 스스로 검증 루프를 돌아 디버깅을 완료한 뒤 보고합니다.
