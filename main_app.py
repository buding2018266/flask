from flask import Flask, render_template, request, session, redirect, url_for
import os
import requests # For making API calls
import json

app = Flask(__name__)
# It's crucial to set a secret key for session management.
# In a real application, use a strong, randomly generated key and keep it secret.
app.secret_key = os.urandom(24) # Generates a random secret key

# API key is hardcoded
DEEPSEEK_API_KEY = "sk-ad5184cc837d4a6c9860bfa46ddd2c68"
DEEPSEEK_API_BASE_URL = "https://api.deepseek.com/v1" # Or your specific base URL

# Prompts and configurations for each perspective
PERSPECTIVES = {
    "perspective_a": {
        "title": "聊天助手 (AI辅助回复)",
        "header": "AI辅助回复信息 💬",
        "input_placeholder": "输入收到的信息，获取分析与建议...",
        "custom_reply_placeholder": "或在此输入你的自定义回复...",
        "button_text": "获取分析与建议",
        "message_labels": {"other_person": "对方发来：", "ai_interpretation": "AI解读：", "ai_suggestions": "AI回复建议：", "user_reply": "我的回复："},
        "system_prompt": "你是一位情感对话助手。用户（女生）收到了一条来自有好感的男生（可能是男友或潜在发展对象）的信息。请先对这条信息进行简短解读（对方的情绪、意图）。然后，用'---'分隔，提供两个既得体又充满情感价值的中文回复选项，帮助用户建立更深的情感连接。回复应温馨、真诚，并能鼓励对方继续愉快地交流。请确保回复听起来发自内心，避免使用油滑或套路化的语言，力求展现真实的关心和连接的渴望。回复选项本身不要包含任何括号以及括号里的解释性文字或指示性说明。只提供纯粹的对话内容。格式如下：\nInterpretation: [解读内容]\n---\n[回复选项1]\n[回复选项2]",
        "user_prompt_template": "信息是：'{user_input}'",
        "api_roles": {"other_person": "user", "chosen_reply": "assistant"} # For DeepSeek API
    },
    "perspective_b": {
        "title": "聊天助手 (AI辅助沟通)",
        "header": "AI辅助组织语言 💬",
        "input_placeholder": "输入女生说的话，获取高情商回复...",
        "custom_reply_placeholder": "或在此输入你的自定义回复...",
        "button_text": "获取分析与建议",
        "message_labels": {"other_person": "对方的话/情景：", "ai_interpretation": "AI解读：", "ai_suggestions": "AI沟通建议：", "user_reply": "我的表达："},
        "system_prompt": "你是一位情感对话助手。用户（男生）想和有好感的女生（可能是女友或潜在发展对象）沟通，或者需要回复她发来的信息。用户会提供情景或女生的话。请先对此进行简短解读（对方的情绪、意图，或此情景下的沟通要点）。然后，用'---'分隔，提供两个既得体又充满情感价值的中文沟通选项，帮助用户建立更深的情感连接。回复应风趣、真诚，并能鼓励对方继续愉快地交流。请确保回复听起来发自内心，避免使用油滑或套路化的语言，力求展现真实的关心和连接的渴望。回复选项本身不要包含任何括号以及括号里的解释性文字或指示性说明。只提供纯粹的对话内容。格式如下：\nInterpretation: [解读内容]\n---\n[沟通选项1]\n[沟通选项2]",
        "user_prompt_template": "情景/对方说：'{user_input}'",
        "api_roles": {"other_person": "user", "chosen_reply": "assistant"}
    }
}

def evaluate_reply_score(reply_text):
    """调用AI接口对自定义回复进行打分，返回0-100分整数"""
    api_url = f"{DEEPSEEK_API_BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    # 设计一个专门用于评分的提示
    prompt_for_scoring = f"请你扮演一位专业的沟通分析师。仔细阅读以下用户回复，并根据其情感表达的恰当性、真诚度、以及在假设的对话情境中可能达成的沟通效果，给出一个综合评分。分数范围为0到100分。请只输出一个整数数字作为评分结果，不要包含任何其他文字、解释或单位。例如，如果评分是85，就只输出 '85'。\n\n用户回复内容如下：\n\'{reply_text}\'"
    
    payload = {
        "model": "deepseek-chat", # 或者其他你选用的模型
        "messages": [
            {"role": "system", "content": "你是一个只输出0-100整数评分的助手。"}, # 强化系统角色，确保只输出数字
            {"role": "user", "content": prompt_for_scoring}
        ],
        "max_tokens": 10,       # 限制token数量，因为我们只需要一个数字
        "temperature": 0.1      # 较低的temperature使输出更稳定和确定
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10) # 设置超时
        response.raise_for_status() # 如果HTTP请求返回了错误状态码，则抛出异常
        data = response.json()
        
        # 从API响应中提取评分数字
        score_content = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        
        # 清理并转换评分，确保是0-100的整数
        score_digits = ''.join(filter(str.isdigit, score_content)) # 只保留数字部分
        if score_digits: # 如果提取到了数字
            score = int(score_digits)
            if score < 0:
                score = 0
            elif score > 100:
                score = 100
            return score
        else:
            print(f"未能从API响应中提取有效评分数字：'{score_content}'")
            return None # 如果没有提取到数字，返回None
            
    except requests.exceptions.RequestException as e:
        print(f"调用评分API失败 (RequestException): {e}")
        return None
    except (KeyError, IndexError, ValueError) as e:
        print(f"解析评分API响应失败: {e}, 响应内容: {data if 'data' in locals() else 'N/A'}")
        return None
    except Exception as e: # 捕获其他所有未知错误
        print(f"评分过程中发生未知错误: {e}")
        return None

@app.route('/')
def index():
    if 'perspective' not in session:
        session['perspective'] = "perspective_b"
    if 'chat_histories' not in session:
        session['chat_histories'] = {p: [] for p in PERSPECTIVES}

    current_perspective = session['perspective']
    perspective_config = PERSPECTIVES[current_perspective]
    current_chat_history = session['chat_histories'][current_perspective]
    
    waiting_for_selection = False
    if current_chat_history and current_chat_history[-1].get("role") == "ai_suggestions":
        waiting_for_selection = True

    return render_template('index.html',
                           chat_history=current_chat_history,
                           perspective=current_perspective,
                           config=perspective_config,
                           waiting_for_selection=waiting_for_selection,
                           PERSPECTIVES=PERSPECTIVES)

@app.route('/generate_suggestions', methods=['POST'])
def generate_suggestions():
    if 'perspective' not in session:
        session['perspective'] = "perspective_b"
    if 'chat_histories' not in session:
        session['chat_histories'] = {p: [] for p in PERSPECTIVES}

    user_input = request.form.get('user_input')
    current_perspective = session.get('perspective', 'perspective_b')
    perspective_config = PERSPECTIVES[current_perspective]
    chat_history_list = session['chat_histories'][current_perspective]

    if not user_input:
        return redirect(url_for('index')) 

    current_message_index = len(chat_history_list)
    chat_history_list.append({"role": "other_person_says", "content": user_input, "interpretation": "正在获取解读..."})
    session.modified = True

    interpretation_text = "未能获取解读。"
    ai_suggestions_list = []
    
    try:
        system_prompt = perspective_config["system_prompt"]
        user_prompt_for_api = perspective_config["user_prompt_template"].format(user_input=user_input)
        
        api_messages = [{"role": "system", "content": system_prompt}]
        
        temp_history_for_api = []
        for i in range(current_message_index):
            message = chat_history_list[i]
            if message["role"] == "other_person_says":
                temp_history_for_api.append({"role": perspective_config["api_roles"]["other_person"], "content": message["content"]})
            elif message["role"] == "user_reply":
                temp_history_for_api.append({"role": perspective_config["api_roles"]["chosen_reply"], "content": message["content"]})
        
        api_messages.extend(temp_history_for_api)
        api_messages.append({"role": "user", "content": user_prompt_for_api})

        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "deepseek-chat",
            "messages": api_messages,
            "max_tokens": 300, 
            "temperature": 0.75
        }

        response = requests.post(f"{DEEPSEEK_API_BASE_URL}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        api_response_data = response.json()
        raw_full_response = api_response_data.get('choices', [{}])[0].get('message', {}).get('content', '抱歉，获取建议时出错。').strip()
        
        parts = raw_full_response.split("\n---\n", 1)
        if len(parts) == 2:
            interp_part, sugg_part = parts
            if interp_part.startswith("Interpretation:"):
                 interpretation_text = interp_part.replace("Interpretation:", "", 1).strip()
            else: 
                 interpretation_text = interp_part.strip()
            ai_suggestions_list = [s.strip() for s in sugg_part.split('\n') if s.strip()]
        else:
            interpretation_text = "无法解析AI回复的结构。"
            ai_suggestions_list = [s.strip() for s in raw_full_response.split('\n') if s.strip()]

        if not ai_suggestions_list: 
            ai_suggestions_list = ["无法获取建议。"]

    except requests.exceptions.RequestException as e:
        interpretation_text = "API连接错误。"
        ai_suggestions_list = [f"{e}"]
    except Exception as e:
        interpretation_text = "处理时发生错误。"
        ai_suggestions_list = [f"{e}"]
    
    if current_message_index < len(chat_history_list) and chat_history_list[current_message_index]["role"] == "other_person_says":
        chat_history_list[current_message_index]["interpretation"] = interpretation_text

    if ai_suggestions_list:
        chat_history_list.append({"role": "ai_suggestions", "suggestions": ai_suggestions_list})
    
    session['chat_histories'][current_perspective] = chat_history_list
    session.modified = True
    return redirect(url_for('index'))

@app.route('/submit_user_reply', methods=['POST'])
def submit_user_reply():
    if 'perspective' not in session:
        session['perspective'] = "perspective_b"
    if 'chat_histories' not in session:
        session['chat_histories'] = {p: [] for p in PERSPECTIVES}
        
    chosen_suggestion = request.form.get('chosen_ai_suggestion')
    custom_reply_text = request.form.get('custom_reply_text')

    reply_to_add = ""
    score = None # 初始化分数为None

    if custom_reply_text and custom_reply_text.strip():
        reply_to_add = custom_reply_text.strip()
        # 对自定义回复进行自动评分
        score = evaluate_reply_score(reply_to_add)
        if score is None:
            print("自定义回复评分失败，将不显示评分。")
    elif chosen_suggestion:
        reply_to_add = chosen_suggestion
        # AI的建议通常不需要再由系统评分，所以score保持为None
        # 如果也想对AI建议进行某种固定评分或用户打分，逻辑需调整
    else:
        # 如果既没有自定义回复也没有选择AI建议，则重定向
        return redirect(url_for('index'))

    current_perspective = session.get('perspective', 'perspective_b')
    chat_history_list = session['chat_histories'][current_perspective]

    # 如果上一条是AI建议，先移除它，因为用户已经做出了选择
    if chat_history_list and chat_history_list[-1].get("role") == "ai_suggestions":
        chat_history_list.pop()
        
    # 添加用户的回复（及可能的评分）到历史记录
    chat_history_list.append({"role": "user_reply", "content": reply_to_add, "score": score})
    session['chat_histories'][current_perspective] = chat_history_list
    session.modified = True
    
    return redirect(url_for('index'))

@app.route('/switch_perspective/<new_perspective>')
def switch_perspective(new_perspective):
    if new_perspective in PERSPECTIVES:
        session['perspective'] = new_perspective
    return redirect(url_for('index'))

@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    if 'perspective' not in session:
        session['perspective'] = "perspective_b"
    if 'chat_histories' not in session:
        session['chat_histories'] = {p: [] for p in PERSPECTIVES}
        
    current_perspective = session.get('perspective', 'perspective_b')
    if 'chat_histories' in session and current_perspective in session['chat_histories']:
        session['chat_histories'][current_perspective] = []
        session.modified = True
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)