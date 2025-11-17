import json
import re
import os
import base64
from openai import OpenAI
from PIL import Image
from dotenv import load_dotenv

# 1. Set proxy (if needed in your network environment)
# os.environ['http_proxy'] = 'http://127.0.0.1:7890'
# os.environ['https_proxy'] = 'http://127.0.0.1:7890'

load_dotenv()

# 2. Initialize Ark client
# Modified: Initialize pointing to Volcano Ark service
# Make sure you have stored your API Key in ARK_API_KEY environment variable
try:
    client = OpenAI(
        # This is the default path, you can configure based on your business region
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        # Get your API Key from environment variable
        api_key=''   #os.environ.get("ARK_API_KEY"),
    )
    print("Volcano Ark client initialized successfully.")
except Exception as e:
    print(f"Volcano Ark client initialization failed: {e}")
import re
import json

def clean_and_parse_json(raw_text: str):
    """
    A robust function to clean and parse a JSON string from an LLM response.
    Handles markdown code blocks, comments, and trailing commas.

    Args:
        raw_text: The raw string response from the model.

    Returns:
        A parsed Python dictionary, or None if parsing fails.
    """
    if not raw_text:
        print("Error: Raw text is empty.")
        return None

    # 1. Extract content from markdown code blocks if present
    # Matches ```json ... ``` or ``` ... ```
    match = re.search(r'```(json)?\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
    if match:
        json_str = match.group(2)
    else:
        # If no markdown block, assume the whole string might be a JSON object,
        # but we need to find the start of it.
        start_index = raw_text.find('{')
        if start_index != -1:
            json_str = raw_text[start_index:]
        else:
            print(f"Error: No JSON object found in the response: {raw_text}")
            return None

    # 2. Remove single-line comments (// ...)
    json_str = re.sub(r'//.*', '', json_str)

    # 3. Remove multi-line comments (/* ... */)
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
    
    # 4. Remove trailing commas from objects and arrays
    # e.g., {"a": 1, "b": 2,} -> {"a": 1, "b": 2}
    # e.g., [1, 2, 3,] -> [1, 2, 3]
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

    # 5. Attempt to parse the cleaned string
    try:
        # The final cleaned string is passed to the parser
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"--- Final JSON Parsing Failed ---")
        print(f"Error: {e}")
        print(f"Cleaned string: {json_str}")
        print(f"Model original response: {raw_text}")

def parse_coordinates(text_response: str):
    """
    (This function needs no modification)
    Parse string containing coordinates.
    """
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
    if image_path.startswith('file://'):
        image_path = image_path[7:]
        
    try:
        with Image.open(image_path) as img:
            format = img.format.lower()
            if format == 'jpeg':
                mime_type = 'image/jpeg'
            elif format == 'png':
                mime_type = 'image/png'
            else:
                mime_type = 'image/png'
    except Exception:
        mime_type = 'image/png'

    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{encoded_string}"


def get_action_and_coordinates(image_path, task_goal, screen_width, screen_height, normalized_elements, history: list = None):
    print("\nPerforming visual analysis... Calling Volcano Ark (Ark) API...")


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
    
    prompt_text = f"""
你是一个安卓任务规划与定位AI。
你的任务目标是：“{task_goal}”。

请分析当前屏幕截图，并根据UI元素列表规划下一步操作，同时返回该操作所涉及目标的坐标。
{history_prompt}

UI元素列表如下：
{elements_str}

你的输出必须是一个RFC8259兼容的JSON对象，包含以下键：
- "thought": (字符串) 你的判断理由；
- "action": (字符串) 动作类型：'tap', 'text', 'swipe', 'back', 'done', 'wait' 之一；
- "target": (字符串) 你要操作的UI控件的文字描述；
- "coords": (列表) 操作目标的中心坐标，例如 [120, 310]；特别地如果是swipe，那么输出应该为[x_start,y_start,x_end,y_end];
- "input_text": (字符串, 如果action是'text'则提供内容，否则为空字符串)。

注意：目标控件请结合文字描述和UI元素坐标综合判断，不要返回多余内容或解释性文字。
"""
    if normalized_elements:
        ui_prompt = "这里是界面上可交互的UI元素列表:\n" + elements_str
        final_prompt = prompt_text + "\n" + ui_prompt
    else:
        vision_only_prompt = "注意：无法获取UI元素信息，请你完全依赖图像内容进行判断。"
        final_prompt = prompt_text + "\n" + vision_only_prompt

    print(f"--- final prompt ---\n{final_prompt}\n------------------")
    
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

        print("\nPerforming visual analysis... Calling Volcano Ark (Ark) API...")
        response = client.chat.completions.create(
            model="doubao-1-5-ui-tars-250428", 
            messages=messages,
            max_tokens=1024 
        )
        
        raw_text = response.choices[0].message.content
        print(f"--- Complete Model Response ---\n{raw_text}\n------------------")
        
        result = clean_and_parse_json(raw_text)

        if not result:
            return None

        if 'coords' in result and result['coords'] and isinstance(result['coords'], list):
            coords_str = json.dumps(result['coords'])
            result['coords'] = parse_coordinates(coords_str)
        return result

    except Exception as e:
        print(f"Unknow Error: {e}")
        return None
