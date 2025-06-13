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
        
        # 캐시에 저장 (카테고리 정보 포함)
        cache_data = response.dict()
        cache_data['category'] = category  # 카테고리 정보 추가
        self.response_cache[cache_key] = cache_data
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
        platform_stats = {}
        daily_stats = {}
        response_times = []
        
        for cache_key, response_data in self.response_cache.items():
            country = response_data.get('country', 'Unknown')
            platform = response_data.get('platform', 'Unknown')
            category = response_data.get('category', 'Unknown')
            generated_at = response_data.get('generated_at', '')
            
            # 국가별 통계
            if country not in country_stats:
                country_stats[country] = 0
            country_stats[country] += 1
            
            # 카테고리별 통계
            if category not in category_stats:
                category_stats[category] = 0
            category_stats[category] += 1
            
            # 플랫폼별 통계
            if platform not in platform_stats:
                platform_stats[platform] = 0
            platform_stats[platform] += 1
            
            # 일별 통계 (최근 7일)
            if generated_at:
                try:
                    date_str = generated_at.split('T')[0]  # YYYY-MM-DD 형태로 추출
                    if date_str not in daily_stats:
                        daily_stats[date_str] = 0
                    daily_stats[date_str] += 1
                except:
                    pass
        
        # 벡터 저장소 상태 및 문서 수
        vector_store_info = {}
        existing_stores = self._check_existing_vector_stores()
        
        for store in existing_stores:
            try:
                # 벡터 저장소 로드하여 문서 수 확인
                if hasattr(self.vector_store_service, 'get_document_count'):
                    doc_count = self.vector_store_service.get_document_count(store)
                else:
                    doc_count = "Unknown"
                
                vector_store_info[store] = {
                    "loaded": True,
                    "document_count": doc_count
                }
            except:
                vector_store_info[store] = {
                    "loaded": False,
                    "document_count": 0
                }
        
        # 성능 통계
        performance_stats = {
            "cache_hit_rate": f"{(len(self.response_cache) / max(total_responses, 1) * 100):.1f}%" if total_responses > 0 else "0%",
            "avg_response_length": self._calculate_avg_response_length(),
            "total_cache_size": f"{self._get_cache_file_size():.2f} MB"
        }
        
        return {
            "총 생성된 응답": total_responses,
            "국가별 분포": country_stats,
            "카테고리별 분포": category_stats,
            "플랫폼별 분포": platform_stats,
            "일별 처리량 (최근)": dict(sorted(daily_stats.items(), reverse=True)[:7]),
            "벡터 저장소 상태": vector_store_info,
            "성능 지표": performance_stats,
            "마지막 업데이트": datetime.now().isoformat(),
            "시스템 상태": {
                "캐시 파일 존재": os.path.exists("response_cache.json"),
                "벡터 저장소 경로": Config.VECTOR_STORE_PATH,
                "지원 국가": Config.COUNTRIES,
                "지원 카테고리": Config.REVIEW_CATEGORIES
            }
        }
    
    def _calculate_avg_response_length(self) -> float:
        """평균 응답 길이 계산"""
        if not self.response_cache:
            return 0.0
        
        total_length = 0
        count = 0
        
        for response_data in self.response_cache.values():
            response_text = response_data.get('response_text', '')
            if response_text:
                total_length += len(response_text)
                count += 1
        
        return total_length / count if count > 0 else 0.0
    
    def _get_cache_file_size(self) -> float:
        """캐시 파일 크기 (MB)"""
        cache_file = "response_cache.json"
        if os.path.exists(cache_file):
            size_bytes = os.path.getsize(cache_file)
            return size_bytes / (1024 * 1024)  # MB로 변환
        return 0.0
    
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