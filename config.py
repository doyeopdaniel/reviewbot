import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OpenAI API 설정
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # 임베딩 모델 설정
    EMBEDDING_MODEL = "text-embedding-3-small"
    
    # LLM 모델 설정
    LLM_MODEL = "gpt-4o-mini"  # 비용 효율적인 모델 사용
    
    # 문서 수집 URL (한국/미국만)
    KNOWLEDGE_BASE_URLS = {
        "kr": "https://docs.channel.io/moneywalk/ko",
        "us": "https://docs.channel.io/moneywalkus/en"
    }
    
    # 텍스트 분할 설정
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 100
    
    # 리뷰 응답 길이 제한
    MAX_RESPONSE_LENGTH = {
        "google_play": 350,
        "app_store": 500
    }
    
    # 벡터 저장소 설정
    VECTOR_STORE_PATH = "vector_stores"
    
    # 케이스 분류 (실제 케이스 기반으로 업데이트)
    REVIEW_CATEGORIES = [
        "포인트_관련",      # 포인트 미지급, 포인트 감소 등
        "광고_관련",        # 광고 시청 오류, 광고 포인트 미지급
        "기능_오류",        # 수면모드 오류, 걸음수 추적 오류
        "접근성",          # VoiceOver, 시각장애 관련
        "상품_교환",        # 교환상품 변경, 기프트카드 지연
        "친구_초대",        # 초대코드, 친구초대 관련
        "문의_누락",        # 앱에서 연락 안받음, 채널톡 연락 안받음
        "칭찬",           # 긍정적 피드백
        "기타"            # 기타 문의
    ]
    
    COUNTRIES = ["KR", "US"] 