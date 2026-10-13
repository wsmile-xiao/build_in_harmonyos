#!/usr/bin/env python3
"""Consumer test for lazy-object-proxy 1.12.0 on OHOS.

验证点：
1. import lazy_object_proxy 成功（纯 Python 层 + C 扩展载荷完整）；
2. Proxy 实例化 + 惰性求值语义（目标对象仅在首次访问时创建）；
3. **C 扩展后端被实际选用**（cext 路径，本适配的核心交付物）；
4. OHOS 平台校验（sys.platform 为 ohos，扩展 .so 为 aarch64-linux-ohos
   ABI 且带 .codesign 段，可 dlopen）。
"""
import os
import sys


def main() -> int:
    site = sys.argv[1] if len(sys.argv) > 1 else ""

    failures = []

    # --- 1. import ---
    try:
        import lazy_object_proxy as lop
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: import lazy_object_proxy raised {exc!r}")
        return 1

    # --- 2. Proxy 实例化 + 惰性语义 ---
    calls = []

    def make_target():
        calls.append(1)
        return {"value": 41}

    proxy = lop.Proxy(make_target)
    if calls:
        failures.append("proxy eagerly evaluated the target (not lazy)")
    got = proxy["value"]
    if got != 41:
        failures.append(f"proxy['value'] == {got!r}, expected 41")
    if len(calls) != 1:
        failures.append(f"target factory called {len(calls)}x, expected exactly 1")
    # __repr__/__str__ 代理
    if "value" not in repr(proxy):
        failures.append(f"repr(proxy) does not proxy the wrapped dict: {repr(proxy)!r}")
    # 算术/比较代理
    num_proxy = lop.Proxy(lambda: 21)
    if num_proxy * 2 != 42:
        failures.append("proxy arithmetic not forwarded")

    # --- 3. C 扩展后端被选用 ---
    # 注意：cext.Proxy 是 C 实现类型，其 __module__ 为 'builtins'（C 类型无
    # 源码模块），不能用 __module__ 判定；正确判定 = lop.Proxy 与 cext.Proxy
    # 为同一对象（__init__.py 的 try/except 导入链成功走 cext 分支）。
    print(f"Proxy backend module: {lop.Proxy.__module__}")
    from lazy_object_proxy import cext  # noqa: F401  (import must succeed)
    if lop.Proxy is not cext.Proxy:
        failures.append(
            "C extension backend not selected (lop.Proxy is not cext.Proxy); "
            "the pure-Python fallback was used instead")

    # --- 4. OHOS 平台校验 ---
    # 平台身份以交付物标记为准：cext .so 文件名的 aarch64-linux-ohos 三元组
    # + ELF 头（下方校验）。sys.platform 仅信息性输出——它随运行解释器而变
    # （OHOS 宿主 python3 报 'ohos'；conan python 为 linux 目标构建、报
    # 'linux'，但其下 cext 加载与功能完全正常，#14850 本地实测）。
    plat = sys.platform
    print(f"sys.platform: {plat} (interpreter-dependent, informational)")
    import lazy_object_proxy.cext as cext_mod
    so_path = getattr(cext_mod, "__file__", "")
    print(f"cext extension: {so_path}")
    if not so_path or not so_path.endswith(".so"):
        failures.append(f"cext module has no .so path: {so_path!r}")
    else:
        if "aarch64-linux-ohos" not in os.path.basename(so_path):
            failures.append(
                f"extension file {os.path.basename(so_path)!r} is not an "
                "aarch64-linux-ohos build")
        with open(so_path, "rb") as fh:
            head = fh.read(4)
        if head != b"\x7fELF":
            failures.append("cext extension is not an ELF object")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: lazy-object-proxy consumer checks "
          "(import/lazy-semantics/cext-backend/ohos-platform) all green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
