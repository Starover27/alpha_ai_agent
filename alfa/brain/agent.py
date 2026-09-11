import json
import re
import requests
from config import LM_STUDIO_HOST, LM_STUDIO_ENDPOINT, LLM_TEMPERATURE, MAX_TOKENS
from tools.universal_tools import search_system_index, open_path, find_contact, create_email_draft

TOOLS_DESCRIPTION = """
Ты — AI-ассистент 'Альфа'. Ты управляешь компьютером через инструменты.

ПРАВИЛА:
1. Если нужно выполнить действие — верни ТОЛЬКО JSON, без слов перед ним и после.
2. Формат JSON строго такой:
{"tool": "имя_инструмента", "args": {"ключ": "значение"}}
3. Никогда не оборачивай JSON в ``` или другие символы.
4. Если задача выполнена — ответь обычным текстом.

ИНСТРУМЕНТЫ:
- search_system_index: поиск программы или файла в базе. args: {"query": "запрос"}
- open_path: открыть файл или программу по пути. args: {"file_path": "путь"}
- find_contact: найти контакт в Outlook. args: {"name": "Имя"}
- create_email_draft: создать черновик письма. args: {"email": "...", "subject": "...", "body": "..."}

ПРИМЕРЫ:
Пользователь: "Открой аутлук"
Твой ответ: {"tool": "search_system_index", "args": {"query": "outlook"}}

Пользователь: "Найди договор"
Твой ответ: {"tool": "search_system_index", "args": {"query": "договор"}}
"""

class Agent:
    def __init__(self):
        self.history = [{"role": "system", "content": TOOLS_DESCRIPTION}]
        print(" Агент готов к работе")

    def process_command(self, user_input: str) -> str:
        self.history.append({"role": "user", "content": user_input})
        max_steps = 6
        
        for step in range(max_steps):
            print(f"\n[Шаг {step+1}] Думаю...")
            response = self._call_llm()
            print(f"LLM: {response[:200]}")
            
            tool_call = self._parse_tool_call(response)
            
            if tool_call:
                tool_name = tool_call["tool"]
                args = tool_call["args"]
                print(f"🛠️ Инструмент: {tool_name}({args})")
                result = self._execute_tool(tool_name, args)
                print(f"📥 Результат: {result}")
                
                self.history.append({"role": "assistant", "content": json.dumps(tool_call, ensure_ascii=False)})
                self.history.append({"role": "user", "content": f"Результат {tool_name}: {json.dumps(result, ensure_ascii=False)}. Что делаем дальше?"})
            else:
                print(f"✅ Ответ пользователю: {response}")
                return response
        
        return "Извините, я запуталась в рассуждениях."

    def _call_llm(self) -> str:
        url = f"{LM_STUDIO_HOST}{LM_STUDIO_ENDPOINT}"
        payload = {
            "model": "qwen2.5-3b-instruct",
            "messages": self.history[-10:],
            "temperature": LLM_TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "stream": False
        }
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"❌ Ошибка LLM: {e}")
            return "Ошибка связи с мозгом."

    def _parse_tool_call(self, text: str) -> dict:
        """Умный парсер — ищет JSON в любом месте текста"""
        text = text.strip()
        
        # 1. Пытаемся распарсить весь текст как JSON
        try:
            data = json.loads(text)
            if "tool" in data and "args" in data:
                return data
        except:
            pass
        
        # 2. Ищем JSON внутри markdown-блоков
        markdown_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(markdown_pattern, text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if "tool" in data and "args" in data:
                    return data
            except:
                pass
        
        # 3. Ищем первый JSON-объект в тексте (самый надёжный способ)
        # Ищем пару { ... } с ключом "tool"
        json_pattern = r'\{[^{}]*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{[^{}]*\}[^{}]*\}'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if "tool" in data and "args" in data:
                    return data
            except:
                pass
        
        # 4. Если ничего не нашли — пробуем найти любую пару фигурных скобок
        brace_pattern = r'\{[^{}]*\}'
        match = re.search(brace_pattern, text)
        if match:
            try:
                data = json.loads(match.group(0))
                if "tool" in data and "args" in data:
                    return data
            except:
                pass
        
        return None

    def _execute_tool(self, tool_name: str, args: dict):
        tools = {
            "search_system_index": search_system_index,
            "open_path": open_path,
            "find_contact": find_contact,
            "create_email_draft": create_email_draft,
        }
        if tool_name in tools:
            try:
                return tools[tool_name](**args)
            except Exception as e:
                return {"error": str(e)}
        return {"error": f"Неизвестный инструмент: {tool_name}"}