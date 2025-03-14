"""Dividend Calendar Standard Model."""


from datetime import date as dateType
from typing import Optional

from pydantic import Field

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.query_params import QueryParams
from openbb_core.provider.utils.descriptions import (
    DATA_DESCRIPTIONS,
    QUERY_DESCRIPTIONS,
)


class DividendCalendarQueryParams(QueryParams):
    """Dividend Calendar Query."""

    start_date: Optional[dateType] = Field(
        default=None, description=QUERY_DESCRIPTIONS.get("start_date", "")
    )
    end_date: Optional[dateType] = Field(
        default=None, description=QUERY_DESCRIPTIONS.get("end_date", "")
    )


class DividendCalendarData(Data):
    """Dividend Calendar Data."""

    date: dateType = Field(
        description=DATA_DESCRIPTIONS.get("date", "") + " (Ex-Dividend)"
    )
    symbol: str = Field(description=DATA_DESCRIPTIONS.get("symbol", ""))
    name: Optional[str] = Field(description="Name of the entity.", default=None)
    record_date: Optional[dateType] = Field(
        default=None,
        description="The record date of ownership for eligibility.",
    )
    payment_date: Optional[dateType] = Field(
        default=None,
        description="The payment date of the dividend.",
    )
    declaration_date: Optional[dateType] = Field(
        default=None,
        description="Declaration date of the dividend.",
    )
    amount: Optional[float] = Field(
        default=None, description="Dividend amount, per-share."
    )
