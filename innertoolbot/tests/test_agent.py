import json
from unittest.mock import MagicMock, patch

import pytest

from tool_registry import ToolRegistry
from tools import calculator, weather
from agent import AIAgent


class TestCalculator:
    """计算器工具测试"""

    def test_basic_arithmetic(self):
        assert calculator("2 + 3") == "5"
        assert calculator("10 - 4") == "6"
        assert calculator("6 * 7") == "42"
        assert calculator("100 / 4") == "25.0"

    def test_complex_expression(self):
        assert calculator("2 + 3 * 4") == "14"
        assert calculator("(2 + 3) * 4") == "20"
        assert calculator("2 ** 10") == "1024"

    def test_math_functions(self):
        assert calculator("sqrt(16)") == "4.0"
        assert calculator("abs(-5)") == "5"
        assert calculator("round(3.14159, 2)") == "3.14"
        assert calculator("max(1, 5, 3)") == "5"
        assert calculator("min(1, 5, 3)") == "1"

    def test_pow_function(self):
        assert calculator("pow(2, 8)") == "256"

    def test_error_expression(self):
        result = calculator("1 / 0")
        assert "计算错误" in result

    def test_invalid_syntax(self):
        result = calculator("2 + ")
        assert "计算错误" in result


class TestWeather:
    """天气查询工具测试"""

    def test_known_city(self):
        result = weather("北京")
        assert "北京" in result
        assert "温度" in result
        assert "晴" in result

    def test_known_city_shanghai(self):
        result = weather("上海")
        assert "上海" in result
        assert "多云" in result

    def test_unknown_city(self):
        result = weather("火星")
        assert "未找到" in result

    def test_city_with_whitespace(self):
        result = weather("  北京  ")
        assert "北京" in result
        assert "温度" in result


class TestToolRegistry:
    """工具注册中心测试"""

    @pytest.fixture
    def registry(self):
        return ToolRegistry()

    def test_register_tool(self, registry):
        registry.register_tool(
            name="test_tool",
            description="测试工具",
            parameters={"type": "object", "properties": {}},
            func=lambda: "ok",
        )
        assert "test_tool" in registry
        assert registry.tool_count == 1

    def test_register_duplicate_tool(self, registry):
        registry.register_tool(
            name="dup_tool",
            description="测试工具",
            parameters={"type": "object", "properties": {}},
            func=lambda: "ok",
        )
        with pytest.raises(ValueError, match="已存在"):
            registry.register_tool(
                name="dup_tool",
                description="重复工具",
                parameters={"type": "object", "properties": {}},
                func=lambda: "ok2",
            )

    def test_register_invalid_name(self, registry):
        with pytest.raises(ValueError, match="非空字符串"):
            registry.register_tool(
                name="",
                description="空名称",
                parameters={"type": "object", "properties": {}},
                func=lambda: "ok",
            )

    def test_unregister_tool(self, registry):
        registry.register_tool(
            name="to_remove",
            description="待删除",
            parameters={"type": "object", "properties": {}},
            func=lambda: "ok",
        )
        assert registry.unregister_tool("to_remove") is True
        assert "to_remove" not in registry
        assert registry.tool_count == 0

    def test_unregister_nonexistent(self, registry):
        assert registry.unregister_tool("no_such_tool") is False

    def test_list_tools(self, registry):
        registry.register_tool(
            name="tool_a",
            description="工具A",
            parameters={"type": "object", "properties": {"x": {"type": "string"}}},
            func=lambda x: x,
        )
        registry.register_tool(
            name="tool_b",
            description="工具B",
            parameters={"type": "object", "properties": {"y": {"type": "string"}}},
            func=lambda y: y,
        )
        tools = registry.list_tools()
        assert len(tools) == 2
        assert tools[0]["name"] == "tool_a"
        assert tools[1]["name"] == "tool_b"
        assert "func" not in tools[0]

    def test_get_openai_tools(self, registry):
        registry.register_tool(
            name="oa_tool",
            description="OpenAI格式工具",
            parameters={"type": "object", "properties": {}},
            func=lambda: "done",
        )
        oa_tools = registry.get_openai_tools()
        assert len(oa_tools) == 1
        assert oa_tools[0]["type"] == "function"
        assert oa_tools[0]["function"]["name"] == "oa_tool"

    def test_execute_tool(self, registry):
        def my_func(name: str, age: int) -> str:
            return f"{name} is {age} years old"

        registry.register_tool(
            name="greet",
            description="问候工具",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                },
                "required": ["name", "age"],
            },
            func=my_func,
        )
        result = registry.execute_tool("greet", {"name": "Alice", "age": 30})
        assert result == "Alice is 30 years old"

    def test_execute_nonexistent_tool(self, registry):
        with pytest.raises(ValueError, match="未注册"):
            registry.execute_tool("ghost", {})

    def test_execute_tool_type_error(self, registry):
        def strict_func(x: int) -> str:
            return str(x * 2)

        registry.register_tool(
            name="strict",
            description="严格参数",
            parameters={
                "type": "object",
                "properties": {"x": {"type": "integer"}},
                "required": ["x"],
            },
            func=strict_func,
        )
        result = registry.execute_tool("strict", {"wrong_param": 5})
        assert "参数错误" in result

    def test_clear(self, registry):
        registry.register_tool(
            name="t1",
            description="工具1",
            parameters={"type": "object", "properties": {}},
            func=lambda: "1",
        )
        registry.register_tool(
            name="t2",
            description="工具2",
            parameters={"type": "object", "properties": {}},
            func=lambda: "2",
        )
        assert registry.tool_count == 2
        registry.clear()
        assert registry.tool_count == 0
        assert registry.list_tools() == []

    def test_get_tool(self, registry):
        registry.register_tool(
            name="find_me",
            description="可查找",
            parameters={"type": "object", "properties": {}},
            func=lambda: "found",
        )
        tool = registry.get_tool("find_me")
        assert tool is not None
        assert tool["name"] == "find_me"

    def test_get_tool_nonexistent(self, registry):
        assert registry.get_tool("nope") is None


def _make_mock_response(content=None, tool_calls=None):
    """创建模拟的 OpenAI API 响应。"""
    mock_response = MagicMock()
    mock_choice = MagicMock()

    if tool_calls:
        mock_choice.finish_reason = "tool_calls"
        mock_tool_calls = []
        for tc in tool_calls:
            mock_tc = MagicMock()
            mock_tc.id = tc.get("id", "call_001")
            mock_tc.function.name = tc["name"]
            mock_tc.function.arguments = json.dumps(tc.get("arguments", {}))
            mock_tool_calls.append(mock_tc)
        mock_choice.message.tool_calls = mock_tool_calls
        mock_choice.message.content = None
    else:
        mock_choice.finish_reason = "stop"
        mock_choice.message.tool_calls = None
        mock_choice.message.content = content or "这是一个直接回答。"

    mock_response.choices = [mock_choice]
    return mock_response


class TestAIAgent:
    """AI Agent 整体测试"""

    @pytest.fixture
    def agent(self):
        return AIAgent(model="qwen3-6b", api_key="test-key", base_url="https://test.api/v1")

    @pytest.fixture
    def agent_with_tools(self, agent):
        agent.register_tool(
            name="calculator",
            description="执行数学计算。参数 expression 为数学表达式。",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式"}
                },
                "required": ["expression"],
            },
            func=calculator,
        )
        agent.register_tool(
            name="weather",
            description="查询城市天气。参数 city 为城市名称。",
            parameters={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"],
            },
            func=weather,
        )
        return agent

    def test_register_tool(self, agent):
        agent.register_tool(
            name="echo",
            description="回显",
            parameters={"type": "object", "properties": {}},
            func=lambda: "echo",
        )
        assert agent.registry.tool_count == 1

    def test_unregister_tool(self, agent_with_tools):
        assert agent_with_tools.unregister_tool("calculator") is True
        assert agent_with_tools.registry.tool_count == 1

    def test_list_tools(self, agent_with_tools):
        tools = agent_with_tools.list_tools()
        assert len(tools) == 2
        names = [t["name"] for t in tools]
        assert "calculator" in names
        assert "weather" in names

    def test_run_direct_answer_no_tools(self, agent):
        """无工具可用时，直接返回 AI 回答。"""
        mock_resp = _make_mock_response(content="你好！有什么可以帮助你的？")

        with patch.object(agent._client.chat.completions, "create", return_value=mock_resp):
            result = agent.run("你好")
            assert result == "你好！有什么可以帮助你的？"

    def test_run_with_calculator_tool(self, agent_with_tools):
        """需要计算时，模型调用计算器工具。"""
        mock_tool_call = _make_mock_response(
            tool_calls=[{
                "id": "call_calc_001",
                "name": "calculator",
                "arguments": {"expression": "12 * 15"},
            }]
        )
        mock_final = _make_mock_response(content="12乘以15等于180。")

        with patch.object(
            agent_with_tools._client.chat.completions, "create", side_effect=[mock_tool_call, mock_final]
        ) as mock_create:
            result = agent_with_tools.run("12乘以15等于多少？")

            assert mock_create.call_count == 2
            assert result == "12乘以15等于180。"

    def test_run_with_weather_tool(self, agent_with_tools):
        """查询天气时，模型调用天气工具。"""
        mock_tool_call = _make_mock_response(
            tool_calls=[{
                "id": "call_wx_001",
                "name": "weather",
                "arguments": {"city": "北京"},
            }]
        )
        mock_final = _make_mock_response(content="北京今天天气晴朗，温度25°C。")

        with patch.object(
            agent_with_tools._client.chat.completions, "create", side_effect=[mock_tool_call, mock_final]
        ) as mock_create:
            result = agent_with_tools.run("北京今天天气怎么样？")

            assert mock_create.call_count == 2
            assert "25°C" in result

    def test_run_multiple_tool_calls(self, agent_with_tools):
        """一次对话中模型调用多个工具。"""
        mock_multi_tool = _make_mock_response(
            tool_calls=[
                {"id": "call_calc_002", "name": "calculator", "arguments": {"expression": "25 + 30"}},
                {"id": "call_wx_002", "name": "weather", "arguments": {"city": "上海"}},
            ]
        )
        mock_final = _make_mock_response(content="计算结果是55，上海今天多云28°C。")

        with patch.object(
            agent_with_tools._client.chat.completions, "create", side_effect=[mock_multi_tool, mock_final]
        ) as mock_create:
            result = agent_with_tools.run("25加30等于多少？还有上海天气怎么样？")

            assert mock_create.call_count == 2
            assert "55" in result

    def test_dynamic_tool_registration(self, agent):
        """测试动态注册工具：先注册再用自然语言触发调用。"""
        agent.register_tool(
            name="calculator",
            description="执行数学计算。参数 expression 为数学表达式。",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式"}
                },
                "required": ["expression"],
            },
            func=calculator,
        )

        mock_tool_call = _make_mock_response(
            tool_calls=[{
                "id": "call_003",
                "name": "calculator",
                "arguments": {"expression": "100 / 5"},
            }]
        )
        mock_final = _make_mock_response(content="100除以5等于20。")

        with patch.object(
            agent._client.chat.completions, "create", side_effect=[mock_tool_call, mock_final]
        ):
            result = agent.run("100除以5等于多少？")
            assert "20" in result

    def test_run_without_tools_direct_answer(self, agent):
        """没有工具可用时，直接回答问题。"""
        mock_resp = _make_mock_response(content="Python是一种流行的编程语言。")

        with patch.object(agent._client.chat.completions, "create", return_value=mock_resp):
            result = agent.run("什么是Python？")
            assert "Python" in result

    def test_run_max_tool_rounds(self, agent):
        """工具调用达到最大轮次限制。"""
        agent.register_tool(
            name="loop_tool",
            description="循环工具",
            parameters={
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
            func=lambda x: f"got {x}",
        )

        mock_responses = []
        for i in range(5):
            mock_responses.append(
                _make_mock_response(
                    tool_calls=[{
                        "id": f"call_{i}",
                        "name": "loop_tool",
                        "arguments": {"x": str(i)},
                    }]
                )
            )

        with patch.object(
            agent._client.chat.completions, "create", side_effect=mock_responses
        ):
            result = agent.run("测试循环")
            assert "最大工具调用轮次" in result

    def test_run_stream(self, agent):
        """测试流式返回。"""
        mock_resp = _make_mock_response(content="流式回答内容")

        with patch.object(agent._client.chat.completions, "create", return_value=mock_resp):
            chunks = list(agent.run_stream("测试流式"))
            assert len(chunks) == 1
            assert chunks[0] == "流式回答内容"


class TestIntegration:
    """集成测试：模拟完整的用户交互流程"""

    @pytest.fixture
    def agent(self):
        agent = AIAgent(model="qwen3-6b", api_key="test-key", base_url="https://test.api/v1")
        agent.register_tool(
            name="calculator",
            description="执行数学计算。参数 expression 为数学表达式。",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式"}
                },
                "required": ["expression"],
            },
            func=calculator,
        )
        agent.register_tool(
            name="weather",
            description="查询城市天气。参数 city 为城市名称。",
            parameters={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"],
            },
            func=weather,
        )
        return agent

    def test_full_calculator_flow(self, agent):
        """完整的计算器调用流程：用户输入 -> 模型判断 -> 调用工具 -> 返回结果。"""
        tool_call_resp = _make_mock_response(
            tool_calls=[{
                "id": "call_integ_001",
                "name": "calculator",
                "arguments": {"expression": "sqrt(144) + 10"},
            }]
        )
        final_resp = _make_mock_response(content="sqrt(144) + 10 的结果是22.0。")

        with patch.object(
            agent._client.chat.completions, "create", side_effect=[tool_call_resp, final_resp]
        ):
            result = agent.run("根号144加10等于多少？")
            assert "22" in result

    def test_full_weather_flow(self, agent):
        """完整的天气查询流程。"""
        tool_call_resp = _make_mock_response(
            tool_calls=[{
                "id": "call_integ_002",
                "name": "weather",
                "arguments": {"city": "广州"},
            }]
        )
        final_resp = _make_mock_response(content="广州今天雷阵雨，温度32°C，湿度80%。")

        with patch.object(
            agent._client.chat.completions, "create", side_effect=[tool_call_resp, final_resp]
        ):
            result = agent.run("广州天气怎么样？")
            assert "广州" in result
            assert "32°C" in result

    def test_dynamic_register_and_use(self, agent):
        """动态注册新工具并使用。"""
        agent.register_tool(
            name="time_tool",
            description="获取当前时间。无参数。",
            parameters={"type": "object", "properties": {}},
            func=lambda: "2026-05-28 18:00:00",
        )

        tool_call_resp = _make_mock_response(
            tool_calls=[{
                "id": "call_dyn_001",
                "name": "time_tool",
                "arguments": {},
            }]
        )
        final_resp = _make_mock_response(content="现在是2026年5月28日18点整。")

        with patch.object(
            agent._client.chat.completions, "create", side_effect=[tool_call_resp, final_resp]
        ):
            result = agent.run("现在几点了？")
            assert "2026" in result

    def test_no_tool_needed_conversation(self, agent):
        """不需要工具的对话场景。"""
        direct_resp = _make_mock_response(content="你好！我是AI助手，很高兴为你服务。")

        with patch.object(
            agent._client.chat.completions, "create", return_value=direct_resp
        ):
            result = agent.run("你好，请介绍一下你自己")
            assert "AI助手" in result

    def test_unregister_then_use(self, agent):
        """注销工具后，模型不应再调用该工具。"""
        agent.unregister_tool("calculator")
        assert agent.registry.tool_count == 1

        tool_call_resp = _make_mock_response(
            tool_calls=[{
                "id": "call_integ_004",
                "name": "weather",
                "arguments": {"city": "成都"},
            }]
        )
        final_resp = _make_mock_response(content="成都今天小雨，温度24°C。")

        with patch.object(
            agent._client.chat.completions, "create", side_effect=[tool_call_resp, final_resp]
        ):
            result = agent.run("成都天气怎么样？")
            assert "成都" in result