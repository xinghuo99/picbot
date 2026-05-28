class QwenAgent:
    def __init__(self, model: str = MODEL_NAME):
        self.model = model
        self.tools_dict: Dict[str, dict] = {}  # 存储工具名称 -> {function, parameters, description}
        self.tools_schema: List[dict] = []    # 存储给 API 用的 schema
        self.messages = []

    def register_tool(self, name: str, description: str, parameters: dict, function: Callable):
        """动态注册一个新工具"""
        self.tools_dict[name] = {
            "description": description,
            "parameters": parameters,
            "function": function,
        }
        # 更新 schema 列表
        self.tools_schema.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            }
        })
        print(f"[工具已注册] {name}")

    def _call_model(self, messages: List[Dict], tools=None) -> GenerationResponse:
        # 若未显式指定 tools，则使用当前注册的所有工具
        if tools is None:
            tools = self.tools_schema
        return Generation.call(model=self.model, messages=messages, tools=tools, ...)

    def execute_tool(self, tool_name: str, arguments: dict) -> str:
        if tool_name not in self.tools_dict:
            return f"未知工具: {tool_name}"
        return self.tools_dict[tool_name]["function"](**arguments)



使用示例：
agent = QwenAgent()

# 初始注册内置工具（也可以不注册，完全动态）
agent.register_tool("calculator", "计算数学表达式", {"type": "object", "properties": {...}}, calculator)
agent.register_tool("query_weather", "查询天气", {"type": "object", "properties": {...}}, query_weather)

# 运行时动态添加一个新工具：获取当前时间
from datetime import datetime
def get_current_time(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    return datetime.now().strftime(format_str)

agent.register_tool(
    name="get_current_time",
    description="获取当前日期和时间，可指定格式",
    parameters={
        "type": "object",
        "properties": {
            "format_str": {"type": "string", "description": "时间格式，例如 '%Y-%m-%d'", "default": "%Y-%m-%d %H:%M:%S"}
        }
    },
    function=get_current_time
)

# 用户提问：“现在几点？” → Agent 会自动调用 get_current_time 工具
print(agent.run("现在几点？"))