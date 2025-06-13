import os
import pickle
from typing import List, Optional
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from config import Config

class VectorStoreService:
    """벡터 저장소 관리 서비스"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=Config.EMBEDDING_MODEL,
            api_key=Config.OPENAI_API_KEY
        )
        self.vector_stores = {}  # 국가별 벡터 저장소
        
    def load_existing_store(self, country: str) -> Optional[FAISS]:
        """기존 벡터 저장소 로드 (오류 처리 포함)"""
        store_path = f"{Config.VECTOR_STORE_PATH}/{country}_faiss"
        
        if not os.path.exists(store_path):
            print(f"경고: {country} 벡터 저장소가 존재하지 않습니다.")
            return None
        
        try:
            # 새로운 FAISS 버전 호환성을 위해 다양한 방법 시도
            vector_store = FAISS.load_local(store_path, self.embeddings)
            self.vector_stores[country] = vector_store
            print(f"{country} 벡터 저장소 로드 성공")
            return vector_store
            
        except Exception as e:
            print(f"벡터 저장소 로드 실패 ({country}): {e}")
            print(f"기존 저장소를 삭제하고 새로 생성이 필요합니다.")
            return None
        
    def create_or_load_vector_store(self, documents: List[Document], country: str) -> FAISS:
        """벡터 저장소 생성 또는 로드"""
        store_path = f"{Config.VECTOR_STORE_PATH}/{country}_faiss"
        
        # 먼저 기존 저장소 로드 시도
        existing_store = self.load_existing_store(country)
        if existing_store is not None:
            return existing_store
        
        # 기존 저장소 로드 실패 시 새로 생성
        return self._create_new_vector_store(documents, country, store_path)
    
    def _create_new_vector_store(self, documents: List[Document], country: str, store_path: str) -> FAISS:
        """새로운 벡터 저장소 생성"""
        print(f"{country} 벡터 저장소 생성 중...")
        
        # 국가별 문서 필터링
        country_docs = [doc for doc in documents if doc.metadata.get('country') == country]
        
        if not country_docs:
            print(f"경고: {country}에 대한 문서가 없습니다.")
            return None
            
        try:
            vector_store = FAISS.from_documents(country_docs, self.embeddings)
            
            # 저장소 저장
            os.makedirs(Config.VECTOR_STORE_PATH, exist_ok=True)
            vector_store.save_local(store_path)
            
            self.vector_stores[country] = vector_store
            print(f"{country} 벡터 저장소 생성 완료")
            return vector_store
            
        except Exception as e:
            print(f"벡터 저장소 생성 실패 ({country}): {e}")
            return None
    
    def similarity_search(self, query: str, country: str, k: int = 3) -> List[Document]:
        """유사도 검색"""
        if country not in self.vector_stores:
            print(f"경고: {country} 벡터 저장소가 없습니다.")
            return []
            
        vector_store = self.vector_stores[country]
        try:
            results = vector_store.similarity_search(query, k=k)
            return results
        except Exception as e:
            print(f"유사도 검색 오류 ({country}): {e}")
            return []
    
    def update_vector_store(self, new_documents: List[Document], country: str):
        """벡터 저장소 업데이트"""
        country_docs = [doc for doc in new_documents if doc.metadata.get('country') == country]
        
        if not country_docs:
            return
            
        try:
            if country in self.vector_stores:
                # 기존 저장소에 문서 추가
                self.vector_stores[country].add_documents(country_docs)
            else:
                # 새로운 저장소 생성
                self.vector_stores[country] = FAISS.from_documents(country_docs, self.embeddings)
            
            # 저장
            store_path = f"{Config.VECTOR_STORE_PATH}/{country}_faiss"
            os.makedirs(Config.VECTOR_STORE_PATH, exist_ok=True)
            self.vector_stores[country].save_local(store_path)
            print(f"{country} 벡터 저장소 업데이트 완료")
            
        except Exception as e:
            print(f"벡터 저장소 업데이트 오류 ({country}): {e}")
    
    def get_store_info(self) -> dict:
        """벡터 저장소 정보 조회"""
        info = {}
        for country, store in self.vector_stores.items():
            try:
                doc_count = store.index.ntotal if hasattr(store, 'index') else 'Unknown'
                info[country] = {
                    "loaded": True,
                    "document_count": doc_count
                }
            except:
                info[country] = {
                    "loaded": False,
                    "document_count": 0
                }
        return info 