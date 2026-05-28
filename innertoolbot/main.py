import os

from agent import AIAgent
from tools import calculator, weather


def create_default_agent() -> AIAgent:
    """创建带有默认工具集的 Agent 实例。"""
    agent = AIAgent(
        model=os.environ.get("MODEL_NAME", "qwen3-6b"),
    )

    agent.register_tool(
        name="calculator",
        description="执行数学计算。支持四则运算、幂运算、三角函数、对数等。参数 expression 为数学表达式字符串，例如 '2+3*4' 或 'sqrt(16)'。",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "需要计算的数学表达式，如 '2+3*4'",
                }
            },
            "required": ["expression"],
        },
        func=calculator,
    )

    agent.register_tool(
        name="weather",
        description="查询指定城市的天气信息，返回温度、天气状况、湿度和风向。",
        parameters={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如 '北京'、'上海'、'广州' 等",
                }
            },
            "required": ["city"],
        },
        func=weather,
    )

    return agent


def main():
    """命令行交互入口。"""
    print("=" * 60)
    print("  AI Agent - 基于 Qwen36 模型")
    print("  已注册工具：计算器、天气查询")
    print("  输入 'quit' 或 'exit' 退出")
    print("  输入 '/tools' 查看已注册工具")
    print("=" * 60)

    agent = create_default_agent()

    while True:
        try:
            user_input = input("\n>>> 您: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            print("再见！")
            break

        if user_input == "/tools":
            tools = agent.list_tools()
            if tools:
                for t in tools:
                    print(f"  - {t['name']}: {t['description']}")
            else:
                print("  （暂无已注册的工具）")
            continue

        print("\nAI: ", end="", flush=True)
        result = agent.run(user_input)
        print(result)


if __name__ == "__main__":
    main()