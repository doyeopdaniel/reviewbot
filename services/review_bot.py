"""리뷰봇 메인 서비스 (테넌트 yaml 기반)

- 내친소(lite): 4~5점 긍정 리뷰만, 카테고리 분류 없음
- 머니워크(premium): 1~5점 전체, 카테고리 분류 후 응답
"""

import hashlib
import json
import logging
import os
from typing import Dict, List

from config import Config
from models.review import Review, ReviewResponse
from services.response_generator import ResponseGenerator

logger = logging.getLogger(__name__)

CACHE_FILE = "response_cache.json"


class ReviewBot:
    """리뷰 응답 봇 (테넌트 설정에 따라 분류기 옵션 활성화)"""

    def __init__(self, tenant_config: dict | None = None):
        self.tenant_config = tenant_config or Config.TENANT_CONFIG
        self.response_generator = ResponseGenerator(self.tenant_config)

        classifier_cfg = self.tenant_config["response_generator"].get(
            "classifier", {}
        )
        if classifier_cfg.get("enabled"):
            from services.review_classifier import ReviewClassifier

            self.classifier = ReviewClassifier(self.tenant_config)
        else:
            self.classifier = None

        self.response_cache = self._load_cache()

    def process_review(self, review: Review) -> ReviewResponse | None:
        """단일 리뷰 처리. 비꼬는 리뷰는 None 반환."""
        cache_key = hashlib.md5(
            f"{review.content}_{review.country}_{review.platform}".encode()
        ).hexdigest()

        if cache_key in self.response_cache:
            logger.info(f"캐시 사용: {review.id}")
            return ReviewResponse(**self.response_cache[cache_key])

        category = "칭찬"
        if self.classifier is not None:
            category = self.classifier.classify_review(review)
            review.category = category

        response = self.response_generator.generate_response(review, category=category)

        if response is None:
            logger.info(f"응답 스킵 (비꼬는 리뷰): {review.id}")
            return None

        self.response_cache[cache_key] = response.dict()
        self._save_cache()

        return response

    def process_reviews_batch(self, reviews: List[Review]) -> List[ReviewResponse]:
        """일괄 처리"""
        responses: List[ReviewResponse] = []
        total = len(reviews)

        for i, review in enumerate(reviews, 1):
            logger.info(f"처리 중: {i}/{total} - {review.id}")
            try:
                result = self.process_review(review)
                if result is not None:
                    responses.append(result)
            except Exception as e:
                logger.error(f"리뷰 처리 오류 {review.id}: {e}")

        logger.info(f"총 {len(responses)}개 응답 생성 완료")
        return responses

    def get_statistics(self) -> Dict:
        return {"총 생성된 응답": len(self.response_cache)}

    def clear_cache(self):
        self.response_cache = {}
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
        print("캐시가 초기화되었습니다.")

    def _load_cache(self) -> Dict:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"캐시 로드 오류: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    self.response_cache, f, ensure_ascii=False, indent=2, default=str
                )
        except Exception as e:
            logger.error(f"캐시 저장 오류: {e}")
