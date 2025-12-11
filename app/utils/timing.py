# app/utils/timing.py
import time
import logging
from typing import Dict, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class PerformanceTimer:
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.start_time = time.time()
        self.steps: Dict[str, float] = {}
        self.step_start: Optional[float] = None
        
    def start_step(self, step_name: str):
        self.step_start = time.time()
        logger.info(f"[{self.request_id}] Starting step: {step_name}")
        
    def end_step(self, step_name: str):
        if self.step_start is None:
            return
        duration = (time.time() - self.step_start) * 1000
        self.steps[step_name] = duration
        logger.info(f"[{self.request_id}] Completed step: {step_name} in {duration:.2f}ms")
        self.step_start = None
        
    @contextmanager
    def time_step(self, step_name: str):
        self.start_step(step_name)
        try:
            yield
        finally:
            self.end_step(step_name)
            
    def get_total_time(self) -> float:
        return (time.time() - self.start_time) * 1000
        
    def log_summary(self):
        total_time = self.get_total_time()
        logger.info(f"[{self.request_id}] Performance Summary:")
        logger.info(f"[{self.request_id}] Total time: {total_time:.2f}ms")
        
        for step, duration in self.steps.items():
            percentage = (duration / total_time) * 100
            logger.info(f"[{self.request_id}] - {step}: {duration:.2f}ms ({percentage:.1f}%)")
