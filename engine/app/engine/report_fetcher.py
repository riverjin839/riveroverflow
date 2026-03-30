"""
NAVER Finance 증권사 리포트 수집기.

https://finance.naver.com/research/company_list.naver 에서
최근 증권사 리포트 목록을 파싱해 dict 리스트로 반환한다.
"""
import logging
import re
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
    "Referer": "https://finance.naver.com/research/",
}
_BASE_URL = "https://finance.naver.com"
_LIST_URL = f"{_BASE_URL}/research/company_list.naver"


async def fetch_naver_reports(pages: int = 3) -> list[dict]:
    """NAVER Finance 리서치 섹션에서 최근 증권사 리포트 목록을 가져온다.

    Args:
        pages: 수집할 페이지 수 (기본 3 ≈ 최근 60건)

    Returns:
        리포트 dict 리스트. 각 항목:
          symbol, company_name, securities_firm, title,
          target_price, report_date, url, nid, source
    """
    all_reports: list[dict] = []
    async with httpx.AsyncClient(
        headers=_HEADERS,
        follow_redirects=True,
        timeout=20.0,
    ) as client:
        for page in range(1, pages + 1):
            try:
                resp = await client.get(_LIST_URL, params={"page": page})
                resp.raise_for_status()
                rows = _parse_page(resp.text)
                if not rows:
                    logger.debug("페이지 %d 파싱 결과 없음, 수집 종료", page)
                    break
                all_reports.extend(rows)
                logger.debug("리포트 페이지 %d 수집: %d건", page, len(rows))
            except httpx.HTTPStatusError as exc:
                logger.warning("NAVER Finance HTTP 오류 page=%d: %s", page, exc)
                break
            except Exception as exc:
                logger.warning("리포트 수집 실패 page=%d: %s", page, exc)
                break

    logger.info("NAVER Finance 리포트 수집 완료: 총 %d건 (요청 %d페이지)", len(all_reports), pages)
    return all_reports


def _parse_page(html: str) -> list[dict]:
    """HTML에서 리포트 행을 파싱해 dict 리스트로 반환."""
    soup = BeautifulSoup(html, "html.parser")

    # 리서치 테이블은 class="type_1" 인 table
    table = soup.find("table", class_="type_1")
    if table is None:
        logger.debug("type_1 테이블을 찾을 수 없음")
        return []

    results = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 6:
            continue

        try:
            # ── 종목명 + 종목코드 ──────────────────────
            company_cell = cells[0]
            company_name = company_cell.get_text(strip=True)
            symbol = None
            company_link = company_cell.find("a")
            if company_link:
                href = company_link.get("href", "")
                m = re.search(r"code=(\d{6})", href)
                symbol = m.group(1) if m else None

            # ── 제목 + URL + nid ──────────────────────
            title_cell = cells[1]
            title = title_cell.get_text(strip=True)
            url, nid = "", None
            title_link = title_cell.find("a")
            if title_link:
                href = title_link.get("href", "")
                url = (_BASE_URL + href) if href.startswith("/") else href
                m = re.search(r"nid=(\d+)", url)
                nid = m.group(1) if m else None

            # ── 증권사 ────────────────────────────────
            securities_firm = cells[2].get_text(strip=True)

            # ── 목표주가 (숫자만, 콤마·원 제거) ──────
            tp_raw = cells[3].get_text(strip=True).replace(",", "").replace("원", "").strip()
            target_price = float(tp_raw) if re.match(r"^\d+$", tp_raw) else None

            # ── 작성일 (YY.MM.DD) ─────────────────────
            date_text = cells[5].get_text(strip=True)
            report_date = _parse_date(date_text)

            if not company_name or not title:
                continue

            results.append({
                "symbol": symbol,
                "company_name": company_name,
                "securities_firm": securities_firm,
                "title": title,
                "target_price": target_price,
                "report_date": report_date,
                "url": url,
                "nid": nid,
                "source": "naver",
            })
        except Exception as exc:
            logger.debug("리포트 행 파싱 실패: %s", exc)
            continue

    return results


def _parse_date(text: str) -> date:
    text = text.strip()
    for fmt in ("%y.%m.%d", "%Y.%m.%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return date.today()
