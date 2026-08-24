#!/usr/bin/env python3
"""urllib3 consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — urllib3 PoolManager + request
against a local HTTPS server? No network on OHOS CI — use the
HTTPResponse/urlopen parser (pure user-space) instead.

Usage: test_urllib3.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "urllib3")):
        raise AssertionError(f"urllib3 package missing in {site}")
    sys.path.insert(0, site)
    # R34: 真实调用被测库 API（纯用户态——解析 HTTP 响应/URL 工具）
    import urllib3
    from urllib3.util.url import parse_url
    from urllib3.response import HTTPResponse
    from urllib3._collections import HTTPHeaderDict

    # URL 解析
    u = parse_url("https://example.com/path?a=1")
    if u.host != "example.com" or u.path != "/path":
        raise AssertionError(f"unexpected parse_url: {u!r}")
    # HTTPResponse 解析（模拟 200 响应——urllib3 2.7.0 用 .data 属性
    # 取 body（实测 read() 在未解码流时返回 None，.data 正确返回））
    resp = HTTPResponse(body=b"hello world", status=200,
                        headers=HTTPHeaderDict({"Content-Type": "text/plain"}),
                        preload_content=True)
    if resp.status != 200:
        raise AssertionError("unexpected status")
    if resp.data != b"hello world":
        raise AssertionError(f"unexpected body: {resp.data!r}")
    # 版本
    if not urllib3.__version__.startswith("2."):
        raise AssertionError(f"unexpected version: {urllib3.__version__}")
    print(f"OK: urllib3 {urllib3.__version__} (parse_url + HTTPResponse ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
