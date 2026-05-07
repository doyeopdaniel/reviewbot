import jwt
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import Config
from models.review import Review

class AppStoreConnectClient:
    """App Store Connect API 클라이언트"""
    
    def __init__(self):
        self.private_key_path = Config.APP_STORE_CONNECT["PRIVATE_KEY_PATH"]
        self.key_id = Config.APP_STORE_CONNECT["KEY_ID"]
        self.issuer_id = Config.APP_STORE_CONNECT["ISSUER_ID"]
        self.bundle_ids = Config.APP_STORE_CONNECT["BUNDLE_ID"]
        
        # API 엔드포인트
        self.base_url = "https://api.appstoreconnect.apple.com"
        
        # 토큰 캐시
        self._token = None
        self._token_expires_at = None
        
        # 유효성 검사
        self._validate_credentials()
    
    def _validate_credentials(self):
        """API 자격증명 유효성 검사"""
        if not self.key_id:
            raise ValueError("APP_STORE_KEY_ID가 설정되지 않았습니다.")
        
        if not self.issuer_id:
            raise ValueError("APP_STORE_ISSUER_ID가 설정되지 않았습니다.")
        
        try:
            with open(self.private_key_path, 'r') as f:
                pass
        except FileNotFoundError:
            raise FileNotFoundError(f"Private key 파일을 찾을 수 없습니다: {self.private_key_path}")
    
    def _generate_jwt_token(self) -> str:
        """JWT 토큰 생성"""
        if self._token and self._token_expires_at and datetime.now() < self._token_expires_at:
            return self._token
        
        # 만료 시간 (최대 20분)
        expiration_time = int(time.time()) + (20 * 60)
        
        # JWT 헤더
        headers = {
            "alg": "ES256",
            "kid": self.key_id,
            "typ": "JWT"
        }
        
        # JWT 페이로드
        payload = {
            "iss": self.issuer_id,
            "iat": int(time.time()),
            "exp": expiration_time,
            "aud": "appstoreconnect-v1"
        }
        
        # Private key 읽기
        with open(self.private_key_path, 'r') as f:
            private_key = f.read()
        
        # JWT 토큰 생성
        token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
        
        # 토큰 캐시
        self._token = token
        self._token_expires_at = datetime.now() + timedelta(minutes=19)  # 1분 여유
        
        return token
    
    def _make_request(self, endpoint: str, method: str = "GET", params: Dict = None) -> Dict:
        """API 요청 실행"""
        token = self._generate_jwt_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=params)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=params)
            else:
                raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"API 요청 오류: {e}")
            if hasattr(e.response, 'text'):
                print(f"응답 내용: {e.response.text}")
            raise
    
    def get_app_id(self, country: str) -> str:
        """Bundle ID로부터 App ID 조회"""
        bundle_id = self.bundle_ids.get(country)
        if not bundle_id:
            raise ValueError(f"지원하지 않는 국가 코드: {country}")
        
        params = {
            "filter[bundleId]": bundle_id,
            "fields[apps]": "bundleId,name"
        }
        
        response = self._make_request("/v1/apps", params=params)
        
        if not response.get("data"):
            raise ValueError(f"Bundle ID {bundle_id}에 해당하는 앱을 찾을 수 없습니다.")
        
        return response["data"][0]["id"]
    
    def get_reviews(
        self,
        country: str,
        limit: int = 200,
        skip_replied: bool = True,
        since_days: Optional[int] = None,
    ) -> List[Review]:
        """앱 리뷰 조회. skip_replied=True면 미답변 리뷰만 반환.

        - since_days: 지정 시 해당 일수 이내의 리뷰만 반환 (예: 180 = 최근 6개월)
        - limit이 200을 초과하면 자동으로 페이지네이션
        """
        app_id = self.get_app_id(country)

        page_size = 200
        params = {
            "filter[territory]": country,
            "sort": "-createdDate",
            "limit": page_size,
            "fields[customerReviews]": "rating,title,body,createdDate,territory,response",
            "fields[customerReviewResponses]": "responseBody,state,lastModifiedDate",
            "include": "response",
        }

        endpoint = f"/v1/apps/{app_id}/customerReviews"
        cutoff = (
            datetime.now().astimezone() - timedelta(days=since_days)
            if since_days
            else None
        )

        reviews: List[Review] = []
        replied_skipped = 0
        out_of_window = 0
        pages_fetched = 0
        next_url: Optional[str] = None
        stop_paging = False

        while len(reviews) < limit and not stop_paging:
            if next_url:
                token = self._generate_jwt_token()
                resp = requests.get(
                    next_url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                    },
                )
                resp.raise_for_status()
                response = resp.json()
            else:
                response = self._make_request(endpoint, params=params)

            pages_fetched += 1

            # 답변 ID 수집 (이번 페이지)
            replied_ids = set()
            if skip_replied:
                for included in response.get("included", []):
                    if included.get("type") == "customerReviewResponses":
                        rel = included.get("relationships", {})
                        review_rel = rel.get("review", {}).get("data", {})
                        if review_rel.get("id"):
                            replied_ids.add(review_rel["id"])
                for review_data in response.get("data", []):
                    resp_rel = (
                        review_data.get("relationships", {})
                        .get("response", {})
                        .get("data")
                    )
                    if resp_rel is not None:
                        replied_ids.add(review_data["id"])

            for review_data in response.get("data", []):
                if skip_replied and review_data["id"] in replied_ids:
                    replied_skipped += 1
                    continue

                attributes = review_data.get("attributes", {})
                created_at = datetime.fromisoformat(
                    attributes.get("createdDate", "").replace("Z", "+00:00")
                )

                # 정렬이 -createdDate이므로, 컷오프보다 옛날이면 이후 리뷰도 모두 옛날
                if cutoff and created_at < cutoff:
                    out_of_window += 1
                    stop_paging = True
                    break

                review = Review(
                    id=review_data["id"],
                    author="익명",
                    rating=attributes.get("rating", 0),
                    content=f"{attributes.get('title', '')} {attributes.get('body', '')}".strip(),
                    created_at=created_at,
                    country=country,
                    platform="app_store",
                )
                reviews.append(review)

                if len(reviews) >= limit:
                    stop_paging = True
                    break

            next_url = response.get("links", {}).get("next")
            if not next_url:
                break

        print("📊 App Store 리뷰 수집 통계:")
        print(f"   - 조회한 페이지: {pages_fetched}개")
        print(f"   - 답변 있어서 제외: {replied_skipped}개")
        if since_days:
            print(f"   - 기간({since_days}일) 밖이라 제외: {out_of_window}개")
        print(f"   - 최종 수집된 리뷰: {len(reviews)}개")

        return reviews
    
    def post_review_response(self, review_id: str, response_text: str) -> bool:
        """리뷰에 응답 게시"""
        try:
            data = {
                "data": {
                    "type": "customerReviewResponses",
                    "attributes": {
                        "responseBody": response_text
                    },
                    "relationships": {
                        "review": {
                            "data": {
                                "type": "customerReviews",
                                "id": review_id
                            }
                        }
                    }
                }
            }
            
            response = self._make_request("/v1/customerReviewResponses", method="POST", params=data)
            return True
            
        except Exception as e:
            print(f"리뷰 응답 게시 오류: {e}")
            return False
    
    def get_review_responses(self, country: str) -> List[Dict]:
        """기존 응답 조회"""
        app_id = self.get_app_id(country)
        
        params = {
            "filter[territory]": country,
            "fields[customerReviewResponses]": "responseBody,createdDate"
        }
        
        try:
            endpoint = f"/v1/apps/{app_id}/customerReviewResponses"
            response = self._make_request(endpoint, params=params)
            return response.get("data", [])
        except Exception as e:
            print(f"기존 응답 조회 오류: {e}")
            return []
    
    def test_connection(self) -> bool:
        """API 연결 테스트"""
        try:
            # 간단한 앱 목록 조회로 연결 테스트
            response = self._make_request("/v1/apps", params={"limit": 1})
            print("✅ App Store Connect API 연결 성공")
            return True
        except Exception as e:
            print(f"❌ App Store Connect API 연결 실패: {e}")
            return False 