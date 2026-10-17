#!/usr/bin/env python3
"""
test_aioredis.py — validates the packaged aioredis Python source files.

Usage:
    python3 test_aioredis.py <package_folder>

Exercises real aioredis API per R34: checks file existence AND content
(class definitions, version declarations, asyncio content). Exit 0 on
success, non-zero on failure with a clear error message.
"""
import os
import sys


def _fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _check_file(pkg_aioredis, relpath, label):
    full = os.path.join(pkg_aioredis, relpath)
    if not os.path.isfile(full):
        _fail(f"{label}: file '{relpath}' not found in package")
    content = _read(full)
    if not content.strip():
        _fail(f"{label}: file '{relpath}' is empty")
    return content


def _check_contains(content, needle, label, file_label):
    if needle not in content:
        _fail(f"{label}: '{needle}' not found in {file_label}")


def _stub_optional_runtime_deps():
    """Stub pip-only deps so import aioredis works without Redis server/pip install.

    CI workers may not have async-timeout/typing_extensions; import-time only
    needs the modules present. Redis server is still not required for R34.
    """
    import types

    if "async_timeout" not in sys.modules:
        try:
            import async_timeout  # noqa: F401
        except ImportError:
            mod = types.ModuleType("async_timeout")

            class _Timeout:
                def __init__(self, *args, **kwargs):
                    pass

                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    return False

            mod.timeout = _Timeout
            sys.modules["async_timeout"] = mod

    if "typing_extensions" not in sys.modules:
        try:
            import typing_extensions  # noqa: F401
        except ImportError:
            sys.modules["typing_extensions"] = types.ModuleType("typing_extensions")


def main():
    if len(sys.argv) < 2:
        _fail("Usage: python3 test_aioredis.py <package_folder>")

    pkg_folder = sys.argv[1]
    pkg_aioredis = os.path.join(pkg_folder, "lib", "aioredis")

    if not os.path.isdir(pkg_aioredis):
        _fail(f"aioredis package directory not found: {pkg_aioredis}")

    # 0. R34: real import + API surface (not string-scan only)
    lib_dir = os.path.join(pkg_folder, "lib")
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    _stub_optional_runtime_deps()
    try:
        import aioredis
    except Exception as exc:
        _fail(f"import aioredis failed: {exc}")
    version = getattr(aioredis, "__version__", "") or ""
    if not version:
        _fail("aioredis.__version__ is missing or empty")
    if not hasattr(aioredis, "RedisConnection") and not hasattr(aioredis, "create_redis"):
        _fail("aioredis API missing RedisConnection/create_redis after import")
    print(f"OK: imported aioredis {version} (R34)")

    # 1. __init__.py exists and is non-empty
    init_content = _check_file(pkg_aioredis, "__init__.py", "aioredis/__init__.py")

    # 2. __init__.py contains 'version'
    _check_contains(init_content, "version", "aioredis/__init__.py version", "__init__.py")

    # 3. connection.py exists and contains 'class RedisConnection'
    conn_content = _check_file(pkg_aioredis, "connection.py", "aioredis/connection.py")
    _check_contains(conn_content, "class RedisConnection", "connection.py class", "connection.py")

    # 4. pool.py exists and contains 'class ConnectionsPool'
    pool_content = _check_file(pkg_aioredis, "pool.py", "aioredis/pool.py")
    _check_contains(pool_content, "class ConnectionsPool", "pool.py class", "pool.py")

    # 5. commands/__init__.py exists and contains 'class Redis'
    cmds_content = _check_file(pkg_aioredis, os.path.join("commands", "__init__.py"), "aioredis/commands/__init__.py")
    _check_contains(cmds_content, "class Redis", "commands/__init__.py class", "commands/__init__.py")

    # 6. locks.py exists and contains 'class Lock'
    locks_content = _check_file(pkg_aioredis, "locks.py", "aioredis/locks.py")
    _check_contains(locks_content, "class Lock", "locks.py class", "locks.py")

    # 7. sentinel/__init__.py exists and contains 'RedisSentinel'
    sentinel_content = _check_file(pkg_aioredis, os.path.join("sentinel", "__init__.py"), "aioredis/sentinel/__init__.py")
    _check_contains(sentinel_content, "RedisSentinel", "sentinel/__init__.py class", "sentinel/__init__.py")

    # 8. pubsub.py exists and contains 'Channel'
    pubsub_content = _check_file(pkg_aioredis, "pubsub.py", "aioredis/pubsub.py")
    _check_contains(pubsub_content, "Channel", "pubsub.py class", "pubsub.py")

    # 9. stream.py exists and contains 'Stream'
    stream_content = _check_file(pkg_aioredis, "stream.py", "aioredis/stream.py")
    _check_contains(stream_content, "Stream", "stream.py class", "stream.py")

    # 10. errors.py exists and contains error class definitions
    errors_content = _check_file(pkg_aioredis, "errors.py", "aioredis/errors.py")
    _check_contains(errors_content, "class ", "errors.py class", "errors.py")
    _check_contains(errors_content, "RedisError", "errors.py RedisError", "errors.py")

    # 11. Count total .py files in aioredis/ directory (should be >= 10)
    py_count = 0
    for root, _dirs, files in os.walk(pkg_aioredis):
        for fname in files:
            if fname.endswith(".py"):
                py_count += 1
    if py_count < 10:
        _fail(f"expected >= 10 .py files in aioredis/, found {py_count}")
    print(f"OK: found {py_count} .py files in aioredis/ (>= 10)")

    # 12. Verify asyncio-related content in .py files
    async_found = False
    for root, _dirs, files in os.walk(pkg_aioredis):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            content = _read(os.path.join(root, fname))
            if "async" in content or "asyncio" in content:
                async_found = True
                break
    if not async_found:
        _fail("no asyncio-related content (async/asyncio) found in any .py file")
    print("OK: asyncio-related content found in .py files")

    print("SUCCESS: all aioredis package validations passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
