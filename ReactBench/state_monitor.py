# Filename: state_monitor.py

import subprocess
import xml.etree.ElementTree as ET
import time
import re

def get_current_activity_name(device_serial: str) -> str | None:
    """
    Get the name of the current foreground Activity using ADB.
    """
    try:
        command = ["adb", "-s", str(device_serial), "shell", "dumpsys", "window", "windows"]
        # Use utf-8 encoding to avoid decoding errors in different system environments
        output = subprocess.check_output(command, text=True, encoding='utf-8', errors='ignore', timeout=5)
        
        # Use regex to match lines with mCurrentFocus or mFocusedApp to get the current active Activity
        # Example: mCurrentFocus=Window{... u0 com.bilibili.app.in/com.bilibili.app.in.MainActivity}
        match = re.search(r'mCurrentFocus=Window{.*\s(?:u\d+\s)?(.*?)/([^\s}]+)}', output)
        if match:
            # match.group(2) is usually the abbreviated Activity name, e.g., .MainActivity
            activity_name = match.group(2)
            # Sometimes includes package name, we only take the last class name part
            if '.' not in activity_name:
                return f".{activity_name}"
            return activity_name
        return "Unknown"
    except Exception:
        return "Unknown"

def get_current_ui_xml_content(device_serial: str) -> str | None:
    """
    Get the current UI's XML layout content using uiautomator dump.
    """
    device_xml_path = "/sdcard/uidump.xml"
    try:
        # First execute dump operation to save UI layout to a temporary file on the device
        subprocess.run(["adb", "-s", str(device_serial), "shell", "uiautomator", "dump", device_xml_path], 
                         check=True, timeout=15, capture_output=True)
        # Brief wait to ensure file write completion
        time.sleep(0.2)
        # Use cat command to read and return the temporary file content
        result = subprocess.run(["adb", "-s", str(device_serial), "shell", "cat", device_xml_path], 
                                capture_output=True, text=True, check=True, timeout=5, encoding='utf-8', errors='ignore')
        return result.stdout
    except Exception:
        return None

def parse_ui_elements(xml_root: ET.Element) -> list:
    """
    Parse XML tree, extract important attributes of all UI nodes, and return a list of dictionaries.
    """
    if xml_root is None:
        return []
        
    ui_elements_list = []
    # Traverse all <node> tags in the XML
    for node in xml_root.iter('node'):
        element_properties = {
            "class": node.get("class", ""),
            "text": node.get("text", ""),
            "resource_id": node.get("resource-id", ""),
            "content_desc": node.get("content-desc", ""),
            "bounds": node.get("bounds", ""),
            "clickable": node.get("clickable", "false") == "true",
            "enabled": node.get("enabled", "false") == "true",
        }
        ui_elements_list.append(element_properties)
    return ui_elements_list


def get_current_state(app_package: str, device_serial: str) -> dict:
    """
    Get a structured state dictionary containing specific data about the current interface.
    """
    # 1. Get current foreground Activity name
    activity = get_current_activity_name(device_serial)
    
    # 2. Get UI layout XML and parse into element list
    raw_xml = get_current_ui_xml_content(device_serial)
    ui_elements = []
    if raw_xml:
        try:
            xml_root = ET.fromstring(raw_xml)
            ui_elements = parse_ui_elements(xml_root)
        except ET.ParseError:
            pass # Return empty list if XML parsing fails

    # 3. (Optional) Check if interference App's popup is in foreground
    is_interference_active = False
    # (This logic can be preserved or modified as needed)
    # try:
    #     output = subprocess.check_output(...)
    #     if companion_app_package in output:
    #         is_interference_active = True
    # except Exception:
    #     pass

    # 4. Assemble into a standard dictionary with specific data that can be directly used by the rule engine
    state = {
        "current_activity": activity,
        "all_ui_elements": ui_elements,
        "is_interference_active": is_interference_active
    }
    
    return state