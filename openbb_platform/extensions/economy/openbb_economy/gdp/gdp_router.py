"""Economy GDP Router."""
from openbb_core.app.model.command_context import CommandContext
from openbb_core.app.model.obbject import OBBject
from openbb_core.app.provider_interface import (
    ExtraParams,
    ProviderChoices,
    StandardParams,
)
from openbb_core.app.query import Query
from openbb_core.app.router import Router
from pydantic import BaseModel

router = Router(prefix="/gdp")

# pylint: disable=unused-argument


@router.command(model="GdpForecast")
def forecast(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject[BaseModel]:
    """Forecasted GDP Data."""
    return OBBject(results=Query(**locals()).execute())


@router.command(model="GdpNominal")
def nominal(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject[BaseModel]:
    """Nominal GDP Data."""
    return OBBject(results=Query(**locals()).execute())


@router.command(model="GdpReal")
def real(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject[BaseModel]:
    """Real GDP Data."""
    return OBBject(results=Query(**locals()).execute())
