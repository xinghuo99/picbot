from tools import CalculatorTool, WeatherTool

class ToolRegistry:
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, tool):
        self.tools[tool.name] = tool
    
    def get_tool(self, tool_name):
        return self.tools.get(tool_name)
    
    def list_tools(self):
        return list(self.tools.keys())
    
    def get_all_tool_definitions(self):
        return [tool.get_tool_definition() for tool in self.tools.values()]

def create_default_tool_registry():
    registry = ToolRegistry()
    registry.register_tool(CalculatorTool())
    registry.register_tool(WeatherTool())
    return registry