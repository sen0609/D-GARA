import json
import re
import os
from http import HTTPStatus
from dashscope import MultiModalConversation
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Get environment variables
dashscope_key = os.getenv("DASHSCOPE_API_KEY")
debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

def parse_coordinates(text_response: str):
    """
    Parse coordinates from model's text response.
    This upgraded version can handle three cases: [x, y], [x1, y1, x2, y2], and empty [].
    """
    if not text_response:
        return None

    # 0. New: First check if it's empty brackets [] indicating "no operation"
    # Using .strip() removes any potential whitespace before/after, improving code robustness
    if text_response.strip() == '[]':
        print(f"Parsing successful (empty coordinates): []")
        return []

    # 1. Next try to match 4 coordinates (designed for swipe action)
    # Regular expression matches format [number, number, number, number]
    swipe_match = re.search(r'\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]', text_response)
    if swipe_match:
        # If match successful, return list containing four integers
        print(f"Parsing successful (4 coordinates): {swipe_match.group(0)}")
        return [
            int(swipe_match.group(1)), 
            int(swipe_match.group(2)), 
            int(swipe_match.group(3)), 
            int(swipe_match.group(4))
        ]

    # 2. Then try to match 2 coordinates (designed for tap/click/input actions)
    # Regular expression matches format [number, number]
    tap_match = re.search(r'\[\s*(\d+)\s*,\s*(\d+)\s*\]', text_response)
    if tap_match:
        # If match successful, return list containing two integers
        print(f"Parsing successful (2 coordinates): {tap_match.group(0)}")
        return [
            int(tap_match.group(1)), 
            int(tap_match.group(2))
        ]
        
    # 3. If all format matches fail, print error and return None
    print(f"Parsing failed: Cannot find coordinates in format [x,y], [x1,y1,x2,y2] or [] in model response '{text_response}'")
    return None


def get_action_and_coordinates(image_path, task_goal, screen_width, screen_height, normalized_elements, history: list = None):
    print("\nVisual analysis in progress... Calling image+text multimodal model...")
    history_prompt = ""
    if history:
        formatted_history = []
        for i, past_action in enumerate(history):
            action_str = f"步骤 {i+1}: 动作='{past_action.get('action', 'N/A')}', 目标='{past_action.get('target', 'N/A')}'"
            if 'input_text' in past_action:
                action_str += f", 输入内容='{past_action['input_text']}'"
            formatted_history.append(action_str)
        history_prompt = f"历史操作记录：\n" + '\n'.join(formatted_history)

    elements_str = json.dumps(normalized_elements, ensure_ascii=False, indent=2)
    local_image_path = f'file://{os.path.abspath(image_path)}'

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

    messages = [{'role': 'user', 'content': [{'image': local_image_path}, {'text': prompt}]}]

    try:
        response = MultiModalConversation.call(model='qwen-vl-max', messages=messages, api_key='')

        if response.status_code == HTTPStatus.OK:
            raw_text = response.output.choices[0].message.content[0]['text'].strip()
            print(f"--- 完整模型回复 ---\n{raw_text}\n------------------")

            json_string = raw_text
            if "```json" in json_string:
                json_string = json_string.split("```json")[1].split("```")[0]

            start_index = json_string.find('{')
            end_index = json_string.rfind('}')
            if start_index != -1 and end_index != -1:
                json_string = json_string[start_index:end_index+1]
                result = json.loads(json_string)
                if 'coords' in result:
                    result['coords'] = parse_coordinates(json.dumps(result['coords']))
                return result
            else:
                raise json.JSONDecodeError("未找到有效的JSON对象", json_string, 0)
        else:
            print(f"API call failed: {response.status_code}, {response.message}")
            return None
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}. Original response: {raw_text}")
        return None
    except Exception as e:
        print(f"API call exception: {e}")
        return None