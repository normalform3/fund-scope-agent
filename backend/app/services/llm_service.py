import os
from typing import Dict


class LLMService:
    def __init__(self) -> None:
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        self.base_url = os.getenv("DASHSCOPE_BASE_URL", "").strip()
        self.model = os.getenv("DASHSCOPE_MODEL", "qwen3.6-plus").strip()

    def test_connection(self) -> Dict[str, object]:
        if not self.api_key:
            return {
                "ok": False,
                "model": self.model,
                "message": "缺少 DASHSCOPE_API_KEY 环境变量。",
            }
        if not self.base_url:
            return {
                "ok": False,
                "model": self.model,
                "message": "缺少 DASHSCOPE_BASE_URL 环境变量，请配置百炼 OpenAI-compatible endpoint。",
            }

        try:
            from openai import OpenAI
        except ImportError:
            return {
                "ok": False,
                "model": self.model,
                "message": "缺少 openai Python 包，请运行 pip install -r requirements.txt。",
            }

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        try:
            answer = ""
            request_id = ""
            usage = None
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是 FundScope Agent 的连接测试助手，只回复简短状态。",
                    },
                    {
                        "role": "user",
                        "content": "请用一句中文回复：基金研究 Agent 服务连接正常。",
                    },
                ],
                extra_body={"enable_thinking": True},
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in completion:
                request_id = getattr(chunk, "id", request_id)
                if not chunk.choices:
                    usage = getattr(chunk, "usage", None)
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    answer += content
            return {
                "ok": True,
                "model": self.model,
                "message": answer.strip() or "服务连接正常。",
                "request_id": request_id,
                "usage": _usage_to_dict(usage),
            }
        except Exception as exc:
            return {
                "ok": False,
                "model": self.model,
                "message": "百炼模型连接失败：%s" % str(exc),
            }


def _usage_to_dict(usage: object) -> Dict[str, object]:
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return usage
    return {}
