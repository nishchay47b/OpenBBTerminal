import traceback
from typing import Dict, Optional, Set, Tuple

from importlib_metadata import entry_points
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    create_model,
)
from pydantic.functional_serializers import PlainSerializer
from typing_extensions import Annotated

from openbb_core.app.model.extension import Extension
from openbb_core.app.provider_interface import ProviderInterface


class LoadingError(Exception):
    """Error loading extension."""


# @model_serializer blocks model_dump with pydantic parameters (include, exclude)
OBBSecretStr = Annotated[
    SecretStr,
    PlainSerializer(
        lambda x: x.get_secret_value(), return_type=str, when_used="json-unless-none"
    ),
]


class CredentialsLoader:
    """Here we create the Credentials model"""

    credentials: Dict[str, Set[str]] = {}

    @staticmethod
    def prepare(
        credentials: Dict[str, Set[str]],
    ) -> Dict[str, Tuple[object, None]]:
        """Prepare credentials map to be used in the Credentials model"""
        formatted: Dict[str, Tuple[object, None]] = {}
        for origin, creds in credentials.items():
            for c in creds:
                # Not sure we should do this, if you require the same credential it breaks
                # if c in formatted:
                #     raise ValueError(f"Credential '{c}' already in use.")
                formatted[c] = (
                    Optional[OBBSecretStr],
                    Field(
                        default=None, description=origin
                    ),  # register the credential origin (obbject, providers)
                )

        return formatted

    def from_obbject(self) -> None:
        """Load credentials from OBBject extensions"""
        self.credentials["obbject"] = set()
        for entry_point in sorted(entry_points(group="openbb_obbject_extension")):
            try:
                entry = entry_point.load()
                if isinstance(entry, Extension):
                    for c in entry.credentials:
                        self.credentials["obbject"].add(c)
            except Exception as e:
                traceback.print_exception(type(e), e, e.__traceback__)
                raise LoadingError(f"Invalid extension '{entry_point.name}'") from e

    def from_providers(self) -> None:
        """Load credentials from providers"""
        self.credentials["providers"] = set()
        for c in ProviderInterface().credentials:
            self.credentials["providers"].add(c)

    def load(self) -> BaseModel:
        """Load credentials from providers"""
        # We load providers first to give them priority choosing credential names
        self.from_providers()
        self.from_obbject()
        return create_model(  # type: ignore
            "Credentials",
            __config__=ConfigDict(validate_assignment=True),
            **self.prepare(self.credentials),
        )


_Credentials = CredentialsLoader().load()


class Credentials(_Credentials):  # type: ignore
    """Credentials model used to store provider credentials"""

    def __repr__(self) -> str:
        """String representation of the credentials"""
        return (
            self.__class__.__name__
            + "\n\n"
            + "\n".join([f"{k}: {v}" for k, v in sorted(self.__dict__.items())])
        )

    def show(self):
        """Unmask credentials and print them"""
        print(  # noqa: T201
            self.__class__.__name__
            + "\n\n"
            + "\n".join(
                [f"{k}: {v}" for k, v in sorted(self.model_dump(mode="json").items())]
            )
        )
