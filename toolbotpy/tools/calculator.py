import math

class CalculatorTool:
    name = "calculator"
    description = "用于执行数学计算，支持加减乘除、幂运算、开方、三角函数等基本数学运算"
    
    def __init__(self):
        pass
    
    def run(self, expression: str) -> str:
        try:
            allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith('_')}
            result = eval(expression, {"__builtins__": None}, allowed_names)
            return f"计算结果：{result}"
        except Exception as e:
            return f"计算错误：{str(e)}"
    
    def get_tool_definition(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "expression": {
                    "type": "string",
                    "description": "需要计算的数学表达式，例如：2 + 3 * 4 或 sqrt(16)"
                }
            }
        }