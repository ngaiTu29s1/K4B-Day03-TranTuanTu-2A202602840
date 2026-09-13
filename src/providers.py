"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
from typing import Dict, Any, List
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Xin chào! Tôi đã nhận được câu hỏi '{prompt}'. (Chế độ Chatbot không có Tool tra cứu dữ liệu thời gian thực)."

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        
        # Mô phỏng nhận diện intent gọi Tool
        if "đặt" in prompt_lower or "order" in prompt_lower or "fastpass" in prompt_lower:
            sid = "2A202602840" if "2a202602840" in prompt_lower else "SV2026002"
            kid = "bep_1" if "bếp 1" in prompt_lower else "bep_2"
            opt = "takeaway" if ("phòng" in prompt_lower or "mang" in prompt_lower or "hộp" in prompt_lower) else "dine_in"
            return {
                "type": "tool_call",
                "tool_name": "order_meal_fastpass",
                "arguments": {"student_id": sid, "kitchen_id": kid, "pickup_time": "13:05", "dining_option": opt, "meal_item": "Suất cơm tiêu chuẩn"},
                "thought": f"Người dùng yêu cầu đặt suất ăn FastPass cho học viên {sid}. Tôi sẽ gọi tool order_meal_fastpass."
            }
        elif "vé" in prompt_lower or "nhà ăn" in prompt_lower or "bếp" in prompt_lower or "ghế" in prompt_lower or "tra cứu" in prompt_lower:
            sid = "2A202602840" if "2a202602840" in prompt_lower else "SV2026001"
            if "sv9999999" in prompt_lower:
                sid = "SV9999999"
            return {
                "type": "tool_call",
                "tool_name": "check_canteen_and_tickets",
                "arguments": {"student_id": sid},
                "thought": f"Người dùng muốn tra cứu tình trạng nhà ăn và vé học viên {sid}. Tôi sẽ gọi tool check_canteen_and_tickets."
            }
        else:
            return {
                "type": "text",
                "content": "[Mock Agent Response]: Nhà ăn VinLab phục vụ từ 13h00 - 14h00, sức chứa 500 ghế ngồi cho 1000 học viên, gồm Bếp 1 (Cơm phần) và Bếp 2 (Bún mì & Healthy). Bạn có thể tra cứu vé hoặc đặt trước suất ăn FastPass.",
                "thought": "Câu hỏi chung về quy chế nhà ăn, trả lời trực tiếp không cần gọi Tool."
            }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
        
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            
            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


class OpenAICompatibleProvider(BaseLLMProvider):
    """Generic OpenAI-compatible Provider (Groq, NVIDIA NIM, OpenRouter, etc.)"""
    def __init__(self, api_key: str, base_url: str, default_model: str, provider_name: str):
        self.api_key = api_key
        self.base_url = base_url
        self.provider_name = provider_name
        self.model_name = default_model or os.getenv("LLM_MODEL") or "qwen/qwen3.8-27b"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or "your_" in self.api_key:
            return f"[{self.provider_name} Error]: Chưa cấu hình API Key trong file .env!"
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages, max_tokens=700)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[{self.provider_name} Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or "your_" in self.api_key:
            print(f"ℹ️ [{self.provider_name} Provider]: Chưa tìm thấy API Key hợp lệ. Chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                temperature=0.2,
                max_tokens=700
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"{self.provider_name} ({self.model_name}) quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": f"{self.provider_name} ({self.model_name}) phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [{self.provider_name} API Warning]: Lỗi kết nối ({str(e)}). Fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        key = api_key or os.getenv("OPENAI_API_KEY")
        super().__init__(
            api_key=key,
            base_url="https://api.openai.com/v1",
            default_model=model or os.getenv("LLM_MODEL") or "gpt-4o-mini",
            provider_name="OpenAI"
        )


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "groq").lower()
    
    if provider_type == "groq":
        key = os.getenv("GROQ_API_KEY")
        if key and not key.startswith("your_"):
            return OpenAICompatibleProvider(
                api_key=key,
                base_url="https://api.groq.com/openai/v1",
                default_model="qwen/qwen3.8-27b",
                provider_name="Groq"
            )
    elif provider_type == "nvidia":
        key = os.getenv("NVIDIA_API_KEY")
        if key and not key.startswith("your_"):
            return OpenAICompatibleProvider(
                api_key=key,
                base_url="https://integrate.api.nvidia.com/v1",
                default_model="meta/llama-3.3-70b-instruct",
                provider_name="NVIDIA NIM"
            )
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and not key.startswith("your_"):
            return OpenAIProvider()
    elif provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and not key.startswith("your_"):
            return GeminiProvider()

    # Fallback to Mock Offline
    return MockOfflineProvider()
