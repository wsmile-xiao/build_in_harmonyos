"""Check HarmonyOS build environment.
"""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
from .utils import log_info, log_ok, log_warn, log_fail


def _check_var(name: str, required: bool = False) -> tuple[str, str]:
    val = os.environ.get(name, "")
    if val:
        return val, "ok"
    return "", "error" if required else "warn"


def _check_cmd(name: str) -> tuple[bool, str]:
    path = shutil.which(name)
    if not path:
        return False, ""
    try:
        r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
        ver = (r.stdout or "").split("\n")[0].strip()
        return True, ver
    except Exception:
        return True, ""


def check_env() -> int:
    """Check build environment. Returns 0=ok, 1=errors."""
    errors = 0
    warnings = 0

    # Environment variables
    log_info("检查环境变量...")
    required_vars = ["TMPDIR"]
    recommended_vars = ["CC", "CXX", "CFLAGS", "DEFAULT_PREFIX", "LD_LIBRARY_PATH"]
    for v in required_vars:
        val, st = _check_var(v, required=True)
        if st == "error":
            log_fail(f"  ❌ {v}: 未设置 (必需)")
            errors += 1
        else:
            log_ok(f"  ✅ {v}={val}")
    for v in recommended_vars:
        val, st = _check_var(v)
        if st == "ok":
            log_ok(f"  ✅ {v}={val}")
        else:
            log_warn(f"  ⚠️ {v}: 未设置")
            warnings += 1

    # Directories
    log_info("检查目录...")
    tmpdir = os.environ.get("TMPDIR", "")
    prefix = os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))
    for d in [tmpdir, f"{prefix}/bin", f"{prefix}/lib"]:
        if d and os.path.isdir(d):
            log_ok(f"  ✅ {d}")
        elif d:
            log_warn(f"  ⚠️ {d} 不存在")
            warnings += 1

    # Compilers
    log_info("检查编译器...")
    for cmd in ["clang", "cc", "c++", "llvm-ar", "llvm-ranlib"]:
        found, ver = _check_cmd(cmd)
        if found:
            log_ok(f"  ✅ {cmd}: {ver}")
        else:
            log_warn(f"  ⚠️ {cmd}: 未找到")
            warnings += 1

    # Build tools
    log_info("检查构建工具...")
    for cmd in ["make", "cmake", "autoconf", "automake", "pkg-config"]:
        found, ver = _check_cmd(cmd)
        if found:
            log_ok(f"  ✅ {cmd}: {ver}")
        else:
            log_warn(f"  ⚠️ {cmd}: 未找到")
            warnings += 1

    # Summary
    print(f"\n  📊 errors={errors}, warnings={warnings}")
    if errors:
        log_fail("环境检查未通过，请配置上述必需项")
        return 1
    log_ok("环境检查通过")
    return 0


def check_env_cli(argv: list[str] | None = None) -> int:
    return check_env()
