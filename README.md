# 국내 컴퓨터·보안 학회 일정판

정보보호·컴퓨팅 분야 국내 학회와 주요 국제 행사의 **일정과 발표논문 마감**을 한 화면에서 추적하는 정적 사이트. 크롤러가 매일 학회 사이트를 수집해 데이터를 갱신한다.

```
.
├── index.html              # 프론트엔드 (단일 파일, 빌드 불필요)
├── crawler.py              # 일정 크롤러 (시드 + 사이트별 파서 + 병합)
├── data/
│   └── conferences.json    # 크롤러가 갱신 / 프론트엔드가 읽음
└── .github/workflows/
    └── crawl.yml           # 매일 자동 크롤링 + GitHub Pages 배포
```

## 구조 (왜 이렇게?)

브라우저는 보안정책(CORS) 때문에 외부 학회 사이트를 직접 크롤링할 수 없다. 그래서:

```
[크롤러(Python, 매일 cron)] → [data/conferences.json] → [정적 프론트엔드가 읽음]
```

- 서버·DB가 없다 → 유지비 0원, GitHub Pages로 무료 호스팅·자동 갱신.
- 프론트엔드는 `data/conferences.json`을 읽되, **없으면 내장 시드 데이터로 폴백**한다. 그래서 로컬에서 `index.html`만 열어도 바로 동작한다(데모 모드).

## 바로 보기

`index.html`을 더블클릭해 브라우저로 열면 내장 데이터로 즉시 렌더링된다. (이때 `data/conferences.json`은 `file://` 보안정책상 안 읽히고 시드가 쓰인다 — 정상.)

## 로컬에서 크롤러+사이트 실행

```bash
pip install requests beautifulsoup4
python crawler.py                 # data/conferences.json 갱신
python -m http.server 8000        # http://localhost:8000 접속 → 크롤링 데이터로 표시됨
```

## GitHub Pages 배포 (자동 갱신)

1. 이 폴더를 GitHub 저장소로 push.
2. 저장소 **Settings → Pages → Source = GitHub Actions** 설정.
3. **Settings → Actions → General → Workflow permissions = Read and write** 허용.
4. 끝. 매일 06:00 KST에 크롤러가 돌고, 변경분이 커밋되며, Pages가 재배포된다. `Actions` 탭에서 수동 실행(`Run workflow`)도 가능.

## 데이터 스키마

```jsonc
{
  "id": "kcc-2026",          // 고유 id (병합 키)
  "name": "한국컴퓨터종합학술대회 (KCC 2026)",
  "host": "한국정보과학회 (KIISE)",
  "scope": "국내",            // 국내 | 국제 | 산업
  "cat": "컴퓨팅 일반",        // 정보보호 | 컴퓨팅 일반 | 소프트웨어 | 시스템 | 산업/정부
  "start": "2026-06-24",
  "end": "2026-06-26",
  "city": "제주",
  "venue": "ICC 제주",
  "cfp": "2026-04-30",        // 발표논문 마감 (없으면 null)
  "url": "https://...",
  "confirmed": true,          // false = 예년 기준 추정 (화면에 '추정' 표시)
  "note": "국내 최대 컴퓨터 학술대회"
}
```

## 크롤러 동작 원칙

- **시드 우선·검증 데이터 보호.** `crawler.py`의 `SEED`는 사람이 검증한 기준 데이터. 크롤링이 전부 실패해도 최소 이 값이 출력된다.
- **확정 항목은 날짜를 덮어쓰지 않는다.** 불완전한 파싱이 검증 데이터를 훼손하지 못하게, `confirmed:true`인 항목은 날짜를 유지하고 비어있는 `cfp`만 보충한다.
- **추정 항목만 승격.** `confirmed:false`(추정) 항목은 유효한 크롤링 날짜(start·end 둘 다, end≥start)가 잡히면 갱신하고 확정으로 올린다.
- **소스별 격리.** 한 사이트가 막히거나(예: 403) 구조가 바뀌어도 경고만 남기고 나머지는 계속 수집한다.

## 새 학회 추가 / 파서 확장

- **일정만 추가:** `crawler.py`의 `SEED`(또는 `data/conferences.json`)에 항목 한 줄 추가.
- **자동 수집 추가:** `scrape_*()` 함수를 만들어 `SCRAPERS` 리스트에 등록. 대부분 게시판형이라 `parse_korean_range()`(한국어 날짜 파서)를 그대로 재사용하면 된다. KSCI·KCSA·KICS·KIPS(ASK) 등이 후보.

## 데이터 출처

한국정보보호학회(KIISC/CISC), 한국정보과학회(KIISE), WISA, ICISC, 한국컴퓨터정보학회(KSCI), 한국융합보안학회(KCSA). 일부 일정은 발표 전이라 예년 기준 추정값이며, 확정 공지가 나오면 크롤러가 갱신한다.
