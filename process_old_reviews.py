#!/usr/bin/env python3
"""옛날 미답변 리뷰 일괄 처리 (내친소).

App Store: 최근 6개월 미답변 4~5점 리뷰에 응답 게시.
Google Play: API로 가져올 수 있는 모든 미답변 4~5점 리뷰에 응답 게시.
  (Google Play Reviews API는 보통 최근 1주일치만 노출되며,
   1주일 이상 된 리뷰는 reply 호출이 거부될 수 있음 — 실패는 카운트만 하고 계속 진행)
"""

import logging
import os
import time
from datetime import datetime

os.environ.setdefault("TENANT", "naechinso")

from config import Config  # noqa: E402
from models.review import Review  # noqa: E402
from services.app_store_client import AppStoreConnectClient  # noqa: E402
from services.google_play_client import GooglePlayConsoleClient  # noqa: E402
from services.review_bot import ReviewBot  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

APP_STORE_SINCE_DAYS = 180  # 최근 6개월
APP_STORE_LIMIT = 500
GOOGLE_PLAY_LIMIT = 500
POST_SLEEP_SEC = 0.5
MAX_PROCESS_PER_PLATFORM = int(os.environ.get("MAX_PROCESS", "50"))


def filter_positive(reviews: list[Review]) -> list[Review]:
    positive = [r for r in reviews if r.rating >= Config.MIN_RATING]
    skipped = len(reviews) - len(positive)
    if skipped:
        logger.info(f"{skipped}개 리뷰 제외 ({Config.MIN_RATING}점 미만)")
    return positive


def process_app_store(bot: ReviewBot) -> dict:
    print("\n" + "=" * 60)
    print(f"📱 App Store 처리 시작 (최근 {APP_STORE_SINCE_DAYS}일)")
    print("=" * 60)

    client = AppStoreConnectClient()
    reviews = client.get_reviews(
        "KOR",
        limit=APP_STORE_LIMIT,
        skip_replied=True,
        since_days=APP_STORE_SINCE_DAYS,
    )
    reviews = filter_positive(reviews)
    if MAX_PROCESS_PER_PLATFORM and len(reviews) > MAX_PROCESS_PER_PLATFORM:
        print(f"   (최대 {MAX_PROCESS_PER_PLATFORM}개로 제한)")
        reviews = reviews[:MAX_PROCESS_PER_PLATFORM]
    print(f"✅ 처리 대상: {len(reviews)}개")

    success = failed = skipped = 0
    for i, review in enumerate(reviews, 1):
        oldest = review.created_at.strftime("%Y-%m-%d")
        print(f"\n[{i}/{len(reviews)}] ⭐{review.rating} {oldest} {review.id}")
        print(f"  📝 {review.content[:80]}")
        try:
            response = bot.process_review(review)
            if response is None:
                print("  ⏭️  비꼬는 리뷰 스킵")
                skipped += 1
                continue
            print(f"  🤖 {response.response_text[:100]}")
            if client.post_review_response(review.id, response.response_text):
                print("  ✅ 게시 성공")
                success += 1
            else:
                print("  ❌ 게시 실패")
                failed += 1
            time.sleep(POST_SLEEP_SEC)
        except Exception as e:
            logger.error(f"App Store 처리 오류 {review.id}: {e}")
            failed += 1

    return {"platform": "app_store", "total": len(reviews),
            "success": success, "failed": failed, "skipped": skipped}


def process_google_play(bot: ReviewBot) -> dict:
    print("\n" + "=" * 60)
    print("🤖 Google Play 처리 시작 (API 가용 범위)")
    print("=" * 60)

    client = GooglePlayConsoleClient()
    reviews = client.get_reviews(
        "KOR",
        limit=GOOGLE_PLAY_LIMIT,
        skip_replied=True,
        infer_country_from_text=True,
        translation_language=None,
    )
    reviews = filter_positive(reviews)
    if MAX_PROCESS_PER_PLATFORM and len(reviews) > MAX_PROCESS_PER_PLATFORM:
        print(f"   (최대 {MAX_PROCESS_PER_PLATFORM}개로 제한)")
        reviews = reviews[:MAX_PROCESS_PER_PLATFORM]
    print(f"✅ 처리 대상: {len(reviews)}개")

    success = failed = skipped = 0
    for i, review in enumerate(reviews, 1):
        oldest = review.created_at.strftime("%Y-%m-%d")
        print(f"\n[{i}/{len(reviews)}] ⭐{review.rating} {oldest} {review.id}")
        print(f"  📝 {review.content[:80]}")
        try:
            response = bot.process_review(review)
            if response is None:
                print("  ⏭️  비꼬는 리뷰 스킵")
                skipped += 1
                continue
            print(f"  🤖 {response.response_text[:100]}")
            ok = client.post_review_response(
                review.id, response.response_text, "KOR"
            )
            if ok:
                print("  ✅ 게시 성공")
                success += 1
            else:
                print("  ❌ 게시 실패 (7일 초과 리뷰는 API에서 거부)")
                failed += 1
            time.sleep(POST_SLEEP_SEC)
        except Exception as e:
            logger.error(f"Google Play 처리 오류 {review.id}: {e}")
            failed += 1

    return {"platform": "google_play", "total": len(reviews),
            "success": success, "failed": failed, "skipped": skipped}


def main():
    print("=" * 60)
    print(f"🤖 {Config.DISPLAY_NAME} 옛날 리뷰 일괄 답변")
    print(f"   tenant={Config.TENANT} rating>={Config.MIN_RATING}")
    print(f"   시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    bot = ReviewBot()
    results = []

    try:
        results.append(process_app_store(bot))
    except Exception as e:
        logger.error(f"App Store 처리 중단: {e}")

    try:
        results.append(process_google_play(bot))
    except Exception as e:
        logger.error(f"Google Play 처리 중단: {e}")

    print("\n" + "=" * 60)
    print("📊 최종 결과")
    print("=" * 60)
    for r in results:
        print(f"  [{r['platform']}] 대상 {r['total']} / "
              f"성공 {r['success']} / 실패 {r['failed']} / 스킵 {r['skipped']}"
              + (f" / 기간초과 {r['expired']}" if 'expired' in r else ""))


if __name__ == "__main__":
    main()
