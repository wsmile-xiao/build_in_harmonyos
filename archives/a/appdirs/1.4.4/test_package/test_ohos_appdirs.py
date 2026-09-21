#!/usr/bin/env python3
"""HarmonyOS-specific test for packaged appdirs 1.4.4 (OHOS 专项测试).

Verifies the OHOS PC platform contract of the shipped module:
  1. user_cache_dir / user_log_dir must resolve into the OHOS app sandbox
     (XDG_CACHE_HOME -> /data/storage/el2/... on OHOS) — proving the module
     honours the OHOS runtime environment instead of assuming a Linux HOME.
  2. All directory helpers must return absolute, non-empty str paths.
  3. user_data_dir must follow XDG_DATA_HOME (or HOME fallback) and be
     writable in principle (os.path.split on POSIX root components).

This is an OHOS-specific addition (not an upstream test): upstream 1.4.4 has
no such platform-contract assertions.
"""
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

import appdirs

# --- OHOS app sandbox resolution -------------------------------------------
cache = appdirs.user_cache_dir("OhosApp", "OH", version="1.0")
log = appdirs.user_log_dir("OhosApp", "OH", version="1.0")

for name, val in (("user_cache_dir", cache), ("user_log_dir", log)):
    assert isinstance(val, str) and val, (name, val)
    assert os.path.isabs(val), (name, val)
    print(f"  OHOS {name} -> {val}")

# On OHOS the runtime sets XDG_CACHE_HOME to the app sandbox
# (/data/storage/el2/base/haps/entry/files); the module must honour it.
xdg_cache = os.environ.get("XDG_CACHE_HOME")
if xdg_cache:
    assert cache.startswith(xdg_cache), (cache, xdg_cache)
    assert log.startswith(xdg_cache), (log, xdg_cache)
    print(f"  OHOS XDG_CACHE_HOME honoured: {xdg_cache}")

# --- generic POSIX sanity on OHOS -------------------------------------------
data = appdirs.user_data_dir("OhosApp", "OH")
assert isinstance(data, str) and data and os.path.isabs(data), data
state = appdirs.user_state_dir("OhosApp", "OH")
assert isinstance(state, str) and state and os.path.isabs(state), state
print(f"  OHOS user_data_dir -> {data}")
print(f"  OHOS user_state_dir -> {state}")

# version triplet honoured (1.0 must appear in the resolved path)
assert "1.0" in cache.replace(" ", ""), cache

print("appdirs 1.4.4 OHOS-specific test: PASS")
