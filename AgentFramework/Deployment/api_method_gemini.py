import json
import re
import os
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
from google.api_core.exceptions import PermissionDenied, ResourceExhausted

# --- Global Settings ---
# 1. Set up proxy (if needed)
os.environ['http_proxy'] = 'http://127.0.0.1:7890'
os.environ['https_proxy'] = 'http://127.0.0.1:7890'

load_dotenv()


# Store all available keys in a list
API_KEYS = [
]

class ApiKeyManager:
    """A simple class to manage and rotate API key list."""
    def __init__(self, keys):
        if not keys:
            raise ValueError("API key list cannot be empty")
        self.keys = keys
        self.current_index = 0

    def get_current_key(self):
        """Get the currently active key."""
        return self.keys[self.current_index]

    def rotate_to_next_key(self):
        """Switch to next key, returns True if we've rotated through all keys."""
        self.current_index = (self.current_index + 1) % len(self.keys)
        print(f"API Key failed or reached limit, switching to next key (index: {self.current_index})...")
        # If index is back to 0, all keys have been tried
        return self.current_index == 0

# Create a global key manager instance
api_key_manager = ApiKeyManager(API_KEYS)

try:
    genai.configure(api_key=api_key_manager.get_current_key())
    print(f"Successfully configured initial API key (index: {api_key_manager.current_index})")
except Exception as e:
    print(f"Initial API key configuration failed: {e}")


# Coordinate parsing function remains unchanged
def parse_coordinates(text_response: str):
    if not text_response:
        return None
    if text_response.strip() == '[]':
        print(f"Parsing successful (empty coordinates): []")
        return []
    swipe_match = re.search(r'\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]', text_response)
    if swipe_match:
        print(f"Parsing successful (4 coordinates): {swipe_match.group(0)}")
        return [int(swipe_match.group(1)), int(swipe_match.group(2)), int(swipe_match.group(3)), int(swipe_match.group(4))]
    tap_match = re.search(r'\[\s*(\d+)\s*,\s*(\d+)\s*\]', text_response)
    if tap_match:
        print(f"Parsing successful (2 coordinates): {tap_match.group(0)}")
        return [int(tap_match.group(1)), int(tap_match.group(2))]
    print(f"Parsing failed: Cannot find coordinates in model response '{text_response}'")
    return None


def get_action_and_coordinates(image_path, task_goal, screen_width, screen_height, normalized_elements, history: list = None):
    """
    Use Gemini Vision API to analyze screenshot and get next action.
    [With key rotation functionality]
    """
    print("\nVisual analysis in progress... Calling Gemini Vision API...")

    history_prompt = ""
    if history:
        formatted_history = [f"步骤 {i+1}: 动作='{pa.get('action', 'N/A')}', 目标='{pa.get('target', 'N/A')}'" for i, pa in enumerate(history)]
        history_prompt = f"历史操作记录：\n" + '\n'.join(formatted_history)
    elements_str = json.dumps(normalized_elements, ensure_ascii=False, indent=2)
    prompt = f"""
你是一个安卓任务规划与定位AI。
你的任务目标是：“{task_goal}”。
请分析当前屏幕截图，规划下一步操作，同时返回该操作所涉及目标的坐标。
{history_prompt}
要求输出一个JSON对象，包含：
- "thought": (字符串) 你的判断理由；
- "action": (字符串) 动作类型：'tap', 'text', 'swipe', 'back', 'done', 'wait' ,'home'之一；
- "target": (字符串) 你要操作的UI控件的文字描述；
- "coords": (列表) 操作目标的中心坐标，例如 [120, 310]；特别地如果是swipe，那么输出应该为[x_start,y_start,x_end,y_end];
- "input_text": (字符串, 可选) 如果是文本输入则提供内容。
例子：
(
  "thought": "我需要点击'设置'按钮",
  "action": "tap",
  "target": "设置",
  "coords": [120, 310]
)
()
    "thought": "我需要向上滑动屏幕以查看更多内容",
    "action": "swipe",
    "target": "向上滑动",
    "coords": [500, 1000, 500, 300]
)
(
    "thought": "我需要返回主界面",
    "action": "home",
    "target": "主界面",
    "coords": []
)
(
    "thought": "我在搜索框处输入天气",
    "action": "text",
    "target": "搜索框",
    "coords": [200, 400],
    "input_text": "天气"
)
(
    "thought": "根据任务以及当前页面，我判断任务已经完成",
    "action": "done",
    "target": "任务完成",
    "coords": []
)
注意：目标控件请结合文字描述综合判断，不要返回多余内容。
"""
    if normalized_elements:
        ui_prompt = "这里是界面上可交互的UI元素列表:\n" + elements_str
        final_prompt = prompt + "\n" + ui_prompt
    else:
        vision_only_prompt = "注意：无法获取UI元素信息，请你完全依赖图像内容进行判断。"
        final_prompt = prompt + "\n" + vision_only_prompt



    raw_text = ""
    for i in range(len(api_key_manager.keys)):
        try:
            current_key = api_key_manager.get_current_key()
            genai.configure(api_key=current_key)
            
            model = genai.GenerativeModel('gemini-2.5-flash')
            if image_path.startswith('file://'):
                image_path = image_path[7:]
            img = Image.open(image_path)
            contents = [final_prompt, img]

            print(f"Sending request to Gemini (using key index: {api_key_manager.current_index})...")
            response = model.generate_content(contents)
            raw_text = response.text
            print(f"--- Complete model response ---\n{raw_text}\n------------------")

            json_string = raw_text
            if "```json" in json_string:
                json_string = json_string.split("```json")[1].split("```")[0]

            start_index = json_string.find('{')
            end_index = json_string.rfind('}')
            if start_index != -1 and end_index != -1:
                json_string = json_string[start_index:end_index+1]
                result = json.loads(json_string)
                if 'coords' in result and result['coords']:
                    result['coords'] = parse_coordinates(json.dumps(result['coords']))
                return result 
            else:
                raise json.JSONDecodeError("No valid JSON object found", json_string, 0)

        # Catch errors related to API key/quota
        except (PermissionDenied, ResourceExhausted) as e:
            print(f"API key (index {api_key_manager.current_index}) validation failed or reached limit: {e}")
            has_wrapped_around = api_key_manager.rotate_to_next_key()
            # If all keys have been tried, no need to continue
            if has_wrapped_around:
                print("All API keys have failed, stopping retry.")
                break # Exit the for loop
        
        # Catch other unknown exceptions
        except Exception as e:
            print(f"Unknown exception occurred during API call or processing: {e}")
            # For unknown errors, we can also choose to switch keys and retry
            api_key_manager.rotate_to_next_key()
            
    # If loop ends without successful return, all keys have failed
    print("All API keys have failed, unable to get model response.")
    return None