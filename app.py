"""
통신 가입 비교 사이트 크롤러
- Playwright 3단계 클릭 → 요금/사은품 추출 → 구글 시트 append
- 아정당: 통신사 × 인터넷 × TV 전 조합 자동 크롤링
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import Page, sync_playwright

# =============================================================================
# [설정 1] 구글 시트 / 인증
# =============================================================================
SPREADSHEET_NAME = "마케팅_크롤링_DB"
CREDENTIALS_FILE = (
    Path(__file__).parent / "site-monitoriing-project-c639a6c0fe66.json"
)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADERS = [
    "수집 일시",
    "타겟사이트명",
    "통신사명",
    "인터넷 상품명",
    "TV상품명",
    "기본 요금",
    "사은품 액수",
]

_PENDING_SHEET_ROWS: dict[int, dict[str, Any]] = {}

# =============================================================================
# [설정 2] 아정당 전체 크롤링 (KT / LGu+ / SK 만)
# - 통신사별 URL 로 직접 이동
# - 각 인터넷 상품: TV 결합 없음(단독) 1건 + TV 상품별 결합 건
# =============================================================================
AJD_SITE_NAME = "아정당"
AJD_TV_BUNDLE_LABEL = "TV와 함께"
AJD_CARRIER_ENTRIES: list[dict[str, str]] = [
    {"carrier": "KT", "url": "https://www.ajd.co.kr/internet/list/sys:product:internet:kt"},
    {
        "carrier": "LGu+",
        "url": "https://www.ajd.co.kr/internet/list/sys:product:internet:lg",
    },
    {"carrier": "SK", "url": "https://www.ajd.co.kr/internet/list/sys:product:internet:skt"},
]

# =============================================================================
# [설정 3] 기타 타겟 사이트 (최대 6개, url 비어 있으면 건너뜀)
# crawl_mode: "single" = 통신사/상품 1조합
# crawl_mode: "all" = 아정당 전체 조합
# crawl_mode: "miso_all" = MISO 전체 조합
# crawl_mode: "lguplus_all" = LGU+ 공식몰 지정 조합
# crawl_mode: "kt_all" = KT 공식몰 인터넷/인터넷+IPTV 지정 조합
# crawl_mode: "skb_all" = SKB 공식몰 인터넷/인터넷+TV 지정 조합
# crawl_mode: "skt_all" = SKT T다이렉트샵 요금계산기 지정 조합
# =============================================================================
TARGET_SITES: list[dict[str, Any]] = [
    {
        "url": "https://www.ajd.co.kr/internet/list/sys:product:internet:skt",
        "site_name": AJD_SITE_NAME,
        "sheet_name": "AJD",
        "crawl_mode": "all",
        "carrier_name": "",
        "internet_name": "",
        "tv_name": "",
        "selectors": {
            "carrier_tab": "",
            "internet_tab": "",
            "tv_tab": "",
            "result_panel": "",
            "base_fee": "",
            "gift_amount": "",
        },
    },
    {
        "url": "https://miso.kr/internet?use-auth=true",
        "site_name": "MISO",
        "sheet_name": "MISO",
        "crawl_mode": "miso_all",
        "carrier_name": "",
        "internet_name": "",
        "tv_name": "",
        "selectors": {
            "carrier_tab": "",
            "internet_tab": "",
            "tv_tab": "",
            "result_panel": "",
            "base_fee": "",
            "gift_amount": "",
        },
    },
    {
        "url": "https://www.lguplus.com/signup/internet?urcHmProdNoList=990001732",
        "site_name": "U+",
        "sheet_name": "U+",
        "crawl_mode": "lguplus_all",
        "carrier_name": "",
        "internet_name": "",
        "tv_name": "",
        "selectors": {
            "carrier_tab": "",
            "internet_tab": "",
            "tv_tab": "",
            "result_panel": "",
            "base_fee": "",
            "gift_amount": "",
        },
    },
    {
        "url": "https://shop.kt.com/wire/view.do?mainProdNo=WR00000263&altnDcYn=Y&phnCombDcYn=Y&Inchan=ktshop&Csnum=list&Cont=IS",
        "site_name": "KT",
        "sheet_name": "KT",
        "crawl_mode": "kt_all",
        "internet_url": "https://shop.kt.com/wire/view.do?mainProdNo=WR00000263&altnDcYn=Y&phnCombDcYn=Y&Inchan=ktshop&Csnum=list&Cont=IS",
        "iptv_url": "https://shop.kt.com/wire/view.do?mainProdNo=WR00000263&subProdNo=WR00076093&altnDcYn=Y&phnCombDcYn=Y&Inchan=ktshop&Csnum=yogolist&Cont=ITS",
        "carrier_name": "",
        "internet_name": "",
        "tv_name": "",
        "selectors": {
            "carrier_tab": "",
            "internet_tab": "",
            "tv_tab": "",
            "result_panel": "",
            "base_fee": "",
            "gift_amount": "",
        },
    },
    {
        "url": "https://www.bworld.co.kr/shop/join/new/prd.do?keepOn=Y&entryCd=07&referCd=02&utm_source=bshop_pc&utm_medium=gnb_selfrecom&utm_campaign=prdcard_favor2&utm_content=direct&utm_term=none&utm_check=01&inetJoinType=inetIPTV1&inetFeeProdId=NI00004324&inetDirect=N&tvFeeProdId=NT00000681&stbClCd=T0024&stbRemoteClCd=null&combLineGbnCd=01&mnvoLine=N&giftMgmtNum=1360091&inetAddMkProdId=null&inetAddMkProdId2=null",
        "site_name": "SKB",
        "sheet_name": "SKB",
        "crawl_mode": "skb_all",
        "internet_url": "https://www.bworld.co.kr/shop/join/new/internet/prd.do",
        "carrier_name": "",
        "internet_name": "",
        "tv_name": "",
        "selectors": {
            "carrier_tab": "",
            "internet_tab": "",
            "tv_tab": "",
            "result_panel": "",
            "base_fee": "",
            "gift_amount": "",
        },
    },
    {
        "url": "https://shop.tworld.co.kr/wire/main",
        "site_name": "SKT",
        "sheet_name": "SKT",
        "crawl_mode": "skt_all",
        "carrier_name": "",
        "internet_name": "",
        "tv_name": "",
        "selectors": {
            "carrier_tab": "",
            "internet_tab": "",
            "tv_tab": "",
            "result_panel": "",
            "base_fee": "",
            "gift_amount": "",
        },
    },
]

# 브라우저 설정
HEADLESS = False
PAGE_LOAD_TIMEOUT_MS = 60_000
CLICK_WAIT_SEC = 1.2
AFTER_CLICK_WAIT_SEC = 1.8
AJD_DEFAULT_SELECTORS = {
    "carrier_tab": "",
    "internet_tab": "",
    "tv_tab": "",
    "result_panel": "",
    "base_fee": "",
    "gift_amount": "",
}


def get_worksheet():
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"인증 파일이 없습니다: {CREDENTIALS_FILE}\n"
            "site-monitoriing-project-c639a6c0fe66.json 파일을 같은 폴더에 두세요."
        )
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_FILE), scopes=SCOPES
    )
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).sheet1


def get_worksheet_by_title(title: str):
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"인증 파일이 없습니다: {CREDENTIALS_FILE}\n"
            "site-monitoriing-project-c639a6c0fe66.json 파일을 같은 폴더에 두세요."
        )
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_FILE), scopes=SCOPES
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open(SPREADSHEET_NAME)
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=1000, cols=20)


def ensure_headers(worksheet) -> None:
    first_row = worksheet.row_values(1)
    if first_row != SHEET_HEADERS:
        if not any(cell.strip() for cell in first_row):
            worksheet.update(range_name="A1:G1", values=[SHEET_HEADERS])
        else:
            print(
                "참고: 1행에 이미 데이터가 있어 헤더를 자동 삽입하지 않았습니다. "
                f"헤더 형식: {SHEET_HEADERS}"
            )


def append_row(worksheet, row: list[str]) -> None:
    key = id(worksheet)
    if key not in _PENDING_SHEET_ROWS:
        _PENDING_SHEET_ROWS[key] = {"worksheet": worksheet, "rows": []}
    _PENDING_SHEET_ROWS[key]["rows"].append(row)
    print(f"  -> 시트 저장 대기: {row}")


def flush_worksheet_rows(worksheet) -> int:
    key = id(worksheet)
    pending = _PENDING_SHEET_ROWS.get(key)
    if not pending or not pending["rows"]:
        return 0

    rows = pending["rows"]
    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    print(f"  -> 시트 일괄 저장 완료: {len(rows)}건")
    pending["rows"] = []
    return len(rows)


def flush_all_pending_rows() -> int:
    total = 0
    for pending in list(_PENDING_SHEET_ROWS.values()):
        worksheet = pending["worksheet"]
        total += flush_worksheet_rows(worksheet)
    return total


def _scroll_to_form(page: Page) -> None:
    form = page.locator("#recommend-form, .recommend-form--inner").first
    if form.count():
        form.scroll_into_view_if_needed()
        time.sleep(0.3)


def _discover_products(page: Page) -> dict[str, list[tuple[int, str]]]:
    data = page.evaluate(
        """() => {
        const internet = [];
        document.querySelectorAll('.at-internet .recommend-option').forEach((el, idx) => {
            const t = (el.innerText || '').trim().split('\\n').filter(Boolean);
            if (t.length) internet.push({ idx, name: t[0] });
        });
        const tv = [];
        document.querySelectorAll('.at-tv .recommend-option').forEach((el, idx) => {
            const t = (el.innerText || '').trim().split('\\n').filter(Boolean);
            if (t.length) tv.push({ idx, name: t[1] || t[0] });
        });
        return { internet, tv };
    }"""
    )
    return {
        "internet": [(x["idx"], x["name"]) for x in data["internet"]],
        "tv": [(x["idx"], x["name"]) for x in data["tv"]],
    }


def _click_carrier_tab(page: Page, label: str) -> None:
    loc = page.locator(".at-operator .recommend-option").filter(has_text=label)
    loc.first.scroll_into_view_if_needed()
    loc.first.click(force=True, timeout=PAGE_LOAD_TIMEOUT_MS)
    time.sleep(AFTER_CLICK_WAIT_SEC)


def _goto_carrier_page(page: Page, entry: dict[str, str]) -> None:
    page.goto(entry["url"], wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
    time.sleep(CLICK_WAIT_SEC)
    _scroll_to_form(page)
    click_name = entry.get("click_carrier", "").strip()
    if click_name:
        _click_carrier_tab(page, click_name)


def _click_product_by_index(page: Page, section: str, index: int) -> None:
    loc = page.locator(f".at-{section} .recommend-option").nth(index)
    loc.scroll_into_view_if_needed()
    loc.click(force=True, timeout=PAGE_LOAD_TIMEOUT_MS)


def _is_tv_bundle_on(page: Page) -> bool:
    label = page.locator("label.check-box").filter(has_text=AJD_TV_BUNDLE_LABEL).first
    classes = (label.get_attribute("class") or "").split()
    return "on" in classes


def _set_tv_bundle(page: Page, enabled: bool) -> None:
    """TV와 함께 체크: 켜면 TV 결합, 끄면 인터넷 단독"""
    label = page.locator("label.check-box").filter(has_text=AJD_TV_BUNDLE_LABEL).first
    label.wait_for(state="visible", timeout=PAGE_LOAD_TIMEOUT_MS)
    is_on = _is_tv_bundle_on(page)
    if enabled and not is_on:
        label.click(force=True, timeout=PAGE_LOAD_TIMEOUT_MS)
        time.sleep(CLICK_WAIT_SEC)
    elif not enabled and is_on:
        label.click(force=True, timeout=PAGE_LOAD_TIMEOUT_MS)
        # TV 해제 후 요금 패널 갱신 대기 (LGu+ 등에서 필요)
        time.sleep(AFTER_CLICK_WAIT_SEC + 1.5)


def _save_combo(
    page: Page,
    worksheet,
    selectors: dict[str, str],
    collected_at: str,
    carrier: str,
    inet_name: str,
    tv_name: str,
) -> tuple[str, str]:
    panel_text = _wait_for_result(page, selectors)
    base_fee, gift_amount = _extract_text(page, panel_text, selectors)
    append_row(
        worksheet,
        [
            collected_at,
            AJD_SITE_NAME,
            carrier,
            inet_name,
            tv_name,
            base_fee,
            gift_amount,
        ],
    )
    return base_fee, gift_amount


def _wait_for_result(page: Page, selectors: dict[str, str]) -> str:
    panel_sel = selectors.get("result_panel", "").strip()
    panel = (
        page.locator(panel_sel).first
        if panel_sel
        else page.locator(".internet-list-total-pc").first
    )
    panel.wait_for(state="visible", timeout=PAGE_LOAD_TIMEOUT_MS)
    time.sleep(AFTER_CLICK_WAIT_SEC)
    return panel.inner_text()


def _parse_base_fee(panel_text: str) -> str:
    patterns = [
        r"기본\s*요금\s*([\d,]+)\s*원",
        r"전용요금\s*\n?\s*([\d,]+)\s*원",
        r"선납혜택\s*\n?\s*([\d,]+)\s*원",
    ]
    for pattern in patterns:
        m = re.search(pattern, panel_text)
        if m:
            return f"{m.group(1)}원"
    m = re.search(r"([\d,]+)\s*원", panel_text)
    return f"{m.group(1)}원" if m else ""


def _parse_gift_amount(panel_text: str) -> str:
    patterns = [
        r"사은품\s*([\d,]+만원|[\d,]+원)",
        r"([\d,]+만원)\s*\+\s*추가혜택",
        r"사은품\s*([\d,]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, panel_text)
        if m:
            value = m.group(1)
            return value if "만원" in value or "원" in value else f"{value}만원"
    return ""


def _extract_text(
    page: Page, panel_text: str, selectors: dict[str, str]
) -> tuple[str, str]:
    base_sel = selectors.get("base_fee", "").strip()
    gift_sel = selectors.get("gift_amount", "").strip()

    if base_sel:
        base_fee = page.locator(base_sel).first.inner_text().strip()
    else:
        base_fee = _parse_base_fee(panel_text)

    if gift_sel:
        gift_amount = page.locator(gift_sel).first.inner_text().strip()
    else:
        gift_amount = _parse_gift_amount(panel_text)

    return base_fee, gift_amount


def crawl_ajd_all(
    page: Page,
    worksheet,
    site: dict[str, Any],
    collected_at: str,
) -> tuple[int, int]:
    selectors = site.get("selectors", AJD_DEFAULT_SELECTORS)
    success = 0
    fail = 0
    total_planned = 0

    print(
        f"\n=== 아정당 전체 크롤링 시작 "
        f"({len(AJD_CARRIER_ENTRIES)}개 통신사: KT, LGu+, SK) ==="
    )

    for entry in AJD_CARRIER_ENTRIES:
        carrier = entry["carrier"]
        print(f"\n[통신사] {carrier} ({entry['url']})")
        try:
            _goto_carrier_page(page, entry)
            products = _discover_products(page)
            inet_list = products["internet"]
            tv_list = products["tv"]
            combos = len(inet_list) * (1 + len(tv_list))
            total_planned += combos
            print(
                f"  인터넷 {len(inet_list)}개 x (단독 1 + TV {len(tv_list)}개) "
                f"= {combos}조합"
            )

            if not inet_list:
                print("  [건너뜀] 인터넷 상품 없음")
                continue

            carrier_success = 0

            for inet_idx, inet_name in inet_list:
                # 1) 인터넷 단독 (TV와 함께 해제)
                try:
                    _click_product_by_index(page, "internet", inet_idx)
                    time.sleep(CLICK_WAIT_SEC)
                    _set_tv_bundle(page, enabled=False)
                    base_fee, gift_amount = _save_combo(
                        page,
                        worksheet,
                        selectors,
                        collected_at,
                        carrier,
                        inet_name,
                        "",
                    )
                    success += 1
                    carrier_success += 1
                    print(
                        f"  [{carrier_success}/{combos}] {inet_name} + (인터넷 단독) "
                        f"-> 요금 {base_fee or '(없음)'}, "
                        f"사은품 {gift_amount or '(없음)'}"
                    )
                except Exception as exc:
                    fail += 1
                    print(f"  [오류] {carrier} / {inet_name} / (인터넷 단독): {exc}")

                # 2) TV 결합 상품별
                if not tv_list:
                    continue

                for tv_idx, tv_name in tv_list:
                    try:
                        _click_product_by_index(page, "internet", inet_idx)
                        time.sleep(CLICK_WAIT_SEC)
                        _set_tv_bundle(page, enabled=True)
                        _click_product_by_index(page, "tv", tv_idx)
                        time.sleep(CLICK_WAIT_SEC)
                        base_fee, gift_amount = _save_combo(
                            page,
                            worksheet,
                            selectors,
                            collected_at,
                            carrier,
                            inet_name,
                            tv_name,
                        )
                        success += 1
                        carrier_success += 1
                        print(
                            f"  [{carrier_success}/{combos}] {inet_name} + {tv_name} "
                            f"-> 요금 {base_fee or '(없음)'}, "
                            f"사은품 {gift_amount or '(없음)'}"
                        )
                    except Exception as exc:
                        fail += 1
                        print(
                            f"  [오류] {carrier} / {inet_name} / {tv_name}: {exc}"
                        )
        except Exception as exc:
            print(f"  [통신사 실패] {carrier}: {exc}")
            fail += 1

    print(
        f"\n아정당 요약: 성공 {success}건 / 실패 {fail}건 "
        f"(예상 조합 약 {total_planned}건)"
    )
    return success, fail


# --- MISO 전체 조합 크롤링 ---

MISO_CARRIERS = [
    ("LG U+", "LGu+"),
    ("KT", "KT"),
    ("SKB", "SK"),
]
MISO_SPEEDS = [
    ("100 MB", "100 Mbps"),
    ("500 MB", "500 Mbps"),
    ("1 GB", "1 Gbps"),
]
MISO_PRODUCTS = [
    ("인터넷", ""),
    ("인터넷 + TV", "인터넷 + TV"),
]


def _miso_click_button(page: Page, text: str, starts: bool = False) -> None:
    page.evaluate(
        """({text, starts}) => {
        const buttons = [...document.querySelectorAll('button')];
        const button = buttons.find((el) => {
            const label = (el.innerText || '').trim();
            const rect = el.getBoundingClientRect();
            const matched = starts ? label.startsWith(text) : label === text;
            return matched && rect.width > 0 && rect.height > 0;
        });
        if (!button) throw new Error(`MISO button not found: ${text}`);
        button.click();
    }""",
        {"text": text, "starts": starts},
    )
    time.sleep(CLICK_WAIT_SEC)


def _miso_result_text(page: Page) -> str:
    text = page.evaluate(
        """() => {
        const el = document.querySelector('[class*="InternetChargeFooter__Container"]');
        return el ? el.innerText : '';
    }"""
    )
    if not text:
        raise RuntimeError("MISO 결과 영역을 찾지 못했습니다.")
    return text


def _miso_extract_result(page: Page) -> tuple[str, str]:
    text = _miso_result_text(page)
    fee_match = re.search(r"월\s*([\d,]+)\s*원", text)
    gift_match = re.search(r"현금\s*([\d,]+만원|[\d,]+원)", text)
    base_fee = f"{fee_match.group(1)}원" if fee_match else ""
    gift_amount = gift_match.group(1) if gift_match else ""
    return base_fee, gift_amount


def _miso_selected_tv_name(page: Page) -> str:
    text = page.evaluate(
        """() => {
        const buttons = [...document.querySelectorAll('button')];
        const button = buttons.find((el) => {
            const label = (el.innerText || '').trim();
            const rect = el.getBoundingClientRect();
            return label.startsWith('인터넷 + TV')
                && !label.includes('집 전화')
                && rect.width > 0
                && rect.height > 0;
        });
        return button ? button.innerText : '';
    }"""
    )
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[1] if len(lines) > 1 else "인터넷 + TV"


def crawl_miso_all(
    page: Page,
    worksheet,
    site: dict[str, Any],
    collected_at: str,
) -> tuple[int, int]:
    success = 0
    fail = 0
    total = len(MISO_CARRIERS) * len(MISO_PRODUCTS) * len(MISO_SPEEDS)

    print(f"\n=== MISO 전체 크롤링 시작 ({total}조합) ===")
    page.goto(site["url"], wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
    time.sleep(4)

    for carrier_button, carrier_name in MISO_CARRIERS:
        print(f"\n[통신사] {carrier_name}")
        try:
            _miso_click_button(page, carrier_button)
            # 아정당의 '기본 요금'과 맞추기 위해 결합 할인은 적용하지 않습니다.
            _miso_click_button(page, "적용 안 함")
        except Exception as exc:
            print(f"  [통신사 선택 오류] {carrier_name}: {exc}")
            fail += 1
            continue

        for product_button, default_tv_name in MISO_PRODUCTS:
            try:
                _miso_click_button(page, product_button)
            except Exception as exc:
                fail += len(MISO_SPEEDS)
                print(f"  [상품 선택 오류] {carrier_name} / {product_button}: {exc}")
                continue

            for speed_button, speed_name in MISO_SPEEDS:
                try:
                    _miso_click_button(page, speed_button, starts=True)
                    time.sleep(AFTER_CLICK_WAIT_SEC)
                    tv_name = (
                        _miso_selected_tv_name(page)
                        if default_tv_name
                        else ""
                    )
                    base_fee, gift_amount = _miso_extract_result(page)
                    append_row(
                        worksheet,
                        [
                            collected_at,
                            "MISO",
                            carrier_name,
                            speed_name,
                            tv_name,
                            base_fee,
                            gift_amount,
                        ],
                    )
                    success += 1
                    print(
                        f"  [{success}/{total}] {carrier_name} / {speed_name} / "
                        f"{tv_name or '(인터넷 단독)'} -> "
                        f"요금 {base_fee or '(없음)'}, 사은품 {gift_amount or '(없음)'}"
                    )
                except Exception as exc:
                    fail += 1
                    print(
                        f"  [오류] {carrier_name} / {product_button} / "
                        f"{speed_name}: {exc}"
                    )

    print(f"\nMISO 요약: 성공 {success}건 / 실패 {fail}건")
    return success, fail


# --- LGU+ 공식몰 지정 조합 크롤링 ---

LGUPLUS_PRODUCT_TYPES = [
    ("인터넷", ""),
    ("인터넷+IPTV", "IPTV"),
]


def _lguplus_click_exact(page: Page, text: str) -> None:
    page.evaluate(
        """(text) => {
        const els = [...document.querySelectorAll('button, a, label, [role="button"]')];
        const el = els.find((node) => {
            const label = (node.innerText || '').trim();
            const rect = node.getBoundingClientRect();
            return label === text && rect.width > 0 && rect.height > 0;
        });
        if (!el) throw new Error(`LGU+ element not found: ${text}`);
        el.click();
    }""",
        text,
    )
    time.sleep(AFTER_CLICK_WAIT_SEC)


def _lguplus_choose_no_mobile_bundle(page: Page) -> None:
    _lguplus_click_exact(page, "U+휴대폰을 사용하지 않아요")


def _lguplus_choose_gift_card(page: Page) -> None:
    try:
        _lguplus_click_exact(page, "상품권\n모바일 상품권으로 온라인 쇼핑을 즐겨보세요")
    except Exception:
        # 해당 URL은 상품권이 기본 선택인 경우가 많습니다.
        pass


def _lguplus_internet_products(page: Page) -> list[tuple[int, str]]:
    page.evaluate(
        """() => {
        const item = [...document.querySelectorAll('.product-type-item')]
            .find((el) => (el.innerText || '').trim().startsWith('인터넷'));
        const button = item?.querySelector('.select-btn');
        if (button) button.click();
    }"""
    )
    time.sleep(CLICK_WAIT_SEC)
    names = page.evaluate(
        """() => {
        const item = [...document.querySelectorAll('.product-type-item')]
            .find((el) => (el.innerText || '').trim().startsWith('인터넷'));
        if (!item) return [];
        const anchors = [...item.querySelectorAll('.c-select-option a')];
        return anchors
            .map((el, index) => ({
                index,
                name: (el.innerText || '').trim().split('\\n')[0].trim(),
            }))
            .filter((item) => item.name && item.name !== '선택됨');
    }"""
    )
    products: list[tuple[int, str]] = []
    seen: set[str] = set()
    for item in names:
        name = item["name"]
        if name in seen:
            continue
        seen.add(name)
        products.append((item["index"], name))
    return products


def _lguplus_select_internet_product(page: Page, product_index: int) -> None:
    page.evaluate(
        """() => {
        const item = [...document.querySelectorAll('.product-type-item')]
            .find((el) => (el.innerText || '').trim().startsWith('인터넷'));
        if (!item) throw new Error('LGU+ internet product area not found');
        const selectButton = item.querySelector('.select-btn');
        if (selectButton) selectButton.click();
    }"""
    )
    time.sleep(CLICK_WAIT_SEC)

    page.evaluate(
        """(productIndex) => {
        const item = [...document.querySelectorAll('.product-type-item')]
            .find((el) => (el.innerText || '').trim().startsWith('인터넷'));
        if (!item) throw new Error('LGU+ internet product area not found');
        const options = [...item.querySelectorAll('.c-select-option a')];
        const option = options[productIndex];
        if (!option) throw new Error(`LGU+ internet product index not found: ${productIndex}`);
        option.click();
    }""",
        product_index,
    )
    time.sleep(AFTER_CLICK_WAIT_SEC + 1.5)


def _lguplus_extract_result(page: Page) -> dict[str, str]:
    text = page.locator("body").inner_text(timeout=30_000)

    monthly_match = re.search(r"월 납부 금액\s*([\d,]+원)/월", text)
    gift_match = re.search(
        r"사은품\s*모바일 [^\n]+ 상품권\s*([\d,]+만원)권", text
    )
    internet_match = re.search(
        r"인터넷\s+(.+?)\s+\(3년 약정\)\s*[\d,]+원", text
    )
    iptv_match = re.search(
        r"IPTV\s+(.+?)\s+\(3년 약정\)\s*[\d,]+원", text
    )

    return {
        "internet_name": internet_match.group(1) if internet_match else "",
        "tv_name": iptv_match.group(1) if iptv_match else "",
        "base_fee": monthly_match.group(1) if monthly_match else "",
        "gift_amount": gift_match.group(1) if gift_match else "",
    }


def crawl_lguplus_all(
    page: Page,
    worksheet,
    site: dict[str, Any],
    collected_at: str,
) -> tuple[int, int]:
    success = 0
    fail = 0
    total = 0

    print("\n=== LGU+ 공식몰 크롤링 시작 (인터넷 하위 상품 전체) ===")
    page.goto(site["url"], wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
    time.sleep(8)

    for product_type, fallback_tv_name in LGUPLUS_PRODUCT_TYPES:
        try:
            _lguplus_click_exact(page, product_type)
            time.sleep(4)
            internet_products = _lguplus_internet_products(page)
            total += len(internet_products)
            print(f"\n[상품 유형] {product_type}: 인터넷 하위 상품 {len(internet_products)}개")

            for internet_index, internet_product in internet_products:
                try:
                    # LGU+ 선택 목록은 선택 후 DOM이 부분 갱신되어 누락될 수 있어
                    # 각 하위 상품마다 새로 진입해 같은 기준으로 선택합니다.
                    page.goto(
                        site["url"],
                        wait_until="domcontentloaded",
                        timeout=PAGE_LOAD_TIMEOUT_MS,
                    )
                    time.sleep(6)
                    _lguplus_click_exact(page, product_type)
                    time.sleep(4)
                    _lguplus_select_internet_product(page, internet_index)
                    _lguplus_choose_no_mobile_bundle(page)
                    _lguplus_choose_gift_card(page)
                    time.sleep(AFTER_CLICK_WAIT_SEC)

                    data = _lguplus_extract_result(page)
                    tv_name = data["tv_name"] or fallback_tv_name

                    append_row(
                        worksheet,
                        [
                            collected_at,
                            "U+",
                            "LGu+",
                            data["internet_name"] or internet_product,
                            tv_name,
                            data["base_fee"],
                            data["gift_amount"],
                        ],
                    )
                    success += 1
                    print(
                        f"  [{success}] {product_type} / "
                        f"{data['internet_name'] or internet_product} / "
                        f"{tv_name or '(인터넷 단독)'} -> "
                        f"요금 {data['base_fee'] or '(없음)'}, "
                        f"상품권 {data['gift_amount'] or '(없음)'}"
                    )
                except Exception as exc:
                    fail += 1
                    print(
                        f"  [오류] LGU+ / {product_type} / "
                        f"{internet_product}: {exc}"
                    )
        except Exception as exc:
            fail += 1
            print(f"  [오류] LGU+ / {product_type}: {exc}")

    print(f"\nLGU+ 요약: 성공 {success}건 / 실패 {fail}건 (발견 상품 {total}건)")
    return success, fail


# --- KT 공식몰 지정 조합 크롤링 ---

KT_SPEEDS = [
    ("inetSpeed100M", "100 Mbps"),
    ("inetSpeed500M", "500 Mbps"),
    ("inetSpeed1G", "1 Gbps"),
]
KT_PRODUCT_PAGES = [
    ("인터넷", "internet_url", ""),
    ("인터넷+IPTV", "iptv_url", "지니 TV"),
]
KT_TV_OPTIONS = [
    ("tvType01", "tvTypeChkWR00055092", "지니TV 기본 채널(238개)"),
    ("tvType02", "tvTypeChkWR00076093", "지니 TV 모든G"),
    ("tvType08", "tvTypeChkWR00046185", "매월 VOD 1만원 + 269채널"),
]


def _kt_click_contains(page: Page, text: str) -> None:
    page.evaluate(
        """(text) => {
        const els = [...document.querySelectorAll('button, a, label, [role="button"], .wCheck, .wRadio, div')];
        const candidates = els
            .map((node) => ({
                node,
                label: (node.innerText || '').trim(),
                rect: node.getBoundingClientRect(),
            }))
            .filter((item) =>
                item.label.includes(text)
                && item.rect.width > 0
                && item.rect.height > 0
                && item.label.length < 260
            )
            .sort((a, b) => a.label.length - b.label.length);
        if (!candidates.length) throw new Error(`KT element not found: ${text}`);
        candidates[0].node.click();
    }""",
        text,
    )
    time.sleep(AFTER_CLICK_WAIT_SEC + 0.8)


def _kt_click_card_contains(page: Page, text: str) -> None:
    page.evaluate(
        """(text) => {
        const cards = [...document.querySelectorAll('.wCheck, .wRadio')];
        const card = cards.find((node) => {
            const label = (node.innerText || '').trim();
            const rect = node.getBoundingClientRect();
            return label.includes(text) && rect.width > 0 && rect.height > 0;
        });
        if (!card) throw new Error(`KT card not found: ${text}`);
        card.click();
    }""",
        text,
    )
    time.sleep(AFTER_CLICK_WAIT_SEC + 0.8)


def _kt_select_speed(page: Page, speed_input_id: str) -> None:
    page.locator(f"#{speed_input_id}").check(force=True, timeout=PAGE_LOAD_TIMEOUT_MS)
    time.sleep(AFTER_CLICK_WAIT_SEC + 1.0)


def _kt_select_tv_option(
    page: Page,
    tv_type_input_id: str,
    tv_product_input_id: str,
) -> None:
    page.locator(f"#{tv_type_input_id}").check(force=True, timeout=PAGE_LOAD_TIMEOUT_MS)
    time.sleep(AFTER_CLICK_WAIT_SEC + 0.8)
    page.locator(f"#{tv_product_input_id}").check(
        force=True, timeout=PAGE_LOAD_TIMEOUT_MS
    )
    time.sleep(AFTER_CLICK_WAIT_SEC + 0.8)


def _kt_select_settop3(page: Page) -> None:
    page.locator("#setTopChk60").check(force=True, timeout=PAGE_LOAD_TIMEOUT_MS)
    time.sleep(AFTER_CLICK_WAIT_SEC + 0.8)


def _kt_force_radio(page: Page, input_id: str) -> None:
    page.evaluate(
        """(inputId) => {
        const input = document.getElementById(inputId);
        if (!input) throw new Error(`KT input not found: ${inputId}`);
        input.checked = true;
        input.click();
        input.dispatchEvent(new Event('change', {bubbles: true}));
    }""",
        input_id,
    )
    time.sleep(AFTER_CLICK_WAIT_SEC + 1.0)


def _kt_select_defaults(
    page: Page,
    speed_input_id: str,
    tv_type_input_id: str = "",
    tv_product_input_id: str = "",
) -> None:
    # 기본값이어도 명시적으로 한 번씩 선택해 조건을 고정합니다.
    _kt_select_speed(page, speed_input_id)
    if tv_type_input_id and tv_product_input_id:
        _kt_select_tv_option(page, tv_type_input_id, tv_product_input_id)
        _kt_select_settop3(page)
    for input_id, required in [
        ("selGiftCpn", False),  # 상품권
        ("phnCombDcN", True),  # KT 휴대폰 미사용
    ]:
        try:
            page.locator(f"#{input_id}").check(force=True, timeout=PAGE_LOAD_TIMEOUT_MS)
            time.sleep(AFTER_CLICK_WAIT_SEC + 1.0)
        except Exception:
            try:
                _kt_force_radio(page, input_id)
            except Exception:
                if required:
                    raise
    try:
        _kt_click_card_contains(page, "GiGA WiFi home")
    except Exception:
        pass
    try:
        _kt_click_contains(page, "3년")
    except Exception:
        pass


def _kt_extract_result(page: Page) -> dict[str, str]:
    text = page.locator("body").inner_text(timeout=30_000)

    monthly_match = re.search(
        r"월 납부 요금\s*정상가\s*월\s*[\d,]+원\s*할인가\s*월\s*([\d,]+)\s*원",
        text,
    )
    if not monthly_match:
        monthly_match = re.search(r"월 납부 요금\s*월\s*([\d,]+)\s*원", text)

    gift_match = re.search(
        r"상품권/ 단말기 할인\s*다양한 곳에서 사용하는 상품권\s*([\d,]+)원",
        text,
    )
    if not gift_match:
        gift_match = re.search(r"상품권\s*([\d,]+)원", text)

    summary_start = text.find("출동비 안내")
    summary = text[summary_start:] if summary_start >= 0 else text
    internet_match = re.search(r"(인터넷 [^\n]+)", summary)
    tv_match = re.search(r"(지니 TV [^\n]+)", summary)

    gift_amount = ""
    if gift_match:
        gift_won = int(gift_match.group(1).replace(",", ""))
        gift_amount = f"{gift_won // 10000}만원"

    return {
        "internet_name": internet_match.group(1).strip() if internet_match else "",
        "tv_name": tv_match.group(1).strip() if tv_match else "",
        "base_fee": f"{monthly_match.group(1)}원" if monthly_match else "",
        "gift_amount": gift_amount,
    }


def crawl_kt_all(
    page: Page,
    worksheet,
    site: dict[str, Any],
    collected_at: str,
) -> tuple[int, int]:
    success = 0
    fail = 0
    total = len(KT_SPEEDS) + (len(KT_SPEEDS) * len(KT_TV_OPTIONS))

    print(f"\n=== KT 공식몰 크롤링 시작 ({total}조합) ===")

    for product_type, url_key, fallback_tv_name in KT_PRODUCT_PAGES:
        url = site[url_key]
        print(f"\n[상품 유형] {product_type}")
        tv_options = (
            [("", "", "")]
            if product_type == "인터넷"
            else KT_TV_OPTIONS
        )
        for speed_input_id, speed_name in KT_SPEEDS:
            for tv_type_input_id, tv_product_input_id, fallback_option_name in tv_options:
                tv_fallback = fallback_option_name or fallback_tv_name
                combo_label = tv_fallback or "(인터넷 단독)"
                try:
                    page.goto(
                        url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS
                    )
                    time.sleep(8)
                    _kt_select_defaults(
                        page,
                        speed_input_id,
                        tv_type_input_id,
                        tv_product_input_id,
                    )
                    time.sleep(AFTER_CLICK_WAIT_SEC)
                    data = _kt_extract_result(page)
                    tv_name = data["tv_name"] or tv_fallback
                    append_row(
                        worksheet,
                        [
                            collected_at,
                            "KT",
                            "KT",
                            data["internet_name"] or speed_name,
                            tv_name,
                            data["base_fee"],
                            data["gift_amount"],
                        ],
                    )
                    success += 1
                    print(
                        f"  [{success}/{total}] {product_type} / {speed_name} / "
                        f"{tv_name or '(인터넷 단독)'} -> "
                        f"요금 {data['base_fee'] or '(없음)'}, "
                        f"상품권 {data['gift_amount'] or '(없음)'}"
                    )
                except Exception as exc:
                    fail += 1
                    print(
                        f"  [오류] KT / {product_type} / {speed_name} / "
                        f"{combo_label}: {exc}"
                    )

    print(f"\nKT 요약: 성공 {success}건 / 실패 {fail}건")
    return success, fail


# --- SKB 공식몰 지정 조합 크롤링 ---

SKB_BTV_OPTIONS = [
    "B tv All",
    "B tv 스탠다드",
    "B tv 이코노미",
    "B tv pop 230",
    "B tv pop 180",
]
SKB_TV_INTERNET_OPTIONS = [
    ("topSubCtgProdItem", 3, 3, "기가(1G)+WiFi 7"),
    ("topSubCtgProdItem", 4, 4, "기가라이트(500M)+WiFi 7"),
    ("topSubCtgProdItem", 5, 5, "광랜(100M)+WiFi 7"),
]
SKB_ONLY_INTERNET_OPTIONS = [
    ("internetList", 3, 3, "기가(1G)+WiFi 7"),
    ("internetList", 4, 4, "기가라이트(500M)+WiFi 7"),
    ("internetList", 5, 5, "광랜(100M)+WiFi 7"),
    ("internet2030List", 3, 9, "2030 다이렉트 1G + WiFi 7"),
    ("internet2030List", 4, 10, "2030 다이렉트 500M + WiFi 7"),
    ("internet2030List", 5, 11, "2030 다이렉트 100M + WiFi 7"),
]


def _skb_click_label(page: Page, text: str, name_hint: str = "") -> None:
    page.evaluate(
        """({text, nameHint}) => {
        const labels = [...document.querySelectorAll('label')];
        const label = labels.find((node) => {
            const value = (node.innerText || '').trim().replace(/\\s+/g, ' ');
            if (value !== text && !value.startsWith(text)) return false;
            if (!nameHint) return true;
            const nodeName = node.getAttribute('name') || '';
            const inputName = node.querySelector('input')?.getAttribute('name') || '';
            return nodeName.includes(nameHint) || inputName.includes(nameHint);
        });
        if (!label) throw new Error(`SKB label not found: ${nameHint} / ${text}`);
        label.click();
    }""",
        {"text": text, "nameHint": name_hint},
    )
    time.sleep(AFTER_CLICK_WAIT_SEC)


def _skb_click_group_index(page: Page, name_hint: str, index: int) -> None:
    page.evaluate(
        """({nameHint, index}) => {
        const labels = [...document.querySelectorAll('label')].filter((node) => {
            const nodeName = node.getAttribute('name') || '';
            const inputName = node.querySelector('input')?.getAttribute('name') || '';
            return nodeName.includes(nameHint) || inputName.includes(nameHint);
        });
        const label = labels[index];
        if (!label) throw new Error(`SKB option not found: ${nameHint} / ${index}`);
        label.click();
    }""",
        {"nameHint": name_hint, "index": index},
    )
    time.sleep(AFTER_CLICK_WAIT_SEC)


def _skb_select_wifi7(page: Page) -> None:
    page.evaluate(
        """() => {
        const select = document.querySelector('#telecom');
        if (!select) throw new Error('SKB WiFi selector not found');
        select.value = 'C000002026';
        select.dispatchEvent(new Event('change', {bubbles: true}));
    }"""
    )
    time.sleep(AFTER_CLICK_WAIT_SEC)


def _skb_select_no_internet_addons(page: Page, default_addon_index: int) -> None:
    page.evaluate(
        """(defaultAddonIndex) => {
        const defaultLabels = [...document.querySelectorAll('label')].filter((label) =>
            label.querySelector('input')?.getAttribute('name') === 'default-form-radio-type-addOns'
        );
        const label = defaultLabels[defaultAddonIndex];
        if (!label) {
            throw new Error(`SKB default addon not found: ${defaultAddonIndex}`);
        }
        label.click();
    }""",
        default_addon_index,
    )
    time.sleep(AFTER_CLICK_WAIT_SEC)


def _skb_uncheck_wifi_addons(page: Page) -> None:
    page.evaluate(
        """() => {
        const labels = [...document.querySelectorAll('label')].filter((label) =>
            label.querySelector('input')?.getAttribute('name') === 'form-checkbox-type-addOns'
        );
        labels.forEach((label) => {
            const input = label.querySelector('input');
            if (input?.checked) {
                label.click();
            }
        });
    }"""
    )
    time.sleep(AFTER_CLICK_WAIT_SEC)


def _skb_select_no_tv_content(page: Page) -> None:
    page.evaluate(
        """() => {
        const tvLabels = [...document.querySelectorAll('label')].filter((label) =>
            label.getAttribute('name') === 'btvMainCtgProdlabel'
        );
        const tvIndex = tvLabels.findIndex((label) => label.querySelector('input')?.checked);
        if (tvIndex < 0) return;
        const defaultLabels = [...document.querySelectorAll('label')].filter((label) =>
            label.querySelector('input')?.getAttribute('name') === 'default-form-radio-type-content'
        );
        const label = defaultLabels[tvIndex];
        if (label && !label.querySelector('input')?.checked) label.click();
    }"""
    )
    time.sleep(AFTER_CLICK_WAIT_SEC)


def _skb_select_internet_product(
    page: Page,
    group_hint: str,
    option_index: int,
    default_addon_index: int,
) -> None:
    _skb_click_group_index(page, group_hint, option_index)
    _skb_uncheck_wifi_addons(page)
    _skb_select_no_internet_addons(page, default_addon_index)


def _skb_select_defaults(
    page: Page,
    group_hint: str,
    option_index: int,
    default_addon_index: int,
    tv_name: str = "",
) -> None:
    _skb_click_label(page, "없음", "packageInfo")
    _skb_select_wifi7(page)
    _skb_select_internet_product(page, group_hint, option_index, default_addon_index)
    if tv_name:
        _skb_click_label(page, tv_name, "btvMainCtgProdlabel")
        _skb_select_no_tv_content(page)
        _skb_click_label(page, "Smart 3", "btvSettoplabel")
        _skb_select_no_tv_content(page)
        _skb_uncheck_wifi_addons(page)
        _skb_select_no_internet_addons(page, default_addon_index)
    _skb_click_label(page, "사은품 선택")
    _skb_select_no_internet_addons(page, default_addon_index)
    if tv_name:
        _skb_select_no_tv_content(page)


def _skb_extract_result(page: Page) -> dict[str, str]:
    text = page.locator("body").inner_text(timeout=30_000)

    monthly_match = re.search(r"예상 납부금액\s*월\s*([\d,]+원)", text)
    gift_match = re.search(r"신세계\s*모바일\s*상품권\s*([\d,]+만원)", text)
    internet_match = re.search(r"상품 요금 정보.*?인터넷\s*\n([^\n]+)", text, re.S)
    tv_match = re.search(r"상품 요금 정보.*?B tv\s*\n([^\n]+)", text, re.S)
    internet_name = internet_match.group(1).strip() if internet_match else ""
    internet_name = internet_name.split("|", 1)[0].strip()

    return {
        "internet_name": internet_name,
        "tv_name": tv_match.group(1).strip() if tv_match else "",
        "base_fee": monthly_match.group(1) if monthly_match else "",
        "gift_amount": gift_match.group(1) if gift_match else "",
    }


def crawl_skb_all(
    page: Page,
    worksheet,
    site: dict[str, Any],
    collected_at: str,
) -> tuple[int, int]:
    success = 0
    fail = 0
    total = (len(SKB_TV_INTERNET_OPTIONS) * len(SKB_BTV_OPTIONS)) + len(
        SKB_ONLY_INTERNET_OPTIONS
    )

    print(f"\n=== SKB 공식몰 크롤링 시작 ({total}조합) ===")

    for group_hint, option_index, addon_index, internet_fallback in SKB_TV_INTERNET_OPTIONS:
        for tv_name in SKB_BTV_OPTIONS:
            try:
                page.goto(
                    site["url"],
                    wait_until="domcontentloaded",
                    timeout=PAGE_LOAD_TIMEOUT_MS,
                )
                time.sleep(8)
                _skb_select_defaults(
                    page,
                    group_hint,
                    option_index,
                    addon_index,
                    tv_name=tv_name,
                )
                data = _skb_extract_result(page)
                append_row(
                    worksheet,
                    [
                        collected_at,
                        "SKB",
                        "SK",
                        data["internet_name"] or internet_fallback,
                        data["tv_name"] or tv_name,
                        data["base_fee"],
                        data["gift_amount"],
                    ],
                )
                success += 1
                print(
                    f"  [{success}/{total}] 인터넷+TV / "
                    f"{data['internet_name'] or internet_fallback} / "
                    f"{data['tv_name'] or tv_name} -> "
                    f"요금 {data['base_fee'] or '(없음)'}, "
                    f"상품권 {data['gift_amount'] or '(없음)'}"
                )
            except Exception as exc:
                fail += 1
                print(f"  [오류] SKB / 인터넷+TV / {internet_fallback} / {tv_name}: {exc}")

    for group_hint, option_index, addon_index, internet_fallback in SKB_ONLY_INTERNET_OPTIONS:
        try:
            page.goto(
                site["internet_url"],
                wait_until="domcontentloaded",
                timeout=PAGE_LOAD_TIMEOUT_MS,
            )
            time.sleep(8)
            _skb_select_defaults(page, group_hint, option_index, addon_index)
            data = _skb_extract_result(page)
            internet_name = (
                internet_fallback
                if internet_fallback.startswith("2030")
                else data["internet_name"] or internet_fallback
            )
            append_row(
                worksheet,
                [
                    collected_at,
                    "SKB",
                    "SK",
                    internet_name,
                    "",
                    data["base_fee"],
                    data["gift_amount"],
                ],
            )
            success += 1
            print(
                f"  [{success}/{total}] 인터넷 단독 / {internet_name} -> "
                f"요금 {data['base_fee'] or '(없음)'}, "
                f"상품권 {data['gift_amount'] or '(없음)'}"
            )
        except Exception as exc:
            fail += 1
            print(f"  [오류] SKB / 인터넷 단독 / {internet_fallback}: {exc}")

    print(f"\nSKB 요약: 성공 {success}건 / 실패 {fail}건")
    return success, fail


# --- SKT T다이렉트샵 요금계산기 지정 조합 크롤링 ---

SKT_INTERNET_OPTIONS = [
    (0, "광랜인터넷 와이파이(100M)"),
    (1, "기가라이트인터넷 와이파이(500M)"),
    (2, "기가인터넷 와이파이(1G)"),
]
SKT_TV_OPTIONS = [
    (0, ""),
    (1, "B tv 이코노미"),
    (2, "B tv 스탠다드"),
    (3, "B tv All"),
]


def _skt_select_ion_range(page: Page, selector: str, index: int) -> None:
    page.evaluate(
        """({selector, index}) => {
        const input = document.querySelector(selector);
        if (!input) throw new Error(`SKT range not found: ${selector}`);
        const $ = window.jQuery || window.$;
        const slider = $ && $(input).data('ionRangeSlider');
        if (!slider) throw new Error(`SKT ionRangeSlider not ready: ${selector}`);
        slider.update({from: index});
        const data = {
            input,
            slider,
            from: index,
            from_value: input.value,
            from_pretty: input.value,
        };
        if (slider.options?.onChange) slider.options.onChange(data);
        if (slider.options?.onFinish) slider.options.onFinish(data);
        input.dispatchEvent(new Event('change', {bubbles: true}));
    }""",
        {"selector": selector, "index": index},
    )
    time.sleep(AFTER_CLICK_WAIT_SEC + 0.8)


def _skt_select_no_mobile_bundle(page: Page) -> None:
    # 기본값이 1대 결합이라면 한 번 감소시켜 "결합안함"으로 맞춥니다.
    text = page.locator("#component673").inner_text(timeout=30_000)
    if "휴대폰 결합할인" not in text:
        return
    page.locator(".opt-quantity-select .btn-minus").click(
        force=True, timeout=PAGE_LOAD_TIMEOUT_MS
    )
    time.sleep(AFTER_CLICK_WAIT_SEC + 0.8)


def _skt_select_defaults(page: Page, internet_index: int, tv_index: int) -> None:
    _skt_select_ion_range(page, 'input[name="ai-range"]', internet_index)
    wifi = page.locator("#_wifi")
    if not wifi.is_checked(timeout=PAGE_LOAD_TIMEOUT_MS):
        wifi.check(force=True, timeout=PAGE_LOAD_TIMEOUT_MS)
        time.sleep(AFTER_CLICK_WAIT_SEC)
    _skt_select_ion_range(page, "#iptvList input.irs-hidden-input", tv_index)
    _skt_select_no_mobile_bundle(page)
    page.locator("#benefitType2").check(force=True, timeout=PAGE_LOAD_TIMEOUT_MS)
    time.sleep(AFTER_CLICK_WAIT_SEC + 0.8)


def _skt_extract_result(page: Page) -> dict[str, str]:
    text = page.locator("#component673").inner_text(timeout=30_000)
    monthly_match = re.search(
        r"예상 납부 요금\s*\(부가세 포함\)\s*월\s*([\d,]+원)",
        text,
    )
    internet_match = re.search(
        r"이용요금\s*월\s*[\d,]+원\s*\n([^\n]+인터넷[^\n]*)",
        text,
    )
    tv_match = re.search(r"\n(B tv [^\n]+)\s*\n월\s*[\d,]+원", text)
    gift_match = re.search(r"사은품\s*([\d,]+만원|[\d,]+원)", text)

    return {
        "internet_name": internet_match.group(1).strip() if internet_match else "",
        "tv_name": tv_match.group(1).strip() if tv_match else "",
        "base_fee": monthly_match.group(1) if monthly_match else "",
        "gift_amount": gift_match.group(1).strip() if gift_match else "",
    }


def crawl_skt_all(
    page: Page,
    worksheet,
    site: dict[str, Any],
    collected_at: str,
) -> tuple[int, int]:
    success = 0
    fail = 0
    total = len(SKT_INTERNET_OPTIONS) * len(SKT_TV_OPTIONS)

    print(f"\n=== SKT T다이렉트샵 크롤링 시작 ({total}조합) ===")

    for internet_index, internet_fallback in SKT_INTERNET_OPTIONS:
        for tv_index, tv_fallback in SKT_TV_OPTIONS:
            try:
                page.goto(
                    site["url"],
                    wait_until="domcontentloaded",
                    timeout=PAGE_LOAD_TIMEOUT_MS,
                )
                time.sleep(8)
                _skt_select_defaults(page, internet_index, tv_index)
                data = _skt_extract_result(page)
                append_row(
                    worksheet,
                    [
                        collected_at,
                        "SKT",
                        "SK",
                        data["internet_name"] or internet_fallback,
                        data["tv_name"] or tv_fallback,
                        data["base_fee"],
                        data["gift_amount"],
                    ],
                )
                success += 1
                print(
                    f"  [{success}/{total}] {data['internet_name'] or internet_fallback} / "
                    f"{data['tv_name'] or tv_fallback or '(TV 선택안함)'} -> "
                    f"요금 {data['base_fee'] or '(없음)'}, "
                    f"사은품 {data['gift_amount'] or '(표시 없음)'}"
                )
            except Exception as exc:
                fail += 1
                print(
                    f"  [오류] SKT / {internet_fallback} / "
                    f"{tv_fallback or '(TV 선택안함)'}: {exc}"
                )

    print(f"\nSKT 요약: 성공 {success}건 / 실패 {fail}건")
    return success, fail


# --- 단일 조합 크롤링 (다른 사이트용) ---


def _click(page: Page, selector: str, label: str, step_name: str) -> None:
    if selector.strip():
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=PAGE_LOAD_TIMEOUT_MS)
        loc.click(timeout=PAGE_LOAD_TIMEOUT_MS)
        print(f"    [{step_name}] CSS 클릭: {selector}")
        return

    if not label.strip():
        print(f"    [{step_name}] 건너뜀")
        return

    loc = page.get_by_text(label, exact=False).first
    loc.wait_for(state="visible", timeout=PAGE_LOAD_TIMEOUT_MS)
    loc.click(timeout=PAGE_LOAD_TIMEOUT_MS)
    print(f"    [{step_name}] 텍스트 클릭: {label}")


def _click_carrier(page: Page, site: dict[str, Any]) -> None:
    selectors = site["selectors"]
    name = site["carrier_name"]

    if selectors["carrier_tab"].strip():
        _click(page, selectors["carrier_tab"], name, "1단계 통신사")
        return

    if not name.strip():
        return

    area = page.locator(".recommend-form--inner")
    already_on = area.locator(".recommend-option.on").filter(has_text=name)
    if already_on.count():
        print(f"    [1단계 통신사] 이미 선택됨: {name}")
        return

    target = area.locator(".recommend-option").filter(has_text=name)
    if target.count() == 0:
        target = area.locator(".recommend-item").filter(has_text=name)
    target.first.click(timeout=PAGE_LOAD_TIMEOUT_MS)
    print(f"    [1단계 통신사] 클릭: {name}")


def _click_internet(page: Page, site: dict[str, Any]) -> None:
    selectors = site["selectors"]
    name = site["internet_name"]

    if selectors["internet_tab"].strip():
        _click(page, selectors["internet_tab"], name, "2단계 인터넷")
        return

    if not name.strip():
        return

    loc = page.locator(".at-internet .recommend-option").filter(
        has_text=name.split()[0]
    )
    if loc.count() == 0:
        loc = page.get_by_text(name, exact=False)
    loc.first.click(timeout=PAGE_LOAD_TIMEOUT_MS)
    print(f"    [2단계 인터넷] 텍스트 클릭: {name}")


def _click_tv(page: Page, site: dict[str, Any]) -> None:
    selectors = site["selectors"]
    name = site["tv_name"]

    if not name.strip() and not selectors["tv_tab"].strip():
        print("    [3단계 TV] 건너뜀 (TV 상품 없음)")
        return

    if selectors["tv_tab"].strip():
        _click(page, selectors["tv_tab"], name, "3단계 TV")
        return

    loc = page.locator(".at-tv .recommend-option").filter(has_text=name)
    if loc.count() == 0:
        loc = page.get_by_text(name, exact=True)
    loc.first.click(timeout=PAGE_LOAD_TIMEOUT_MS)
    print(f"    [3단계 TV] 텍스트 클릭: {name}")


def crawl_site(page: Page, site: dict[str, Any]) -> dict[str, str]:
    url = site["url"].strip()
    selectors = site["selectors"]

    print(f"\n▶ 크롤링 시작: {site['site_name']} ({url})")
    page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
    time.sleep(CLICK_WAIT_SEC)
    _scroll_to_form(page)

    if site["carrier_name"].strip() or selectors["carrier_tab"].strip():
        _click_carrier(page, site)
        time.sleep(CLICK_WAIT_SEC)

    _click_internet(page, site)
    time.sleep(CLICK_WAIT_SEC)

    _click_tv(page, site)
    time.sleep(CLICK_WAIT_SEC)

    panel_text = _wait_for_result(page, selectors)
    base_fee, gift_amount = _extract_text(page, panel_text, selectors)

    return {
        "site_name": site["site_name"],
        "carrier_name": site["carrier_name"],
        "internet_name": site["internet_name"],
        "tv_name": site.get("tv_name", "").strip(),
        "base_fee": base_fee,
        "gift_amount": gift_amount,
    }


def run() -> None:
    active_sites = [s for s in TARGET_SITES if s["url"].strip()]
    if not active_sites:
        print("실행할 사이트가 없습니다. TARGET_SITES 에 url 을 입력하세요.")
        return

    collected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    last_worksheet_title = ""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=HEADLESS)
        page = browser.new_page(viewport={"width": 1400, "height": 1000})

        for site in active_sites:
            worksheet = get_worksheet_by_title(site.get("sheet_name", site["site_name"]))
            ensure_headers(worksheet)
            last_worksheet_title = worksheet.title
            try:
                if site.get("crawl_mode") == "all" and "ajd.co.kr" in site["url"]:
                    crawl_ajd_all(page, worksheet, site, collected_at)
                    flush_worksheet_rows(worksheet)
                    continue

                if site.get("crawl_mode") == "miso_all" and "miso.kr" in site["url"]:
                    crawl_miso_all(page, worksheet, site, collected_at)
                    flush_worksheet_rows(worksheet)
                    continue

                if (
                    site.get("crawl_mode") == "lguplus_all"
                    and "lguplus.com" in site["url"]
                ):
                    crawl_lguplus_all(page, worksheet, site, collected_at)
                    flush_worksheet_rows(worksheet)
                    continue

                if site.get("crawl_mode") == "kt_all" and "shop.kt.com" in site["url"]:
                    crawl_kt_all(page, worksheet, site, collected_at)
                    flush_worksheet_rows(worksheet)
                    continue

                if site.get("crawl_mode") == "skb_all" and "bworld.co.kr" in site["url"]:
                    crawl_skb_all(page, worksheet, site, collected_at)
                    flush_worksheet_rows(worksheet)
                    continue

                if site.get("crawl_mode") == "skt_all" and "shop.tworld.co.kr" in site["url"]:
                    crawl_skt_all(page, worksheet, site, collected_at)
                    flush_worksheet_rows(worksheet)
                    continue

                data = crawl_site(page, site)
                append_row(
                    worksheet,
                    [
                        collected_at,
                        data["site_name"],
                        data["carrier_name"],
                        data["internet_name"],
                        data["tv_name"],
                        data["base_fee"],
                        data["gift_amount"],
                    ],
                )
                flush_worksheet_rows(worksheet)
            except Exception as exc:
                print(f"  [오류] {site['site_name']}: {exc}")
                flush_worksheet_rows(worksheet)

        browser.close()

    print("\n완료: 구글 시트에 데이터를 누적 저장했습니다.")
    print(f"마지막 저장 시트: {SPREADSHEET_NAME} > {last_worksheet_title}")


if __name__ == "__main__":
    run()
