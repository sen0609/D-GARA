import os
import json
import time
import subprocess
import readchar
from AgentFramework.tools.utilis import get_screen_state,get_screen_xml
from env_config import (
    TASKS_JSON_PATH
)

# Load task list
def load_task_names(task_file=TASKS_JSON_PATH):
    with open(task_file, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    return tasks

# Execute ADB command to open application
def open_app_with_adb(package_name):
    try:
        subprocess.run(['adb', 'shell', 'monkey', '-p', package_name, '-c', 'android.intent.category.LAUNCHER', '1'], check=True)

        print(f"Application '{package_name}' has been successfully launched!")
    except subprocess.CalledProcessError:
        print(f"❌ Unable to launch application: {package_name}")
        return False
    return True

# Take screenshot and get XML file
def save_screenshot_and_xml(device_serial, task_name, step, task_dir):
    # --- Screenshot part (robust two-step method) ---
    device_path = f"/sdcard/screen_{step}.png"
    temp_local_path = f"temp_screenshot_{step}.png" 
    final_screenshot_path = os.path.join(task_dir, f"step_{step}_screenshot.png")

    try:
        # Step 0: Take screenshot on device
        subprocess.run(['adb', '-s', device_serial, 'shell', 'screencap', device_path], check=True, capture_output=True)
        
        # Step 1: Pull screenshot to local temporary file
        subprocess.run(['adb', '-s', device_serial, 'pull', device_path, temp_local_path], check=True, capture_output=True)
        
        # Step 2: Move temporary file to final complex path using Python
        os.rename(temp_local_path, final_screenshot_path)
        print(f"  > Saved screenshot as: {final_screenshot_path}")

    except (subprocess.CalledProcessError, OSError) as e:
        print(f"  > Failed to get or save screenshot: {e}")
    finally:
        # Clean up screenshot on device and temporary local file
        subprocess.run(['adb', '-s', device_serial, 'shell', 'rm', device_path], capture_output=True)
        if os.path.exists(temp_local_path):
            os.remove(temp_local_path)

    # --- XML part ---
    raw_ui_xml = get_screen_xml(device_serial)
    if raw_ui_xml:
        groundtruth_xml_path = os.path.join(task_dir, f"step_{step}_ui.xml")
        with open(groundtruth_xml_path, 'w', encoding='utf-8') as f:
            f.write(raw_ui_xml)
        print(f"  > Saved XML as: {groundtruth_xml_path}")
    else:
        print(f"  > Failed to get UI XML, skipping save")


# Task execution loop
def execute_task(device_serial, task_file=TASKS_JSON_PATH, start_task_id=1, max_steps=50):
    # Load task list
    tasks = load_task_names(task_file)
    
    # Directly iterate through task list, no longer using enumerate
    for task in tasks:
        # Get id directly from task object
        task_id = task['id']

        if task_id < start_task_id:
            continue
        
        task_name = task['description']
        package_name = task['app']

        # Construct new directory name with ID
        dir_name_with_id = f"{task_id}_{task_name}"

        # Add task ID to print message for better clarity
        print(f"\n{'='*15} [Task {task_id}] {task_name} {'='*15}")
        
        # Launch application
        if not open_app_with_adb(package_name):
            print("❌ Skipping this task.")
            continue
        
        # Create task directory using new directory name
        task_dir = os.path.join("Collected_trajs", dir_name_with_id)
        try:
            os.makedirs(task_dir, exist_ok=True)
        except OSError as e:
            print(f"❌ Failed to create directory '{task_dir}': {e}")
            print("❌ Possible reason: task description contains special characters invalid for filenames. Skipping this task.")
            continue

        for i in range(1, max_steps + 1):
            print(f"\n{'='*10} [Step: {i}] Executing task {task_name} {'='*10}")
            
            # Get user input: whether to take screenshot and save XML
            print("Press S to take screenshot and save XML, N to skip this task: ", end="", flush=True) # Print prompt
            user_input = readchar.readkey().upper()  # Wait for single key press and convert to uppercase
            print(user_input) # Echo user input immediately for better experience
            
            if user_input == 'S':
                save_screenshot_and_xml(device_serial, task_name, i, task_dir)
            elif user_input == 'N':
                # When user inputs 'N'
                print(f"❌ User chose to skip current task: {task_name}")
                break  # Use break to immediately terminate this task's step loop
            
            # Wait 1 second, simulating next step
            print(f"  > Waiting 1 second...")
            time.sleep(1)

    # Protect against task_name being undefined if tasks is empty
    if 'task_name' in locals():
        print(f"Task '{task_name}' execution completed.\n")


device_serial = 'emulator-5554'  # Change this to your device's serial number
execute_task(device_serial)
