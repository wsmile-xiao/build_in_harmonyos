#!/usr/bin/env python3
"""安装 Mozilla CA 证书到 HarmonyOS Python 环境。

问题：鸿蒙 Python (OpenSSL) 编译时硬编码了证书路径但未提供证书文件，
导致所有 HTTPS 请求报 CERTIFICATE_VERIFY_FAILED。

解决：从 curl.se 下载 Mozilla CA Root 证书包，放到 OpenSSL 期望的位置。

用法：
    python3 scripts/install-ca-certs.py          # 安装
    python3 scripts/install-ca-certs.py --verify  # 仅验证
"""
import os
import ssl
import sys
import urllib.request
from pathlib import Path

CERT_URL = "https://curl.se/ca/cacert.pem"
CERT_PATH = "/storage/Users/currentUser/usr/local/ssl/cert.pem"


def install(force: bool = False) -> int:
    target = Path(CERT_PATH)
    openssl_dir = ssl.get_default_verify_paths().openssl_cafile

    # Check if already installed
    if target.exists() and not force:
        size = target.stat().st_size
        print(f"✅ 证书已存在: {target} ({size} 字节)")
        return verify()

    print(f"📍 目标路径: {target}")
    print(f"📍 OpenSSL 期望: {openssl_dir}")

    # Download with SSL-verify disabled (chicken-and-egg)
    print(f"⬇️  下载 Mozilla CA 证书包...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(CERT_URL, headers={"User-Agent": "ohc/1.0"})
        data = urllib.request.urlopen(req, timeout=60, context=ctx).read()
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        print(f"   手动下载: curl -ksSL -o {target} {CERT_URL}")
        return 1

    # Validate it looks like a PEM cert bundle
    head = data[:200].decode("utf-8", errors="ignore")
    if "BEGIN CERTIFICATE" not in data.decode("utf-8", errors="ignore"):
        print(f"❌ 下载内容不像 PEM 证书")
        return 1

    # Write
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    count = data.count(b"BEGIN CERTIFICATE")
    print(f"✅ 已安装 {count} 个根证书到 {target} ({len(data)} 字节)")

    return verify()


def verify() -> int:
    """验证证书是否生效。"""
    print(f"\n🔍 验证...")
    p = ssl.get_default_verify_paths()
    exists = Path(p.openssl_cafile or "").exists() if p.openssl_cafile else False
    print(f"   openssl_cafile: {p.openssl_cafile} {'✅' if exists else '❌'}")

    if not exists:
        print(f"❌ 证书文件不存在")
        return 1

    # Test HTTPS
    test_urls = [
        "https://ftp.gnu.org/",
        "https://github.com/",
        "https://pypi.org/",
    ]
    ok = 0
    for url in test_urls:
        try:
            urllib.request.urlopen(url, timeout=10)
            print(f"   {url} ✅")
            ok += 1
        except Exception as e:
            print(f"   {url} ❌ {e}")

    if ok == len(test_urls):
        print(f"\n✅ 全部验证通过 ({ok}/{len(test_urls)})")
        return 0
    else:
        print(f"\n⚠️ 部分验证失败 ({ok}/{len(test_urls)})")
        return 1


def main() -> int:
    if "--verify" in sys.argv:
        return verify()
    force = "--force" in sys.argv
    return install(force)


if __name__ == "__main__":
    sys.exit(main())
