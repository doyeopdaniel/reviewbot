# 머니워크 리뷰 응답 자동화 시스템

LangChain 기반 RAG 아키텍처를 활용한 Google Play Store, Apple App Store 리뷰 자동 응답 시스템입니다.

## 주요 기능

- **자동 리뷰 분류**: AI 기반 리뷰 카테고리 자동 분류
- **RAG 기반 응답 생성**: 머니워크 공식 문서를 기반으로 한 정확한 응답 생성
- **국가별 대응**: 한국(KR), 미국(US) 별 맞춤형 응답
- **캐시 시스템**: 중복 응답 방지 및 성능 최적화
- **자동 업데이트**: 지식베이스 주기적 자동 업데이트

## 시스템 요구사항

- Python 3.8+
- OpenAI API Key

## 설치 및 설정

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정
```bash
# .env 파일 생성
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

### 3. 시스템 실행
```bash
python main.py
```

## 프로젝트 구조

```
├── main.py                 # 메인 실행 파일
├── config.py              # 시스템 설정
├── requirements.txt       # 의존성 목록
├── models/
│   └── review.py         # 데이터 모델
├── services/
│   ├── review_bot.py     # 메인 서비스
│   ├── vector_store.py   # 벡터 저장소 관리
│   ├── review_classifier.py  # 리뷰 분류
│   └── response_generator.py # 응답 생성
├── utils/
│   └── document_loader.py    # 문서 로더
└── schedulers/
    └── update_scheduler.py   # 자동 업데이트 스케줄러
```

## 사용 예시

### 단일 리뷰 처리
```python
from services.review_bot import ReviewBot
from models.review import Review

# 리뷰봇 초기화
bot = ReviewBot()
bot.initialize_knowledge_base()

# 리뷰 생성
review = Review(
    id="test_001",
    author="김민수",
    rating=2,
    content="잠자기 버튼이 사라졌어요",
    created_at=datetime.now(),
    country="KR",
    platform="google_play"
)

# 응답 생성
response = bot.process_review(review)
print(response.response_text)
```

## 라이센스

MIT License 