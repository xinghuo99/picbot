import json
import os
from typing import Any, Dict, Generator, List, Optional

from openai import OpenAI

from tool_registry import ToolRegistry


class AIAgent:
    """基于 Qwen36 模型的 AI Agent，支持工具调用。

    使用 OpenAI 兼容的 API 接口调用 Qwen36 模型，
    自动判断用户意图并决定是否调用已注册的工具。
    """

    def __init__(
        self,
        model: str = "qwen3-6b",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Args:
            model: 模型名称，默认 "qwen3-6b"
            api_key: API 密钥，默认从环境变量 OPENAI_API_KEY 读取
            base_url: API 基础地址，默认从环境变量 OPENAI_BASE_URL 读取
            system_prompt: 系统提示词
        """
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "sk-placeholder")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.system_prompt = system_prompt or (
            "你是一个智能助手，可以使用工具来帮助用户解决问题。"
            "当用户的问题需要计算或查询天气时，请调用相应的工具。"
            "如果不需要工具，直接给出回答。"
        )
        self.registry = ToolRegistry()
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self._max_tool_rounds = 5

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: dict,
        func,
    ) -> None:
        """注册一个工具到 Agent 的工具集中。"""
        self.registry.register_tool(name, description, parameters, func)

    def unregister_tool(self, name: str) -> bool:
        """注销一个工具。"""
        return self.registry.unregister_tool(name)

    def list_tools(self):
        """列出所有已注册的工具。"""
        return self.registry.list_tools()

    def _build_messages(self, user_input: str):
        """构建发送给模型的消息列表。"""
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]

    def _call_model(self, messages: list, tools: Optional[list] = None):
        """调用大模型 API。"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return self._client.chat.completions.create(**kwargs)

    def run(self, user_input: str) -> str:
        """处理用户输入，自动判断是否需要工具调用。

        如果模型决定调用工具，Agent 会执行工具并获取结果，
        然后将结果再次发送给模型生成最终回复。
        如果不需要工具，直接返回模型的回复。

        Args:
            user_input: 用户的自然语言输入

        Returns:
            AI 的最终回复文本
        """
        messages = self._build_messages(user_input)
        tools = self.registry.get_openai_tools()

        for _ in range(self._max_tool_rounds):
            response = self._call_model(messages, tools if tools else None)
            choice = response.choices[0]

            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                messages.append(choice.message.model_dump())

                for tool_call in choice.message.tool_calls:
                    func_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    result = self.registry.execute_tool(func_name, arguments)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
            else:
                return choice.message.content or ""

        return "已达到最大工具调用轮次，请简化您的问题。"

    def run_stream(self, user_input: str):
        """流式处理用户输入，逐步生成回复。

        当模型需要调用工具时，会在工具执行完成后流式返回最终结果。
        """
        messages = self._build_messages(user_input)
        tools = self.registry.get_openai_tools()

        tool_round = 0
        while tool_round < self._max_tool_rounds:
            response = self._call_model(messages, tools if tools else None)
            choice = response.choices[0]

            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                messages.append(choice.message.model_dump())

                for tool_call in choice.message.tool_calls:
                    func_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    result = self.registry.execute_tool(func_name, arguments)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
                tool_round += 1
            else:
                yield choice.message.content or ""
                return

        yield "已达到最大工具调用轮次，请简化您的问题。"