import schedule
import time
import threading
from datetime import datetime
from services.review_bot import ReviewBot

class UpdateScheduler:
    """지식베이스 업데이트 스케줄러"""
    
    def __init__(self, review_bot: ReviewBot):
        self.review_bot = review_bot
        self.is_running = False
        self.scheduler_thread = None
    
    def setup_schedule(self):
        """스케줄 설정"""
        # 매일 오전 2시에 지식베이스 업데이트
        schedule.every().day.at("02:00").do(self._update_knowledge_base)
        
        # 매주 일요일 오전 3시에 캐시 정리
        schedule.every().sunday.at("03:00").do(self._cleanup_cache)
        
        print("업데이트 스케줄 설정 완료:")
        print("- 지식베이스 업데이트: 매일 오전 2시")
        print("- 캐시 정리: 매주 일요일 오전 3시")
    
    def start_scheduler(self):
        """스케줄러 시작"""
        if self.is_running:
            print("스케줄러가 이미 실행 중입니다.")
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        print("업데이트 스케줄러가 시작되었습니다.")
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        
        schedule.clear()
        print("업데이트 스케줄러가 중지되었습니다.")
    
    def _run_scheduler(self):
        """스케줄러 실행"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 확인
    
    def _update_knowledge_base(self):
        """지식베이스 업데이트 작업"""
        try:
            print(f"[{datetime.now()}] 지식베이스 자동 업데이트 시작")
            self.review_bot.update_knowledge_base()
            print(f"[{datetime.now()}] 지식베이스 자동 업데이트 완료")
        except Exception as e:
            print(f"[{datetime.now()}] 지식베이스 업데이트 오류: {e}")
    
    def _cleanup_cache(self):
        """캐시 정리 작업"""
        try:
            print(f"[{datetime.now()}] 캐시 정리 시작")
            # 현재는 간단히 통계만 출력
            stats = self.review_bot.get_statistics()
            print(f"현재 캐시된 응답 수: {stats['total_responses']}")
            print(f"[{datetime.now()}] 캐시 정리 완료")
        except Exception as e:
            print(f"[{datetime.now()}] 캐시 정리 오류: {e}") 