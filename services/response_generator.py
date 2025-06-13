from typing import List
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from config import Config
from models.review import Review, ReviewResponse
from services.vector_store import VectorStoreService

class ResponseGenerator:
    """리뷰 응답 생성 서비스"""
    
    def __init__(self, vector_store_service: VectorStoreService):
        self.llm = ChatOpenAI(
            model=Config.LLM_MODEL,
            api_key=Config.OPENAI_API_KEY,
            temperature=0.3
        )
        self.vector_store_service = vector_store_service
        
        # 국가별 프롬프트 템플릿
        self.kr_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 머니워크 운영팀을 대신하여 공식적이고 정중한 리뷰 답변을 작성하는 어시스턴트입니다.

다음 공식 답변 형식을 반드시 따라 답변을 작성하세요:

**기본 구조:**
1. "안녕하세요, 머니워크 운영팀입니다" 또는 "**안녕하세요, 머니워크 운영팀입니다.**"
2. "소중한 시간을 내어 리뷰를 남겨주셔서 감사합니다."
3. 리뷰 내용에 맞는 구체적이고 정중한 응답
4. 해결책이나 안내사항 제시
5. "**1:1 문의**" 또는 "**앱 내 1:1 문의**"로 추가 도움 유도

**실제 답변 예시:**

**현금 인출 관련:**
"더 나은 서비스를 제공하기 위한 기능 업데이트 과정에서 약 3~4일간 일시적으로 현금 인출 기능이 표시되지 않았을 수 있습니다. 현재는 정상적으로 이용 가능하오니 다시 한번 확인 부탁드립니다."

**문의 답변 지연:**
"문의 답변이 지연되어 불편을 드려 죄송합니다. 채팅 문의의 특성상 간혹 누락이 발생할 수 있으며, 이런 경우 기존 문의가 아닌 **'새 문의'**로 다시 남겨주시면 더욱 신속하게 확인하여 답변드리겠습니다."

**기능 변경:**
"기존 기능을 유지하는 것보다, **유저분들께 더욱 유용한 경험을 제공하기 위해 새로운 기능 개발에 집중하고 있습니다.** 앞으로도 지속적인 개선을 통해 더 나은 서비스를 제공할 수 있도록 노력하겠습니다."

**상품 변경:**
"쿠폰의 경우 공급 상황에 따라 구성이 변경될 수 있으며, 더 많은 상품을 제공하기 위해 이번 **선물샵 개편을 통해 300여 가지의 새로운 상품을 추가했습니다.**"

**일반적인 불편사항:**
"이용 중 불편을 겪으셨다니 죄송한 마음입니다. 정확한 확인을 위해 **앱 내 1:1 문의**를 남겨주시면 신속하게 도움을 드리겠습니다. 유저분들의 피드백을 소중하게 생각하며, 더 나은 서비스 제공을 위해 지속적으로 개선하겠습니다."

**작성 가이드라인:**
- 공식적이고 정중한 톤 유지
- **볼드체**로 중요 부분 강조
- 구체적인 해결책이나 설명 제시
- 사과와 감사 표현 적극 활용
- "1:1 문의" 적극 유도
- {max_length}자 이내로 작성

참고할 지식베이스:
{knowledge_context}"""),
            ("user", """작성자: {author}
국가: {country}
리뷰 카테고리: {category}
리뷰 내용: "{review_content}"

위 리뷰에 대한 머니워크 운영팀 공식 스타일의 한국어 답변을 작성해주세요.""")
        ])
        
        self.us_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a review assistant that writes responses on behalf of the MoneyWalk team.

Please refer to these actual response examples to write natural and helpful responses:

**Actual Response Examples:**
- Step Tracking Error: "Hi [Name], sorry for the confusion! Step data may sync differently depending on your phone's motion settings. Please check if the app has motion permission enabled in Settings."
- Accessibility: "Hi [Name], thank you for your feedback and for using VoiceOver. We're aware of this issue and working to improve accessibility. Your input truly helps us build a better experience."
- Reward Delays: "Hi [Name], sorry to hear that. Gift card delivery may take some time depending on provider. If you still haven't received it, please contact us through the in-app Help Center."
- Points Decrease: "Hi [Name], thanks for your feedback. Point amounts may change over time based on app events and level progress. We appreciate your continued support!"

**Response Guidelines:**
1. Start with personalized greeting: "Hi [Name]" (only if name is appropriate)
2. Provide specific solutions or explanations
3. Direct users to "in-app Help Center" for further assistance
4. Use friendly and helpful tone
5. Keep within {max_length} characters

Knowledge base for reference:
{knowledge_context}"""),
            ("user", """Author: {author}
Country: {country}
Review Category: {category}
Review Content: "{review_content}"

Please write a natural and helpful English response to the above review.""")
        ])
    
    def generate_response(self, review: Review, category: str) -> ReviewResponse:
        """리뷰에 대한 응답 생성"""
        try:
            # RAG 검색으로 관련 문서 검색
            relevant_docs = self.vector_store_service.similarity_search(
                review.content, 
                review.country.lower(), 
                k=3
            )
            
            # 지식베이스 컨텍스트 구성
            knowledge_context = "\n\n".join([
                f"문서 {i+1}: {doc.page_content}" 
                for i, doc in enumerate(relevant_docs)
            ])
            
            # 응답 길이 제한 설정
            max_length = Config.MAX_RESPONSE_LENGTH.get(review.platform, 350)
            
            # 국가별 프롬프트 선택
            if review.country.upper() == "KR":
                prompt = self.kr_prompt
            else:
                prompt = self.us_prompt
            
            # 사용자명 처리 (짧고 적절한 경우만 사용)
            author_name = self._process_author_name(review.author)
            
            # 응답 생성
            chain = prompt | self.llm
            result = chain.invoke({
                "author": author_name,
                "country": review.country,
                "category": category,
                "review_content": review.content,
                "knowledge_context": knowledge_context,
                "max_length": max_length
            })
            
            response_text = result.content.strip()
            
            # 길이 제한 확인 및 조정
            if len(response_text) > max_length:
                response_text = self._truncate_response(response_text, max_length)
            
            # 사용된 소스 추출
            used_sources = [doc.metadata.get('source', '') for doc in relevant_docs]
            
            return ReviewResponse(
                review_id=review.id,
                response_text=response_text,
                generated_at=datetime.now(),
                country=review.country,
                platform=review.platform,
                used_sources=used_sources
            )
            
        except Exception as e:
            print(f"응답 생성 오류: {e}")
            # 기본 응답 반환
            return self._generate_fallback_response(review, category)
    
    def _process_author_name(self, author: str) -> str:
        """작성자명 처리 (길거나 부적절한 이름 필터링)"""
        if not author or len(author) > 10 or any(char in author for char in ['@', '#', '$', '%']):
            return ""
        return author
    
    def _truncate_response(self, response: str, max_length: int) -> str:
        """응답 길이 조정"""
        if len(response) <= max_length:
            return response
        
        # 문장 단위로 자르기 시도
        sentences = response.split('.')
        truncated = ""
        
        for sentence in sentences:
            if len(truncated + sentence + ".") <= max_length - 10:  # 여유 공간 확보
                truncated += sentence + "."
            else:
                break
        
        if not truncated:
            # 문장 단위로 자르기 실패 시 글자 단위로 자르기
            truncated = response[:max_length-10] + "..."
        
        return truncated.strip()
    
    def _generate_fallback_response(self, review: Review, category: str) -> ReviewResponse:
        """기본 응답 생성 (오류 발생 시)"""
        if review.country.upper() == "KR":
            response_text = """**안녕하세요, 머니워크 운영팀입니다.**

소중한 시간을 내어 리뷰를 남겨주셔서 감사합니다.

더 정확한 확인을 위해 **앱 내 1:1 문의**를 남겨주시면 신속하게 도움을 드리겠습니다.

지속적으로 더 나은 서비스 제공을 위해 노력하겠습니다."""
        else:
            response_text = "Hi, thank you for your valuable feedback. We're continuously working to improve our service. Thank you!"
        
        return ReviewResponse(
            review_id=review.id,
            response_text=response_text,
            generated_at=datetime.now(),
            country=review.country,
            platform=review.platform,
            used_sources=[]
        ) 