#!/usr/bin/env python3
"""멀티테넌트 리뷰 응답 자동화 시스템 (내친소 / 머니워크)

테넌트는 환경변수 TENANT로 선택 (기본: naechinso).
"""

import logging
from datetime import datetime
from config import Config
from models.review import Review
from services.review_bot import ReviewBot
from services.google_play_client import GooglePlayConsoleClient
from services.app_store_client import AppStoreConnectClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def filter_positive_reviews(reviews: list[Review]) -> list[Review]:
    """테넌트의 MIN_RATING 이상 리뷰만 필터링"""
    positive = [r for r in reviews if r.rating >= Config.MIN_RATING]
    filtered_count = len(reviews) - len(positive)
    if filtered_count:
        logger.info(f"{filtered_count}개 리뷰 제외 ({Config.MIN_RATING}점 미만)")
    return positive


def process_sample_reviews(bot: ReviewBot):
    """샘플 리뷰 테스트"""
    sample_reviews = [
        Review(
            id="kr_sample_001",
            content="친구가 소개해줘서 시작했는데 진짜 좋은 사람 만났어요! 감사합니다",
            author="김민수",
            platform="google_play",
            country="KOR",
            rating=5,
            created_at=datetime.now(),
        ),
        Review(
            id="kr_sample_002",
            content="다른 소개팅 앱보다 훨씬 믿음이 가요. 친구 추천이라 안심되고 추천합니다",
            author="이지영",
            platform="google_play",
            country="KOR",
            rating=5,
            created_at=datetime.now(),
        ),
        Review(
            id="kr_sample_003",
            content="UI 깔끔하고 매칭 퀄리티도 괜찮아요",
            author="박철수",
            platform="google_play",
            country="KOR",
            rating=4,
            created_at=datetime.now(),
        ),
        Review(
            id="kr_sample_004",
            content="소개팅 앱 여러개 써봤는데 여기가 제일 나은 듯",
            author="최수진",
            platform="google_play",
            country="KOR",
            rating=4,
            created_at=datetime.now(),
        ),
    ]

    responses = bot.process_reviews_batch(sample_reviews)
    print_results(sample_reviews, responses)


def process_google_play_reviews(bot: ReviewBot):
    """실제 Google Play 4~5점 리뷰 처리 (한국)"""
    try:
        gp_client = GooglePlayConsoleClient()

        print("\n📥 한국 Google Play 미답변 리뷰 가져오는 중...")
        reviews = gp_client.get_reviews(
            "KOR", limit=100, skip_replied=True,
            infer_country_from_text=True, translation_language=None,
        )

        if not reviews:
            print("❌ 가져온 리뷰가 없습니다.")
            return

        # 4~5점만 필터
        reviews = filter_positive_reviews(reviews)
        if not reviews:
            print("❌ 4~5점 리뷰가 없습니다.")
            return

        print(f"✅ {len(reviews)}개 긍정 리뷰 (4~5점)")

        print("\n1. 응답만 생성 (게시하지 않음)")
        print("2. 응답 생성 후 실제 게시")
        action = input("선택 (1-2): ").strip()

        responses = bot.process_reviews_batch(reviews)
        print_results(reviews, responses)

        if action == "2":
            post_responses(gp_client, reviews, responses)

    except Exception as e:
        logger.error(f"처리 중 오류: {e}")


def process_app_store_reviews(bot: ReviewBot, limit: int = 100, since_days: int | None = None):
    """실제 App Store 4~5점 리뷰 처리 (한국)"""
    try:
        as_client = AppStoreConnectClient()

        window_msg = f" (최근 {since_days}일)" if since_days else ""
        print(f"\n📥 한국 App Store 미답변 리뷰 가져오는 중...{window_msg}")
        reviews = as_client.get_reviews("KOR", limit=limit, since_days=since_days)

        if not reviews:
            print("❌ 가져온 리뷰가 없습니다.")
            return

        reviews = filter_positive_reviews(reviews)
        if not reviews:
            print("❌ 4~5점 리뷰가 없습니다.")
            return

        print(f"✅ {len(reviews)}개 긍정 리뷰 (4~5점)")

        print("\n1. 응답만 생성 (게시하지 않음)")
        print("2. 응답 생성 후 실제 게시")
        action = input("선택 (1-2): ").strip()

        responses = bot.process_reviews_batch(reviews)
        print_results(reviews, responses)

        if action == "2":
            print("\n📤 App Store에 응답 게시 중...")
            success = 0
            for review, response in zip(reviews, responses):
                try:
                    if as_client.post_review_response(review.id, response.response_text):
                        success += 1
                        print(f"✅ {review.id} 게시 성공")
                    else:
                        print(f"❌ {review.id} 게시 실패")
                except Exception as e:
                    logger.error(f"{review.id} 게시 오류: {e}")
            print(f"\n🎉 {success}/{len(responses)}개 게시 완료!")

    except Exception as e:
        logger.error(f"처리 중 오류: {e}")


def post_responses(gp_client, reviews, responses):
    """Google Play 응답 게시"""
    print("\n📤 Google Play에 응답 게시 중...")
    success = 0
    for review, response in zip(reviews, responses):
        try:
            if gp_client.post_review_response(review.id, response.response_text, "KOR"):
                success += 1
                print(f"✅ {review.id} 게시 성공")
            else:
                print(f"❌ {review.id} 게시 실패")
        except Exception as e:
            logger.error(f"{review.id} 게시 오류: {e}")

    print(f"\n🎉 {success}/{len(responses)}개 게시 완료!")


def print_results(reviews, responses):
    """결과 출력"""
    print("\n" + "=" * 50)
    print("📋 처리 결과")
    print("=" * 50)

    for i, (review, response) in enumerate(zip(reviews, responses), 1):
        print(f"\n[{i}] ⭐ {review.rating}점 | {review.author}")
        print(f"📝 리뷰: {review.content}")
        print(f"🤖 응답: {response.response_text}")
        print("-" * 40)

    print(f"\n✅ 총 {len(responses)}개 응답 생성 완료!")


def main():
    """메인"""
    print("=" * 50)
    print(
        f"🤖 {Config.DISPLAY_NAME} 리뷰봇 "
        f"(plan={Config.PLAN}, rating>={Config.MIN_RATING})"
    )
    print("=" * 50)

    bot = ReviewBot()

    print("\n1. 샘플 리뷰 테스트")
    print("2. App Store 실제 리뷰 처리")
    print("3. Google Play 실제 리뷰 처리")
    print("4. 통계 조회")
    print("5. 캐시 초기화")

    choice = input("\n선택 (1-5): ").strip()

    if choice == "1":
        process_sample_reviews(bot)
    elif choice == "2":
        process_app_store_reviews(bot)
    elif choice == "3":
        process_google_play_reviews(bot)
    elif choice == "4":
        stats = bot.get_statistics()
        print(f"\n📊 총 응답: {stats.get('총 생성된 응답', 0)}개")
    elif choice == "5":
        bot.clear_cache()
    else:
        print("잘못된 선택입니다.")


if __name__ == "__main__":
    main()
