import keyword
from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class FundPrice:
    fund_name: str
    price_per_unit: float
    price_type: str = "nav"
    as_of: str | None = None


FundPriceMap = dict[str, FundPrice]


class PricingProviderError(RuntimeError):
    """A configured pricing provider could not return usable prices."""


@runtime_checkable
class PricingProvider(Protocol):
    name: str

    def fetch_prices(self, fund_codes: list[str]) -> FundPriceMap: ...


_PROVIDER_PACKAGE = "providers"


def _provider_module_name(provider_name: str) -> str:
    if (
        not provider_name.isidentifier()
        or keyword.iskeyword(provider_name)
        or provider_name.startswith("_")
    ):
        raise ValueError(
            "pricing provider name must be a public Python identifier, "
            "for example 'eastmoney'."
        )
    return f"{_PROVIDER_PACKAGE}.{provider_name}"


def load_provider(provider_name: str) -> PricingProvider | None:
    module_name = _provider_module_name(provider_name)
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name != module_name:
            raise
        return None

    provider = getattr(module, "PROVIDER", None)
    if provider is None:
        raise ValueError(f"Provider module {module_name!r} does not expose PROVIDER.")
    if not isinstance(provider, PricingProvider):
        raise TypeError(f"Provider module {module_name!r} has an invalid PROVIDER.")
    if provider.name != provider_name:
        raise ValueError(
            f"Provider module {module_name!r} exposes provider {provider.name!r}; "
            f"expected {provider_name!r}."
        )
    return provider


def get_fund_prices(
    fund_codes: Sequence[str],
    provider_name: str | None,
    provider: PricingProvider | None = None,
) -> FundPriceMap:
    if provider is not None and provider_name not in (None, provider.name):
        raise ValueError(
            f"Injected provider {provider.name!r} does not match configured "
            f"provider {provider_name!r}."
        )

    selected_provider = provider
    if selected_provider is None and provider_name:
        selected_provider = load_provider(provider_name)

    if selected_provider is None:
        return {}

    try:
        return selected_provider.fetch_prices([str(code) for code in fund_codes])
    except PricingProviderError as exc:
        print(f"Pricing provider {selected_provider.name!r} failed: {exc}")
        return {}
