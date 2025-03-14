"""FMP Dividend Calendar Model."""


from datetime import datetime
from typing import Any, Dict, List, Optional

from dateutil.relativedelta import relativedelta
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.calendar_dividend import (
    DividendCalendarData,
    DividendCalendarQueryParams,
)
from openbb_fmp.utils.helpers import get_data_many, get_querystring
from pydantic import Field, field_validator


class FMPDividendCalendarQueryParams(DividendCalendarQueryParams):
    """FMP Dividend Calendar Query.

    Source: https://site.financialmodelingprep.com/developer/docs/dividend-calendar-api/

    The maximum time interval between the start and end date can be 3 months.
    """


class FMPDividendCalendarData(DividendCalendarData):
    """FMP Dividend Calendar Data."""

    __alias_dict__ = {
        "amount": "dividend",
        "record_date": "recordDate",
        "payment_date": "paymentDate",
        "declaration_date": "declarationDate",
    }

    adjusted_amount: Optional[float] = Field(
        default=None,
        description="The adjusted-dividend amount.",
        alias="adjDividend",
    )
    label: Optional[str] = Field(
        default=None, description="Ex-dividend date formatted for display."
    )

    @field_validator(
        "date",
        "record_date",
        "payment_date",
        "declaration_date",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def date_validate(cls, v: str):  # pylint: disable=E0213
        """Return the date as a datetime object."""
        return datetime.strptime(v, "%Y-%m-%d") if v else None


class FMPDividendCalendarFetcher(
    Fetcher[
        FMPDividendCalendarQueryParams,
        List[FMPDividendCalendarData],
    ]
):
    """Transform the query, extract and transform the data from the FMP endpoints."""

    @staticmethod
    def transform_query(params: Dict[str, Any]) -> FMPDividendCalendarQueryParams:
        """Transform the query params."""
        transformed_params = params

        now = datetime.now().date()
        if params.get("start_date") is None:
            transformed_params["start_date"] = now
        if params.get("end_date") is None:
            transformed_params["end_date"] = now + relativedelta(days=3)

        return FMPDividendCalendarQueryParams(**transformed_params)

    @staticmethod
    def extract_data(
        query: FMPDividendCalendarQueryParams,
        credentials: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> List[Dict]:
        """Return the raw data from the FMP endpoint."""
        api_key = credentials.get("fmp_api_key") if credentials else ""

        base_url = "https://financialmodelingprep.com/api/v3"
        query_str = get_querystring(query.model_dump(), [])
        query_str = query_str.replace("start_date", "from").replace("end_date", "to")
        url = f"{base_url}/stock_dividend_calendar?{query_str}&apikey={api_key}"

        return get_data_many(url, **kwargs)

    @staticmethod
    def transform_data(
        query: FMPDividendCalendarQueryParams, data: List[Dict], **kwargs: Any
    ) -> List[FMPDividendCalendarData]:
        """Return the transformed data."""
        return [FMPDividendCalendarData.model_validate(d) for d in data]
