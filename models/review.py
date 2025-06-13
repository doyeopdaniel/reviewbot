from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Review(BaseModel):
    """리뷰 데이터 모델"""
    id: str
    author: str
    rating: int
    content: str
    created_at: datetime
    country: str  # KR, US
    platform: str  # google_play, app_store
    category: Optional[str] = None  # 분류된 카테고리
    
class ReviewResponse(BaseModel):
    """리뷰 응답 데이터 모델"""
    review_id: str
    response_text: str
    generated_at: datetime
    country: str
    platform: str
    used_sources: list[str] = []  # RAG에서 사용된 문서 소스들 