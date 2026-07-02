import json
import os
import re
from typing import Dict, List, Tuple


class LLMService:
    def __init__(self) -> None:
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        self.base_url = os.getenv("DASHSCOPE_BASE_URL", "").strip()
        self.model = os.getenv("DASHSCOPE_MODEL", "glm-5.1").strip()

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
                "max_loss_tolerance": "number, decimal such as 0.1 for 10%",
                "investment_horizon_months": "integer",
                "can_delay_use": "boolean, whether the user can delay using the money",
                "money_purpose": "emergency|education|retirement|idle|near_term",
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

    def explain_discovery_decision(
        self,
        profile: Dict[str, object],
        fund_type_matches: List[Dict[str, object]],
        candidates: List[Dict[str, object]],
        include_candidates: bool,
    ) -> Tuple[str, List[str], bool, str]:
        """Explain deterministic discovery results without changing them."""
        if not self.api_key or not self.base_url:
            return "", [], False, ""

        try:
            from openai import OpenAI
        except ImportError:
            return "", [], False, "LLM 解释未启用：缺少 openai Python 包。"

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        prompt = {
            "profile": profile,
            "fund_type_matches": fund_type_matches,
            "candidates": candidates,
            "include_candidates": include_candidates,
            "task": (
                "用中文解释这些由规则和真实数据生成的基金研究方向。"
                "不得新增基金类型，不得改写分数，不得推荐买入卖出，不得承诺收益。"
            ),
            "schema": {
                "explanation": "string, 80-180 Chinese chars",
                "follow_up_questions": "array of up to 3 short Chinese questions",
            },
        }
        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是基金研究助手，只能解释已经给定的规则结果。"
                            "不要推荐具体买卖，不要添加新的基金方向，不要计算指标。"
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
            return "", [], False, "LLM 解释失败，已使用规则说明：%s" % str(exc)

        explanation = str(payload.get("explanation", "")).strip()[:240]
        questions = _normalize_string_list(payload.get("follow_up_questions"), 3, 80)
        if not explanation:
            return "", questions, False, "LLM 解释结果不可用，已使用规则说明。"
        return explanation, questions, True, "已使用 LLM 将确定性匹配依据改写为可读解释，未参与候选筛选或排序。"


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
    max_loss_tolerance = _normalize_loss_tolerance(payload.get("max_loss_tolerance"))
    if max_loss_tolerance is not None:
        normalized["max_loss_tolerance"] = str(max_loss_tolerance)
    investment_horizon_months = _normalize_positive_int(payload.get("investment_horizon_months"))
    if investment_horizon_months is not None:
        normalized["investment_horizon_months"] = str(investment_horizon_months)
    can_delay_use = _normalize_optional_bool(payload.get("can_delay_use"))
    if can_delay_use is not None:
        normalized["can_delay_use"] = "true" if can_delay_use else "false"
    money_purpose = _normalize_money_purpose(payload.get("money_purpose"))
    if money_purpose:
        normalized["money_purpose"] = money_purpose
    preferred = payload.get("preferred_fund_types")
    if isinstance(preferred, list):
        normalized["preferred_fund_types"] = ",".join(str(item).strip() for item in preferred if str(item).strip())[:160]
    notes = payload.get("notes")
    if isinstance(notes, list):
        normalized["notes"] = "；".join(str(item).strip() for item in notes if str(item).strip())[:240]
    return normalized


def _normalize_loss_tolerance(value: object):
    if value is None or value == "":
        return None
    try:
        number = abs(float(value))
    except (TypeError, ValueError):
        return None
    if number > 1:
        number = number / 100
    return min(number, 1.0)


def _normalize_positive_int(value: object):
    if value is None or value == "":
        return None
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _normalize_optional_bool(value: object):
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"true", "yes", "1", "y", "可以", "可延期", "能延期", "能", "是"}:
        return True
    if text in {"false", "no", "0", "n", "不可以", "不可延期", "不能延期", "不能", "否"}:
        return False
    return None


def _normalize_money_purpose(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    mapping = {
        "emergency": "emergency",
        "备用金": "emergency",
        "应急": "emergency",
        "生活费": "emergency",
        "education": "education",
        "教育": "education",
        "学费": "education",
        "retirement": "retirement",
        "养老": "retirement",
        "退休": "retirement",
        "idle": "idle",
        "闲置": "idle",
        "观察": "idle",
        "near_term": "near_term",
        "近期": "near_term",
        "买房": "near_term",
        "购房": "near_term",
        "首付": "near_term",
        "旅行": "near_term",
    }
    raw = str(value)
    for source, target in mapping.items():
        if text == source or source in raw:
            return target
    return text if text in {"emergency", "education", "retirement", "idle", "near_term"} else ""


def _normalize_string_list(value: object, limit: int, item_limit: int) -> List[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        text = str(item).strip()
        if text:
            result.append(text[:item_limit])
        if len(result) >= limit:
            break
    return result
