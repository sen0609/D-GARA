# Filename: utilis.py 
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
import time
import traceback

# It's recommended to make ADB_PATH configurable, but we simplify it as a constant here
# Please ensure your 'adb.exe' path is in the system's PATH environment variable
ADB_PATH = "adb" 

# ==============================================================================
# Tool Name: ADB Command Executor
# ==============================================================================
def run_adb_command(device_serial: str, command: list):
    """
    Execute an ADB command given as a list for a specific device.
    - device_serial: Target device's serial number (e.g., 'emulator-5554').
    - command: A list containing the command and its arguments (e.g., ['shell', 'ls', '-l']).
    Returns: Command's standard output string on success, None on failure.
    """
    # -s <device_serial> 参数被插入到 'adb' 之后，明确指定目标设备。
    full_command = [ADB_PATH, "-s", device_serial] + command
    
    try:
        result = subprocess.run(
            full_command, 
            check=True,         # Raises exception if command returns non-zero exit code
            capture_output=True,# Capture both stdout and stderr
            timeout=15          # Set 15-second timeout to prevent infinite hang
        )
        # Try UTF-8 decoding first, as it's the most standard case
        try:
            return result.stdout.decode('utf-8').strip()
        except UnicodeDecodeError:
            # If UTF-8 decoding fails, typically in Windows Chinese environment, try GBK
            return result.stdout.decode('gbk', errors='ignore').strip()

    except subprocess.CalledProcessError as e:
        # When command executed but returned error code (e.g., file not found)
        error_message = e.stderr.decode('gbk', errors='ignore').strip()
        print(f"  > [ADB Error] Command '{' '.join(full_command)}' failed. Return code: {e.returncode}, Error message: {error_message}")
        return None
    except subprocess.TimeoutExpired:
        print(f"  > [ADB Error] Command '{' '.join(full_command)}' timed out.")
        return None
    except FileNotFoundError:
        print(f"  > [System Error] ADB command '{ADB_PATH}' not found. Please ensure ADB is properly installed and in PATH.")
        return None
    except Exception as e:
        print(f"  > [Unknown Error] Error executing ADB command: {e}")
        return None

# ==============================================================================
# Tool Name: Get Screen XML Layout
# ==============================================================================
def get_screen_xml(device_serial: str) -> str | None:
    """
    Get UI XML layout content from specified device using a stable "two-step" method.
    Returns: XML content string, or None on failure.
    """
    print("  > [Status] Getting UI XML layout...")
    device_xml_path = "/sdcard/window_dump.xml"
    
    dump_command = ["shell", "uiautomator", "dump", device_xml_path, "--compressed"]
    if run_adb_command(device_serial, dump_command) is None:
        print("  > [Error] uiautomator dump command execution failed.")
        return None
    time.sleep(0.2)
    cat_command = ["shell", "cat", device_xml_path]
    xml_content = run_adb_command(device_serial, cat_command)
    rm_command = ["shell", "rm", device_xml_path]
    run_adb_command(device_serial, rm_command)
    if xml_content:
        start_index = xml_content.find('<')
        if start_index != -1:
            print("  > [Status] Successfully retrieved and cleaned XML content.")
            return xml_content[start_index:]
    print("  > [Error] Retrieved XML content is empty or invalid.")
    return None



# ==============================================================================
# Tool Name: Normalize UI XML Layout
# ==============================================================================
def normalize_ui_xml(raw_xml_string: str) -> list:
    """Parse raw XML string into a list of dictionaries containing key UI element information."""
    if not raw_xml_string: return []

    def parse_bounds(bounds_str):
        match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
        if not match: return None
        x1, y1, x2, y2 = map(int, match.groups())
        return [(x1 + x2) // 2, (y1 + y2) // 2]

    def traverse(node, elements_list):
        # Extract key attributes
        description = node.get('text', '') or node.get('content-desc', '')
        resource_id = node.get('resource-id', '')
        
        # Only add when element has substantial content or is identifiable
        if description or resource_id:
            center_coords = parse_bounds(node.get('bounds', ''))
            if center_coords:
                elements_list.append({
                    "uid": len(elements_list),
                    "resource_id": resource_id,
                    "description": description,
                    "class": node.get('class', ''),
                    "clickable": node.get('clickable') == 'true',
                    "center_coords": center_coords
                })
        for child in node:
            traverse(child, elements_list)

    try:
        root = ET.fromstring(raw_xml_string)
        flattened_list = []
        traverse(root, flattened_list)
        return flattened_list
    except ET.ParseError as e:
        print(f"  > [Error] XML parsing failed: {e}")
        return []

# ==============================================================================
# Tool Name: Get Screen Screenshot
# ==============================================================================

def get_screen_state(run_dir: str, round_count: int, device_serial: str) -> str | None:
    """
    Capture the current screen of the specified device and save it to the run directory.
    [Final Integration]: Fixed all known issues including parameter order, path logic, and encoding.
    """
    try:
        # Step 1: Define a pure, simple filename
        screenshot_filename = f"{round_count}_screen.png"

        # Step 2: Define the complete path where image will be saved on the host computer
        host_save_path = os.path.join(run_dir, screenshot_filename)

        # Step 3: Define the simple path where screenshot will be temporarily saved on Android device
        device_temp_path = f"/sdcard/{screenshot_filename}"


        screencap_command = ["adb", "-s", str(device_serial), "shell", "screencap", str(device_temp_path)]
        subprocess.run(screencap_command, check=True, capture_output=True, encoding='utf-8', errors='ignore')

        pull_command = ["adb", "-s", str(device_serial), "pull", str(device_temp_path), str(host_save_path)]
        subprocess.run(pull_command, check=True, capture_output=True, encoding='utf-8', errors='ignore')

        rm_command = ["adb", "-s", str(device_serial), "shell", "rm", str(device_temp_path)]
        subprocess.run(rm_command, check=False, capture_output=True, encoding='utf-8', errors='ignore')
        
        print(f"  > [{device_serial}] [Util] Screenshot successful, saved to: {host_save_path}")
        return host_save_path

    except Exception as e:
        print(f"\n > [{device_serial}] [Util] [Failed] Error occurred during get_screen_state execution: {e}")
        traceback.print_exc()
        return None
# ==============================================================================
# Tool Name: Draw Grid
# ==============================================================================

def draw_grid_on_image(image_path: str, output_path: str, grid_interval=100, font_size=35):
    """Draw red grid lines and pure numeric coordinate labels on the image."""
    print(f"  > [Image Processing] Drawing coordinate grid for image {os.path.basename(image_path)}...")
    try:
        image = Image.open(image_path).convert("RGBA")
        overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        width, height = image.size

        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        for x in range(0, width, grid_interval):
            draw.line([(x, 0), (x, height)], fill=(255, 0, 0, 100), width=1)
            draw.text((x + 2, 2), f"{x}", fill=(255, 0, 0, 200), font=font)

        for y in range(0, height, grid_interval):
            draw.line([(0, y), (width, y)], fill=(255, 0, 0, 100), width=1)
            draw.text((2, y + 2), f"{y}", fill=(255, 0, 0, 200), font=font)

        combined = Image.alpha_composite(image, overlay).convert("RGB")
        combined.save(output_path, "PNG")
        print(f"  > [Image Processing] Grid image saved to: {output_path}")
        return output_path

    except Exception as e:
        print(f"  > [Error] Failed to draw grid: {e}")
        return image_path

def get_connected_devices() -> list:
    """Get serial numbers of all currently connected ADB devices."""
    try:
        output = subprocess.check_output(["adb", "devices"], text=True, encoding='utf-8', errors='ignore')
        devices = [line.split('\t')[0] for line in output.strip().split('\n')[1:] if "device" in line]
        return devices
    except Exception:
        return []
def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename or folder name by removing all Windows illegal characters.
    """
    # Define set of all illegal characters
    illegal_chars = r'[\/\\:*\?"<>|，]'
    
    # Use re.sub() to replace all illegal characters with underscore '_'
    sanitized_name = re.sub(illegal_chars, '_', filename)
    return sanitized_name