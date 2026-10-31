from types import SimpleNamespace

import pytest

import pricing_providers


class FakePricingProvider:
    name = "fake"

    def fetch_prices(self, fund_codes: list[str]) -> dict:
        return {}


def test_load_provider_maps_name_to_same_named_module(monkeypatch):
    requested_modules = []

    def fake_import_module(module_name):
        requested_modules.append(module_name)
        return SimpleNamespace(PROVIDER=FakePricingProvider())

    monkeypatch.setattr(pricing_providers, "import_module", fake_import_module)

    provider = pricing_providers.load_provider("fake")

    assert requested_modules == ["providers.fake"]
    assert provider is not None
    assert provider.name == "fake"


@pytest.mark.parametrize(
    "provider_name", ["../eastmoney", "providers.eastmoney", "_private"]
)
def test_load_provider_rejects_unsafe_names(provider_name):
    with pytest.raises(ValueError, match="public Python identifier"):
        pricing_providers.load_provider(provider_name)
