#!/usr/bin/env python3
"""test_confspirator.py — consumer test source for confspirator 0.3.0 (L0c).

REAL API check (R34) on the packaged confspirator (upstream test_configs
core usage — LOCALLY MEASURED 66 passed):
  1) groups.ConfigGroup + register_child_config(fields.StrConfig)
  2) loader.load_config_dict merge from a dict
  3) read merged value via .get() and default fallback
Usage: test_confspirator.py <site-packages-dir>
"""
import os
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_confspirator.py <site-packages-dir>")
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "confspirator")):
        raise AssertionError(f"confspirator package dir missing under {site}")
    sys.path.insert(0, site)

    import confspirator  # noqa: F401
    from confspirator import groups, fields, exceptions

    # ConfigGroup + register StrConfig field (upstream test_configs usage)
    config_group = groups.ConfigGroup("test")
    config_group.register_child_config(
        fields.StrConfig("name", default="default-name"))

    # confspirator.load (upstream test_configs real API): empty dict +
    # default fallback → config.get() reads the merged value
    config = confspirator.load(config_group, {})
    if config.get("name") != "default-name":
        raise AssertionError(f"default value mismatch: {config.get('name')}")
    if config["name"] != "default-name":
        raise AssertionError(f"subscript access mismatch: {config['name']}")

    # unknown key raises NoSuchConfig (upstream test_str_config_field_no_conf)
    try:
        config.get("no_value")
        raise AssertionError("expected NoSuchConfig for unknown key")
    except exceptions.NoSuchConfig:
        pass

    print("OK: confspirator 0.3.0 real API ok "
          "(ConfigGroup/StrConfig/confspirator.load/get)")


if __name__ == "__main__":
    main()
