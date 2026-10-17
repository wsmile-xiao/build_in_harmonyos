#!/usr/bin/env python3
"""Test for aiohttp-fast-zlib 0.3.0 test_package — substantively exercise the packaged library.

R34: test must substantively depend on the package under test.
This test imports the packaged `aiohttp_fast_zlib` from the Conan-installed
site-packages (via PYTHONPATH set by the test_package conanfile) and exercises
the documented public API:

1. `__version__` reports "0.3.0".
2. `enable()` then `disable()` round-trip succeeds (best_zlib fallback to
   stdlib zlib when isal/zlib_ng are absent is a supported path).
3. After `disable()`, aiohttp's zlib reference is restored to the stdlib.
"""
import importlib.util
import sys
import zlib

import aiohttp_fast_zlib


def test_version():
    assert aiohttp_fast_zlib.__version__ == "0.3.0", \
        f"expected 0.3.0, got {aiohttp_fast_zlib.__version__}"


def test_enable_disable_roundtrip():
    """enable()/disable() must round-trip without raising on any aiohttp version.

    On hosts without isal/zlib_ng installed, enable() logs a warning and is a
    no-op (best_zlib falls back to stdlib zlib); disable() restores the stdlib
    backend. This is the supported degraded path and must not raise.
    """
    import aiohttp
    aiohttp_version = aiohttp_fast_zlib._AIOHTTP_VERSION

    aiohttp_fast_zlib.enable()
    try:
        # disable() restores the original zlib backend.
        aiohttp_fast_zlib.disable()
    finally:
        # Always restore, even if assertions below raise.
        aiohttp_fast_zlib.disable()

    # After disable, the fast backend is gone and aiohttp is back on stdlib zlib.
    if aiohttp_version >= (3, 12):
        from aiohttp.compression_utils import ZLibBackend
        assert ZLibBackend._zlib_backend is zlib, \
            "after disable() ZLibBackend should be the stdlib zlib"
    else:
        # Pre-3.12 path patches aiohttp.compression_utils.zlib directly.
        import aiohttp.compression_utils as cu
        assert cu.zlib is zlib, \
            "after disable() aiohttp.compression_utils.zlib should be stdlib zlib"


def test_best_zlib_is_importable():
    """best_zlib must be a module exposing zlib-compatible compress/decompress."""
    bz = aiohttp_fast_zlib.best_zlib
    data = b"the quick brown fox jumps over the lazy dog"
    compressed = bz.compress(data)
    assert zlib.decompress(compressed) == data, \
        "best_zlib output must round-trip through stdlib zlib"


if __name__ == "__main__":
    sys.exit(0 if all(
        __import__("pytest").main([__file__, "-v"]) == 0
        for _ in [None]
    ) else 1)
