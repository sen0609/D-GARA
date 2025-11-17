# Standard library imports
import argparse
import sys
import json
import os
import subprocess

# Local application imports
from AgentFramework.Pipeline import whole_agent_run
from AgentFramework.tools.utilis import sanitize_filename, get_connected_devices
from env_config import (
    TASKS_JSON_PATH,
    RESOLUTION_WIDTH,
    RESOLUTION_HEIGHT
)

# Default screen dimensions for device automation
SCREEN_WIDTH = RESOLUTION_WIDTH
SCREEN_HEIGHT = RESOLUTION_HEIGHT

def load_tasks(json_path):
    """
    Load task configurations from a JSON file.
    
    Args:
        json_path (str): Path to the JSON file containing task definitions
        
    Returns:
        dict: Loaded task configurations or None if file not found
    """
    if not os.path.exists(json_path):
        print(f"❌ Error: Task file not found '{json_path}'.")
        return None
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def close_all_apps_and_return_home(device_serial):
    """
    Close all running third-party applications on the specified Android device.
    
    Args:
        device_serial (str): The serial number of the target Android device
        
    Returns:
        bool: True if operation successful, False otherwise
    """
    if not device_serial:
        print("❌ [close_all_apps] Operation failed: No valid device serial number provided.")
        return False

    EXCLUSION_LIST = {
        "com.github.kr328.clash",
        # Add any other apps that should not be closed here
    }
        
    try:
        print(f"\nℹ️ Getting third-party app list for device {device_serial}...")
        command_get_packages = ["adb", "-s", device_serial, "shell", "pm", "list", "packages", "-3"]
        
        result = subprocess.run(
            command_get_packages,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        
        package_lines = result.stdout.strip().splitlines()
        if not package_lines:
            print("  - No third-party applications found.")
        else:
            print(f"  - Found {len(package_lines)} third-party apps, preparing to clear background...")
            closed_count = 0
            for line in package_lines:
                package_name = line.split(":", 1)[1].strip()
                
                if package_name in EXCLUSION_LIST or "launcher" in package_name:
                    print(f"  - Skipping excluded app: {package_name}")
                    continue
                
                print(f"  - Closing: {package_name}")
                command_force_stop = ["adb", "-s", device_serial, "shell", "am", "force-stop", package_name]
                subprocess.run(command_force_stop, check=True, capture_output=True)
                closed_count += 1
            print(f"✅ Closed {closed_count} third-party applications.")

        settings_package = "com.android.settings"
        try:
            print(f"  - Closing: {settings_package}")
            command_force_stop_settings = ["adb", "-s", device_serial, "shell", "am", "force-stop", settings_package]
            subprocess.run(command_force_stop_settings, check=True, capture_output=True)
            print(f"✅ Application {settings_package} has been closed.")
        except subprocess.CalledProcessError:
            print(f"  - (Note) {settings_package} is not running or cannot be closed.")
            pass

        return True

    except FileNotFoundError:
        print("❌ Error: 'adb' command not found. Please ensure Android SDK Platform-Tools is installed and configured in system PATH.")
        return False
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip() if e.stderr else "No error output"
        print(f"❌ Error: ADB command execution failed.")
        print(f"   - Error message: {error_message}")
        return False
    except Exception as e:
        print(f"❌ Unknown error occurred in close_all_apps_and_return_home: {e}")
        return False

if __name__ == "__main__":
    # Initialize argument parser for command-line interface
    parser = argparse.ArgumentParser(description="AI Agent Automation Test Batch Execution Script")
    parser.add_argument("--device", type=str, help="Specify device serial number for task execution (optional)")
    parser.add_argument("--step", type=int, default=15, help="Set maximum execution steps, default is 15")
    parser.add_argument("--width", type=int, default=SCREEN_WIDTH, help="Set screen width")
    parser.add_argument("--height", type=int, default=SCREEN_HEIGHT, help="Set screen height")
    parser.add_argument("--interference", action="store_true", help="Use this flag to enable interference")
    parser.add_argument("--max-interferences", type=int, default=1, help="Maximum number of interferences in one task, default is 1")
    parser.add_argument("--start-id", type=int, default=None, help="Specify starting task ID (optional, starts from beginning by default)")
    parser.add_argument("--end-id", type=int, default=None, help="Specify ending task ID (optional, runs until end of list by default)")
    args = parser.parse_args()

    tasks = load_tasks(TASKS_JSON_PATH)
    if not tasks:
        sys.exit(1)
        
    print(f"✅ Successfully loaded {len(tasks)} tasks.")

    device_serial = args.device
    if not device_serial:
        print("No device specified, will automatically select the first detected device...")
        devices = get_connected_devices()
        if not devices:
            print("❌ Error: No Android devices detected.")
            sys.exit(1)
        device_serial = devices[0]
    
    print(f"✅ Target device: {device_serial}")
    print(f"   - Interference enabled: {args.interference}")

    start_index = 0  
    if args.start_id is not None:
        print(f"ℹ️ Looking for starting task ID: {args.start_id}...")
        found = False
        for i, task in enumerate(tasks):
            if task.get('id') == args.start_id:
                start_index = i
                found = True
                print(f"✅ Found starting task, will begin from task {start_index + 1}.")
                break
        
        if not found:
            print(f"❌ Error: Task with ID {args.start_id} not found in task list.")
            sys.exit(1)

    end_index = len(tasks) - 1 
    if args.end_id is not None:
        print(f"ℹ️ Looking for ending task ID: {args.end_id}...")
        found = False
        for i, task in enumerate(tasks):
            if task.get('id') == args.end_id:
                end_index = i
                found = True
                print(f"✅ Found ending task, will stop at task {end_index + 1}.")
                break
        
        if not found:
            print(f"❌ Error: Task with ID {args.end_id} not found in task list.")
            sys.exit(1)

    print("-" * 50)

    for i in range(start_index, end_index + 1):
        task = tasks[i] 
        
        task_id = task.get('id', 'N/A') 
        task_description = task.get('description', 'No description')
        task_rule_key = task.get('rule_key', 'No rule')
        
        current_run_number = i - start_index + 1
        total_run_count = end_index - start_index + 1
        print(f"\n▶️ Starting task {current_run_number}/{total_run_count} (Task {i+1} in total list, ID: {task_id})")
        print(f"   - Task description: \"{task_description}\"")
        print(f"   - Validation rule key: {task_rule_key}")

        whole_agent_run(
            device_serial=device_serial,
            current_task=task,
            max_steps=args.step,
            screen_width=args.width,
            screen_height=args.height,
            interference_enabled=args.interference,
            max_interferences=args.max_interferences
        )

        print(f"\n✅ Task {current_run_number}/{total_run_count} (ID: {task_id}) execution completed.")
        
        print("Cleaning up background applications on device...")
        close_all_apps_and_return_home(device_serial)
        
        print("-" * 50)

    print("\n🎉 All specified tasks have been completed.")