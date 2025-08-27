from openai import OpenAI
import os
import time
import json
from datetime import datetime


def save_conversation(history):
    """保存对话历史到文件"""
    with open('conversation_log.txt', 'w', encoding='utf-8') as f:
        for msg in history:
            f.write(f"{msg['role']}: {msg['content']}\n\n")

def api_call_with_retry(model, messages, temperature, max_tokens, stream, max_retries=3):
    """带重试机制的API调用"""
    for attempt in range(max_retries):
        try:
            if stream:
                return client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                ), None
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False
                )
                return response, None
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            print(f"API调用失败，{max_retries - attempt - 1}次重试剩余: {str(e)}")
            time.sleep(2 ** attempt)  # 指数退避策略
    
    return None, None

def handle_empty_response(ai_reply, user_input):
    """处理空响应情况"""
    if not ai_reply or ai_reply.strip() == "":
        print("AI助手返回了空响应，正在尝试处理...")
        # 根据用户输入生成一个默认回复或请求澄清
        if "你好" in user_input or "hello" in user_input:
            return "你好！我是AI助手，很高兴为您服务。"
        elif "?" in user_input or "？" in user_input:
            return "您的问题可能需要更具体的描述，能否提供更多细节？"
        else:
            return "我已收到您的消息，但需要更多信息来提供准确的回答。"
    return ai_reply

def chat_with_ai(model="deepseek-chat", temperature=0.7, max_tokens=1024, stream=False):
    """与AI交互式对话（支持自定义参数）"""
    global conversation_history
    
    while True:
        user_input = input("你: ")
        
        if user_input.lower() in ['退出', 'exit', 'quit']:
            print("对话结束，已保存对话记录。")
            save_conversation(conversation_history)
            break
        
        conversation_history.append({"role": "user", "content": user_input})
        
        try:
            # 带重试机制的API调用
            if stream:
                response_stream, _ = api_call_with_retry(
                    model, conversation_history, temperature, max_tokens, True
                )
                
                if response_stream is None:
                    print("API调用失败，请稍后重试")
                    continue
                
                ai_reply = ""
                print("\nAI助手: ", end="")
                for chunk in response_stream:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        delta = chunk.choices[0].delta.content
                        ai_reply += delta
                        print(delta, end="", flush=True)
                print("\n")
                
            else:
                response, _ = api_call_with_retry(
                    model, conversation_history, temperature, max_tokens, False
                )
                
                if response is None:
                    print("API调用失败，请稍后重试")
                    continue
                
                # 检查响应结构是否完整
                if (not response.choices or 
                    not response.choices[0] or 
                    not response.choices[0].message or 
                    not response.choices[0].message.content):
                    print("API返回了无效的数据结构")
                    ai_reply = "抱歉，我无法处理这个请求，请稍后再试。"
                else:
                    ai_reply = response.choices[0].message.content
                
                print("\nAI助手:", ai_reply, "\n")
            
            # 处理空响应
            ai_reply = handle_empty_response(ai_reply, user_input)
            
            conversation_history.append({"role": "assistant", "content": ai_reply})
        
        except Exception as e:
            print(f"发生错误: {str(e)}")
            # 在对话历史中添加错误信息，保持上下文连贯
            conversation_history.append({
                "role": "assistant", 
                "content": "抱歉，处理您的请求时出现了技术问题，请重新尝试或换个方式提问。"
            })
            continue

if __name__ == "__main__":
    # 默认API文件路径（根据不同操作系统设置默认值）
    default_api_path = ""
    if os.name == 'nt':  # Windows系统
        default_api_path = r"api.txt"
    else:  # Linux/Unix系统
        default_api_path = os.path.expanduser("~/api.txt")
    
    # 提示用户输入API文件路径
    print(f"默认API文件路径: {default_api_path}")
    api_path_input = input("请输入api.txt文件的完整路径(直接回车使用默认路径): ").strip()
    
    # 处理用户输入
    if not api_path_input:  # 用户直接回车，使用默认路径
        api_file_path = default_api_path
    else:
        # 移除用户可能拖拽文件时带入的引号
        api_file_path = api_path_input.strip('"\'')
    
    # 检查文件是否存在
    if not os.path.isfile(api_file_path):
        print(f"错误: 在路径 '{api_file_path}' 未找到api.txt文件")
        print("请确保文件存在且路径正确")
        exit(1)
    
    # 读取API密钥
    try:
        with open(api_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                api = line.strip()
                if api:  # 确保不是空行
                    break
    except Exception as e:
        print(f"读取API文件时出错: {str(e)}")
        exit(1)
    # 初始化客户端
    client = OpenAI(api_key=api, base_url=" https://api.deepseek.com ".strip())
    # 初始化对话历史
    conversation_history = [{"role": "system", "content": "你是一个通用语言模型,负责解答用户问题。"}]


    print('欢迎使用 hdf_ai(ai with high degree of freedom)')
    diy_model = input('你想使用自定义模式吗? (y/n)：').strip().lower()

    model = "deepseek-chat"
    temperature = 0.7
    max_tokens = 1024
    stream = False

    if diy_model == 'y':
        print('进入自定义模式...')
        conversation_history[0]["content"] = input('请设置初始提示词:')
        if input('需要深度思考吗?(y/n): ').lower() == 'y':
            model = "deepseek-reasoner"
        
        try:
            temperature = float(input('请输入创造性值(0-2):'))
            temperature = max(0.0, min(2.0, temperature))
        except ValueError:
            print("输入无效，使用默认值0.7")
            temperature = 0.7
        
        try:
            max_tokens = int(input('请输入支持最长上下文长度(tokens):'))
            max_tokens = max(1, min(4096, max_tokens))
        except ValueError:
            print("输入无效，使用默认值1024")
            max_tokens = 1024
        
        if input('需要流式输出吗?(y/n): ').lower() == 'y':
            stream = True
        
        print('设置完毕，开始对话')
        chat_with_ai(model, temperature, max_tokens, stream)
    
    elif diy_model == 'n':
        chat_with_ai()
    
    else:
        print('输入无效，请输入 y 或 n')
