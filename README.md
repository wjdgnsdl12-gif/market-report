# 글로벌 매크로 리포트 (모바일 웹)

주요국·신흥국 지수, 각국 섹터, 환율, 국채금리 커브, 신용·변동성, 원자재, 암호화폐를
수집하고 **Gemini API**로 투자관점 코멘트를 붙여 **모바일 반응형 웹페이지**로 보여줍니다.

서버 없이 **GitHub Actions**가 주기적으로 빌드해 **GitHub Pages**로 배포합니다(무료).
폰에서 URL만 열면 마지막 빌드 시점 기준의 리포트가 즉시 표시됩니다.

---

## 동작 구조

```
GitHub Actions (cron, 무료)
   └─ report.py
        ① yfinance 로 시세 수집 (일간·주간·월간 변동)
        ② Gemini API 로 투자 코멘트 생성
        ③ public/index.html 반응형 페이지 생성
   └─ upload-pages-artifact → deploy-pages (GitHub Pages 배포)
```

폰: Pages URL을 홈 화면에 추가하면 앱처럼 사용할 수 있습니다.

---

## 설치 순서

### 1. 저장소 만들기
이 `market-report` 폴더를 GitHub 저장소로 올립니다.

```bash
cd market-report
git init
git add .
git commit -m "init macro report"
git branch -M main
git remote add origin https://github.com/<본인계정>/<저장소>.git
git push -u origin main
```

> **공개/비공개 참고**: GitHub Pages 무료 배포는 **공개(Public) 저장소**에서 가장 간단합니다.
> 배포되는 페이지에는 API 키가 들어가지 않고 시장 데이터·AI 코멘트만 담기므로 민감정보는 없지만,
> URL을 아는 사람은 볼 수 있습니다. 완전 비공개가 필요하면 아래 "대안: Vercel" 참고.

### 2. Gemini API 키를 Secret으로 등록
저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| 이름 | 값 |
|------|-----|
| `GEMINI_API_KEY` | Google AI Studio에서 발급한 Gemini API 키 |

### 3. GitHub Pages 활성화
저장소 → **Settings** → **Pages** → **Build and deployment** → **Source** 를
**GitHub Actions** 로 설정합니다. (브랜치 방식 아님)

### 4. 첫 배포
- 저장소 → **Actions** → **Build & Deploy Report** → **Run workflow** 로 수동 실행.
- 완료되면 Actions 로그의 deploy 단계 또는 **Settings → Pages** 상단에 뜨는 URL로 접속합니다.
- 이후에는 cron 스케줄에 따라 자동 갱신됩니다.

---

## 갱신 주기
`.github/workflows/deploy-pages.yml` 의 cron으로 제어합니다. (cron은 **UTC** 기준)

기본값은 **2시간 간격**(`0 */2 * * *`)입니다. 더 자주/덜 자주 원하면 이 값만 바꾸세요.
예) 평일 30분 간격: `*/30 * * * 1-5`

> 참고: GitHub Actions 예약 실행은 러너 부하에 따라 수 분~수십 분 지연될 수 있습니다(무료 정책).
> "지금 이 순간" 값이 꼭 필요하면 Actions 탭에서 **Run workflow**로 즉시 갱신하거나, 아래 Vercel 온디맨드를 고려하세요.

---

## 로컬 미리보기
```bash
pip install -r requirements.txt

# Windows PowerShell
$env:GEMINI_API_KEY="발급받은키"; python report.py

# macOS / Linux
GEMINI_API_KEY=발급받은키 python report.py
```
`public/index.html` 이 생성됩니다. 브라우저로 열어 확인하세요.
(키 없이 실행하면 시세·레이아웃은 정상이고 코멘트 자리에 안내문이 들어갑니다.)

---

## 모니터링 항목 바꾸기
`config.py` 의 `CATEGORIES` 만 편집하면 됩니다.
- `kind="price"`: 지수/가격 (변화 %)
- `kind="yield"`: 금리 (변화 bp)
- 특수 티커 `SPREAD:A,B` : 두 금리의 차(A-B) 계산 (예: 10Y-3M 스프레드)
- 티커는 [Yahoo Finance](https://finance.yahoo.com) 심볼을 사용합니다.

---

## 화면 구성과 표기
- **일 / 주 / 월** = 각각 1·5·21 거래일 전 종가 대비 변화. 각 줄에 **좌우 발산형 막대**로 크기를 시각화(중앙 0 기준, 상승=오른쪽 빨강 / 하락=왼쪽 파랑).
- 색상: 한국 관례로 **빨강=상승, 파랑=하락**.
- 각 섹션 헤더 우측에 **데이터 출처**를 표기. 코멘트는 Gemini 생성분으로 별도 명시.
- 화면 폭에 따라 **1열(폰) ↔ 2열(데스크톱)** 로 자동 전환.

---

## 현재 범위와 제한

**무료로 매일 안정적 커버:** 주요국·신흥국 지수, 미국/한국/유럽/일본/중국 섹터(대표 ETF 프록시),
M7 개별주, 환율(주요+신흥국), 미국채 커브(3M·5Y·10Y·30Y)+10Y-3M 스프레드, 신용·변동성(HYG·LQD·TLT·MOVE·VIX),
원자재(원유·가스·금·은·구리·백금·팔라듐·알루미늄·곡물), 암호화폐.

**대체·제외 항목:**
- **한·일 국채금리**: 무료로는 '금리'가 없어 **국채 ETF '가격'**으로 대체(가격↑=금리↓, 별도 섹션에 명시).
- **니켈**: LME 상장이라 Yahoo 무료 데이터 없음 → **알루미늄**으로 대체.
- **독일 등 기타국 국채금리(일별), 선물 미결제약정, 옵션 내재변동성**: 무료·무키로는 안정적 일별 확보 어려워 제외.

### 확장 가이드
- 해외 국채금리(일별)나 선물/옵션 심화가 꼭 필요하면 유료/외부 API 연동이 필요합니다.
  `fetch_quote`(report.py)에 소스별 분기를 추가하는 구조로 확장하세요.

---

## 대안: Vercel(비공개/온디맨드)
- **비공개**가 필요하면 비공개 저장소 + Vercel 정적 배포로 URL을 감출 수 있습니다.
- **열 때마다 실시간 페치**를 원하면 Vercel 서버리스 함수로 전환할 수 있으나, 100+ 티커 실시간
  수집은 무료 함수 실행시간 제한에 걸리기 쉬워 **티커 축소 + 캐시(5~15분)** 설계가 필요합니다.
- 필요 시 이 구조로의 전환을 별도로 도와드릴 수 있습니다.

---

## 이메일로도 받고 싶다면 (선택)
`report.py`는 `SEND_EMAIL=1` 환경변수가 있으면 같은 리포트를 이메일로도 보냅니다.
`GMAIL_USER`, `GMAIL_APP_PASSWORD`(2단계 인증 후 앱 비밀번호), `RECIPIENT` Secret을 추가하고
워크플로우의 build 단계 env에 이들을 넘기면 됩니다. 단, 확장된 리포트는 용량이 커
Gmail에서 잘릴 수 있으니 항목을 줄이거나 웹 링크를 함께 보내는 방식을 권장합니다.
