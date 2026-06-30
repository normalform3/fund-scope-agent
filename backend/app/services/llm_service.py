import json
import os
import re
from typing import Dict, Tuple


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

    def parse_discovery_profile(self, goal_text: str, answers: Dict[str, str], refinement_text: str = "") -> Tuple[Dict[str, str], str]:
        """Parse fuzzy user preference text into a small JSON profile.

        The caller must still validate every field and run deterministic matching
        and filtering. This method intentionally returns only normalized hints.
        """
        if not self.api_key or not self.base_url:
            return {}, ""

        try:
            from openai import OpenAI
        except ImportError:
            return {}, "LLM 画像解析未启用：缺少 openai Python 包。"

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        prompt = {
            "goal_text": goal_text,
            "answers": answers,
            "refinement_text": refinement_text,
            "schema": {
                "investment_goal": "string",
                "risk_tolerance": "low|medium|high",
                "horizon": "short|medium|long",
                "liquidity_need": "high|medium|low",
                "experience_level": "beginner|some|experienced",
                "preferred_fund_types": "array of strings",
                "notes": "array of short Chinese strings",
            },
        }
        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你只负责把基金研究用户的自然语言偏好解析成 JSON。"
                            "不要推荐具体基金，不要计算指标，不要输出投资建议。"
                            "只能返回一个 JSON object。"
                        ),
                    },
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                temperature=0,
                max_tokens=500,
                response_format={"type": "json_object"},
                extra_body={"enable_thinking": False},
            )
            content = completion.choices[0].message.content or ""
            payload = _extract_json_object(content)
        except Exception as exc:
            return {}, "LLM 画像解析失败，已使用规则解析：%s" % str(exc)

        normalized = _normalize_profile_payload(payload)
        if not normalized:
            return {}, "LLM 画像解析结果不可用，已使用规则解析。"
        return normalized, "已使用 LLM 将自然语言偏好解析为结构化画像，候选筛选仍由确定性规则完成。"


def _usage_to_dict(usage: object) -> Dict[str, object]:
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return usage
    return {}


def _extract_json_object(content: str) -> Dict[str, object]:
    text = content.strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_profile_payload(payload: Dict[str, object]) -> Dict[str, str]:
    allowed = {
        "risk_tolerance": {"low", "medium", "high"},
        "horizon": {"short", "medium", "long"},
        "liquidity_need": {"high", "medium", "low"},
        "experience_level": {"beginner", "some", "experienced"},
    }
    normalized: Dict[str, str] = {}
    for key, values in allowed.items():
        value = str(payload.get(key, "")).strip().lower()
        if value in values:
            normalized[key] = value
    investment_goal = str(payload.get("investment_goal", "")).strip()
    if investment_goal:
        normalized["investment_goal"] = investment_goal[:120]
    preferred = payload.get("preferred_fund_types")
    if isinstance(preferred, list):
        normalized["preferred_fund_types"] = ",".join(str(item).strip() for item in preferred if str(item).strip())[:160]
    notes = payload.get("notes")
    if isinstance(notes, list):
        normalized["notes"] = "；".join(str(item).strip() for item in notes if str(item).strip())[:240]
    return normalized
