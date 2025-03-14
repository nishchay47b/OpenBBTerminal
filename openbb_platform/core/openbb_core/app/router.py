import traceback
import warnings
from functools import lru_cache, partial
from inspect import Parameter, Signature, isclass, signature
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

from fastapi import APIRouter, Depends
from importlib_metadata import entry_points
from pydantic import BaseModel
from pydantic.v1.validators import find_validators
from typing_extensions import Annotated, ParamSpec, _AnnotatedAlias

from openbb_core.app.model.abstract.warning import OpenBBWarning
from openbb_core.app.model.command_context import CommandContext
from openbb_core.app.model.obbject import OBBject
from openbb_core.app.provider_interface import (
    ExtraParams,
    ProviderChoices,
    ProviderInterface,
    StandardParams,
)
from openbb_core.env import Env

P = ParamSpec("P")


class OpenBBErrorResponse(BaseModel):
    """OpenBB Error Response."""

    detail: str
    error_kind: str


class CommandValidator:
    @staticmethod
    def is_standard_pydantic_type(value_type: Type) -> bool:
        """Check whether or not a parameter type is a valid Pydantic Standard Type."""
        try:
            func = next(
                find_validators(value_type, config=dict(arbitrary_types_allowed=True))
            )
            valid_type = func.__name__ != "arbitrary_type_validator"
        except Exception:
            valid_type = False

        return valid_type

    @staticmethod
    def is_valid_pydantic_model_type(model_type: Type) -> bool:
        if not isclass(model_type):
            return False

        if issubclass(model_type, BaseModel):
            try:
                model_type.model_json_schema()
                return True
            except ValueError:
                return False
        return False

    @classmethod
    def is_serializable_value_type(cls, value_type: Type) -> bool:
        return cls.is_standard_pydantic_type(
            value_type=value_type
        ) or cls.is_valid_pydantic_model_type(model_type=value_type)

    @staticmethod
    def is_annotated_dc(annotation) -> bool:
        return isinstance(annotation, _AnnotatedAlias) and hasattr(
            annotation.__args__[0], "__dataclass_fields__"
        )

    @staticmethod
    def check_reserved_param(
        name: str,
        expected_annot: Any,
        parameter_map: Mapping[str, Parameter],
        func: Callable,
        sig: Signature,
    ):
        if name in parameter_map:
            annotation = getattr(parameter_map[name], "annotation", None)
            if annotation is not None and CommandValidator.is_annotated_dc(annotation):
                annotation = annotation.__args__[0].__bases__[0]
            if not annotation == expected_annot:
                raise TypeError(
                    f"The parameter `{name}` must be a {expected_annot}.\n"
                    f"module    = {func.__module__}\n"
                    f"function  = {func.__name__}\n"
                    f"signature = {sig}\n"
                )

    @classmethod
    def check_parameters(cls, func: Callable):
        sig = signature(func)
        parameter_map = sig.parameters

        check_reserved = partial(
            cls.check_reserved_param, parameter_map=parameter_map, func=func, sig=sig
        )
        check_reserved("cc", CommandContext)
        check_reserved("provider_choices", ProviderChoices)
        check_reserved("standard_params", StandardParams)
        check_reserved("extra_params", ExtraParams)

        for parameter in parameter_map.values():
            if not cls.is_serializable_value_type(value_type=parameter.annotation):
                raise TypeError(
                    "Invalid parameter type, please provide a serializable type like:"
                    "BaseModel, Pydantic Standard Type or CommandContext.\n"
                    f"module    = {func.__module__}\n"
                    f"function  = {func.__name__}\n"
                    f"signature = {sig}\n"
                    f"parameter = {parameter}\n"
                )

    @classmethod
    def check_return(cls, func: Callable):
        sig = signature(func)
        return_type = sig.return_annotation

        valid_return_type = False

        if isclass(return_type) and issubclass(return_type, OBBject):
            results_type = return_type.__pydantic_generic_metadata__.get("args", [])[
                0
            ]  # type: ignore
            if not isinstance(results_type, type(None)):
                generic_type_list = get_args(results_type)
                if len(generic_type_list) >= 1:
                    valid_return_type = cls.is_serializable_value_type(
                        value_type=generic_type_list[len(generic_type_list) - 1]
                    )
                else:
                    valid_return_type = cls.is_serializable_value_type(
                        value_type=results_type
                    )

        if not valid_return_type:
            raise TypeError(
                "\nInvalid function: "
                f"    {func.__module__}.{func.__name__}\n"
                "Invalid return type in signature:"
                f"    {func.__name__}(...) -> {sig.return_annotation}:\n"
                "Allowed return type:"
                f"    {func.__name__}(...) -> OBBject[T] :\n"
                "If you need T = None, use an empty model instead.\n"
            )

    @classmethod
    def check(cls, func: Callable):
        cls.check_return(func=func)
        cls.check_parameters(func=func)


class Router:
    @property
    def api_router(self) -> APIRouter:
        return self._api_router

    def __init__(
        self,
        prefix: str = "",
    ) -> None:
        self._api_router = APIRouter(
            prefix=prefix,
            responses={404: {"description": "Not found"}},
        )

    @overload
    def command(self, func: Optional[Callable[P, OBBject]]) -> Callable[P, OBBject]:
        pass

    @overload
    def command(self, **kwargs) -> Callable:
        pass

    def command(
        self,
        func: Optional[Callable[P, OBBject]] = None,
        **kwargs,
    ) -> Optional[Callable]:
        if func is None:
            return lambda f: self.command(f, **kwargs)

        api_router = self._api_router

        model = kwargs.pop("model", "")
        if model:
            kwargs["response_model_exclude_unset"] = True
            kwargs["openapi_extra"] = {"model": model}

        func = SignatureInspector.complete_signature(func, model)

        if func:
            CommandValidator.check(func=func)

            kwargs["operation_id"] = kwargs.get(
                "operation_id", SignatureInspector.get_operation_id(func)
            )
            kwargs["path"] = kwargs.get("path", f"/{func.__name__}")
            kwargs["endpoint"] = func
            kwargs["methods"] = kwargs.get("methods", ["GET"])
            kwargs["response_model"] = kwargs.get(
                "response_model",
                func.__annotations__["return"],  # type: ignore
            )
            kwargs["response_model_by_alias"] = kwargs.get(
                "response_model_by_alias", False
            )
            kwargs["description"] = SignatureInspector.get_description(func)
            kwargs["responses"] = kwargs.get(
                "responses",
                {
                    400: {
                        "model": OpenBBErrorResponse,
                        "description": "No Results Found",
                    },
                    404: {"description": "Not found"},
                    500: {
                        "model": OpenBBErrorResponse,
                        "description": "Internal Error",
                    },
                },
            )

            api_router.add_api_route(**kwargs)

        return func

    def include_router(
        self,
        router: "Router",
        prefix: str = "",
    ):
        tags = [prefix[1:]] if prefix else None
        self._api_router.include_router(
            router=router.api_router, prefix=prefix, tags=tags  # type: ignore
        )


class SignatureInspector:
    @classmethod
    def complete_signature(
        cls, func: Callable[P, OBBject], model: str
    ) -> Optional[Callable[P, OBBject]]:
        """Complete function signature."""

        if isclass(return_type := func.__annotations__["return"]) and not issubclass(
            return_type, OBBject
        ):
            return func

        provider_interface = ProviderInterface()

        if model:
            if model not in provider_interface.models:
                if Env().DEBUG_MODE:
                    warnings.warn(
                        message=f"\nSkipping api route '/{func.__name__}'.\n"
                        f"Model '{model}' not found.\n\n"
                        "Check available models in ProviderInterface().models",
                        category=OpenBBWarning,
                    )
                return None

            cls.validate_signature(
                func,
                {
                    "provider_choices": ProviderChoices,
                    "standard_params": StandardParams,
                    "extra_params": ExtraParams,
                },
            )

            func = cls.inject_dependency(
                func=func,
                arg="provider_choices",
                callable_=provider_interface.model_providers[model],
            )

            func = cls.inject_dependency(
                func=func,
                arg="standard_params",
                callable_=provider_interface.params[model]["standard"],
            )

            func = cls.inject_dependency(
                func=func,
                arg="extra_params",
                callable_=provider_interface.params[model]["extra"],
            )

            func = cls.inject_return_type(
                func=func,
                inner_type=provider_interface.return_schema[model],
                outer_type=provider_interface.return_map[model],
            )
        else:
            func = cls.polish_return_schema(func)
            if (
                "provider_choices" in func.__annotations__
                and func.__annotations__["provider_choices"] == ProviderChoices
            ):
                func = cls.inject_dependency(
                    func=func,
                    arg="provider_choices",
                    callable_=provider_interface.provider_choices,
                )

        return func

    @staticmethod
    def inject_return_type(
        func: Callable[P, OBBject], inner_type: Any, outer_type: Any
    ) -> Callable[P, OBBject]:
        """Inject full return model into the function.
        Also updates __name__ and __doc__ for API schemas."""
        ReturnModel = inner_type
        if get_origin(outer_type) == list:
            ReturnModel = List[inner_type]  # type: ignore
        elif get_origin(outer_type) == Union:
            ReturnModel = Union[List[inner_type], inner_type]  # type: ignore

        return_type = OBBject[ReturnModel]  # type: ignore
        return_type.__name__ = f"OBBject[{inner_type.__name__}]"
        return_type.__doc__ = f"OBBject with results of type '{inner_type.__name__}'."
        return_type.model_rebuild(force=True)

        func.__annotations__["return"] = return_type
        return func

    @staticmethod
    def polish_return_schema(func: Callable[P, OBBject]) -> Callable[P, OBBject]:
        """Polish API schemas by filling __doc__ and __name__"""
        return_type = func.__annotations__["return"]
        is_list = False

        results_type = get_type_hints(return_type)["results"]
        if not isinstance(results_type, type(None)):
            results_type = get_args(results_type)[0]

        is_list = get_origin(results_type) == list
        args = get_args(results_type)
        inner_type = args[0] if is_list and args else results_type
        inner_type_name = getattr(inner_type, "__name__", inner_type)

        func.__annotations__["return"].__doc__ = "OBBject"
        func.__annotations__["return"].__name__ = f"OBBject[{inner_type_name}]"

        return func

    @staticmethod
    def validate_signature(
        func: Callable[P, OBBject], expected: Dict[str, type]
    ) -> None:
        """Validate function signature before binding to model."""
        for k, v in expected.items():
            if k not in func.__annotations__:
                raise AttributeError(
                    f"Invalid signature: '{func.__name__}'. Missing '{k}' parameter."
                )

            if func.__annotations__[k] != v:
                raise TypeError(
                    f"Invalid signature: '{func.__name__}'. '{k}' parameter must be of type '{v.__name__}'."
                )

    @staticmethod
    def inject_dependency(
        func: Callable[P, OBBject], arg: str, callable_: Any
    ) -> Callable[P, OBBject]:
        """Annotate function with dependency injection."""
        func.__annotations__[arg] = Annotated[callable_, Depends()]  # type: ignore
        return func

    @staticmethod
    def get_description(func: Callable) -> str:
        """Get description from docstring."""
        doc = func.__doc__
        if doc:
            description = doc.split("    Parameters\n    ----------")[0]
            description = description.split("    Returns\n    -------")[0]
            description = "\n".join([line.strip() for line in description.split("\n")])

            return description
        return ""

    @staticmethod
    def get_operation_id(func: Callable) -> str:
        """Get operation id"""
        operation_id = [
            t.replace("_router", "")
            for t in func.__module__.split(".")[1:] + [func.__name__]
        ]
        cleaned_id = "_".join({c: "" for c in operation_id if c}.keys())
        return cleaned_id


class CommandMap:
    """Matching Routes with Commands."""

    def __init__(
        self, router: Optional[Router] = None, coverage_sep: Optional[str] = None
    ) -> None:
        self._router = router or RouterLoader.from_extensions()
        self._map = self.get_command_map(router=self._router)
        self._provider_coverage = self.get_provider_coverage(
            router=self._router, sep=coverage_sep
        )
        self._command_coverage = self.get_command_coverage(
            router=self._router, sep=coverage_sep
        )
        self._commands_model = self.get_commands_model(
            router=self._router, sep=coverage_sep
        )

    @property
    def map(self) -> Dict[str, Callable]:
        return self._map

    @property
    def provider_coverage(self) -> Dict[str, List[str]]:
        return self._provider_coverage

    @property
    def command_coverage(self) -> Dict[str, List[str]]:
        return self._command_coverage

    @property
    def commands_model(self) -> Dict[str, List[str]]:
        return self._commands_model

    @staticmethod
    def get_command_map(
        router: Router,
    ) -> Dict[str, Callable]:
        api_router = router.api_router
        command_map = {route.path: route.endpoint for route in api_router.routes}  # type: ignore
        return command_map

    @staticmethod
    def get_provider_coverage(
        router: Router, sep: Optional[str] = None
    ) -> Dict[str, List[str]]:
        api_router = router.api_router

        mapping = ProviderInterface().map

        coverage_map: Dict[Any, Any] = {}
        for route in api_router.routes:
            openapi_extra = getattr(route, "openapi_extra")
            if openapi_extra:
                model = openapi_extra.get("model", None)
                if model:
                    providers = list(mapping[model].keys())
                    if "openbb" in providers:
                        providers.remove("openbb")
                    for provider in providers:
                        if provider not in coverage_map:
                            coverage_map[provider] = []
                        if hasattr(route, "path"):
                            rp = (
                                route.path  # type: ignore
                                if sep is None
                                else route.path.replace("/", sep)  # type: ignore
                            )
                            coverage_map[provider].append(rp)

        return coverage_map

    @staticmethod
    def get_command_coverage(
        router: Router, sep: Optional[str] = None
    ) -> Dict[str, List[str]]:
        api_router = router.api_router

        mapping = ProviderInterface().map

        coverage_map: Dict[Any, Any] = {}
        for route in api_router.routes:
            openapi_extra = getattr(route, "openapi_extra")
            if openapi_extra:
                model = openapi_extra.get("model", None)
                if model:
                    providers = list(mapping[model].keys())
                    if "openbb" in providers:
                        providers.remove("openbb")

                    if hasattr(route, "path"):
                        rp = (
                            route.path if sep is None else route.path.replace("/", sep)  # type: ignore
                        )
                        if route.path not in coverage_map:  # type: ignore
                            coverage_map[rp] = []
                        coverage_map[rp] = providers
        return coverage_map

    @staticmethod
    def get_commands_model(
        router: Router, sep: Optional[str] = None
    ) -> Dict[str, List[str]]:
        api_router = router.api_router

        coverage_map: Dict[Any, Any] = {}
        for route in api_router.routes:
            openapi_extra = getattr(route, "openapi_extra")
            if openapi_extra:
                model = openapi_extra.get("model", None)
                if model and hasattr(route, "path"):
                    rp = (
                        route.path if sep is None else route.path.replace("/", sep)  # type: ignore
                    )
                    if route.path not in coverage_map:  # type: ignore
                        coverage_map[rp] = []
                    coverage_map[rp] = model
        return coverage_map

    def get_command(self, route: str) -> Optional[Callable]:
        return self._map.get(route, None)


class LoadingError(Exception):
    """Error loading extension."""


class RouterLoader:
    @staticmethod
    @lru_cache
    def from_extensions() -> Router:
        router = Router()

        for entry_point in sorted(entry_points(group="openbb_core_extension")):
            try:
                entry = entry_point.load()
                if isinstance(entry, Router):
                    router.include_router(router=entry, prefix=f"/{entry_point.name}")
            except Exception as e:
                traceback.print_exception(type(e), e, e.__traceback__)
                raise LoadingError(f"Invalid extension '{entry_point.name}'") from e

        return router
