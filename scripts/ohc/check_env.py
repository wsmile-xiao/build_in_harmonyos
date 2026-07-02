"""Check HarmonyOS build environment.
"""
from __future__ import annotations
import os
import shutil
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path
from .utils import log_info, log_ok, log_warn, log_fail

_CA_CERT_PATH = "/storage/Users/currentUser/usr/local/ssl/cert.pem"
_CA_CERT_URL = "https://curl.se/ca/cacert.pem"


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
        return False, str(e)


def _check_ssl_certs() -> bool:
    """Check if CA certificates are installed, auto-install if missing."""
    cert_path = Path(_CA_CERT_PATH)

    # Already installed — quick test
    if cert_path.exists():
        try:
            urllib.request.urlopen("https://ftp.gnu.org/", timeout=5)
            log_ok(f"  ✅ SSL 证书正常 ({cert_path})")
            return True
        except Exception:
            log_warn(f"  ⚠️ 证书存在但 HTTPS 验证失败，尝试更新...")

    # Install
    log_info(f"  ⬇️ 安装 CA 证书到 {cert_path}...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(_CA_CERT_URL, headers={"User-Agent": "ohc/1.0"})
        data = urllib.request.urlopen(req, timeout=60, context=ctx).read()
        if b"BEGIN CERTIFICATE" not in data:
            raise ValueError("下载内容不是 PEM 证书")
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        cert_path.write_bytes(data)
        count = data.count(b"BEGIN CERTIFICATE")
        log_ok(f"  ✅ 已安装 {count} 个根证书")
        return True
    except Exception as e:
        log_fail(f"  ❌ 证书安装失败: {e}")
        log_fail(f"     手动安装: python3 scripts/install-ca-certs.py")
        return False


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

    # SSL certificates
    log_info("检查 SSL 证书...")
    cert_ok = _check_ssl_certs()
    if not cert_ok:
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
