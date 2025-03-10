"""Query executor module."""
from typing import Any, Dict, Optional, Type

from pydantic import SecretStr

from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.provider import Provider
from openbb_core.provider.registry import Registry, RegistryLoader
from openbb_core.provider.utils.errors import ProviderError


class QueryExecutor:
    """Class to execute queries from providers."""

    def __init__(self, registry: Optional[Registry] = None) -> None:
        """Initialize the query executor."""
        self.registry = registry or RegistryLoader.from_extensions()

    def get_provider(self, provider_name: str) -> Provider:
        """Get a provider from the registry."""
        name = provider_name.lower()
        if name not in self.registry.providers:
            raise ProviderError(
                f"Provider '{name}' not found in the registry."
                f"Available providers: {list(self.registry.providers.keys())}"
            )
        return self.registry.providers[name]

    def get_fetcher(self, provider: Provider, model_name: str) -> Type[Fetcher]:
        """Get a fetcher from a provider."""
        if model_name not in provider.fetcher_dict:
            raise ProviderError(
                f"Fetcher not found for model '{model_name}' in provider '{provider.name}'."
            )
        return provider.fetcher_dict[model_name]

    @staticmethod
    def filter_credentials(
        credentials: Optional[Dict[str, SecretStr]],
        provider: Provider,
        require_credentials: bool,
    ) -> Dict[str, str]:
        """Filter credentials and check if they match provider requirements."""
        filtered_credentials = {}

        if provider.credentials:
            if credentials is None:
                credentials = {}

            for c in provider.credentials:
                credential_value = credentials.get(c)
                if c not in credentials or credential_value is None:
                    if require_credentials:
                        raise ProviderError(f"Missing credential '{c}'.")
                else:
                    filtered_credentials[c] = credential_value.get_secret_value()

        return filtered_credentials

    def execute(
        self,
        provider_name: str,
        model_name: str,
        params: Dict[str, Any],
        credentials: Optional[Dict[str, SecretStr]] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute query.

        Parameters
        ----------
        provider_name : str
            Name of the provider, for example: "fmp".
        model_name : str
            Name of the model, for example: "EquityHistorical".
        params : Dict[str, Any]
            Query parameters, for example: {"symbol": "AAPL"}
        credentials : Optional[Dict[str, SecretStr]], optional
            Credentials for the provider, by default None
            For example, {"fmp_api_key": SecretStr("1234")}.

        Returns
        -------
        Any
            Query result.
        """
        provider = self.get_provider(provider_name)
        fetcher = self.get_fetcher(provider, model_name)
        filtered_credentials = self.filter_credentials(
            credentials, provider, fetcher.require_credentials
        )

        try:
            return fetcher.fetch_data(params, filtered_credentials, **kwargs)
        except Exception as e:
            raise ProviderError(e) from e
