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

def print_detailed_statistics(stats: dict):
    """상세 통계 정보를 보기 좋게 출력"""
    print("\n" + "=" * 60)
    print("📊 머니워크 리뷰봇 상세 통계")
    print("=" * 60)
    
    # 기본 통계
    print(f"\n📈 기본 통계:")
    print(f"   총 생성된 응답: {stats.get('총 생성된 응답', 0):,}개")
    
    # 국가별 분포
    country_dist = stats.get('국가별 분포', {})
    if country_dist:
        print(f"\n🌍 국가별 분포:")
        for country, count in country_dist.items():
            percentage = (count / stats.get('총 생성된 응답', 1)) * 100
            print(f"   {country}: {count:,}개 ({percentage:.1f}%)")
    
    # 플랫폼별 분포
    platform_dist = stats.get('플랫폼별 분포', {})
    if platform_dist:
        print(f"\n📱 플랫폼별 분포:")
        for platform, count in platform_dist.items():
            percentage = (count / stats.get('총 생성된 응답', 1)) * 100
            print(f"   {platform}: {count:,}개 ({percentage:.1f}%)")
    
    # 카테고리별 분포
    category_dist = stats.get('카테고리별 분포', {})
    if category_dist:
        print(f"\n📂 카테고리별 분포:")
        # 카테고리를 개수 순으로 정렬
        sorted_categories = sorted(category_dist.items(), key=lambda x: x[1], reverse=True)
        for category, count in sorted_categories:
            percentage = (count / stats.get('총 생성된 응답', 1)) * 100
            print(f"   {category}: {count:,}개 ({percentage:.1f}%)")
    
    # 일별 처리량
    daily_stats = stats.get('일별 처리량 (최근)', {})
    if daily_stats:
        print(f"\n📅 최근 일별 처리량:")
        for date, count in daily_stats.items():
            print(f"   {date}: {count:,}개")
    
    # 벡터 저장소 상태
    vector_stores = stats.get('벡터 저장소 상태', {})
    if vector_stores:
        print(f"\n🗄️  벡터 저장소 상태:")
        for store, info in vector_stores.items():
            status = "✅ 로드됨" if info.get('loaded', False) else "❌ 미로드"
            doc_count = info.get('document_count', 0)
            print(f"   {store.upper()}: {status} | 문서 수: {doc_count:,}개")
    
    # 성능 지표
    performance = stats.get('성능 지표', {})
    if performance:
        print(f"\n⚡ 성능 지표:")
        print(f"   캐시 적중률: {performance.get('cache_hit_rate', 'N/A')}")
        print(f"   평균 응답 길이: {performance.get('avg_response_length', 0):.1f}자")
        print(f"   캐시 파일 크기: {performance.get('total_cache_size', 'N/A')}")
    
    # 시스템 상태
    system_status = stats.get('시스템 상태', {})
    if system_status:
        print(f"\n🔧 시스템 상태:")
        cache_exists = "✅ 존재" if system_status.get('캐시 파일 존재', False) else "❌ 없음"
        print(f"   캐시 파일: {cache_exists}")
        print(f"   벡터 저장소 경로: {system_status.get('벡터 저장소 경로', 'N/A')}")
        
        countries = system_status.get('지원 국가', [])
        categories = system_status.get('지원 카테고리', [])
        print(f"   지원 국가: {', '.join(countries)} ({len(countries)}개)")
        print(f"   지원 카테고리: {len(categories)}개")
    
    # 마지막 업데이트
    last_updated = stats.get('마지막 업데이트', '')
    if last_updated:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n🕒 마지막 업데이트: {formatted_time}")
        except:
            print(f"\n🕒 마지막 업데이트: {last_updated}")
    
    print("\n" + "=" * 60)

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
        print_detailed_statistics(stats)
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
        Review(
            id="kr_inquiry_001",
            content="문의했는데 답변이 없어요. 채널톡으로도 연락했는데 응답이 없습니다.",
            author="정사용자",
            platform="google_play", 
            country="KR",
            rating=1,
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
        ),
        Review(
            id="us_inquiry_001",
            content="I contacted support through the app but haven't received any response. I also tried the chat but no one replied.",
            author="SarahJ",
            platform="google_play",
            country="US",
            rating=1,
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