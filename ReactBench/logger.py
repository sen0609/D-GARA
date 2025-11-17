# Filename: logger.py
import json
import time
from typing import Dict, Any

class TestLogger:
    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.events = [] 
        with open(self.log_file_path, 'w') as f:
            pass 

    def log_event(self, event_type: str, details: Dict[str, Any]):
        log_entry = {
            "timestamp": time.time(),
            "type": event_type,
            **details
        }
        self.events.append(log_entry)
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        print(f"  > [Logger] Event recorded: {event_type}")