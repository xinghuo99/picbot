from tools import CalculatorTool, WeatherTool
from tool_registry import ToolRegistry, create_default_tool_registry
from agent import Qwen36Agent

def main():
    tool_registry = create_default_tool_registry()
    agent = Qwen36Agent(tool_registry)
    
    print("AI Agent已启动，输入问题开始对话（输入'退出'结束）")
    while True:
        user_input = input("用户: ")
        if user_input == "退出":
            print("对话结束")
            break
        response = agent.chat(user_input)
        print("AI: ", response)

if __name__ == "__main__":
    main()