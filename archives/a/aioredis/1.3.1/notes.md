# aioredis 1.3.1 — Adaptation Notes

## Software Info
- **Name**: aioredis
- **Version**: 1.3.1
- **Description**: asyncio (PEP 3156) Redis client — Python library for async Redis access
- **License**: MIT
- **Homepage**: https://github.com/aio-libs-abandoned/aioredis-py
- **Source URL**: https://github.com/aio-libs-abandoned/aioredis-py/archive/refs/tags/v1.3.1.tar.gz
- **SHA256**: `be5d4360443547b5cc4a7ea5753d4e60a8e079e41b44ba043060e822ab896000`
- **Type**: Pure Python library — no C/C++ compilation needed

## Build Characteristics
- aioredis is a **pure Python library** (asyncio Redis client). There are no compiled
  extensions — all source files are `.py` files.
- The `build()` step is a no-op (`pass`); no compilation is needed.
- The `package()` step copies the `aioredis/` Python source directory into the
  package folder under `lib/`, and copies the LICENSE file to `licenses/`.

## Dependencies (Python runtime — NOT Conan dependencies)
- **async-timeout**: Required runtime dependency for asyncio timeout handling.
- **hiredis**: Optional dependency for parser speedup. Has a C extension but the
  pure Python fallback parser is used when hiredis is not available.
- **typing-extensions**: For older Python versions (not needed on Python 3.12+).

These are Python runtime dependencies, not Conan dependencies. They must be
installed via pip in the target Python environment. Documented here per the
design decisions.

## Adaptation Process
1. Downloaded source tarball from GitHub (aio-libs-abandoned/aioredis-py v1.3.1 tag).
2. Verified SHA256: `be5d4360443547b5cc4a7ea5753d4e60a8e079e41b44ba043060e822ab896000`.
3. Examined source structure: `aioredis/` package directory with 29 `.py` files
   (including subpackages `commands/` and `sentinel/`).
4. Created Conan recipe with `package_type='header-library'` (content package,
   no compiled binary).
5. Settings restricted to `os` and `arch` only (no compiler/build_type needed
   for pure Python).
6. `build()` is a no-op; `package()` copies `.py` files.
7. test_package validates packaged source files structurally (content checks,
   not just file existence).

## Test Approach
The upstream test suite (`tests/` directory) is pytest-based and requires a
running Redis server for integration tests. Since this is a pure Python
library packaged as source (no compiled binary to test), the test_package
validates the packaged `.py` files structurally:
- Checks file existence AND content (class definitions, version declarations).
- Verifies 12 substantive conditions per R34.
- Confirms asyncio-related content is present.

## Key Decisions
- **package_type = 'header-library'**: Pure Python content package, no compiled binary.
- **settings = 'os', 'arch'**: No compiler or build_type needed — pure Python.
- **generators = ''**: No generators needed.
- **requirements() = pass**: Python runtime deps are not Conan deps.
- **build() = pass**: No compilation — just file packaging.

## Abandoned Project Note
aioredis is an **abandoned project**. This is the final 1.3.1 release before
the project was archived. aioredis 2.x merged into redis-py (`redis.asyncio`).
Users are encouraged to use `redis.asyncio` from the redis-py package for new
projects. This recipe packages the abandoned 1.3.1 release for HarmonyOS PC
compatibility.
