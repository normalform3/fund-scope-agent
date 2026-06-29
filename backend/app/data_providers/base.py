from abc import ABC, abstractmethod
from typing import List

from app.models import FundProfile, NavPoint


class FundDataProvider(ABC):
    @abstractmethod
    def search_funds(self, query: str) -> List[FundProfile]:
        raise NotImplementedError

    @abstractmethod
    def get_profile(self, code: str) -> FundProfile:
        raise NotImplementedError

    @abstractmethod
    def get_nav_history(self, code: str) -> List[NavPoint]:
        raise NotImplementedError

