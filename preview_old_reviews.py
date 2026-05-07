#!/usr/bin/env python3
"""게시 없이 옛날 미답변 리뷰 개수만 미리 확인."""

import os
os.environ.setdefault("TENANT", "naechinso")

from config import Config  # noqa: E402
from services.app_store_client import AppStoreConnectClient  # noqa: E402
from services.google_play_client import GooglePlayConsoleClient  # noqa: E402

APP_STORE_SINCE_DAYS = 180
APP_STORE_LIMIT = 500
GOOGLE_PLAY_LIMIT = 500


def main():
    print(f"=== {Config.DISPLAY_NAME} 미답변 리뷰 미리보기 ===\n")

    print(f"📱 App Store (최근 {APP_STORE_SINCE_DAYS}일):")
    try:
        as_client = AppStoreConnectClient()
        as_reviews = as_client.get_reviews(
            "KOR", limit=APP_STORE_LIMIT, skip_replied=True,
            since_days=APP_STORE_SINCE_DAYS,
        )
        positive = [r for r in as_reviews if r.rating >= Config.MIN_RATING]
        print(f"   미답변 전체: {len(as_reviews)}개 / "
              f"{Config.MIN_RATING}점 이상: {len(positive)}개")
        if positive:
            oldest = min(r.created_at for r in positive)
            newest = max(r.created_at for r in positive)
            print(f"   기간: {oldest.strftime('%Y-%m-%d')} ~ "
                  f"{newest.strftime('%Y-%m-%d')}")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

    print("\n🤖 Google Play (API 가용 범위):")
    try:
        gp_client = GooglePlayConsoleClient()
        gp_reviews = gp_client.get_reviews(
            "KOR", limit=GOOGLE_PLAY_LIMIT, skip_replied=True,
            infer_country_from_text=True, translation_language=None,
        )
        positive = [r for r in gp_reviews if r.rating >= Config.MIN_RATING]
        print(f"   미답변 전체: {len(gp_reviews)}개 / "
              f"{Config.MIN_RATING}점 이상: {len(positive)}개")
        if positive:
            oldest = min(r.created_at for r in positive)
            newest = max(r.created_at for r in positive)
            print(f"   기간: {oldest.strftime('%Y-%m-%d')} ~ "
                  f"{newest.strftime('%Y-%m-%d')}")
    except Exception as e:
        print(f"   ❌ 오류: {e}")


if __name__ == "__main__":
    main()
