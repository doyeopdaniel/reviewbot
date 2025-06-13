import json
import os
from datetime import datetime
from typing import List, Dict
from models.review import Review, ReviewResponse
from services.vector_store import VectorStoreService
from services.review_classifier import ReviewClassifier
from services.response_generator import ResponseGenerator
from utils.document_loader import DocumentLoader
from config import Config

class ReviewBot:
    """리뷰봇 메인 서비스"""
    
    def __init__(self):
        self.document_loader = DocumentLoader()
        self.vector_store_service = VectorStoreService()
        self.review_classifier = ReviewClassifier()
        self.response_generator = ResponseGenerator(self.vector_store_service)
        
        # 캐시 저장소
        self.response_cache = self._load_response_cache()
        
    def initialize_knowledge_base(self, force_update: bool = False):
        """지식베이스 초기화 (기존 저장소가 있으면 재사용)"""
        print("지식베이스 초기화 시작...")
        
        # 기존 벡터 저장소 확인
        existing_stores = self._check_existing_vector_stores()
        
        if existing_stores and not force_update:
            print("기존 벡터 저장소 발견. 재사용합니다.")
            # 기존 저장소 로드
            for country in Config.COUNTRIES:
                if country.lower() in existing_stores:
                    print(f"{country} 벡터 저장소 로드 중...")
                    self.vector_store_service.load_existing_store(country.lower())
            
            print("기존 지식베이스 로드 완료")
            return
        
        # 새로운 벡터 저장소 생성
        print("새로운 지식베이스 생성 중...")
        
        # 웹 문서 수집
        documents = self.document_loader.load_web_documents(Config.KNOWLEDGE_BASE_URLS)
        print(f"총 {len(documents)}개 문서 청크 수집됨")
        
        # 국가별 벡터 저장소 생성
        for country in Config.COUNTRIES:
            self.vector_store_service.create_or_load_vector_store(documents, country.lower())
        
        print("지식베이스 초기화 완료")
    
    def _check_existing_vector_stores(self) -> List[str]:
        """기존 벡터 저장소 확인"""
        existing_stores = []
        
        if not os.path.exists(Config.VECTOR_STORE_PATH):
            return existing_stores
        
        for country in Config.COUNTRIES:
            store_path = f"{Config.VECTOR_STORE_PATH}/{country.lower()}_faiss"
            if os.path.exists(store_path):
                existing_stores.append(country.lower())
        
        return existing_stores
    
    def process_review(self, review: Review) -> ReviewResponse:
        """단일 리뷰 처리"""
        # 캐시 확인
        cache_key = self._generate_cache_key(review)
        if cache_key in self.response_cache:
            print(f"캐시된 응답 사용: {review.id}")
            cached_response = self.response_cache[cache_key]
            # 캐시된 데이터를 ReviewResponse 객체로 변환
            return ReviewResponse(**cached_response)
        
        # 리뷰 분류
        category = self.review_classifier.classify_review(review)
        review.category = category
        
        print(f"리뷰 분류: {review.id} -> {category}")
        
        # 응답 생성
        response = self.response_generator.generate_response(review, category)
        
        # 캐시에 저장
        self.response_cache[cache_key] = response.dict()
        self._save_response_cache()
        
        return response
    
    def process_reviews_batch(self, reviews: List[Review]) -> List[ReviewResponse]:
        """여러 리뷰 일괄 처리"""
        responses = []
        
        print(f"{len(reviews)}개 리뷰 처리 시작...")
        
        for i, review in enumerate(reviews, 1):
            print(f"처리 중: {i}/{len(reviews)} - {review.id}")
            
            try:
                response = self.process_review(review)
                responses.append(response)
            except Exception as e:
                print(f"리뷰 처리 오류 {review.id}: {e}")
                continue
        
        print(f"총 {len(responses)}개 응답 생성 완료")
        return responses
    
    def update_knowledge_base(self):
        """지식베이스 강제 업데이트"""
        print("지식베이스 강제 업데이트 시작...")
        
        try:
            # 기존 벡터 저장소 삭제
            if os.path.exists(Config.VECTOR_STORE_PATH):
                import shutil
                shutil.rmtree(Config.VECTOR_STORE_PATH)
            
            # 새로운 지식베이스 생성
            self.initialize_knowledge_base(force_update=True)
            print("지식베이스 강제 업데이트 완료")
            
        except Exception as e:
            print(f"지식베이스 업데이트 오류: {e}")
    
    def get_statistics(self) -> Dict:
        """처리 통계 조회"""
        total_responses = len(self.response_cache)
        
        # 국가별 통계
        country_stats = {}
        category_stats = {}
        
        for cache_key, response_data in self.response_cache.items():
            country = response_data.get('country', 'Unknown')
            
            if country not in country_stats:
                country_stats[country] = 0
            country_stats[country] += 1
        
        # 벡터 저장소 상태
        existing_stores = self._check_existing_vector_stores()
        
        return {
            "total_responses": total_responses,
            "country_distribution": country_stats,
            "vector_stores": existing_stores,
            "last_updated": datetime.now().isoformat()
        }
    
    def _generate_cache_key(self, review: Review) -> str:
        """캐시 키 생성"""
        # 리뷰 내용과 국가를 기반으로 해시 생성
        import hashlib
        content = f"{review.content}_{review.country}_{review.platform}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _load_response_cache(self) -> Dict:
        """응답 캐시 로드"""
        cache_file = "response_cache.json"
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"캐시 로드 오류: {e}")
                return {}
        
        return {}
    
    def _save_response_cache(self):
        """응답 캐시 저장"""
        cache_file = "response_cache.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.response_cache, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"캐시 저장 오류: {e}")
    
    def clear_cache(self):
        """캐시 초기화"""
        self.response_cache = {}
        cache_file = "response_cache.json"
        if os.path.exists(cache_file):
            os.remove(cache_file)
        print("캐시가 초기화되었습니다.") 