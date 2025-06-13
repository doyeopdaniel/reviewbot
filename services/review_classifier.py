from typing import Dict
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from config import Config
from models.review import Review

class ReviewClassifier:
    """리뷰 분류 서비스"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=Config.LLM_MODEL,
            api_key=Config.OPENAI_API_KEY,
            temperature=0
        )
        
        self.classification_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 모바일 앱 리뷰를 분류하는 전문가입니다.
주어진 리뷰를 다음 카테고리 중 하나로 분류해주세요:

**카테고리 및 예시:**
- 포인트_관련: 포인트 미지급, 포인트 감소, 포인트 적립 문제
  예시: "광고보고 포인트 지급 안됨", "포인트가 줄어들었어요"
  
- 광고_관련: 광고 시청 오류, 광고 길이 문제, 광고 포인트 미지급
  예시: "광고가 안 나와요", "15초 광고라고 했는데 더 길어요"
  
- 기능_오류: 수면모드, 걸음수 추적, 앱 크래시 등 기능 문제
  예시: "수면모드 버튼이 안 눌려요", "걸음수가 정확하지 않아요", "앱이 계속 꺼져요"
  
- 접근성: VoiceOver, 시각장애, 접근성 관련 문제
  예시: "VoiceOver 사용이 어려워요", "시각장애인이 사용하기 힘들어요"
  
- 상품_교환: 기프트카드, 교환상품, 교환 포인트 변경
  예시: "기프트카드가 안 와요", "교환 포인트가 올랐어요"
  
- 친구_초대: 초대코드, 친구초대 기능 관련
  예시: "초대코드 입력했는데", "친구초대 보상"
  
- 문의_누락: 앱에서 연락 안받음, 채널톡에서 연락 안받음, 문의 답변 없음
  예시: "문의했는데 답변이 없어요", "채널톡으로 연락했는데 응답이 없어요", "앱에서 연락이 안 와요"
  
- 칭찬: 긍정적 피드백, 만족 표현, 감사 인사
  예시: "앱이 좋아요", "도움이 많이 돼요", "감사합니다"
  
- 기타: 위 카테고리에 해당하지 않는 경우

오직 카테고리명만 반환해주세요."""),
            ("user", "리뷰 내용: {review_content}")
        ])
    
    def classify_review(self, review: Review) -> str:
        """리뷰 분류"""
        try:
            chain = self.classification_prompt | self.llm
            result = chain.invoke({"review_content": review.content})
            
            category = result.content.strip()
            
            # 유효한 카테고리인지 확인
            if category in Config.REVIEW_CATEGORIES:
                return category
            else:
                return "기타"
                
        except Exception as e:
            print(f"리뷰 분류 오류: {e}")
            return "기타"
    
    def batch_classify_reviews(self, reviews: list[Review]) -> Dict[str, str]:
        """여러 리뷰 일괄 분류"""
        classifications = {}
        
        for review in reviews:
            category = self.classify_review(review)
            classifications[review.id] = category
            
        return classifications 