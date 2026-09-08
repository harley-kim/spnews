# SP News

썬포토(주) 취급 브랜드의 해외 공식 뉴스와 주요 사진/영상 미디어 기사를 모아 한국어로 보여주는 반응형 뉴스 허브입니다.

## 핵심 기능

- 해외 제조사 공식 뉴스 + DPReview / Digital Camera Watch 등 미디어 수집
- 썬포토 취급 브랜드 키워드 필터링
- Gemini API를 이용한 한국어 제목/요약 번역
- YouTube Data API를 이용한 한국어 리뷰 영상 수집
- PC / 모바일 반응형 타임라인 UI
- 브랜드 필터, 검색, 뉴스/영상 필터
- GitHub Actions로 매일 **09:00 / 18:00 KST** 자동 업데이트
- 정적 사이트 구조라 Netlify / Vercel / GitHub Pages에 바로 배포 가능

## 자동 업데이트용 GitHub Secrets

Repository → Settings → Secrets and variables → Actions에서 아래 값을 등록합니다.

- `GEMINI_API_KEY`: Google AI Studio API Key. 없으면 원문 제목을 그대로 사용합니다.
- `YOUTUBE_API_KEY`: YouTube Data API v3 Key. 없으면 뉴스만 갱신됩니다.

## 로컬 실행

```bash
python -m http.server 8080
```

브라우저에서 `http://localhost:8080`을 엽니다.

뉴스 수집기를 직접 실행하려면:

```bash
pip install -r requirements.txt
python scripts/update_news.py
```

## 배포

정적 사이트이므로 저장소 루트를 publish directory로 지정하면 됩니다. `netlify.toml`이 포함되어 있어 Netlify에서는 별도 빌드 명령 없이 배포할 수 있습니다.

## 데이터

`data/news.json`은 자동 생성됩니다. GitHub Actions가 새 뉴스가 있을 때만 파일을 커밋합니다.
