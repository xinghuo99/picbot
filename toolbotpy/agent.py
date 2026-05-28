import re

class Qwen36Agent:
    def __init__(self, tool_registry):
        self.tool_registry = tool_registry

    def chat(self, user_input):
        tool_name = None
        params = {}
        
        if "计算" in user_input or "+" in user_input or "-" in user_input or "*" in user_input or "/" in user_input:
            tool_name = "calculator"
            expr_start = user_input.find("算")
            if expr_start != -1:
                params["expression"] = user_input[expr_start+1:].strip()
            else:
                params["expression"] = user_input.replace("计算", "").strip()
        
        elif "天气" in user_input:
            tool_name = "weather"
            city_start = user_input.find("天气")
            if city_start != -1:
                city = user_input[:city_start].strip()
                if not city:
                    city = "北京"
                params["city"] = city
        
        if tool_name and self.tool_registry.get_tool(tool_name):
            tool = self.tool_registry.get_tool(tool_name)
            try:
                result = tool.run(**params)
                return result
            except Exception as e:
                return f"工具调用失败: {str(e)}"
        
        return self._generate_direct_response(user_input)

    def _generate_direct_response(self, user_input):
        return f"这是直接回答: {user_input}"