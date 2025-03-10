"""Analyst Estimates Standard Model."""


from datetime import date as dateType
from typing import List, Literal, Set, Union

from pydantic import Field, field_validator

from openbb_core.provider.abstract.data import Data, StrictInt
from openbb_core.provider.abstract.query_params import QueryParams
from openbb_core.provider.utils.descriptions import (
    DATA_DESCRIPTIONS,
    QUERY_DESCRIPTIONS,
)


class AnalystEstimatesQueryParams(QueryParams):
    """Analyst Estimates Query."""

    symbol: str = Field(description=QUERY_DESCRIPTIONS.get("symbol", ""))
    period: Literal["quarter", "annual"] = Field(
        default="annual", description=QUERY_DESCRIPTIONS.get("period", "")
    )
    limit: int = Field(default=30, description=QUERY_DESCRIPTIONS.get("limit", ""))

    @field_validator("symbol", mode="before", check_fields=False)
    def upper_symbol(cls, v: Union[str, List[str], Set[str]]):
        """Convert symbol to uppercase."""
        if isinstance(v, str):
            return v.upper()
        return ",".join([symbol.upper() for symbol in list(v)])


class AnalystEstimatesData(Data):
    """Analyst Estimates data."""

    symbol: str = Field(description=DATA_DESCRIPTIONS.get("symbol", ""))
    date: dateType = Field(description=DATA_DESCRIPTIONS.get("date", ""))
    estimated_revenue_low: StrictInt = Field(description="Estimated revenue low.")
    estimated_revenue_high: StrictInt = Field(description="Estimated revenue high.")
    estimated_revenue_avg: StrictInt = Field(description="Estimated revenue average.")
    estimated_ebitda_low: StrictInt = Field(description="Estimated EBITDA low.")
    estimated_ebitda_high: StrictInt = Field(description="Estimated EBITDA high.")
    estimated_ebitda_avg: StrictInt = Field(description="Estimated EBITDA average.")
    estimated_ebit_low: StrictInt = Field(description="Estimated EBIT low.")
    estimated_ebit_high: StrictInt = Field(description="Estimated EBIT high.")
    estimated_ebit_avg: StrictInt = Field(description="Estimated EBIT average.")
    estimated_net_income_low: StrictInt = Field(description="Estimated net income low.")
    estimated_net_income_high: StrictInt = Field(
        description="Estimated net income high."
    )
    estimated_net_income_avg: StrictInt = Field(
        description="Estimated net income average."
    )
    estimated_sga_expense_low: StrictInt = Field(
        description="Estimated SGA expense low."
    )
    estimated_sga_expense_high: StrictInt = Field(
        description="Estimated SGA expense high."
    )
    estimated_sga_expense_avg: StrictInt = Field(
        description="Estimated SGA expense average."
    )
    estimated_eps_avg: float = Field(description="Estimated EPS average.")
    estimated_eps_high: float = Field(description="Estimated EPS high.")
    estimated_eps_low: float = Field(description="Estimated EPS low.")
    number_analyst_estimated_revenue: StrictInt = Field(
        description="Number of analysts who estimated revenue."
    )
    number_analysts_estimated_eps: StrictInt = Field(
        description="Number of analysts who estimated EPS."
    )

    @field_validator("symbol", mode="before", check_fields=False)
    def upper_symbol(cls, v: Union[str, List[str], Set[str]]):
        """Convert symbol to uppercase."""
        if isinstance(v, str):
            return v.upper()
        return ",".join([symbol.upper() for symbol in list(v)]) if v else None
