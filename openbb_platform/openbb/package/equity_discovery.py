### THIS FILE IS AUTO-GENERATED. DO NOT EDIT. ###

import datetime
from typing import List, Literal, Optional, Union

from openbb_core.app.model.custom_parameter import OpenBBCustomParameter
from openbb_core.app.model.obbject import OBBject
from openbb_core.app.static.container import Container
from openbb_core.app.static.decorators import validate
from openbb_core.app.static.filters import filter_inputs
from openbb_core.provider.abstract.data import Data
from typing_extensions import Annotated


class ROUTER_equity_discovery(Container):
    """/equity/discovery
    filings
    """

    def __repr__(self) -> str:
        return self.__doc__ or ""

    @validate
    def filings(
        self,
        start_date: Annotated[
            Union[datetime.date, None, str],
            OpenBBCustomParameter(
                description="Start date of the data, in YYYY-MM-DD format."
            ),
        ] = None,
        end_date: Annotated[
            Union[datetime.date, None, str],
            OpenBBCustomParameter(
                description="End date of the data, in YYYY-MM-DD format."
            ),
        ] = None,
        form_type: Annotated[
            Optional[str],
            OpenBBCustomParameter(
                description="Fuzzy filter by form type. E.g. 10-K, 10, 8, 6-K, etc."
            ),
        ] = None,
        limit: Annotated[
            int,
            OpenBBCustomParameter(description="The number of data entries to return."),
        ] = 100,
        provider: Optional[Literal["fmp"]] = None,
        **kwargs
    ) -> OBBject[List[Data]]:
        """Get the most-recent filings submitted to the SEC.

        Parameters
        ----------
        start_date : Optional[datetime.date]
            Start date of the data, in YYYY-MM-DD format.
        end_date : Optional[datetime.date]
            End date of the data, in YYYY-MM-DD format.
        form_type : Optional[str]
            Fuzzy filter by form type. E.g. 10-K, 10, 8, 6-K, etc.
        limit : int
            The number of data entries to return.
        provider : Optional[Literal['fmp']]
            The provider to use for the query, by default None.
            If None, the provider specified in defaults is selected or 'fmp' if there is
            no default.
        is_done : Optional[Literal['true', 'false']]
            Flag for whether or not the filing is done. (provider: fmp)

        Returns
        -------
        OBBject
            results : List[DiscoveryFilings]
                Serializable results.
            provider : Optional[Literal['fmp']]
                Provider name.
            warnings : Optional[List[Warning_]]
                List of warnings.
            chart : Optional[Chart]
                Chart object.
            extra: Dict[str, Any]
                Extra info.

        DiscoveryFilings
        ----------------
        timestamp : datetime
            The timestamp from when the filing was accepted.
        symbol : Optional[str]
            Symbol representing the entity requested in the data.
        cik : str
            The CIK of the filing
        title : str
            The title of the filing
        form_type : str
            The form type of the filing
        url : Optional[str]
            The URL of the filing
        is_done : Optional[Literal['True', 'False']]
            Whether or not the filing is done. (provider: fmp)

        Example
        -------
        >>> from openbb import obb
        >>> obb.equity.discovery.filings(limit=100)
        """  # noqa: E501

        inputs = filter_inputs(
            provider_choices={
                "provider": provider,
            },
            standard_params={
                "start_date": start_date,
                "end_date": end_date,
                "form_type": form_type,
                "limit": limit,
            },
            extra_params=kwargs,
        )

        return self._run(
            "/equity/discovery/filings",
            **inputs,
        )
