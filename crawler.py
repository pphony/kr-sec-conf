#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
국내 컴퓨터·보안 학회 일정 크롤러
================================

동작 방식
---------
1. SEED: 사람이 검증한 기준 일정(아래 리스트). 크롤링이 모두 실패해도
   최소 이 데이터로 conferences.json 이 채워진다.
2. 각 학회 사이트별 파서가 best-effort 로 최신 일정을 긁어온다.
   - 사이트 구조가 자주 바뀌고 일부는 JS 렌더링이라, 파서는 "보조 수단"이다.
   - 한 소스가 실패해도 전체 실행은 계속된다(소스별 try/except).
3. merge(): 크롤링 결과를 id 기준으로 SEED 에 덮어쓴다.
   - 크롤링으로 확정된 항목은 confirmed=True 로 승격된다.
4. data/conferences.json 으로 저장(프론트엔드가 이 파일을 읽음).

의존성:  pip install requests beautifulsoup4
실행:    python crawler.py
"""

import json
import re
import sys
import datetime as dt
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("의존성 누락: pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)

OUT = Path(__file__).parent / "data" / "conferences.json"
KST = dt.timezone(dt.timedelta(hours=9))
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ConfCalendarBot/1.0; academic schedule aggregator)"}
TIMEOUT = 15

# ---------------------------------------------------------------------------
# SEED — 사람이 검증한 기준 데이터 (확정/추정 혼합)
# ---------------------------------------------------------------------------
SEED = [
    {"id":"csc-2026","name":"정보과학회 컴퓨터시스템 동계학술대회","host":"한국정보과학회 컴퓨터시스템 소사이어티","scope":"국내","cat":"시스템","start":"2026-01-19","end":"2026-01-21","city":"평창","venue":"모나용평 그린피아","cfp":None,"url":"https://css.or.kr/csc2026","confirmed":True,"note":""},
    {"id":"secon-2026","name":"전자정부 정보보호 콘퍼런스 (SECON & eGISEC)","host":"보안뉴스 외","scope":"산업","cat":"산업/정부","start":"2026-03-18","end":"2026-03-20","city":"고양","venue":"일산 킨텍스","cfp":None,"url":"https://www.seconexpo.com","confirmed":True,"note":"4개 트랙 52개 강연"},
    {"id":"cisc-s-2026","name":"한국정보보호학회 하계학술대회 (CISC-S'26)","host":"한국정보보호학회 (KIISC)","scope":"국내","cat":"정보보호","start":"2026-05-07","end":"2026-05-08","city":"부산","venue":"벡스코 제2전시장","cfp":None,"url":"https://www.cisc.or.kr","confirmed":True,"note":""},
    {"id":"typhooncon-2026","name":"TyphoonCon 2026","host":"SSD Secure Disclosure","scope":"산업","cat":"정보보호","start":"2026-05-28","end":"2026-05-29","city":"서울","venue":"Moxy 명동","cfp":None,"url":"https://typhooncon.com","confirmed":True,"note":"공격보안 컨퍼런스 (트레이닝 5/25~27)"},
    {"id":"kcc-2026","name":"한국컴퓨터종합학술대회 (KCC 2026)","host":"한국정보과학회 (KIISE)","scope":"국내","cat":"컴퓨팅 일반","start":"2026-06-24","end":"2026-06-26","city":"제주","venue":"ICC 제주","cfp":"2026-04-30","url":"https://www.kiise.or.kr/conference/kcc/2026/","confirmed":True,"note":"국내 최대 컴퓨터 학술대회"},
    {"id":"ksci-summer-2026","name":"한국컴퓨터정보학회 하계학술대회 (제74차)","host":"한국컴퓨터정보학회 (KSCI)","scope":"국내","cat":"컴퓨팅 일반","start":"2026-07-15","end":"2026-07-17","city":"미정","venue":"미정","cfp":None,"url":"https://ksci.re.kr","confirmed":False,"note":"예년 7월 개최 기준 추정"},
    {"id":"wisa-2026","name":"WISA 2026 — 27th World Conf. on Info. Security Applications","host":"KIISC · ETRI","scope":"국제","cat":"정보보호","start":"2026-08-26","end":"2026-08-28","city":"제주","venue":"MAISON GLAD Jeju","cfp":None,"url":"https://wisa.or.kr","confirmed":True,"note":"AI·블록체인·HW 암호 등"},
    {"id":"cisc-w-2026","name":"한국정보보호학회 동계학술대회 (CISC-W'26)","host":"한국정보보호학회 (KIISC)","scope":"국내","cat":"정보보호","start":"2026-11-27","end":"2026-11-28","city":"미정","venue":"미정","cfp":None,"url":"https://www.cisc.or.kr","confirmed":False,"note":"예년 11월 말 개최 기준 추정"},
    {"id":"kcsa-fall-2026","name":"한국융합보안학회 추계학술대회","host":"한국융합보안학회 (KCSA)","scope":"국내","cat":"정보보호","start":"2026-11-13","end":"2026-11-13","city":"미정","venue":"미정","cfp":None,"url":"http://www.kcgsa.org","confirmed":False,"note":"예년 기준 추정"},
    {"id":"icisc-2026","name":"ICISC 2026 — 29th Int'l Conf. on Info. Security & Cryptology","host":"한국정보보호학회 (KIISC)","scope":"국제","cat":"정보보호","start":"2026-12-02","end":"2026-12-04","city":"서울","venue":"미정","cfp":"2026-09-01","url":"http://www.icisc.org","confirmed":False,"note":"예년 11~12월 개최/마감 기준 추정"},
    {"id":"ksc-2026","name":"한국소프트웨어종합학술대회 (KSC 2026)","host":"한국정보과학회 (KIISE)","scope":"국내","cat":"소프트웨어","start":"2026-12-16","end":"2026-12-18","city":"미정","venue":"미정","cfp":None,"url":"https://www.kiise.or.kr","confirmed":False,"note":"예년 12월 개최 기준 추정"},
]

# ---------------------------------------------------------------------------
# 날짜 파싱 유틸 — 한국어 날짜 표기 → ISO(YYYY-MM-DD)
# ---------------------------------------------------------------------------
def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    return r.text

def parse_korean_range(text, default_year=None):
    """
    '2026년 05월 07일 ~ 08일', '6.24(수)~26(금)', '2026-08-26 ~ 2026-08-28'
    같은 표기에서 (start_iso, end_iso) 를 추출. 실패 시 (None, None).
    """
    if not text:
        return None, None
    t = re.sub(r"\([월화수목금토일]\)", "", text)  # (수) 요일 제거
    t = t.replace("．", ".").strip()
    year = default_year or dt.datetime.now(KST).year

    # 패턴 A: 2026년 5월 7일 ~ 8일  /  2026년 5월 7일
    m = re.search(r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일"
                  r"(?:\s*[~∼\-–]\s*(?:(\d{1,2})\s*월\s*)?(\d{1,2})\s*일)?", t)
    if m:
        y, mo, d1 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        mo2 = int(m.group(4)) if m.group(4) else mo
        d2 = int(m.group(5)) if m.group(5) else d1
        return f"{y:04d}-{mo:02d}-{d1:02d}", f"{y:04d}-{mo2:02d}-{d2:02d}"

    # 패턴 B: 6.24~26  또는 6.24~6.26
    m = re.search(r"(\d{1,2})\.(\d{1,2})\s*[~∼\-–]\s*(?:(\d{1,2})\.)?(\d{1,2})", t)
    if m:
        mo, d1 = int(m.group(1)), int(m.group(2))
        mo2 = int(m.group(3)) if m.group(3) else mo
        d2 = int(m.group(4))
        return f"{year:04d}-{mo:02d}-{d1:02d}", f"{year:04d}-{mo2:02d}-{d2:02d}"

    # 패턴 C: 2026-08-26 ~ 2026-08-28
    iso = re.findall(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})", t)
    if iso:
        a = iso[0]
        b = iso[1] if len(iso) > 1 else iso[0]
        return f"{int(a[0]):04d}-{int(a[1]):02d}-{int(a[2]):02d}", f"{int(b[0]):04d}-{int(b[1]):02d}-{int(b[2]):02d}"

    return None, None

# ---------------------------------------------------------------------------
# 사이트별 파서 (best-effort)
#   각 파서는 {id: {갱신할 필드}} 형태의 dict 를 반환한다.
#   * 사이트 구조 변경 시 셀렉터/정규식만 손보면 된다.
#   * 실패하면 빈 dict 반환 → SEED 값 유지.
# ---------------------------------------------------------------------------
def scrape_cisc():
    """한국정보보호학회 학술대회 메인(하계/동계 일정 노출)."""
    out = {}
    try:
        html = fetch("https://www.cisc.or.kr/")
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        # 하계
        m = re.search(r"하계학술대회.{0,60}?(20\d{2}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일[^·\n]{0,30})", text)
        if m:
            s, e = parse_korean_range(m.group(1))
            if s:
                out["cisc-s-2026"] = {"start": s, "end": e, "confirmed": True}
        # 동계
        m = re.search(r"동계학술대회.{0,60}?(20\d{2}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일[^·\n]{0,30})", text)
        if m:
            s, e = parse_korean_range(m.group(1))
            if s:
                out["cisc-w-2026"] = {"start": s, "end": e, "confirmed": True}
    except Exception as ex:
        log("cisc", ex)
    return out

def scrape_kiise_kcc():
    """한국정보과학회 메인 공지에서 KCC/KSC 일정·논문마감."""
    out = {}
    try:
        html = fetch("https://kiise.or.kr/academy/main/main.fa")
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        m = re.search(r"KCC\s*20\d{2}.{0,40}?(\d{1,2}\.\d{1,2}[^,]{0,20}[~∼]\s*\d{1,2})", text)
        if m:
            s, e = parse_korean_range(m.group(1), default_year=2026)
            if s:
                out["kcc-2026"] = {"start": s, "end": e, "confirmed": True}
        dl = re.search(r"논문접수마감\s*[:：]?\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
        if dl and "kcc-2026" in out:
            out["kcc-2026"]["cfp"] = f"2026-{int(dl.group(1)):02d}-{int(dl.group(2)):02d}"
    except Exception as ex:
        log("kiise", ex)
    return out

def scrape_wisa():
    """WISA 메인 상단 배너의 'August 26-28, 2026' 류 영문 일자."""
    out = {}
    try:
        html = fetch("https://wisa.or.kr/")
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        m = re.search(r"([A-Z][a-z]+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2}),?\s*(20\d{2})", text)
        if m:
            months = {n: i for i, n in enumerate(
                ["January","February","March","April","May","June","July",
                 "August","September","October","November","December"], 1)}
            mo = months.get(m.group(1))
            if mo:
                y = int(m.group(4))
                out["wisa-2026"] = {
                    "start": f"{y}-{mo:02d}-{int(m.group(2)):02d}",
                    "end":   f"{y}-{mo:02d}-{int(m.group(3)):02d}",
                    "confirmed": True}
    except Exception as ex:
        log("wisa", ex)
    return out

def scrape_icisc():
    """ICISC Important Dates 페이지에서 마감/개최일 추출(텍스트 기반)."""
    out = {}
    try:
        html = fetch("http://www.icisc.org/")
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        s, e = parse_korean_range(text)
        if s:
            out["icisc-2026"] = {"start": s, "end": e, "confirmed": True}
    except Exception as ex:
        log("icisc", ex)
    return out

SCRAPERS = [scrape_cisc, scrape_kiise_kcc, scrape_wisa, scrape_icisc]
# TODO: KSCI(ksci.re.kr), KCSA(kcgsa.org), KICS, KIPS(ASK) 파서 추가 가능.
#       대부분 게시판형이라 위 패턴을 재사용하면 된다.

# ---------------------------------------------------------------------------
def log(src, ex):
    print(f"[warn] {src}: {type(ex).__name__}: {ex}", file=sys.stderr)

def merge(seed, scraped):
    """
    병합 정책 (사람이 검증한 데이터 보호 우선):
    - 시드가 이미 confirmed=True 면 → 날짜(start/end)는 덮어쓰지 않는다.
      (불완전한 크롤링 파싱이 검증 데이터를 훼손하는 것을 방지)
      단, 비어있던 cfp(논문마감)는 채울 수 있다.
    - 시드가 confirmed=False(추정)면 → 유효한 크롤링 날짜로 갱신하고 True 로 승격.
    - 유효성: start/end 둘 다 있고 end >= start 일 때만 날짜를 신뢰한다.
    """
    by_id = {c["id"]: dict(c) for c in seed}
    changed = 0
    for cid, fields in scraped.items():
        if cid not in by_id or not fields:
            continue
        cur = by_id[cid]
        applied = {}

        s, e = fields.get("start"), fields.get("end")
        valid_range = bool(s and e and e >= s)

        if valid_range and not cur.get("confirmed"):
            # 추정 항목만 날짜 갱신 + 확정 승격
            applied.update({"start": s, "end": e, "confirmed": True})
        # cfp 는 비어있을 때만 보충 (확정/추정 공통)
        if fields.get("cfp") and not cur.get("cfp"):
            applied["cfp"] = fields["cfp"]

        if applied:
            cur.update(applied)
            changed += 1
            print(f"[ok] {cid} 갱신: {applied}")
    return list(by_id.values()), changed

def main():
    scraped = {}
    for fn in SCRAPERS:
        try:
            scraped.update(fn())
        except Exception as ex:
            log(fn.__name__, ex)

    confs, changed = merge(SEED, scraped)
    confs.sort(key=lambda c: c["start"])
    payload = {
        "updated": dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
        "conferences": confs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장 완료: {OUT}  (총 {len(confs)}건, 크롤링 갱신 {changed}건)")

if __name__ == "__main__":
    main()
