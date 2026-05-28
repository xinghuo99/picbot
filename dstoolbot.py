import os
import json
import math
import requests
from typing import Dict, Any, List, Callable
from dashscope import Generation
from dashscope.api_entities.dashscope_response import GenerationResponse

# ----------------------------- 配置 ----------------------------------
# 请设置您的阿里云 DashScope API Key，可通过环境变量 DASHSCOPE_API_KEY 设置
# 获取地址：https://dashscope.console.aliyun.com/apiKey
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "your-api-key-here")
if DASHSCOPE_API_KEY == "your-api-key-here":
    raise ValueError("请先设置有效的 DASHSCOPE_API_KEY 环境变量或直接修改代码中的密钥")

MODEL_NAME = "qwen-max"  # 实际使用 Qwen-Max 模型（Qwen-36B 的云端版本），若需使用其他模型可更换

# ----------------------------- 工具定义 ----------------------------------
# 工具：计算器
def calculator(expression: str) -> str:
    """
    安全地计算数学表达式（支持加减乘除、幂、三角函数等基本运算）
    """
    try:
        # 限制可用函数和变量，避免恶意代码
        safe_dict = {
            "abs": abs, "round": round, "min": min, "max": max,
            "sum": sum, "pow": pow, "math": math
        }
        # 允许部分数学常量
        safe_dict.update({"pi": math.pi, "e": math.e})
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        return f"计算结果为: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"

# 工具：查询天气（使用免费 wttr.in API，无需密钥，国内网络可能不稳定）
def query_weather(city: str) -> str:
    """
    查询指定城市的当前天气（摄氏度）
    """
    try:
        # 使用 wttr.in 的简洁格式：温度、天气状况、湿度等
        url = f"https://wttr.in/{city}?format=%C+%t+%h+%w"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.text.strip()
            if data and "Unknown" not in data:
                return f"{city}天气：{data}"
            else:
                return f"未找到城市 '{city}' 的天气信息"
        else:
            return f"天气服务返回错误码: {response.status_code}"
    except Exception as e:
        # 备选：模拟天气数据（实际使用时请替换为真实天气 API）
        # 此处为演示，返回模拟数据
        return f"无法获取实时天气（{str(e)}），使用模拟数据：{city} 当前晴，气温 22°C，湿度 60%"

# 工具注册表：名称 -> (描述, 参数schema, 执行函数)
TOOLS = {
    "calculator": {
        "description": "计算数学表达式，支持加减乘除、幂、三角函数等。",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "需要计算的数学表达式，例如 '2+3*4' 或 'sin(pi/2)'",
                }
            },
            "required": ["expression"],
        },
        "function": calculator,
    },
    "query_weather": {
        "description": "查询指定城市的实时天气情况（温度、天气状况、湿度、风速等）。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如 'Beijing'、'上海'",
                }
            },
            "required": ["city"],
        },
        "function": query_weather,
    },
}

# 构造 DashScope 所需的工具列表格式
def build_tools_for_api():
    tools = []
    for tool_name, tool_info in TOOLS.items():
        tools.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_info["description"],
                "parameters": tool_info["parameters"],
            }
        })
    return tools

# ----------------------------- 执行工具 ----------------------------------
def execute_tool(tool_name: str, arguments: dict) -> str:
    """根据工具名称和参数执行对应函数，返回字符串结果"""
    if tool_name not in TOOLS:
        return f"错误：未知工具 '{tool_name}'"
    func = TOOLS[tool_name]["function"]
    try:
        # 调用工具函数，传入参数
        result = func(**arguments)
        return result if isinstance(result, str) else str(result)
    except Exception as e:
        return f"工具执行异常: {str(e)}"

# ----------------------------- Agent 类 ----------------------------------
class QwenAgent:
    def __init__(self, model: str = MODEL_NAME):
        self.model = model
        self.tools = build_tools_for_api()
        # 对话历史（多轮）
        self.messages = []

    def _call_model(self, messages: List[Dict], tools=None) -> GenerationResponse:
        """调用 DashScope 模型接口，支持 tools"""
        response = Generation.call(
            model=self.model,
            messages=messages,
            tools=tools,
            result_format="message",
            # 控制模型决策是否强制使用工具（可选）
            # tool_choice="auto",
        )
        if response.status_code != 200:
            raise Exception(f"API 调用失败: {response.code} - {response.message}")
        return response

    def run(self, user_input: str) -> str:
        # 1. 将用户输入加入消息历史
        self.messages.append({"role": "user", "content": user_input})
        
        # 2. 第一次调用模型，判断是否需要调用工具
        response = self._call_model(self.messages, tools=self.tools)
        assistant_msg = response.output.choices[0].message
        
        # 若模型返回了工具调用指令
        if assistant_msg.get("tool_calls"):
            # 将助手的工具调用消息加入历史
            self.messages.append(assistant_msg)
            
            # 依次执行每个工具调用
            tool_results = []
            for tool_call in assistant_msg["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                arguments = json.loads(tool_call["function"]["arguments"])
                print(f"[Agent 调用工具] {tool_name}({arguments})")
                result = execute_tool(tool_name, arguments)
                tool_results.append({
                    "tool_call_id": tool_call["id"],
                    "role": "tool",
                    "content": result,
                })
            
            # 将所有工具执行结果加入消息历史
            self.messages.extend(tool_results)
            
            # 3. 再次调用模型，让其基于工具结果生成最终回答
            final_response = self._call_model(self.messages)
            final_answer = final_response.output.choices[0].message["content"]
            self.messages.append({"role": "assistant", "content": final_answer})
            return final_answer
        else:
            # 无需工具调用，直接返回模型回答
            answer = assistant_msg.get("content", "")
            # 某些情况可能 content 为空，此时忽略
            if answer:
                self.messages.append({"role": "assistant", "content": answer})
                return answer
            else:
                # 模型未提供有效回答
                return "抱歉，我无法回答这个问题。"

# ----------------------------- 交互式运行 ----------------------------------
def main():
    agent = QwenAgent()
    print("🤖 AI Agent 启动（支持计算器、天气查询）。输入 'exit' 退出。")
    while True:
        try:
            user_input = input("\n用户: ").strip()
            if user_input.lower() in ("exit", "quit"):
                print("再见！")
                break
            if not user_input:
                continue
            print("Agent: ", end="")
            response = agent.run(user_input)
            print(response)
        except KeyboardInterrupt:
            print("\n退出程序")
            break
        except Exception as e:
            print(f"发生错误: {e}")

if __name__ == "__main__":
    main()