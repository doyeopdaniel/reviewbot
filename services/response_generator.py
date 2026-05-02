"""테넌트 주입형 리뷰 응답 생성 서비스 (내친소 lite / 머니워크 premium)"""

import logging
import random
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from config import Config
from models.review import Review, ReviewResponse

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """리뷰 응답 생성 (테넌트 yaml 기반)"""

    def __init__(self, tenant_config: dict | None = None):
        cfg = (tenant_config or Config.TENANT_CONFIG)["response_generator"]
        self.cfg = cfg
        self.personas: list[str] = cfg["personas"]
        self.greeting_template: str = cfg["greeting_template"]
        self.fallback_response: str = cfg["fallback_response"]

        self.short_review_cfg = cfg.get("short_review", {"enabled": False})
        self.sarcasm_cfg = cfg.get("sarcasm_filter", {"enabled": False})
        self.classifier_cfg = cfg.get("classifier", {"enabled": False})

        self.llm = ChatOpenAI(
            model_name=Config.LLM_MODEL,
            api_key=Config.OPENAI_API_KEY,
            temperature=0.7,
        )

        messages = [("system", cfg["system_prompt"])]
        for shot in cfg.get("few_shots", []):
            messages.append(("human", shot["human"]))
            messages.append(("assistant", shot["assistant"]))

        if self.classifier_cfg.get("enabled"):
            messages.append((
                "human",
                "리뷰 카테고리: {category}\n리뷰 내용: {review_content}",
            ))
        else:
            messages.append(("human", "리뷰 내용: {review_content}"))

        self.prompt = ChatPromptTemplate.from_messages(messages)

    def _greet(self, persona: str) -> str:
        return self.greeting_template.format(persona=persona)

    def _is_short_review(self, content: str) -> bool:
        sr = self.short_review_cfg
        if not sr.get("enabled"):
            return False
        stripped = content.strip().rstrip(".!~ㅋㅎ")
        keywords = sr.get("keywords", [])
        if (
            len(stripped) <= sr.get("max_length_with_keyword", 10)
            and any(kw in stripped for kw in keywords)
        ):
            return True
        if len(stripped) <= sr.get("max_length_no_keyword", 5):
            return True
        return False

    def _is_sarcastic(self, content: str) -> bool:
        sf = self.sarcasm_cfg
        if not sf.get("enabled"):
            return False
        return any(kw in content for kw in sf.get("keywords", []))

    def _build_short_response(self, review: Review) -> ReviewResponse:
        persona = random.choice(self.personas)
        body = random.choice(self.short_review_cfg["responses"])
        text = f"{self._greet(persona)} {body}"
        return ReviewResponse(
            review_id=review.id,
            response_text=text,
            generated_at=datetime.now(),
            country=review.country,
            platform=review.platform,
            used_sources=[],
        )

    def generate_response(
        self,
        review: Review,
        category: str = "칭찬",
    ) -> ReviewResponse | None:
        """리뷰 응답 생성. 비꼬는 리뷰는 None."""
        if self._is_sarcastic(review.content):
            logger.info(f"비꼬는 리뷰 스킵: {review.id} - {review.content[:30]}")
            return None

        if self._is_short_review(review.content):
            logger.info(f"짧은 리뷰 고정 응답: {review.id}")
            return self._build_short_response(review)

        try:
            persona = random.choice(self.personas)
            chain = self.prompt | self.llm
            invoke_kwargs = {
                "review_content": review.content,
                "persona": persona,
                "max_length": Config.MAX_RESPONSE_LENGTH.get(review.platform, 350),
            }
            if self.classifier_cfg.get("enabled"):
                invoke_kwargs["category"] = category
            result = chain.invoke(invoke_kwargs)
            response_text = result.content.strip().replace("**", "")

            max_length = Config.MAX_RESPONSE_LENGTH.get(review.platform, 350)
            if len(response_text) > max_length:
                response_text = self._truncate(response_text, max_length)

            return ReviewResponse(
                review_id=review.id,
                response_text=response_text,
                generated_at=datetime.now(),
                country=review.country,
                platform=review.platform,
                used_sources=[],
            )

        except Exception as e:
            logger.error(f"응답 생성 오류: {e}")
            persona = random.choice(self.personas)
            return ReviewResponse(
                review_id=review.id,
                response_text=f"{self._greet(persona)} {self.fallback_response}",
                generated_at=datetime.now(),
                country=review.country,
                platform=review.platform,
                used_sources=[],
            )

    @staticmethod
    def _truncate(text: str, max_length: int) -> str:
        sentences = text.split(".")
        result = ""
        for s in sentences:
            if len(result + s + ".") <= max_length - 5:
                result += s + "."
            else:
                break
        return result.strip() if result else text[: max_length - 3] + "..."
