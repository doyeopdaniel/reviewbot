"""멀티테넌트 리뷰봇 설정 (내친소 / 머니워크 통합)"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

TENANTS_DIR = Path(__file__).parent / "tenants"


def _load_tenant(name: str) -> dict:
    path = TENANTS_DIR / f"{name}.yaml"
    if not path.exists():
        available = sorted(p.stem for p in TENANTS_DIR.glob("*.yaml"))
        raise FileNotFoundError(
            f"테넌트 설정을 찾을 수 없습니다: {path}. "
            f"사용 가능한 테넌트: {available}"
        )
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Config:
    """앱 설정 (테넌트별 동적 로드)"""

    TENANT = os.environ.get("TENANT", "naechinso")
    TENANT_CONFIG = _load_tenant(TENANT)

    # OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    LLM_MODEL = "gpt-4o-mini"
    EMBEDDING_MODEL = "text-embedding-3-small"

    # 테넌트 메타데이터
    DISPLAY_NAME = TENANT_CONFIG["display_name"]
    PLAN = TENANT_CONFIG.get("plan", "lite")
    COUNTRIES = TENANT_CONFIG.get("countries", ["KOR"])
    MIN_RATING = TENANT_CONFIG["rating"]["min"]
    MAX_RATING = TENANT_CONFIG["rating"].get("max", 5)

    # 카테고리 (머니워크: classifier 사용 / 내친소: 미사용)
    REVIEW_CATEGORIES = (
        TENANT_CONFIG["response_generator"].get("classifier", {}).get("categories", [])
    )

    # 벡터 저장소
    VECTOR_STORE_PATH = "vector_stores"
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200

    # 응답 길이 제한
    MAX_RESPONSE_LENGTH = TENANT_CONFIG["response_generator"]["max_length"]

    # App Store Connect
    APP_STORE_CONNECT = {
        "PRIVATE_KEY_PATH": os.environ.get("APP_STORE_PRIVATE_KEY_PATH", ""),
        "KEY_ID": os.environ.get("APP_STORE_KEY_ID", ""),
        "ISSUER_ID": os.environ.get("APP_STORE_ISSUER_ID", ""),
        "BUNDLE_ID": {
            country: os.environ.get(
                f"APP_STORE_BUNDLE_ID_{country}",
                bundle_id,
            )
            for country, bundle_id in TENANT_CONFIG["app_store"]["bundle_id"].items()
        },
    }

    # Google Play Console
    GOOGLE_PLAY_CONSOLE = {
        "SERVICE_ACCOUNT_KEY": os.environ.get(
            "GOOGLE_PLAY_SERVICE_ACCOUNT_KEY", "service_account.json"
        ),
        "PACKAGE_NAME": {
            country: os.environ.get(
                f"GOOGLE_PLAY_PACKAGE_NAME_{country}",
                package_name,
            )
            for country, package_name in TENANT_CONFIG["google_play"]["package_name"].items()
        },
    }
