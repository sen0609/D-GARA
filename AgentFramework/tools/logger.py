# Filename: logger.py
import os
import json
import time
from datetime import datetime
import shutil

# Filename: logger.py

class TaskLogger:
    """
    A dedicated logger for managing log records of a single task.
    [New Version: Overwrite Mode] If a task folder with the same name exists, it will be deleted and recreated.
    """
    def __init__(self, task: dict, log_dir: str = os.path.abspath("LOGFINAL"),interference_enabled: bool=True):
        """
        Initialize a task logger.

        Args:
            task_id (str): Unique identifier for the current task.
            log_dir (str, optional): Root directory for storing all log files. Defaults to "logs".
        """
        task_goal = task.get('description', 'No task description')
        task_id = task.get('id', 'N/A')
        # 1. Construct folder path named by task ID (no longer using timestamp)
        #    Example: logs/bili_search_daoxiang
        if interference_enabled:

            run_type_dir="interference"
        else:
            run_type_dir="baseline"
        file_name=run_type_dir+'-'+str(task_id)
        run_dir=os.path.join(log_dir,run_type_dir,file_name)


        # 2. Check if this folder exists
        if os.path.exists(run_dir):
            # 3. If exists, delete the old folder and all its contents first
            print(f"Found existing task folder: {run_dir}. Deleting...")
            shutil.rmtree(run_dir)
            print("Old folder deleted.")

        # 4. Create a brand new empty folder
        os.makedirs(run_dir)
        print(f"Created new task folder: {run_dir}")
        
        # 5. Define and store attributes for later use
        self.run_dir = run_dir
        self.log_file_path = os.path.join(self.run_dir, "run_log.jsonl")

    def log(self, event_type: str, event_data: dict):
        """
        Log an event to the log file. (This method does not need modification)
        """
        log_entry = {
            "timestamp": time.time(),
            "type": event_type,
            **event_data
        }
        
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except IOError as e:
            print(f"[Error] Cannot write to log file {self.log_file_path}: {e}")

