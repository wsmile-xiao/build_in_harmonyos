#!/usr/bin/env python3
"""Exercise public six APIs from the Conan package payload."""

import os
from pathlib import Path

import six
from six.moves.urllib.parse import parse_qs, urlencode, urlparse


expected_root = Path(os.environ["SIX_PACKAGE_ROOT"]).resolve()
module_path = Path(six.__file__).resolve()
assert module_path.name == "six.py"
assert expected_root in module_path.parents
assert six.__version__ == "1.17.0"
assert six.PY3
assert six.text_type is str
assert six.binary_type is bytes
assert six.ensure_text(b"harmony") == "harmony"
assert six.ensure_binary("harmony") == b"harmony"
assert six.ensure_str(b"harmony") == "harmony"
assert list(six.iteritems({"answer": 42})) == [("answer", 42)]


class Base:
    pass


class Derived(six.with_metaclass(type, Base)):
    pass


assert issubclass(Derived, Base)


@six.python_2_unicode_compatible
class Label:
    def __str__(self):
        return "six"


assert str(Label()) == "six"
query = urlencode({"library": "six", "version": six.__version__})
parsed = urlparse(f"https://example.invalid/?{query}")
assert parsed.scheme == "https"
assert parsed.netloc == "example.invalid"
assert parse_qs(parsed.query) == {"library": ["six"], "version": ["1.17.0"]}
print("six 1.17.0 compatibility API: PASS")
