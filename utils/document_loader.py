import os
import requests
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from typing import List
from urllib.parse import urljoin, urlparse
from config import Config

class DocumentLoader:
    """머니워크 공식 문서를 수집하고 처리하는 클래스"""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def load_web_documents(self, urls: dict) -> List[Document]:
        """웹 문서들을 로드하고 청크화 (메인 페이지 + 세부 문서들)"""
        documents = []
        
        for country, url in urls.items():
            try:
                print(f"문서 수집 중: {country} - {url}")
                
                # 메인 페이지 수집
                main_content = self._fetch_web_content(url)
                if main_content:
                    documents.extend(self._create_documents(main_content, url, country, "main"))
                
                # 세부 링크들 찾기 및 수집
                sub_links = self._find_sub_links(url)
                print(f"  → {len(sub_links)}개의 세부 페이지 발견")
                
                for i, sub_url in enumerate(sub_links[:10]):  # 최대 10개로 제한
                    print(f"    세부 문서 {i+1}: {sub_url}")
                    sub_content = self._fetch_web_content(sub_url)
                    if sub_content:
                        documents.extend(self._create_documents(sub_content, sub_url, country, f"sub_{i+1}"))
                        
            except Exception as e:
                print(f"문서 로드 실패 {url}: {e}")
                
        return documents
    
    def _find_sub_links(self, base_url: str) -> List[str]:
        """메인 페이지에서 세부 문서 링크들을 찾기"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(base_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            base_domain = urlparse(base_url).netloc
            
            links = []
            # 다양한 링크 패턴 찾기
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)
                
                # 같은 도메인 내의 문서 링크만 수집
                if (base_domain in full_url and 
                    full_url != base_url and
                    not any(skip in full_url for skip in ['#', 'javascript:', 'mailto:', 'tel:'])):
                    links.append(full_url)
            
            # 중복 제거
            return list(set(links))
            
        except Exception as e:
            print(f"세부 링크 찾기 실패 {base_url}: {e}")
            return []
    
    def _create_documents(self, content: str, url: str, country: str, doc_type: str) -> List[Document]:
        """텍스트 내용을 Document 객체들로 변환"""
        documents = []
        chunks = self.text_splitter.split_text(content)
        
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "source": url,
                    "country": country,
                    "doc_type": doc_type,
                    "chunk_id": f"{country}_{doc_type}_{i}"
                }
            )
            documents.append(doc)
        
        return documents
    
    def _fetch_web_content(self, url: str) -> str:
        """웹 페이지에서 텍스트 내용 추출"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 불필요한 태그 제거
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            # 텍스트만 추출
            text = soup.get_text()
            
            # 공백 정리
            lines = [line.strip() for line in text.splitlines()]
            text = '\n'.join(line for line in lines if line)
            
            return text
            
        except Exception as e:
            print(f"웹 콘텐츠 가져오기 실패 {url}: {e}")
            return "" 