import pytest
from tools import CalculatorTool, WeatherTool
from tool_registry import ToolRegistry
from agent import Qwen36Agent

class TestCalculatorTool:
    def test_calculator_add(self):
        tool = CalculatorTool()
        result = tool.run("2 + 3")
        assert "计算结果：5" in result
    
    def test_calculator_multiply(self):
        tool = CalculatorTool()
        result = tool.run("4 * 5")
        assert "计算结果：20" in result
    
    def test_calculator_sqrt(self):
        tool = CalculatorTool()
        result = tool.run("sqrt(16)")
        assert "计算结果：4" in result
    
    def test_calculator_invalid_expression(self):
        tool = CalculatorTool()
        result = tool.run("invalid")
        assert "计算错误" in result

class TestWeatherTool:
    def test_weather_query(self):
        tool = WeatherTool()
        result = tool.run("Beijing")
        assert "北京" in result or "错误" in result

class TestToolRegistry:
    def test_register_tool(self):
        registry = ToolRegistry()
        tool = CalculatorTool()
        registry.register_tool(tool)
        assert registry.get_tool("calculator") is not None
    
    def test_get_tool(self):
        registry = ToolRegistry()
        tool = CalculatorTool()
        registry.register_tool(tool)
        retrieved = registry.get_tool("calculator")
        assert retrieved.name == "calculator"
    
    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())
        registry.register_tool(WeatherTool())
        tools = registry.list_tools()
        assert "calculator" in tools
        assert "weather" in tools

class TestQwen36Agent:
    def setup_method(self):
        self.registry = ToolRegistry()
        self.registry.register_tool(CalculatorTool())
        self.registry.register_tool(WeatherTool())
        self.agent = Qwen36Agent(self.registry)
    
    def test_agent_calculator_call(self):
        response = self.agent.chat("计算 10 + 20")
        assert "计算结果" in response
    
    def test_agent_weather_call(self):
        response = self.agent.chat("北京天气")
        assert "北京" in response or "错误" in response
    
    def test_agent_direct_response(self):
        response = self.agent.chat("你好")
        assert "这是直接回答" in response
    
    def test_agent_no_tool_available(self):
        response = self.agent.chat("告诉我一个故事")
        assert "这是直接回答" in response