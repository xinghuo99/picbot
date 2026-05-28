import requests

class WeatherTool:
    name = "weather"
    description = "用于查询指定城市的天气信息"
    
    def __init__(self):
        self.api_key = "your_api_key_here"
    
    def run(self, city: str) -> str:
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric&lang=zh_cn"
            response = requests.get(url)
            data = response.json()
            
            if data.get("cod") == 200:
                weather = data["weather"][0]["description"]
                temp = data["main"]["temp"]
                humidity = data["main"]["humidity"]
                wind_speed = data["wind"]["speed"]
                return f"{city}的天气：{weather}，温度：{temp}°C，湿度：{humidity}%，风速：{wind_speed}m/s"
            else:
                return f"无法查询到{city}的天气信息，错误信息：{data.get('message', '未知错误')}"
        except Exception as e:
            return f"查询天气时发生错误：{str(e)}"
    
    def get_tool_definition(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "city": {
                    "type": "string",
                    "description": "要查询天气的城市名称，例如：Beijing 或 北京"
                }
            }
        }