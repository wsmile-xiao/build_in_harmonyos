#!/usr/bin/env python3
"""Consumer smoke test for the packaged PyYAML module."""

import yaml


def main():
    assert yaml.__version__ == "6.0.2"
    assert yaml.__with_libyaml__ is False

    document = """
    name: pyyaml
    version: 6.0.2
    items:
      - harmony
      - conan
    enabled: true
    """
    loaded = yaml.safe_load(document)
    assert loaded["name"] == "pyyaml"
    assert loaded["version"] == "6.0.2"
    assert loaded["items"] == ["harmony", "conan"]
    assert loaded["enabled"] is True

    dumped = yaml.safe_dump(loaded, sort_keys=True)
    assert yaml.safe_load(dumped) == loaded

    stream = "---\na: 1\n---\nb: 2\n"
    docs = list(yaml.safe_load_all(stream))
    assert docs == [{"a": 1}, {"b": 2}]

    events = list(yaml.parse("key: value\n"))
    assert len(events) >= 4
    assert events[0].__class__.__name__ == "StreamStartEvent"

    print("pyyaml 6.0.2 ok")


if __name__ == "__main__":
    main()
