import sys
import os
import time
import json
import pprint 
from AgentFramework.tools.logger import TaskLogger
from SuccessValidator.success_validator import SuccessValidator 
from time import sleep


from env_config import (
    SUCCESS_CONDITIONS_YAML_PATH
)

# --- 1. Path Configuration and Module Import ---
try:
    # Ensure script can find module folders in current or parent directories
    current_dir = os.path.dirname(os.path.abspath(__file__))

    reactbench_path = os.path.join( 'ReactBench')
    framework_path = os.path.join('AgentFramework')

    if reactbench_path not in sys.path: sys.path.insert(0, reactbench_path)
    if framework_path not in sys.path: sys.path.insert(0, framework_path)

    # Import ReactBench modules
    from ReactBench.state_monitor import get_current_state
    from ReactBench.rule_engine import RuleEngine
    from ReactBench.logger import TestLogger
    # Import all required tools from injector, using Queue version of LogMonitor
    from ReactBench.injector import LogMonitor, execute_adb_command

    # Import all required functions from AI Agent Framework
    from AgentFramework.tools.utilis import get_screen_state, draw_grid_on_image, get_screen_xml, normalize_ui_xml
    from AgentFramework.tools.executor import execute_agent_action


    # Choose which Models to be tested.
    from AgentFramework.Deployment.api_method_gemini import get_action_and_coordinates

except ImportError as e:
    print(f"❌ Module import failed: {e}")
    print("Please ensure 'ReactBench' and 'Framework' folders are in the correct project structure.")
    sys.exit(1)

# --- 2. Global Configuration ---
COMPANION_APP_PACKAGE = "com.example.adbsmarttest"
TEST_SEED = 123
LOGCAT_TAG = "ReactBench_Event"

# --- 4. Core Task Execution Loop ---
def whole_agent_run(
    device_serial: str,
    current_task: dict, 
    max_steps: int,
    screen_width: int,
    screen_height: int,
    interference_enabled: bool,
    max_interferences: int
):
    task_goal = current_task.get('description', 'No task description')
    rule_key = current_task.get('rule_key', 'No rule key')
    task_id = current_task.get('id', 'N/A')
    print(interference_enabled) 
    print(f"[{device_serial}] Task started: \"{task_goal}\" ")
    
    root_log_dir = os.path.abspath("LOGFINAL")
    run_type_dir = "interference" if interference_enabled else "baseline"
    file_name = run_type_dir + '-' + str(task_id)
    final_log_dir = os.path.join(root_log_dir, run_type_dir, file_name, "eva_log.jsonl")
    final_dir=os.path.join(root_log_dir, run_type_dir, file_name)

    os.makedirs(os.path.dirname(final_log_dir), exist_ok=True)

    logger = TaskLogger(task=current_task, interference_enabled=interference_enabled)
    logger_whole = TestLogger(final_log_dir)
    run_dir = logger.run_dir
    action_history = []
    engine = RuleEngine('ReactBench/rules.yaml', 'ReactBench/interference_library.yaml', TEST_SEED, logger_whole, device_serial=device_serial, max_interferences=max_interferences)
    
    # Please ensure your success_conditions.yaml file is located at this path
    success_validator = SuccessValidator(str(SUCCESS_CONDITIONS_YAML_PATH))
    
    log_monitor = None
    active_interference = None
    triggered_interference = None
    final_status = "failure"
    failure_reason = "Task terminated early for unknown reason"
    
    try:
        logger_whole.log_event("task_start", { "device_id": device_serial, "task_id": task_goal, "rule_key": rule_key, "interference_enabled": interference_enabled })

        for i in range(1, max_steps + 1):
            print(f"\n{'='*15} [Device: {device_serial}] Task Execution Step {i} {'='*15}")
            
            # --- Interference Evaluation and Injection ---
            if interference_enabled and not active_interference:
                current_state = get_current_state(COMPANION_APP_PACKAGE, device_serial)
                triggered_interference = engine.evaluate_and_interfere(current_task,current_state, i)
                if triggered_interference:
                    print(f"  > [ReactBench] Interference injected (ID: {triggered_interference.get('id')}). Waiting for Agent response...")
                    active_interference = triggered_interference
                    time.sleep(1.5)
            
            if active_interference and not log_monitor: 
                monitor_output_file = os.path.join(run_dir, f"step_{i}_monitor_event.txt")
                log_monitor = LogMonitor(device_serial, LOGCAT_TAG, monitor_output_file)
                log_monitor.start()
            
            # --- Step 1: Get Screen State ---
            screenshot_path = get_screen_state(final_dir, i, device_serial)
            if not screenshot_path: 
                failure_reason = f"Failed to get screenshot at step {i}"
                logger.log("step_warning", {"step": i, "reason": "screenshot_failed"})      
                logger_whole.log_event("step_warning", {"step": i, "reason": failure_reason})
                break
            raw_ui_xml = get_screen_xml(device_serial)
            if not raw_ui_xml:
                failure_reason = f"Failed to get UI XML at step {i}" 
                logger.log("step_warning", {"step": i, "reason": "ui_xml_failed"})
                logger_whole.log_event("step_warning", {"step": i, "reason": failure_reason})

            # --- Step 2: AI Decision ---
            gridded_screenshot_path = os.path.join(final_dir, f"{i}_screen_gridded.png")
            draw_grid_on_image(screenshot_path, gridded_screenshot_path)
            normalized_ui_elements = normalize_ui_xml(raw_ui_xml)
            # print("Normalized UI elements obtained:")
            # pprint.pprint(normalized_ui_elements)
            action_json = get_action_and_coordinates(
                gridded_screenshot_path, 
                task_goal, 
                screen_width, 
                screen_height, 
                normalized_ui_elements,
                history=action_history
            )
            TARGET_OPTIONAL = {"done", "wait", "back", "text", "swipe", "home","tap"}

            if not action_json or (not action_json.get("target") and action_json.get("action") not in TARGET_OPTIONAL): 
                failure_reason = f"At step {i}, AI decision failed to provide valid target"
                logger_whole.log_event("agent_decision_vlm", {"step": i, "decision": action_json, "history": action_history})
                logger_whole.log_event("step_warning", {"step": i, "reason": failure_reason})
                print(f"❌ Error: {failure_reason}")
                continue
            
            coordinates = action_json.get("coords")
            COORDS_OPTIONAL = {"done", "wait", "back", "home"}
            if not coordinates and action_json.get("action") not in COORDS_OPTIONAL: # If not a done action, must have coordinates
                failure_reason = f"At step {i}, AI response did not include coordinates"
                logger_whole.log_event("agent_decision_vlm", {"step": i, "decision": action_json, "history": action_history})
                logger.log("step_warning", {"step": i, "reason": "missing_coordinates"})
                logger_whole.log_event("step_warning", {"step": i, "reason": failure_reason})
                continue
        
            # --- Step 3: Execute Action ---
            # If it's a done action, skip execution and proceed directly to validation
            if action_json.get("action") != "done":
                result = execute_agent_action(device_serial, action_json, coordinates, screen_width, screen_height, logger=logger)
                print("Action execution completed")
            else:
                result = "DONE_ACTION_SKIPPED" 
                print("AI decision is DONE, skipping actual operation, proceeding to final validation.")

            logger_whole.log_event("agent_decision_vlm", {"step": i, "decision": action_json, "history": action_history})
            logger_whole.log_event("agent_action_execution", {"step": i, "result": result})

            # --- Interference Response Evaluation ---
            if active_interference and log_monitor:
                print(f"  > [ReactBench] Agent has responded to interference. Stopping monitoring and checking results...")
                print("  > [ReactBench] Waiting for log monitoring thread to stabilize...")
                sleep(1) 
                log_monitor.stop()
                captured_events = None
                try:
                    with open(monitor_output_file, 'r', encoding='utf-8') as f:
                        captured_events = f.read().strip()
                except FileNotFoundError:
                    print("No messages captured!")
                
                log_monitor = None 
                
                print("Capture successful this time: ", captured_events)
                if captured_events:
                    active_interference=None
                    
                    print(f"  > [ReactBench] Successfully captured new event '{captured_events}', checking follow-up actions...")
                    post_actions = triggered_interference.get('post_actions', {})
                    triggered_interference = None
                    event_key = f"EVENT:{captured_events}"
                    if event_key in post_actions:
                        actions_to_run = post_actions[event_key]
                        print(f"  > Match successful! Preparing to execute {len(actions_to_run)} follow-up actions...")
                        for action in actions_to_run:
                            if action.get('type') == 'adb':
                                command_str = action.get('command')
                                if command_str: execute_adb_command(device_serial, ["shell"] + command_str.split())
                            elif action.get('type') == 'log':
                                print(f"  > [Post-Action Log]: {action.get('message')}")
                        print("  > All follow-up actions executed!")
                    else:
                        print("  > No follow-up actions configured for this event.")
                        active_interference = None
                        triggered_interference = None

                else:
                    print("  > No button click events detected.")
                    active_interference = None
                    triggered_interference = None

            if action_json:
                action_history.append(action_json)
            if len(action_history) > 5:
                action_history.pop(0)

            print(f"  > Waiting 3 seconds for UI to stabilize...")
            time.sleep(3)

            print("  > Executing objective success state validation...")

            final_check_xml = get_screen_xml(device_serial)
            if final_check_xml and success_validator.check(rule_key, final_check_xml):
                print(f"\n🎉🎉🎉 [{device_serial}] Task '{rule_key}' successfully passed objective validation!")
                final_status = "success"
                failure_reason = ""
                logger.log("task_end", {"status": "success", "reason": "Objective validation passed"})
                logger_whole.log_event("task_end", {"status": "success", "reason": "Objective validation passed"})
                print("Saving success screenshot")
                get_screen_state(final_dir, i+1, device_serial)
                break 
            else:
                # If AI thinks it's done but objective validation fails, this is a special failure mode
                if action_json.get("action") == "done":
                    failure_reason = "AI reported task completion but failed objective validation"
                    logger.log("task_end", {"status": "failure", "failure_mode": "failed_objective_validation"})
                    logger_whole.log_event("task_end", {"status": "failure", "reason": failure_reason})
                    get_screen_state(final_dir, i+1, device_serial)
                    break
                else:
                    print("  > Task has not reached success state yet, continuing...")

        else: 
            print(f"\n⚠️ [{device_serial}] Maximum steps reached, task terminated.")
            failure_reason = "Maximum execution steps reached"
            logger.log("task_end", {"status": "failure", "failure_mode": "max_steps_reached"})
            logger_whole.log_event("task_end", {"status": "failure", "reason": failure_reason})

    finally:
        if log_monitor and log_monitor.thread and log_monitor.thread.is_alive():
            log_monitor.stop()
        print("🏁 Task process completed.")

    print("\n" + "="*20 + " Task Final Result " + "="*20)
    if final_status == "success":
        print("✅ Task Successful!")
    else:
        print("❌ Task Failed!")
        print(f"   Failure reason: {failure_reason}")
    print("="*55)