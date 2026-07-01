"""모니터링 대상과 리포트 설정.

여기만 수정하면 리포트에 나오는 항목을 바꿀 수 있다.
- kind="price": 가격/지수. 변화는 % 로 표시.
- kind="yield": 금리(%). 변화는 bp(베이시스포인트)로 표시.
티커는 모두 Yahoo Finance 심볼 기준이며, 아래 목록은 3개월 히스토리 유효성 검증을 통과한 것들이다.
특수 티커 "SPREAD:A,B" 는 A와 B의 금리차(A-B)를 계산해 보여준다.
"""

# 사용할 Gemini 모델. 무료 티어에서 쓰기 좋은 최신 Flash 계열.
GEMINI_MODEL = "gemini-2.5-flash"

CATEGORIES = [
    {
        "name": "🌎 주요국 지수",
        "kind": "price",
        "source": "Yahoo Finance (각국 거래소 지수)",
        "items": [
            ("미국 S&P500", "^GSPC"),
            ("미국 나스닥", "^IXIC"),
            ("미국 다우존스", "^DJI"),
            ("미국 러셀2000", "^RUT"),
            ("한국 코스피", "^KS11"),
            ("한국 코스닥", "^KQ11"),
            ("일본 닛케이225", "^N225"),
            ("중국 상하이종합", "000001.SS"),
            ("중국 CSI300", "000300.SS"),
            ("홍콩 항셍", "^HSI"),
            ("유럽 유로스톡스50", "^STOXX50E"),
            ("독일 DAX", "^GDAXI"),
            ("영국 FTSE100", "^FTSE"),
            ("프랑스 CAC40", "^FCHI"),
        ],
    },
    {
        "name": "🌏 신흥국·아시아 지수",
        "kind": "price",
        "source": "Yahoo Finance (각국 거래소 지수)",
        "items": [
            ("인도 Nifty50", "^NSEI"),
            ("대만 가권", "^TWII"),
            ("인도네시아", "^JKSE"),
            ("태국 SET", "^SET.BK"),
            ("브라질 보베스파", "^BVSP"),
            ("멕시코 IPC", "^MXX"),
            ("캐나다 TSX", "^GSPTSE"),
        ],
    },
    {
        "name": "🏭 미국 섹터 (SPDR ETF)",
        "kind": "price",
        "source": "Yahoo Finance (NYSE Arca 상장 SPDR ETF)",
        "items": [
            ("기술 XLK", "XLK"),
            ("금융 XLF", "XLF"),
            ("헬스케어 XLV", "XLV"),
            ("에너지 XLE", "XLE"),
            ("임의소비재 XLY", "XLY"),
            ("필수소비재 XLP", "XLP"),
            ("산업재 XLI", "XLI"),
            ("소재 XLB", "XLB"),
            ("유틸리티 XLU", "XLU"),
            ("부동산 XLRE", "XLRE"),
            ("커뮤니케이션 XLC", "XLC"),
        ],
    },
    {
        "name": "🇰🇷 한국 섹터",
        "kind": "price",
        "source": "Yahoo Finance (KRX 상장 KODEX 섹터 ETF)",
        "items": [
            ("반도체", "091160.KS"),
            ("IT", "266370.KS"),
            ("은행", "091170.KS"),
            ("증권", "102970.KS"),
            ("자동차", "091180.KS"),
            ("2차전지", "305720.KS"),
            ("바이오", "244580.KS"),
            ("철강", "117680.KS"),
        ],
    },
    {
        "name": "🇪🇺 유럽 섹터",
        "kind": "price",
        "source": "Yahoo Finance (iShares STOXX Europe 600 섹터 ETF)",
        "items": [
            ("은행", "EXV1.DE"),
            ("기술", "EXV3.DE"),
            ("헬스케어", "EXV4.DE"),
            ("에너지", "EXH1.DE"),
            ("자동차", "EXV5.DE"),
            ("산업재", "EXH4.DE"),
            ("기초소재", "EXV6.DE"),
            ("유틸리티", "EXH9.DE"),
        ],
    },
    {
        "name": "🇯🇵 일본 섹터",
        "kind": "price",
        "source": "Yahoo Finance (NEXT FUNDS TOPIX-17 섹터 ETF)",
        "items": [
            ("전기·정밀", "1625.T"),
            ("자동차·수송기", "1622.T"),
            ("은행", "1631.T"),
            ("의약품", "1621.T"),
            ("정보통신", "1626.T"),
            ("기계", "1624.T"),
            ("상사·도매", "1629.T"),
            ("부동산", "1633.T"),
        ],
    },
    {
        "name": "🇨🇳 중국 섹터",
        "kind": "price",
        "source": "Yahoo Finance (중국 인터넷/섹터 ETF)",
        "items": [
            ("인터넷 KWEB", "KWEB"),
            ("기술 CQQQ", "CQQQ"),
            ("반도체", "512480.SS"),
            ("증권", "512880.SS"),
            ("은행", "512800.SS"),
        ],
    },
    {
        "name": "🚀 핵심 개별종목 (M7)",
        "kind": "price",
        "source": "Yahoo Finance (미국 상장 개별주)",
        "items": [
            ("엔비디아", "NVDA"),
            ("애플", "AAPL"),
            ("마이크로소프트", "MSFT"),
            ("알파벳(구글)", "GOOGL"),
            ("아마존", "AMZN"),
            ("메타", "META"),
            ("테슬라", "TSLA"),
        ],
    },
    {
        "name": "💱 환율",
        "kind": "price",
        "source": "Yahoo Finance (외환 스팟)",
        "items": [
            ("달러인덱스(DXY)", "DX-Y.NYB"),
            ("원/달러", "KRW=X"),
            ("엔/달러", "JPY=X"),
            ("유로/달러", "EURUSD=X"),
            ("위안/달러", "CNY=X"),
            ("인도루피/달러", "INR=X"),
            ("대만달러/달러", "TWD=X"),
            ("브라질헤알/달러", "BRL=X"),
            ("멕시코페소/달러", "MXN=X"),
        ],
    },
    {
        "name": "📈 국채금리 커브",
        "kind": "yield",
        "source": "Yahoo Finance / CBOE (미 국채 수익률 지수)",
        "items": [
            ("미국 3개월", "^IRX"),
            ("미국 5년", "^FVX"),
            ("미국 10년", "^TNX"),
            ("미국 30년", "^TYX"),
            ("10년-3개월 스프레드", "SPREAD:^TNX,^IRX"),
        ],
    },
    {
        # 한·일은 무료로 '금리'가 없어 국채 ETF '가격'으로 대체(가격↑ = 금리↓, 방향 반대).
        "name": "🏦 한·일 국채 ETF (가격 ↑=금리↓)",
        "kind": "price",
        "source": "Yahoo Finance (국채 ETF 가격 · 금리와 반대 방향)",
        "items": [
            ("한국 국고채10년", "148070.KS"),
            ("한국 국고채3년", "114260.KS"),
            ("일본 국채10년", "2510.T"),
        ],
    },
    {
        "name": "📊 신용·변동성",
        "kind": "price",
        "source": "Yahoo Finance (ICE·CBOE 지수/ETF)",
        "items": [
            ("하이일드 채권(HYG)", "HYG"),
            ("투자등급 채권(LQD)", "LQD"),
            ("미국 장기국채(TLT)", "TLT"),
            ("채권 변동성(MOVE)", "^MOVE"),
            ("주식 변동성(VIX)", "^VIX"),
        ],
    },
    {
        "name": "🛢️ 원자재",
        "kind": "price",
        "source": "Yahoo Finance (CME/ICE 근월물 선물)",
        "items": [
            ("WTI 원유", "CL=F"),
            ("브렌트유", "BZ=F"),
            ("천연가스", "NG=F"),
            ("금", "GC=F"),
            ("은", "SI=F"),
            ("구리", "HG=F"),
            ("백금", "PL=F"),
            ("팔라듐", "PA=F"),
            ("알루미늄", "ALI=F"),
            ("옥수수", "ZC=F"),
            ("밀", "ZW=F"),
        ],
    },
    {
        "name": "₿ 암호화폐",
        "kind": "price",
        "source": "Yahoo Finance (코인 USD 환산)",
        "items": [
            ("비트코인", "BTC-USD"),
            ("이더리움", "ETH-USD"),
            ("솔라나", "SOL-USD"),
            ("리플(XRP)", "XRP-USD"),
        ],
    },
]

# 무료·무키로는 일별 확보가 어려워 이번 범위에서 제외한 항목(리포트 하단에 안내로 표기).
LIMITED_NOTE = (
    "한국·일본·독일 등 해외 국채금리(일별)와 선물 미결제약정·옵션 내재변동성은 "
    "무료·무API키 소스로 안정적 일별 확보가 어려워 제외했습니다. "
    "미국채 커브·10Y-3M 스프레드·MOVE(채권변동성)·VIX(주식변동성)를 금리·위험 대리지표로 활용하세요."
)
