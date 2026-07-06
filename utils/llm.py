"""
LLM Client with retry and validation decorator.
Copied from REUSABLE_MODULES.md
"""
import os
import json
import logging
import time
from typing import TypeVar, Callable, Type, Optional, Dict, Any
from functools import wraps
from pydantic import BaseModel, ValidationError
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
T = TypeVar('T', bound=BaseModel)


class TokenStats:
    """Token 统计类"""

    def __init__(self):
        self.total_tokens = 0
        self.start_time = None

    def start(self):
        self.start_time = time.time()
        self.total_tokens = 0

    def update(self, new_tokens: int):
        self.total_tokens += new_tokens

    def get_speed(self) -> float:
        """返回平均生成速度（tokens/s）"""
        if not self.start_time:
            return 0.0
        elapsed = time.time() - self.start_time
        return self.total_tokens / elapsed if elapsed > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "speed": self.get_speed(),
            "elapsed_time": time.time() - self.start_time if self.start_time else 0
        }


class LLMClient:
    """LLM 客户端，读取 .env 配置，兼容任意 OpenAI 格式接口"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.info(f"LLM Client initialized with model: {self.model}")

    def call_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> str:
        """
        流式调用 LLM，返回完整文本。

        Args:
            callback: 每 10 个 chunk 调用一次，接收 TokenStats.get_stats() 字典
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stats = TokenStats()
        stats.start()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )

        full_content = ""
        chunk_count = 0

        for chunk in response:
            if chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                full_content += content_chunk
                stats.update(len(content_chunk) // 4 + 1)
                chunk_count += 1
                if callback and chunk_count % 10 == 0:
                    callback(stats.get_stats())

        if callback:
            callback(stats.get_stats())

        return full_content


def get_llm_client():
    """工厂函数：根据 USE_MOCK 环境变量返回对应客户端"""
    use_mock = os.getenv("USE_MOCK", "false").lower() == "true"
    if use_mock:
        from utils.mock_llm import MockLLMClient
        return MockLLMClient()
    return LLMClient()


def retry_and_validate(
    response_model: Type[T],
    max_attempts: int = 3,
    system_prompt: Optional[str] = None,
    use_stream: bool = False
) -> Callable:
    """
    装饰器：LLM 调用 + JSON 解析 + Pydantic 验证 + 自动 Self-Correction 重试
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            ui_callback = kwargs.pop('ui_callback', None)

            llm_client = get_llm_client()
            prompt = func(*args, **kwargs)
            last_error = None

            for attempt in range(1, max_attempts + 1):
                logger.info(f"Attempt {attempt}/{max_attempts}")

                if attempt > 1 and ui_callback:
                    ui_callback({
                        "type": "retry",
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "message": f"AI 正在生成第 {attempt} 份结果以提高质量..."
                    })

                if use_stream and ui_callback:
                    def token_callback(stats):
                        ui_callback({"type": "token_update", **stats})
                    response_text = llm_client.call_stream(prompt, system_prompt, callback=token_callback)
                else:
                    response_text = llm_client.call_stream(prompt, system_prompt)

                try:
                    json_text = response_text.strip()
                    if json_text.startswith("```json"):
                        json_text = json_text.split("```json")[1].split("```")[0].strip()
                    elif json_text.startswith("```"):
                        json_text = json_text.split("```")[1].split("```")[0].strip()
                    response_data = json.loads(json_text)
                except json.JSONDecodeError as e:
                    error_msg = f"JSON parsing failed: {e}"
                    logger.warning(error_msg)
                    if attempt < max_attempts:
                        prompt = (
                            f"Previous response was not valid JSON. Error: {error_msg}\n\n"
                            f"Original prompt:\n{prompt}\n\n"
                            f"Your previous response:\n{response_text}\n\n"
                            "Please provide a valid JSON response."
                        )
                        last_error = error_msg
                        continue
                    raise Exception(f"Failed to parse JSON after {max_attempts} attempts: {error_msg}")

                try:
                    validated = response_model(**response_data)
                    logger.info(f"Validated successfully on attempt {attempt}")
                    return validated
                except ValidationError as e:
                    error_msg = f"Pydantic validation failed: {e}"
                    logger.warning(error_msg)
                    if attempt < max_attempts:
                        prompt = (
                            f"Previous response failed validation. Errors:\n{e.json()}\n\n"
                            f"Original prompt:\n{prompt}\n\n"
                            f"Your previous response:\n{response_text}\n\n"
                            "Please provide a corrected JSON response."
                        )
                        last_error = error_msg
                        continue
                    raise Exception(f"Failed validation after {max_attempts} attempts: {error_msg}")

            raise Exception(f"Failed after {max_attempts} attempts. Last error: {last_error}")

        return wrapper
    return decorator


def call_llm_simple(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.3
) -> str:
    """简单 LLM 调用，返回纯文本"""
    client = get_llm_client()
    return client.call_stream(prompt, system_prompt, temperature)

