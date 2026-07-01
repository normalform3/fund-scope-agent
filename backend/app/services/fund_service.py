import os
from threading import Lock
from typing import List, Optional

from app.data_providers.akshare_provider import AkshareFundDataProvider
from app.data_providers.base import FundDataProvider
from app.data_providers.sample_provider import SampleFundDataProvider
from app.models import FundFee, FundHolding, FundProfile, IndustryAllocation, NavPoint
from app.storage.cache import SQLiteCache

PROFILE_TTL_SECONDS = 60 * 60 * 12
NAV_TTL_SECONDS = 60 * 60 * 6
HOLDINGS_TTL_SECONDS = 60 * 60 * 24
FEES_TTL_SECONDS = 60 * 60 * 24


class FundService:
    def __init__(
        self,
        provider: Optional[FundDataProvider] = None,
        fallback_provider: Optional[FundDataProvider] = None,
        cache: Optional[SQLiteCache] = None,
    ) -> None:
        self.provider = provider or _build_default_provider()
        self.cache_namespace = _cache_namespace(self.provider)
        self.fallback_provider = fallback_provider or SampleFundDataProvider()
        self.fallback_namespace = _cache_namespace(self.fallback_provider)
        self.cache = cache or SQLiteCache()
        self._data_events = []
        self._data_events_lock = Lock()

    def clear_data_events(self) -> None:
        with self._data_events_lock:
            self._data_events = []

    def get_data_events(self) -> List[dict]:
        with self._data_events_lock:
            return [dict(item) for item in self._data_events]

    def search_funds(self, query: str) -> List[FundProfile]:
        try:
            return self.provider.search_funds(query)
        except Exception:
            return self.fallback_provider.search_funds(query)

    def list_funds(self, limit: int = 100) -> List[FundProfile]:
        try:
            return self.provider.list_funds(limit)
        except Exception:
            return self.fallback_provider.list_funds(limit)

    def get_profile(self, code: str) -> FundProfile:
        cache_key = "%s:profile:%s" % (self.cache_namespace, code)
        cached = self.cache.get(cache_key, PROFILE_TTL_SECONDS)
        if cached:
            self._record_data_event("profile", cached.get("data_source") or self.cache_namespace, cache_hit=True)
            return FundProfile(**cached)

        profile = self._get_profile_uncached(code)
        self.cache.set(cache_key, profile.to_dict())
        return profile

    def get_nav_history(self, code: str) -> List[NavPoint]:
        cache_key = "%s:nav:%s" % (self.cache_namespace, code)
        cached = self.cache.get(cache_key, NAV_TTL_SECONDS)
        if cached:
            self._record_data_event("nav_points", "%s:cache" % self.cache_namespace, cache_hit=True)
            return [NavPoint(**item) for item in cached]

        points = self._get_nav_uncached(code)
        self.cache.set(cache_key, [point.to_dict() for point in points])
        return points

    def get_holdings(self, code: str) -> List[FundHolding]:
        cache_key = "%s:holdings:%s" % (self.cache_namespace, code)
        cached = self.cache.get(cache_key, HOLDINGS_TTL_SECONDS)
        if cached:
            self._record_data_event("holdings", "%s:cache" % self.cache_namespace, cache_hit=True)
            return [FundHolding(**item) for item in cached]
        holdings = self._provider_with_fallback("get_holdings", code)
        self.cache.set(cache_key, [item.to_dict() for item in holdings])
        return holdings

    def get_industry_allocation(self, code: str) -> List[IndustryAllocation]:
        cache_key = "%s:industry:%s" % (self.cache_namespace, code)
        cached = self.cache.get(cache_key, HOLDINGS_TTL_SECONDS)
        if cached:
            self._record_data_event("industry_allocation", "%s:cache" % self.cache_namespace, cache_hit=True)
            return [IndustryAllocation(**item) for item in cached]
        allocations = self._provider_with_fallback("get_industry_allocation", code)
        self.cache.set(cache_key, [item.to_dict() for item in allocations])
        return allocations

    def get_fees(self, code: str) -> List[FundFee]:
        cache_key = "%s:fees:%s" % (self.cache_namespace, code)
        cached = self.cache.get(cache_key, FEES_TTL_SECONDS)
        if cached:
            self._record_data_event("fees", "%s:cache" % self.cache_namespace, cache_hit=True)
            return [FundFee(**item) for item in cached]
        fees = self._provider_with_fallback("get_fees", code)
        self.cache.set(cache_key, [item.to_dict() for item in fees])
        return fees

    def _get_profile_uncached(self, code: str) -> FundProfile:
        try:
            profile = self.provider.get_profile(code)
            self._record_data_event("profile", profile.data_source or self.cache_namespace)
            return profile
        except Exception as exc:
            profile = self.fallback_provider.get_profile(code)
            self._record_data_event(
                "profile",
                profile.data_source or self.fallback_namespace,
                fallback=True,
                message="主数据源失败，已使用备用数据源：%s" % exc,
            )
            return profile

    def _get_nav_uncached(self, code: str) -> List[NavPoint]:
        try:
            points = self.provider.get_nav_history(code)
            self._record_data_event("nav_points", self.cache_namespace)
            return points
        except Exception as exc:
            points = self.fallback_provider.get_nav_history(code)
            self._record_data_event(
                "nav_points",
                self.fallback_namespace,
                fallback=True,
                message="主数据源失败，已使用备用数据源：%s" % exc,
            )
            return points

    def _provider_with_fallback(self, method_name: str, code: str):
        section = _method_section(method_name)
        try:
            result = getattr(self.provider, method_name)(code)
            self._record_data_event(section, self.cache_namespace)
            return result
        except Exception as exc:
            result = getattr(self.fallback_provider, method_name)(code)
            self._record_data_event(
                section,
                self.fallback_namespace,
                fallback=True,
                message="主数据源失败，已使用备用数据源：%s" % exc,
            )
            return result

    def _record_data_event(
        self,
        section: str,
        source: str,
        fallback: bool = False,
        cache_hit: bool = False,
        message: str = "",
    ) -> None:
        event = {
            "section": section,
            "source": source,
            "fallback": fallback,
            "cache_hit": cache_hit,
            "message": message,
        }
        with self._data_events_lock:
            self._data_events.append(event)


def _build_default_provider() -> FundDataProvider:
    provider_name = os.getenv("FUNDSCOPE_DATA_PROVIDER", "akshare").strip().lower()
    if provider_name == "akshare":
        return AkshareFundDataProvider()
    return SampleFundDataProvider()


def _cache_namespace(provider: FundDataProvider) -> str:
    if isinstance(provider, AkshareFundDataProvider):
        return "akshare"
    if isinstance(provider, SampleFundDataProvider):
        return "sample"
    return provider.__class__.__name__.lower()


def _method_section(method_name: str) -> str:
    return {
        "get_holdings": "holdings",
        "get_industry_allocation": "industry_allocation",
        "get_fees": "fees",
    }.get(method_name, method_name)
