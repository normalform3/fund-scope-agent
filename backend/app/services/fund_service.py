import os
from typing import List, Optional

from app.data_providers.akshare_provider import AkshareFundDataProvider
from app.data_providers.base import FundDataProvider
from app.data_providers.sample_provider import SampleFundDataProvider
from app.models import FundProfile, NavPoint
from app.storage.cache import SQLiteCache

PROFILE_TTL_SECONDS = 60 * 60 * 12
NAV_TTL_SECONDS = 60 * 60 * 6


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
        self.cache = cache or SQLiteCache()

    def search_funds(self, query: str) -> List[FundProfile]:
        try:
            return self.provider.search_funds(query)
        except Exception:
            return self.fallback_provider.search_funds(query)

    def get_profile(self, code: str) -> FundProfile:
        cache_key = "%s:profile:%s" % (self.cache_namespace, code)
        cached = self.cache.get(cache_key, PROFILE_TTL_SECONDS)
        if cached:
            return FundProfile(**cached)

        profile = self._get_profile_uncached(code)
        self.cache.set(cache_key, profile.to_dict())
        return profile

    def get_nav_history(self, code: str) -> List[NavPoint]:
        cache_key = "%s:nav:%s" % (self.cache_namespace, code)
        cached = self.cache.get(cache_key, NAV_TTL_SECONDS)
        if cached:
            return [NavPoint(**item) for item in cached]

        points = self._get_nav_uncached(code)
        self.cache.set(cache_key, [point.to_dict() for point in points])
        return points

    def _get_profile_uncached(self, code: str) -> FundProfile:
        try:
            return self.provider.get_profile(code)
        except Exception:
            return self.fallback_provider.get_profile(code)

    def _get_nav_uncached(self, code: str) -> List[NavPoint]:
        try:
            return self.provider.get_nav_history(code)
        except Exception:
            return self.fallback_provider.get_nav_history(code)


def _build_default_provider() -> FundDataProvider:
    provider_name = os.getenv("FUNDSCOPE_DATA_PROVIDER", "sample").strip().lower()
    if provider_name == "akshare":
        return AkshareFundDataProvider()
    return SampleFundDataProvider()


def _cache_namespace(provider: FundDataProvider) -> str:
    if isinstance(provider, AkshareFundDataProvider):
        return "akshare"
    if isinstance(provider, SampleFundDataProvider):
        return "sample"
    return provider.__class__.__name__.lower()
