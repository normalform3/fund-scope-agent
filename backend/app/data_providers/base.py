from abc import ABC, abstractmethod
from typing import List

from app.models import FundFee, FundHolding, FundProfile, IndustryAllocation, NavPoint


class FundDataProvider(ABC):
    @abstractmethod
    def search_funds(self, query: str) -> List[FundProfile]:
        raise NotImplementedError

    def list_funds(self, limit: int = 100) -> List[FundProfile]:
        return self.search_funds("")[:limit]

    @abstractmethod
    def get_profile(self, code: str) -> FundProfile:
        raise NotImplementedError

    @abstractmethod
    def get_nav_history(self, code: str) -> List[NavPoint]:
        raise NotImplementedError

    def get_holdings(self, code: str) -> List[FundHolding]:
        return []

    def get_industry_allocation(self, code: str) -> List[IndustryAllocation]:
        return []

    def get_fees(self, code: str) -> List[FundFee]:
        return []
