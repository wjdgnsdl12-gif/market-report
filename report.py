"""글로벌 매크로 리포트 생성기.

파이프라인: 시장 데이터 수집(yfinance) → Gemini API 해석 → 반응형 HTML 페이지 생성.
GitHub Actions가 주기적으로 실행해 public/index.html 을 만들고 GitHub Pages로 배포한다.

환경변수:
  GEMINI_API_KEY      : Google AI Studio에서 발급한 Gemini API 키 (필수)
  OUTPUT_DIR (선택)   : 결과물 폴더. 기본값 "public"
  SEND_EMAIL (선택)   : "1"이면 아래 자격증명으로 이메일도 함께 발송(기본 미발송)
  GMAIL_USER / GMAIL_APP_PASSWORD / RECIPIENT : 이메일 병행 발송 시에만 필요
"""

import html as html_lib
import os
import smtplib
import ssl
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
import yfinance as yf

from config import CATEGORIES, GEMINI_MODEL, LIMITED_NOTE

# 한국어 Windows 콘솔(cp949)에서도 이모지 로그가 깨지지 않도록 stdout을 UTF-8로.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KST = timezone(timedelta(hours=9))

# 한국 투자자 관례에 맞춘 색상: 상승=빨강, 하락=파랑.
UP_COLOR = "#d60000"
DOWN_COLOR = "#0050d6"
FLAT_COLOR = "#666666"


# ──────────────────────────────────────────────────────────────
# 1) 데이터 수집
# ──────────────────────────────────────────────────────────────
# 각 기간의 "며칠 전 종가와 비교할지"(거래일 기준). 휴장일 때문에 달력과 미세하게 다름.
HORIZON_OFFSETS = {"d": 1, "w": 5, "m": 21}


def _closes_to_quote(closes):
    """종가 시계열(pandas Series)에서 현재값 + 일/주/월 변화를 계산."""
    n = len(closes)
    if n < 2:
        return None
    last = float(closes.iloc[-1])
    quote = {"price": last}
    for key, off in HORIZON_OFFSETS.items():
        if n > off:
            base = float(closes.iloc[-1 - off])
            chg = last - base
            quote[key] = {"chg": chg, "pct": (chg / base * 100) if base else 0.0}
        else:
            quote[key] = None  # 히스토리가 짧으면 해당 기간은 표시 안 함
    return quote


def fetch_quote(ticker):
    """티커 하나의 현재값과 일/주/월 변화를 반환. 실패 시 None.

    특수 티커 "SPREAD:A,B" 는 두 금리의 차(A-B) 시계열로 계산한다.
    """
    try:
        if ticker.startswith("SPREAD:"):
            a, b = ticker[len("SPREAD:"):].split(",")
            ha = yf.Ticker(a).history(period="3mo", interval="1d")["Close"].dropna()
            hb = yf.Ticker(b).history(period="3mo", interval="1d")["Close"].dropna()
            spread = (ha - hb).dropna()  # 공통 날짜만 남음
            return _closes_to_quote(spread)
        closes = yf.Ticker(ticker).history(period="3mo", interval="1d")["Close"].dropna()
        return _closes_to_quote(closes)
    except Exception as e:  # 네트워크/심볼 문제 등은 개별적으로 흡수하고 계속 진행
        print(f"[warn] {ticker} 조회 실패: {e}")
        return None


def collect():
    """설정된 모든 카테고리를 순회하며 시세를 모은다."""
    data = []
    for cat in CATEGORIES:
        rows = []
        for label, ticker in cat["items"]:
            rows.append({"label": label, "ticker": ticker, "quote": fetch_quote(ticker)})
        data.append({
            "name": cat["name"],
            "kind": cat["kind"],
            "source": cat.get("source", "Yahoo Finance"),
            "rows": rows,
        })
    return data


# ──────────────────────────────────────────────────────────────
# 2) 포맷 헬퍼
# ──────────────────────────────────────────────────────────────
# 막대그래프에서 "가득 참"으로 볼 변화 크기(캡). 이보다 크면 최대 길이로 표시.
BAR_CAP_PCT = 3.0    # 가격(일간): ±3%면 반쪽 막대가 가득
BAR_CAP_BP = 12.0    # 금리(일간): ±12bp면 가득
# 기간별 캡 배율(주간·월간은 변동폭이 크므로 캡을 키워 시각적으로 비교 가능하게)
BAR_SCALE = {"d": 1.0, "w": 2.2, "m": 4.0}


def _color_for(chg):
    if chg > 0:
        return UP_COLOR
    if chg < 0:
        return DOWN_COLOR
    return FLAT_COLOR


def _arrow(chg):
    return "▲" if chg > 0 else ("▼" if chg < 0 else "—")


def value_text(q, kind):
    """현재값 문자열."""
    if q is None:
        return "N/A"
    return f"{q['price']:.3f}%" if kind == "yield" else f"{q['price']:,.2f}"


def horizon_text(h, kind):
    """한 기간(일/주/월)의 (변화 문자열, 색상). h는 {'chg','pct'} 또는 None."""
    if not h:
        return ("–", FLAT_COLOR)
    chg = h["chg"]
    color = _color_for(chg)
    arrow = _arrow(chg)
    if kind == "yield":
        return (f"{arrow}{abs(chg * 100):.1f}bp", color)
    return (f"{arrow}{abs(h['pct']):.2f}%", color)


def bar_html(h, kind, horizon="d"):
    """변화를 중앙 0 기준의 좌우 발산형 flex 막대로. (CSS는 build_html에 정의)

    horizon(d/w/m)에 따라 캡을 다르게 적용해 기간별 변동폭을 시각적으로 비교한다.
    """
    if not h:
        return '<div class="track"><div class="half"></div><div class="cline"></div><div class="half"></div></div>'
    signed = h["chg"] * 100 if kind == "yield" else h["pct"]
    base = BAR_CAP_BP if kind == "yield" else BAR_CAP_PCT
    cap = base * BAR_SCALE.get(horizon, 1.0)
    w = round(min(1.0, abs(signed) / cap) * 100, 1) if cap else 0.0
    if signed >= 0:  # 중앙에서 오른쪽으로 성장
        left = '<div class="half"></div>'
        right = f'<div class="half"><div class="fill up" style="width:{w}%"></div></div>'
    else:            # 중앙에서 왼쪽으로 성장
        left = f'<div class="half r"><div class="fill down" style="width:{w}%"></div></div>'
        right = '<div class="half"></div>'
    return f'<div class="track">{left}<div class="cline"></div>{right}</div>'


# ──────────────────────────────────────────────────────────────
# 3) Gemini 해석
# ──────────────────────────────────────────────────────────────
def build_text_summary(data):
    """Gemini에 넘길 순수 텍스트 요약(일간/주간/월간 변화 포함)."""
    lines = []
    for cat in data:
        lines.append(f"[{cat['name']}]")
        for row in cat["rows"]:
            q = row["quote"]
            kind = cat["kind"]
            val = value_text(q, kind)
            d = horizon_text(q["d"] if q else None, kind)[0]
            w = horizon_text(q["w"] if q else None, kind)[0]
            m = horizon_text(q["m"] if q else None, kind)[0]
            lines.append(f"- {row['label']}: {val} (일간 {d} / 주간 {w} / 월간 {m})")
        lines.append("")
    return "\n".join(lines)


def gemini_commentary(summary_text, session_title):
    """시장 데이터를 근거로 투자관점 코멘트를 생성."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return "(GEMINI_API_KEY가 설정되지 않아 코멘트를 생성하지 못했습니다.)"

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )
    prompt = f"""당신은 글로벌 매크로 전략가입니다. 아래는 {session_title} 기준 주요 시장 데이터이며,
각 항목에 일간/주간/월간 변화가 함께 주어집니다. 한국인 투자자 관점에서 분석을 작성하세요.

반드시 아래 형식을 정확히 지키세요. 각 섹션은 '@@ 제목' 한 줄로 시작합니다.

@@ 시장 요약
2~3문장 문단. 일간뿐 아니라 주간·월간 추세도 함께 짚으세요.
@@ 섹터·자산군 함의
· 불릿 3~5개. 각 불릿은 1문장, '· '로 시작.
@@ 리스크·관전 포인트
· 불릿 2~4개. 각 불릿은 1문장, '· '로 시작.

작성 원칙:
- 데이터에 근거해 설명하고 과장하지 마세요.
- 특정 종목 매수/매도를 권유하지 말고, 참고용 분석임을 전제로 하세요.
- 가장 중요한 결론·키워드는 **별표 두 개**로 감싸 강조하세요. 예: **위험선호 회복**.
- 수치를 언급할 땐 +1.2%, -3bp 처럼 부호를 붙이세요.
- '@@', '· ', '**' 외의 마크다운 기호(#, 표 등)는 쓰지 마세요.

[시장 데이터]
{summary_text}
"""
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
    }
    try:
        r = requests.post(url, json=body, timeout=90)
        r.raise_for_status()
        j = r.json()
        return j["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        return f"(Gemini 코멘트 생성 실패: {e})"


# ──────────────────────────────────────────────────────────────
# 4) HTML 조립
# ──────────────────────────────────────────────────────────────
import re


def _num_color(m):
    """부호 있는 수치(+1.2% / -3bp)에 상승=빨강/하락=파랑 색."""
    s = m.group(0)
    cls = "dn" if s.startswith("-") else "up"
    return f'<b class="{cls}">{s}</b>'


def _inline(s):
    """한 조각 텍스트에 이스케이프 + 강조(**) + 등락 수치 색상 적용."""
    t = html_lib.escape(s)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"[+\-]\d+(?:\.\d+)?\s?(?:%p|%|bp)", _num_color, t)
    return t


def _accent(title):
    """섹션 제목 키워드로 아이콘·스타일 클래스 결정."""
    if any(k in title for k in ("리스크", "위험", "관전", "주의")):
        return ("⚠️", "risk")
    if any(k in title for k in ("함의", "섹터", "자산", "전략", "기회")):
        return ("💡", "idea")
    return ("📌", "sum")


def render_commentary(text):
    """Gemini 코멘트를 '@@ 제목' 구획 단위로 파싱해 위계 있는 카드로 렌더링.

    형식을 안 지켜도(제목 없이 문단/불릿만 와도) 깨지지 않도록 폴백 처리한다.
    """
    blocks = []
    cur = {"title": None, "icon": "🧭", "cls": "sum", "html": [], "bul": []}

    def flush_bullets():
        if cur["bul"]:
            lis = "".join(f"<li>{x}</li>" for x in cur["bul"])
            cur["html"].append(f'<ul class="cmt-ul">{lis}</ul>')
            cur["bul"] = []

    def push():
        flush_bullets()
        if cur["title"] or cur["html"]:
            blocks.append(dict(cur))

    for raw in text.split("\n"):
        s = raw.strip()
        if not s:
            flush_bullets()
            continue
        if s.startswith("@@"):
            push()
            title = s[2:].strip()
            icon, cls = _accent(title)
            cur = {"title": title, "icon": icon, "cls": cls, "html": [], "bul": []}
        elif s[0] in "·-•*▶":
            cur["bul"].append(_inline(s.lstrip("·-•*▶ ").strip()))
        else:
            flush_bullets()
            cur["html"].append(f'<p class="cmt-p">{_inline(s)}</p>')
    push()

    out = []
    for b in blocks:
        head = (
            f'<div class="cmt-h">{b["icon"]} {html_lib.escape(b["title"])}</div>'
            if b["title"] else ""
        )
        out.append(f'<div class="cmt-sec {b["cls"]}">{head}{"".join(b["html"])}</div>')
    return "".join(out)


def _metric_row(mark, h, kind, horizon):
    """일/주/월 한 줄: 라벨 + 막대 + 변화 수치."""
    txt, col = horizon_text(h, kind)
    bar = bar_html(h, kind, horizon)
    return (
        f'<div class="mrow"><span class="mk">{mark}</span>{bar}'
        f'<span class="chg" style="color:{col}">{txt}</span></div>'
    )


def render_item(row, kind):
    """항목 하나를 모바일 카드형 블록으로(일/주/월 각각 막대 포함)."""
    q = row["quote"]
    val = value_text(q, kind)
    qd = q["d"] if q else None
    qw = q["w"] if q else None
    qm = q["m"] if q else None
    return (
        '<div class="item">'
        '<div class="i-main">'
        f'<span class="i-label">{html_lib.escape(row["label"])}</span>'
        f'<span class="i-price">{val}</span>'
        '</div>'
        '<div class="i-rows">'
        f'{_metric_row("일", qd, kind, "d")}'
        f'{_metric_row("주", qw, kind, "w")}'
        f'{_metric_row("월", qm, kind, "m")}'
        '</div>'
        '</div>'
    )


def render_category(cat):
    kind = cat["kind"]
    source = cat.get("source", "Yahoo Finance")
    items = "".join(render_item(row, kind) for row in cat["rows"])
    return (
        '<section class="cat">'
        '<div class="cat-head">'
        f'<span class="cat-name">{html_lib.escape(cat["name"])}</span>'
        f'<span class="src">출처: {html_lib.escape(source)}</span>'
        '</div>'
        f'<div class="items">{items}</div>'
        '</section>'
    )


PAGE_CSS = """
:root{--up:#d60000;--dn:#0050d6;--flat:#888;--bg:#f2f3f5;--card:#fff;--ink:#1a1a1a;--sub:#6b7280;--line:#eceef1;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',-apple-system,Arial,sans-serif;
 -webkit-text-size-adjust:100%;}
.wrap{max-width:820px;margin:0 auto;padding:0 12px 40px;}
.hdr{position:sticky;top:0;z-index:5;background:#111;color:#fff;padding:16px 18px;
 border-radius:0 0 14px 14px;box-shadow:0 2px 10px rgba(0,0,0,.15);}
.hdr h1{font-size:17px;margin:0;font-weight:800;letter-spacing:-.3px;}
.hdr .sub{font-size:12px;opacity:.82;margin-top:3px;}
.hdr .upd{font-size:11px;opacity:.65;margin-top:2px;}
.card{background:var(--card);border-radius:14px;padding:16px 16px;margin-top:14px;
 box-shadow:0 1px 4px rgba(0,0,0,.05);}
.card h2{font-size:14px;margin:0 0 8px;font-weight:800;}
.comment{font-size:14px;color:#333;}
.comment strong{color:#000;font-weight:800;}
.comment .up{color:var(--up);} .comment .dn{color:var(--dn);}
.cmt-sec{padding:11px 13px;border-radius:10px;margin-top:10px;background:#f7f8fa;}
.cmt-sec:first-child{margin-top:0;}
.cmt-sec.sum{border-left:4px solid #2563eb;}
.cmt-sec.idea{border-left:4px solid #059669;}
.cmt-sec.risk{border-left:4px solid #d97706;background:#fff7ed;}
.cmt-h{font-weight:800;font-size:13.5px;margin-bottom:6px;letter-spacing:-.2px;}
.cmt-p{margin:0 0 6px;font-size:13.5px;line-height:1.72;}
.cmt-p:last-child{margin-bottom:0;}
.cmt-ul{margin:0;padding:0;list-style:none;}
.cmt-ul li{position:relative;padding-left:15px;margin:5px 0;font-size:13.5px;line-height:1.62;}
.cmt-ul li::before{content:"";position:absolute;left:2px;top:8px;width:5px;height:5px;
 border-radius:50%;background:#94a3b8;}
.cat{background:var(--card);border-radius:14px;margin-top:14px;overflow:hidden;
 box-shadow:0 1px 4px rgba(0,0,0,.05);}
.cat-head{display:flex;align-items:baseline;justify-content:space-between;gap:8px;
 padding:13px 16px 9px;border-bottom:2px solid #1a1a1a;}
.cat-name{font-size:15px;font-weight:800;}
.src{font-size:10.5px;color:#9aa0a6;text-align:right;flex:0 1 auto;}
.items{display:grid;grid-template-columns:1fr;}
.item{padding:9px 16px;border-bottom:1px solid var(--line);}
.i-main{display:flex;justify-content:space-between;align-items:baseline;gap:10px;}
.i-label{font-size:13.5px;font-weight:600;}
.i-price{font-size:14px;font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap;}
.i-rows{margin-top:5px;}
.mrow{display:flex;align-items:center;gap:8px;margin-top:3px;}
.mk{font-size:11px;color:#9aa0a6;width:13px;flex:0 0 auto;font-weight:700;}
.chg{font-size:12px;font-variant-numeric:tabular-nums;min-width:56px;}
.track{display:flex;align-items:center;width:100px;height:8px;flex:0 0 auto;}
.half{flex:1;display:flex;height:6px;}
.half.r{justify-content:flex-end;}
.fill{height:6px;border-radius:3px;}
.fill.up{background:var(--up);} .fill.down{background:var(--dn);}
.cline{width:2px;height:11px;background:#c4c4c4;flex:0 0 auto;}
.foot{font-size:11.5px;color:var(--sub);line-height:1.7;margin-top:16px;padding:0 6px;}
.foot b{color:#444;}
@media(min-width:640px){
 .items{grid-template-columns:1fr 1fr;}
 .item:nth-last-child(2):nth-child(odd){border-bottom:1px solid var(--line);}
 .item{border-right:1px solid var(--line);}
 .item:nth-child(even){border-right:none;}
}
"""


def build_html(data, commentary, now, session_title):
    sections = "".join(render_category(cat) for cat in data)
    commentary_html = render_commentary(commentary)
    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>글로벌 매크로 리포트</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<header class="hdr">
  <h1>🌐 글로벌 매크로 리포트</h1>
  <div class="sub">{html_lib.escape(session_title)}</div>
  <div class="upd">마지막 업데이트: {now:%Y-%m-%d %H:%M} KST</div>
</header>
<div class="wrap">

  <div class="card">
    <h2>🤖 Gemini 투자관점 코멘트</h2>
    <div class="comment">{commentary_html}</div>
  </div>

  {sections}

  <div class="foot">
    ※ 색상: <b style="color:{UP_COLOR}">빨강=상승</b> / <b style="color:{DOWN_COLOR}">파랑=하락</b>. 가격은 %, 금리는 bp.<br>
    ※ <b>일 / 주 / 월</b>은 각각 1·5·21 거래일 전 종가 대비 변화. '일' 옆 막대는 중앙 0 기준으로
    상승은 오른쪽(빨강)·하락은 왼쪽(파랑)으로 크기를 시각화한 것입니다.<br>
    ※ {html_lib.escape(LIMITED_NOTE)}<br>
    ※ <b>시세 출처</b>: Yahoo Finance (항목별 세부 출처는 각 섹션 헤더 표기 참고).<br>
    ※ <b>해석 출처</b>: Google Gemini ({GEMINI_MODEL}) — AI 생성 참고 분석이며 투자 권유가 아닙니다.
  </div>

</div>
</body></html>"""


# ──────────────────────────────────────────────────────────────
# 5) 이메일 발송
# ──────────────────────────────────────────────────────────────
def send_email(subject, html):
    user = os.environ["GMAIL_USER"]
    pw = os.environ["GMAIL_APP_PASSWORD"]
    recipients = [x.strip() for x in os.environ["RECIPIENT"].split(",") if x.strip()]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html", "utf-8"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
        s.login(user, pw)
        s.sendmail(user, recipients, msg.as_string())


# ──────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────
def main():
    now = datetime.now(KST)
    session = "🌅 아침 브리핑" if now.hour < 12 else "🌆 저녁 브리핑"
    session_title = f"{now:%Y-%m-%d (%a)} {session} · KST {now:%H:%M}"

    print(f"데이터 수집 시작... ({session_title})")
    data = collect()
    summary_text = build_text_summary(data)

    print("Gemini 코멘트 생성 중...")
    commentary = gemini_commentary(summary_text, session_title)

    html = build_html(data, commentary, now, session_title)

    # 정적 사이트 산출물: public/index.html (GitHub Pages가 이 폴더를 배포)
    out_dir = os.environ.get("OUTPUT_DIR", "public")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"생성 완료: {out_path}")

    # 이메일은 선택 사항(SEND_EMAIL=1 이고 자격증명이 있을 때만).
    if os.environ.get("SEND_EMAIL") == "1":
        subject = f"[매크로 리포트] {now:%m/%d} {session}"
        send_email(subject, html)
        print("이메일 발송 완료:", subject)


if __name__ == "__main__":
    main()
