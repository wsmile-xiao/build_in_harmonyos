#!/usr/bin/env python3
"""Consumer test for pysmappee 0.2.29 — import API and exercise pure helpers."""
import sys


def test_import_and_symbols():
    from pysmappee import Smappee
    from pysmappee.api import SmappeeApi, SmappeeLocalApi
    from pysmappee.helper import urljoin
    from pysmappee import config

    assert Smappee is not None
    assert SmappeeApi is not None
    assert SmappeeLocalApi is not None
    assert callable(urljoin)
    assert isinstance(config.config, dict)
    print("PASS: pysmappee public symbols imported")


def test_helper_urljoin():
    from pysmappee.helper import urljoin

    assert urljoin("https://a.com/", "b", "c") == "https://a.com/b/c"
    assert urljoin("https://a.com", "/b/", "c/") == "https://a.com/b/c"
    assert urljoin(1, 2, 3) == "1/2/3"
    print("PASS: urljoin helper works")


def test_helper_serial_detectors():
    from pysmappee.helper import (
        is_smappee_energy,
        is_smappee_solar,
        is_smappee_plus,
        is_smappee_genius,
        is_smappee_connect,
    )

    assert is_smappee_energy("100123") is True
    assert is_smappee_energy("200123") is False
    assert is_smappee_solar("110123") is True
    assert is_smappee_plus("200123") is True
    assert is_smappee_genius("500123") is True
    assert is_smappee_connect("510123") is True
    print("PASS: serialnumber detector helpers work")


def test_config_farms():
    from pysmappee import config

    for farm in (1, 2, 3):
        assert farm in config.config["API_URL"]
        assert "token_url" in config.config["API_URL"][farm]
        assert "servicelocation_url" in config.config["API_URL"][farm]
        assert farm in config.config["MQTT"]
        assert "host" in config.config["MQTT"][farm]
        assert "port" in config.config["MQTT"][farm]
    assert config.config["MQTT"]["local"]["port"] == 1883
    print("PASS: config farms/MQTT entries present")


def test_construct_api_objects():
    from pysmappee.api import SmappeeApi, SmappeeLocalApi
    from pysmappee import Smappee

    api = SmappeeApi(
        client_id="dummy-client",
        client_secret="dummy-secret",
        farm=1,
    )
    assert api.farm == 1
    assert "Authorization" in api.headers

    local = SmappeeLocalApi(ip="127.0.0.1")
    assert local is not None

    wrapper = Smappee(api=api, serialnumber=None)
    assert wrapper.local_polling is False
    assert wrapper.service_locations == {}
    print("PASS: SmappeeApi/SmappeeLocalApi/Smappee constructible")


if __name__ == "__main__":
    tests = [
        test_import_and_symbols,
        test_helper_urljoin,
        test_helper_serial_detectors,
        test_config_farms,
        test_construct_api_objects,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
        except Exception as e:
            print(f"FAIL: {fn.__name__}: {e}", file=sys.stderr)
            failed += 1
    if failed:
        print(f"\n{failed} test(s) FAILED", file=sys.stderr)
        sys.exit(1)
    print("\nAll pysmappee consumer tests passed.")
    sys.exit(0)
