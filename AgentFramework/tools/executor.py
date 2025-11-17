import time
import subprocess
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from tools.utilis import run_adb_command, get_screen_xml
from tools.logger import TaskLogger

def execute_agent_action(device_serial: str, action_json: dict, coordinates: tuple, screen_width: int, screen_height: int,logger):
    """Execute ADB actions on the specified device based on decisions and coordinates."""
    action_type = action_json.get("action")
    input_text = action_json.get("input_text", "")
    
    if not coordinates and action_type != "DONE" and action_type != "back" and action_type != "wait" and action_type != "home":
        log_message = f"Action '{action_type}' cannot be executed due to missing coordinates."
        print(f"  > [Error] {log_message}")
        # Record this attempt even if execution fails
        logger.log("agent_action", {
            "action": action_type,
            "success": False,
            "reason": "missing_coordinates"
        })
        return False
    
    if action_type in ("tap", "click"):
        if coordinates and len(coordinates) == 2:
            x, y = coordinates
            run_adb_command(device_serial, ["shell", "input", "tap", str(x), str(y)])
            logger.log("agent_action", {
                "action": action_type,
                "target_coordinates": [x, y],
                "success": True 
            })
            return True
        else:
            log_message = f"Action '{action_type}' provided incorrect number of coordinates: {len(coordinates) if coordinates else 0} (should be 2)."
            print(f"  > [Error] {log_message}")
            logger.log("agent_action", {"action": action_type, "success": False, "reason": "incorrect_coordinate_count"})
            return False

    elif action_type in ("text", "input", "type"):
        if coordinates and len(coordinates) == 2:
            x, y = coordinates
            run_adb_command(device_serial, ["shell", "input", "tap", str(x), str(y)])
            time.sleep(0.5)
            # Note: In newer versions of ADB, directly passing text might be more stable, no extra quotes needed
            run_adb_command(device_serial, ["shell", "input", "text", input_text])
            logger.log("agent_action", {
                "action": action_type,
                "target_coordinates": [x, y],
                "text": input_text,
                "success": True
            })
            return True
        else:
            log_message = f"Action '{action_type}' provided incorrect number of coordinates: {len(coordinates) if coordinates else 0} (should be 2)."
            print(f"  > [Error] {log_message}")
            logger.log("agent_action", {"action": action_type, "success": False, "reason": "incorrect_coordinate_count"})
            return False

    elif action_type == "swipe":
        if coordinates and len(coordinates) == 4:
            x1, y1, x2, y2 = coordinates
            duration_ms = 300 # Set a reasonable swipe duration in milliseconds
            run_adb_command(device_serial, ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])
            logger.log("agent_action", {
                "action": action_type,
                "start_coordinates": [x1, y1],
                "end_coordinates": [x2, y2],
                "duration_ms": duration_ms,
                "success": True
            })
            return True
        else:
            # If coordinate count is incorrect, log the error
            log_message = f"Action '{action_type}' provided incorrect number of coordinates: {len(coordinates) if coordinates else 0} (should be 4)."
            print(f"  > [Error] {log_message}")
            logger.log("agent_action", {"action": action_type, "success": False, "reason": "incorrect_coordinate_count"})
            return False
            
    elif action_type == "back":
        run_adb_command(device_serial, ["shell", "input", "keyevent", "4"])
        logger.log("agent_action", {"action": "back", "success": True})
        return True 
        
    elif action_type == "wait":
        time.sleep(1)
        logger.log("agent_action", {"action": "wait", "success": True})
        return True 
    
    elif action_type == "home":
        run_adb_command(device_serial, ["shell", "input", "keyevent", "3"])
        logger.log("agent_action", {"action": "home", "success": True})
        return True
        
    elif action_type == "DONE":
        logger.log("agent_action", {"action": "DONE", "success": True})
        return "DONE"
    
    log_message = f"Unknown action type: {action_type}"
    print(f"  > [Warning] {log_message}")
    logger.log("agent_action", {
        "action": action_type,
        "success": False,
        "reason": "unknown_action_type"
    })
    return False