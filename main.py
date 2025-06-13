#!/usr/bin/env python3
"""
머니워크 리뷰 응답 자동화 시스템
LangChain 기반 RAG 아키텍처를 활용한 리뷰봇
"""

import os
import sys
from datetime import datetime
from models.review import Review
from services.review_bot import ReviewBot
from schedulers.update_scheduler import UpdateScheduler

def create_sample_reviews():
    """테스트용 샘플 리뷰 생성"""
    sample_reviews = [
        Review(
            id="kr_001",
            author="김민수",
            rating=2,
            content="잠자기 버튼이 사라졌어요. 어디 있나요?",
            created_at=datetime.now(),
            country="KR",
            platform="google_play"
        ),
        Review(
            id="kr_002", 
            author="이지영",
            rating=5,
            content="앱이 정말 좋아요! 걸으면서 포인트도 모으고 재미있네요",
            created_at=datetime.now(),
            country="KR",
            platform="app_store"
        ),
        Review(
            id="us_001",
            author="John",
            rating=1,
            content="This app is not voiceover friendly. Hard to use for blind users.",
            created_at=datetime.now(),
            country="US",
            platform="google_play"
        ),
        Review(
            id="kr_003",
            author="박철민",
            rating=3,
            content="광고를 봤는데 포인트가 안 들어와요. 확인해주세요.",
            created_at=datetime.now(),
            country="KR", 
            platform="google_play"
        ),
        Review(
            id="us_002",
            author="Sarah",
            rating=4,
            content="Great app! But sometimes it crashes when I try to watch ads.",
            created_at=datetime.now(),
            country="US",
            platform="app_store"
        )
    ]
    
    return sample_reviews

def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("🤖 머니워크 리뷰 응답 자동화 봇")
    print("=" * 50)
    
    # 봇 초기화
    bot = ReviewBot()
    
    # 사용자 선택 메뉴
    print("\n다음 중 선택해주세요:")
    print("1. 기존 지식베이스 사용 (빠름)")
    print("2. 지식베이스 강제 업데이트 (느림, API 비용 발생)")
    print("3. 통계 조회")
    print("4. 캐시 초기화")
    
    choice = input("\n선택 (1-4): ").strip()
    
    if choice == "1":
        # 기존 지식베이스 사용
        bot.initialize_knowledge_base(force_update=False)
    elif choice == "2":
        # 강제 업데이트
        print("\n⚠️  경고: 새로운 문서를 크롤링하고 벡터 저장소를 재생성합니다.")
        print("   OpenAI API 비용이 발생하며 시간이 오래 걸립니다.")
        confirm = input("계속하시겠습니까? (y/N): ").strip().lower()
        if confirm == 'y':
            bot.update_knowledge_base()
        else:
            print("취소되었습니다.")
            return
    elif choice == "3":
        # 통계 조회
        stats = bot.get_statistics()
        print("\n📊 시스템 통계:")
        print(f"- 총 생성된 응답: {stats['total_responses']}개")
        print(f"- 국가별 분포: {stats['country_distribution']}")
        print(f"- 벡터 저장소: {stats['vector_stores']}")
        print(f"- 마지막 업데이트: {stats['last_updated']}")
        return
    elif choice == "4":
        # 캐시 초기화
        bot.clear_cache()
        return
    else:
        print("잘못된 선택입니다.")
        return
    
    # 샘플 리뷰 처리 테스트 (실제 케이스 반영)
    print("\n📝 실제 케이스 기반 샘플 리뷰 테스트...")
    
    sample_reviews = [
        # 한국 케이스들
        Review(
            id="kr_point_001",
            content="광고보고 포인트 지급 안되는 횟수가 압도적으로 많고 5초짜리 광고라고 해놓고 대놓고 15초 이상 광고 보여줌.",
            author="김사용자",
            platform="google_play",
            country="KR",
            rating=1,
            created_at=datetime.now()
        ),
        Review(
            id="kr_sleep_001", 
            content="수면모드로 전환버튼 눌러도 안 눌릴 때가 많고 아까 낮부터는 아예 잠자기 시작 버튼 자체가 안떠요.",
            author="이사용자",
            platform="app_store",
            country="KR", 
            rating=2,
            created_at=datetime.now()
        ),
        Review(
            id="kr_exchange_001",
            content="현금45,000원 교환 포인트 원래 7만원대였는데 지금 8만포인트네요.",
            author="박사용자",
            platform="google_play",
            country="KR",
            rating=3,
            created_at=datetime.now()
        ),
        Review(
            id="kr_invite_001",
            content="초대코드 입력하시면 1000포인트 줍니다",
            author="최사용자",
            platform="app_store", 
            country="KR",
            rating=5,
            created_at=datetime.now()
        ),
        # 미국 케이스들
        Review(
            id="us_step_001",
            content="I walk more than 10,000 steps each day. The app says I have walked less than 2,000.",
            author="Mare",
            platform="google_play",
            country="US",
            rating=2,
            created_at=datetime.now()
        ),
        Review(
            id="us_accessibility_001",
            content="I have low vision and use voiceover... it's extremely frustrating for me right now.",
            author="Hali",
            platform="app_store",
            country="US",
            rating=1,
            created_at=datetime.now()
        ),
        Review(
            id="us_giftcard_001",
            content="I ordered a gift card and I have not received it.",
            author="ET21000",
            platform="google_play",
            country="US",
            rating=2,
            created_at=datetime.now()
        ),
        Review(
            id="us_points_001",
            content="I used to get 500 points for steps, now only 100 after cashing out.",
            author="LaLob",
            platform="app_store",
            country="US",
            rating=3,
            created_at=datetime.now()
        )
    ]
    
    # 리뷰 처리
    responses = bot.process_reviews_batch(sample_reviews)
    
    # 결과 출력
    print("\n" + "=" * 50)
    print("📋 생성된 응답 결과")
    print("=" * 50)
    
    for i, response in enumerate(responses, 1):
        review = sample_reviews[i-1]  # 해당 리뷰 가져오기
        
        print(f"\n[{i}] 리뷰 ID: {response.review_id}")
        print(f"📍 국가: {response.country} | 플랫폼: {response.platform}")
        print(f"📝 원본 리뷰: {review.content}")
        print(f"🤖 생성된 응답:")
        print("-" * 40)
        print(response.response_text)
        print("-" * 40)
        print(f"📚 사용된 소스: {len(response.used_sources)}개")
        
    print(f"\n✅ 총 {len(responses)}개 응답 생성 완료!")
    
    # 벡터 저장소 정보 출력
    vector_info = bot.vector_store_service.get_store_info()
    print(f"\n📊 벡터 저장소 상태: {vector_info}")
    
    print("\n🎉 테스트 완료! 실제 운영 시에는 API를 통해 리뷰를 수집하고 응답을 게시할 수 있습니다.")

if __name__ == "__main__":
    main() 