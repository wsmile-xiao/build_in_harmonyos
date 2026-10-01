# Vine

Vine provides promise and synchronization primitives used by Python applications. Version 5.1.0 is a pure Python package with no runtime dependencies.

The Conan package places the upstream `vine` modules under `lib/python/vine` and exposes that directory through `PYTHONPATH`. It does not compile native code or invoke upstream `setup.py` during packaging.

The upstream unit suite is run with pytest. A one-line patch renames its barrier fixture hook from nose's `setup()` convention to pytest's supported `setup_method()` convention; no Vine runtime code is changed. The Conan consumer test checks imports from the package path, version metadata, promise callbacks/chaining, barriers, and conversion helpers.

Upstream: https://github.com/celery/vine
License: BSD-3-Clause (upstream LICENSE retained in the package).

Validation: H1-004 W3 Conan package consumers passed 6/6. The local patched upstream suite passed 42/42. H1 target `pytest.stdout` reports 42 passed in 0.30s with empty stderr, but its outer runner returned RC 1 afterward while resolving bare `python3 --version`; the pytest subprocess RC was not persisted, so no pytest RC 0 is claimed. H1-004's legacy `clean-verify` returned RC 1 after applying the patch because the pure-Python source archive has no `./configure`; this is recorded separately from the successful Conan path.
