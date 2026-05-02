"""테넌트 yaml 기반 리뷰 카테고리 분류 (Premium 플랜 전용)"""

import logging
from typing import Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from config import Config
from models.review import Review

logger = logging.getLogger(__name__)


class ReviewClassifier:
    """리뷰를 테넌트 정의 카테고리 중 하나로 분류"""

    def __init__(self, tenant_config: dict | None = None):
        cfg = (tenant_config or Config.TENANT_CONFIG)["response_generator"]
        classifier_cfg = cfg.get("classifier", {})
        if not classifier_cfg.get("enabled"):
            raise ValueError(
                "현재 테넌트는 카테고리 분류기를 사용하지 않습니다 "
                f"(tenant={Config.TENANT}). yaml의 classifier.enabled를 true로 설정하세요."
            )

        self.categories: List[str] = classifier_cfg["categories"]
        descriptions = classifier_cfg.get("descriptions", {})
        category_block = "\n".join(
            f"- {name}: {descriptions.get(name, '')}".rstrip(": ")
            for name in self.categories
        )

        self.llm = ChatOpenAI(
            model_name=Config.LLM_MODEL,
            api_key=Config.OPENAI_API_KEY,
            temperature=0,
        )

        self.classification_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""당신은 모바일 앱 리뷰를 분류하는 전문가입니다.
주어진 리뷰를 다음 카테고리 중 하나로 분류해주세요:

{category_block}

오직 카테고리명만 반환해주세요."""),
            ("user", "리뷰 내용: {review_content}"),
        ])

    def classify_review(self, review: Review) -> str:
        try:
            chain = self.classification_prompt | self.llm
            result = chain.invoke({"review_content": review.content})
            category = result.content.strip()
            return category if category in self.categories else "기타"
        except Exception as e:
            logger.error(f"리뷰 분류 오류: {e}")
            return "기타"

    def batch_classify_reviews(self, reviews: List[Review]) -> Dict[str, str]:
        return {review.id: self.classify_review(review) for review in reviews}
