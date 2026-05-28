from typing import Any, Callable, Dict, List, Optional


class ToolRegistry:
    """工具注册中心，支持动态注册和调用工具。"""

    def __init__(self):
        self._tools: Dict[str, dict] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: dict,
        func: Callable[..., str],
    ) -> None:
        """注册一个工具到工具集中。

        Args:
            name: 工具名称（唯一标识）
            description: 工具功能描述，AI 用来判断何时调用
            parameters: JSON Schema 格式的参数定义
            func: 工具的执行函数，接收关键字参数，返回字符串结果
        """
        if not name or not isinstance(name, str):
            raise ValueError("工具名称必须是非空字符串")
        if name in self._tools:
            raise ValueError(f"工具 '{name}' 已存在，请使用不同的名称")

        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "func": func,
        }

    def unregister_tool(self, name: str) -> bool:
        """注销一个工具。

        Returns:
            True 表示成功注销，False 表示工具不存在
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get_tool(self, name: str) -> Optional[dict]:
        """获取指定工具的信息。"""
        return self._tools.get(name)

    def list_tools(self) -> List[dict]:
        """列出所有已注册的工具信息（不含执行函数）。"""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            }
            for t in self._tools.values()
        ]

    def get_openai_tools(self) -> List[dict]:
        """返回 OpenAI function calling 格式的工具列表。"""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in self._tools.values()
        ]

    def execute_tool(self, name: str, arguments: dict) -> str:
        """执行指定工具。

        Args:
            name: 工具名称
            arguments: 工具参数字典

        Returns:
            工具执行后的结果字符串

        Raises:
            ValueError: 工具不存在时抛出
        """
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"工具 '{name}' 未注册，无法执行。可用工具: {list(self._tools.keys())}")

        try:
            return tool["func"](**arguments)
        except TypeError as e:
            return f"工具调用参数错误: {e}"

    def clear(self) -> None:
        """清空所有已注册的工具。"""
        self._tools.clear()

    @property
    def tool_count(self) -> int:
        """已注册工具的数量。"""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools