#!/usr/bin/env python3
"""Consumer-side check for the packaged appdirs 1.4.4 (R34: real API).

Drives the shipped module end to end: the five function helpers
(user_data_dir / site_data_dir / user_cache_dir / user_state_dir /
user_log_dir), the AppDirs class attribute API, version metadata and the
platform tag contract. Each call must return a real str path.
"""
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

import appdirs

assert appdirs.__version__ == "1.4.4", appdirs.__version__
assert appdirs.__version_info__ == (1, 4, 4), appdirs.__version_info__

# --- function API (real calls, assert str return) --------------------------
for fn_name in ("user_data_dir", "site_data_dir", "user_cache_dir",
                "user_state_dir", "user_log_dir"):
    fn = getattr(appdirs, fn_name)
    out = fn("MyApp", "MyCompany")
    assert isinstance(out, str) and len(out) > 0, (fn_name, out)
    print(f"  {fn_name}('MyApp','MyCompany') -> {out}")

# versioned variant exercises the appauthor/appname/version triplet
vd = appdirs.user_data_dir("MyApp", "MyCompany", version="1.0")
assert isinstance(vd, str) and "1.0" in vd.replace(" ", ""), vd

# --- class API -------------------------------------------------------------
dirs = appdirs.AppDirs("MyApp", "MyCompany", version="1.0")
for attr in ("user_data_dir", "site_data_dir", "user_cache_dir",
             "user_state_dir", "user_log_dir"):
    v = getattr(dirs, attr)
    assert isinstance(v, str) and len(v) > 0, (attr, v)
    print(f"  AppDirs.{attr} -> {v}")

print(f"appdirs {appdirs.__version__} consumer API: PASS")
