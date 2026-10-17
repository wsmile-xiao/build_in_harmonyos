#!/usr/bin/env python3
"""HarmonyOS-specific test for packaged ubelt 1.4.0 (OHOS 专项测试，数量 ≥1).

验证装机后 ubelt 在 OHOS 平台上的平台契约：
  1. 解释器平台标识：本机 CPython 3.12 报告 sys.platform == 'ohos'
     （ubuntu/linux 上为 'linux'），ubelt 必须在此标识下正常导入与工作。
  2. 平台路径分派：ubelt.util_platform 的 POSIX 判定必须为真，且
     platform_cache_dir()/platform_data_dir() 不得落入
     `raise NotImplementedError('Unknown Platform ...')` 分支。
  3. OHOS 应用沙箱：XDG_CACHE_HOME 由 OHOS 运行时注入到应用沙箱
     （/data/storage/el2/...），ub.Path.appdir() 必须落在该沙箱内。
  4. 沙箱可写：appdir 目录可真实创建与读写。

这是 OHOS 专属补充用例（上游 1.4.0 无此平台契约断言）。
用法： python3 test_ohos_ubelt.py <site-packages-dir-of-package>
"""
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

import ubelt as ub
from ubelt import util_platform as up


def main():
    # 1. 解释器平台标识
    assert sys.platform == "ohos", f"expected ohos, got {sys.platform!r}"
    print(f"  OHOS sys.platform = {sys.platform!r}")

    # 2. 平台路径分派不得抛 NotImplementedError（OHOS 取 POSIX 分支）
    assert up.POSIX is True, "ubelt.util_platform.POSIX must be True on OHOS"
    cache_dir = up.platform_cache_dir()
    data_dir = up.platform_data_dir()
    for name, val in (("platform_cache_dir", cache_dir),
                      ("platform_data_dir", data_dir)):
        assert isinstance(val, str) and val, (name, val)
        assert os.path.isabs(val), (name, val)
        print(f"  OHOS {name} -> {val}")

    # 3. XDG_CACHE_HOME 由 OHOS 运行时注入应用沙箱 → appdir 必须落在其下
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    appdir = ub.Path.appdir("ubelt/ohos-selftest")
    assert os.path.isabs(str(appdir)), appdir
    if xdg_cache:
        assert str(appdir).startswith(xdg_cache), (str(appdir), xdg_cache)
        print(f"  OHOS XDG_CACHE_HOME honoured: {xdg_cache}")

    # 4. 沙箱可写：真实建目录 + 读写
    dpath = ub.Path(str(appdir)).ensuredir()
    assert dpath.is_dir(), dpath
    fpath = dpath / "ohos_probe.txt"
    fpath.write_text("ohos")
    assert fpath.read_text() == "ohos"
    fpath.delete()
    print(f"  OHOS sandbox writable: {dpath}")

    print("ubelt 1.4.0 OHOS-specific test: PASS")


if __name__ == "__main__":
    main()
