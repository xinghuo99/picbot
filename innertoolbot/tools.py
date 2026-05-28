import math
import json
from typing import Any


def calculator(expression: str) -> str:
    """计算数学表达式的结果。支持基本四则运算、幂运算、三角函数等。"""
    allowed_names = {
        k: v for k, v in math.__dict__.items() if not k.startswith("__")
    }
    allowed_names["abs"] = abs
    allowed_names["round"] = round
    allowed_names["pow"] = pow
    allowed_names["max"] = max
    allowed_names["min"] = min

    try:
        code = compile(expression, "<calculator>", "eval")
        for name in code.co_names:
            if name not in allowed_names and name not in __builtins__:
                raise ValueError(f"不允许使用 '{name}'")
        result = eval(code, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"


def weather(city: str) -> str:
    """查询指定城市的天气信息（模拟数据）。"""
    weather_data = {
        "北京": {"温度": "25°C", "天气": "晴", "湿度": "40%", "风向": "北风 3级"},
        "上海": {"温度": "28°C", "天气": "多云", "湿度": "65%", "风向": "东南风 2级"},
        "广州": {"温度": "32°C", "天气": "雷阵雨", "湿度": "80%", "风向": "南风 4级"},
        "深圳": {"温度": "30°C", "天气": "阵雨", "湿度": "75%", "风向": "西南风 3级"},
        "杭州": {"温度": "26°C", "天气": "阴", "湿度": "70%", "风向": "东风 2级"},
        "成都": {"温度": "24°C", "天气": "小雨", "湿度": "78%", "风向": "北风 2级"},
        "武汉": {"温度": "29°C", "天气": "晴转多云", "湿度": "55%", "风向": "南风 3级"},
        "西安": {"温度": "27°C", "天气": "晴", "湿度": "35%", "风向": "东风 2级"},
    }

    city = city.strip()
    if city in weather_data:
        info = weather_data[city]
        return f"{city}天气：温度{info['温度']}，{info['天气']}，湿度{info['湿度']}，{info['风向']}"
    else:
        return f"未找到城市'{city}'的天气数据，请尝试其他城市"