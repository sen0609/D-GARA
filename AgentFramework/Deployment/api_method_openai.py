import json
import re
import os
import base64
from openai import OpenAI
from PIL import Image
from dotenv import load_dotenv

# 1. Set up proxy (if needed)
os.environ['http_proxy'] = 'http://127.0.0.1:7890'
os.environ['https_proxy'] = 'http://127.0.0.1:7890'

load_dotenv()

# 2. Initialize OpenAI client
# This will automatically read the key from the `OPENAI_API_KEY` environment variable
try:
    client = OpenAI()
except Exception as e:
    print(f"OpenAI client initialization failed: {e}")


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

def encode_image_to_base64(image_path):
    """
    Encode local image file to Base64 string.
    """
    # Remove possible file path protocol header
    if image_path.startswith('file://'):
        image_path = image_path[7:]
        
    # Get image format
    try:
        with Image.open(image_path) as img:
            format = img.format.lower()
            if format == 'jpeg':
                mime_type = 'image/jpeg'
            elif format == 'png':
                mime_type = 'image/png'
            else:
                # Provide a default value or handle other formats
                mime_type = 'image/png'
    except Exception:
        # If can't open with PIL (e.g., not an image file), use png as default
         mime_type = 'image/png'

    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{encoded_string}"


def get_action_and_coordinates(image_path, task_goal, screen_width, screen_height, normalized_elements, history: list = None):
    """
    Use OpenAI Vision API to analyze screenshot and get next action.
    """
    print("\nVisual analysis in progress... Calling OpenAI Vision API...")

    # --- 1. Prepare Prompt (logic same as original code) ---
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
    try:
        base64_image = encode_image_to_base64(image_path)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": final_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": base64_image}
                    }
                ]
            }
        ]

        # 3. Call the model
        print("Sending request to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4o",  # Recommended to use the latest gpt-4o model
            messages=messages,
            response_format={"type": "json_object"}, 
            max_tokens=1024 
        )
        
        # 4. Extract returned JSON content
        raw_text = response.choices[0].message.content
        print(f"--- Complete model response ---\n{raw_text}\n------------------")
        
        # 5. Parse JSON string
        # Since JSON mode is enabled, can usually parse directly without cleaning
        result = json.loads(raw_text)

        # 6. Parse coordinates (same logic as original)
        if 'coords' in result and result['coords']:
            # Convert list back to string to work with parse_coordinates function
            coords_str = json.dumps(result['coords'])
            result['coords'] = parse_coordinates(coords_str)
        return result

    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}. Original response: {raw_text}")
        return None
    except Exception as e:
        # Capture and print more specific OpenAI API error information
        print(f"Unknown exception occurred during API call or processing: {e}")
        return None