"""
Daily crawler runner with KakaoTalk progress notifications.

This script runs all configured sites in app.py, appends results to Google Sheets,
and sends progress summaries to KakaoTalk "나에게 보내기" when kakao_config.json exists.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

import app

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).parent
KAKAO_CONFIG_FILE = BASE_DIR / "kakao_config.json"
LOG_DIR = BASE_DIR / "logs"
SHEET_URL = "https://docs.google.com/spreadsheets/"


class KakaoNotifier:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.config = self._load_config()
        self.enabled = bool(
            self.config.get("rest_api_key")
            and self.config.get("refresh_token")
            and self.config.get("access_token")
        )
        if not self.enabled:
            print(
                "[카카오톡 알림 비활성화] kakao_config.json 설정이 없거나 비어 있습니다.",
                flush=True,
            )

    def _load_config(self) -> dict[str, str]:
        if not self.config_path.exists():
            return {}
        with self.config_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save_config(self) -> None:
        with self.config_path.open("w", encoding="utf-8") as file:
            json.dump(self.config, file, ensure_ascii=False, indent=2)

    def refresh_access_token(self) -> bool:
        if not self.config.get("rest_api_key") or not self.config.get("refresh_token"):
            return False

        payload = urllib.parse.urlencode(
            {
                "grant_type": "refresh_token",
                "client_id": self.config["rest_api_key"],
                "refresh_token": self.config["refresh_token"],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "https://kauth.kakao.com/oauth/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            print(f"[카카오톡 토큰 갱신 실패] {exc}", flush=True)
            return False

        self.config["access_token"] = data["access_token"]
        if data.get("refresh_token"):
            self.config["refresh_token"] = data["refresh_token"]
        self.config["token_refreshed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save_config()
        self.enabled = True
        return True

    def send(self, text: str) -> None:
        print(f"[카카오톡 알림] {text}", flush=True)
        if not self.enabled:
            return

        if not self._send_once(text):
            if self.refresh_access_token():
                self._send_once(text)

    def _send_once(self, text: str) -> bool:
        template = {
            "object_type": "text",
            "text": text[:1000],
            "link": {
                "web_url": SHEET_URL,
                "mobile_web_url": SHEET_URL,
            },
            "button_title": "구글시트 확인",
        }
        payload = urllib.parse.urlencode(
            {"template_object": json.dumps(template, ensure_ascii=False)}
        ).encode("utf-8")
        request = urllib.request.Request(
            "https://kapi.kakao.com/v2/api/talk/memo/default/send",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.config.get('access_token', '')}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                response.read()
            return True
        except urllib.error.HTTPError as exc:
            print(f"[카카오톡 발송 실패] HTTP {exc.code}: {exc.read()}", flush=True)
            return False
        except Exception as exc:
            print(f"[카카오톡 발송 실패] {exc}", flush=True)
            return False


def run_site(page, worksheet, site: dict[str, Any], collected_at: str):
    mode = site.get("crawl_mode")
    url = site["url"]
    if mode == "all" and "ajd.co.kr" in url:
        return app.crawl_ajd_all(page, worksheet, site, collected_at)
    if mode == "miso_all" and "miso.kr" in url:
        return app.crawl_miso_all(page, worksheet, site, collected_at)
    if mode == "lguplus_all" and "lguplus.com" in url:
        return app.crawl_lguplus_all(page, worksheet, site, collected_at)
    if mode == "kt_all" and "shop.kt.com" in url:
        return app.crawl_kt_all(page, worksheet, site, collected_at)
    if mode == "skb_all" and "bworld.co.kr" in url:
        return app.crawl_skb_all(page, worksheet, site, collected_at)
    if mode == "skt_all" and "shop.tworld.co.kr" in url:
        return app.crawl_skt_all(page, worksheet, site, collected_at)

    data = app.crawl_site(page, site)
    app.append_row(
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
    return (1, 0)


def normalize_result(result) -> tuple[int, int]:
    if isinstance(result, tuple) and len(result) >= 2:
        return int(result[0]), int(result[1])
    return 0, 0


def main() -> int:
    app.HEADLESS = True
    LOG_DIR.mkdir(exist_ok=True)
    notifier = KakaoNotifier(KAKAO_CONFIG_FILE)
    sites = [site for site in app.TARGET_SITES if site["url"].strip()]
    collected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_start_dt = datetime.now()
    total_start = time.perf_counter()
    summaries: list[str] = []
    total_success = 0
    total_fail = 0

    notifier.send(
        f"[크롤링 시작]\n"
        f"시각: {total_start_dt:%Y-%m-%d %H:%M:%S}\n"
        f"대상: {len(sites)}개 사이트\n"
        f"수집 기준: {collected_at}"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 1000})

        for site in sites:
            site_name = site.get("sheet_name", site["site_name"])
            worksheet = app.get_worksheet_by_title(site_name)
            app.ensure_headers(worksheet)

            site_start_dt = datetime.now()
            site_start = time.perf_counter()
            notifier.send(f"[{site_name}] 크롤링 시작\n시각: {site_start_dt:%H:%M:%S}")
            try:
                result = run_site(page, worksheet, site, collected_at)
                app.flush_worksheet_rows(worksheet)
                success, fail = normalize_result(result)
                status = "성공" if fail == 0 else "일부 실패"
            except Exception as exc:
                app.flush_worksheet_rows(worksheet)
                success, fail = 0, 1
                status = "실패"
                traceback.print_exc()
                notifier.send(f"[{site_name}] 오류 발생\n{exc}")

            site_elapsed = time.perf_counter() - site_start
            total_success += success
            total_fail += fail
            summary = (
                f"{site_name}: {status}, 성공 {success}건, 실패 {fail}건, "
                f"{site_elapsed / 60:.2f}분"
            )
            summaries.append(summary)
            notifier.send(f"[{site_name}] 완료\n{summary}")

        browser.close()

    total_elapsed = time.perf_counter() - total_start
    total_end_dt = datetime.now()
    final_message = (
        f"[크롤링 완료]\n"
        f"종료: {total_end_dt:%Y-%m-%d %H:%M:%S}\n"
        f"총 소요: {total_elapsed / 60:.2f}분\n"
        f"총 성공: {total_success}건 / 총 실패: {total_fail}건\n"
        + "\n".join(summaries)
    )
    notifier.send(final_message)
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
