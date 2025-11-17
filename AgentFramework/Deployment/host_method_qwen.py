# Filename: host_method.py
import json
import re
from PIL import Image

import openai
import base64
from io import BytesIO



API_BASE_URL = "http://localhost:8001/v1" # Change this if your vLLM server is at a different address
API_KEY = "not-needed" 
MODEL_NAME = "Qwen2.5-VL-7B-Instruct"  # Change this to your desired model name


def parse_coordinates(text_response: str):
    """
    Parse coordinates from the model's text response.
    This upgraded version can handle three cases: [x, y], [x1, y1, x2, y2], and empty [].
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

def get_action_and_coordinates(
    image_path,
    task_goal,
    screen_width,
    screen_height,
    normalized_elements,
    history: list = None
):
    """
    [vLLM API Version] This function performs inference by requesting the vLLM server through API.
    """
    print("\nMultimodal vision analysis in progress (via vLLM API)...")

    history_prompt = ""
    if history:
        formatted_history = [f"步骤 {i+1}: 动作='{pa.get('action', 'N/A')}', 目标='{pa.get('target', 'N/A')}'" for i, pa in enumerate(history)]
        history_prompt = f"历史操作记录：\n" + '\n'.join(formatted_history)

    elements_str = json.dumps(normalized_elements, ensure_ascii=False, indent=2)
    prompt_template = f"""
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
Note: Please make a comprehensive judgment of target elements based on text descriptions, don't return unnecessary content.
"""
    if normalized_elements:
        ui_prompt = "这里是界面上可交互的UI元素列表:\n" + elements_str
        final_prompt = prompt_template + "\n" + ui_prompt
    else:
        vision_only_prompt = "注意：无法获取UI元素信息，请你完全依赖图像内容进行判断。"
        final_prompt = prompt_template + "\n" + vision_only_prompt
    
    raw_text = ""
    try:
        # 1. Image processing: Load image and encode to Base64
        image = Image.open(image_path).convert("RGB")
        buffered = BytesIO()
        image.save(buffered, format="JPEG") # Save as JPEG for better compression ratio
        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # 2. Initialize client pointing to vLLM server
        client = openai.OpenAI(
            base_url=API_BASE_URL,
            api_key=API_KEY,
        )

        # 3. Construct multimodal input in OpenAI format
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": final_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
        
        # 4. Send API request
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=1024, 
            temperature=0.1,  
        )
        
        # 5. Extract model response
        raw_text = response.choices[0].message.content
        print(f"--- Complete Model Response ---\n{raw_text}\n------------------")

        json_string = raw_text
        if "```json" in json_string:
            json_string = json_string.split("```json")[1].split("```")[0]
        
        start_index = json_string.find('{')
        end_index = json_string.rfind('}')
        if start_index != -1 and end_index != -1:
            json_string = json_string[start_index:end_index+1]
            result = json.loads(json_string)
            if 'coords' in result and result['coords']:
                coords_str = str(result['coords'])
                result['coords'] = parse_coordinates(coords_str)
            return result
        else:
            raise json.JSONDecodeError("No valid JSON object found", json_string, 0)

    except openai.APIConnectionError as e:
        print(f"❌ Connection Error: Cannot connect to vLLM server {API_BASE_URL}")
        print("Please verify if your vLLM service is running correctly on localhost:8080.")
        return None
    except Exception as e:
        print(f"Unknown error occurred during vLLM API call or processing: {e}")
        return None