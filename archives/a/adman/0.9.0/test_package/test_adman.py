#!/usr/bin/env python3
"""adman test_package 测试脚本.

验证 adman 包可正常导入（version 模块无外部依赖——adman 完整 CLI 运行时
依赖 python-ldap/dnspython/PyYAML 为系统级模块，OHOS 沙箱未预装），
确认打包内容完整可用。

用法: python3 test_adman.py <site-packages 目录>
"""
import sys

pkg_dir = sys.argv[1]
sys.path.insert(0, pkg_dir)

from adman.version import __version__  # noqa: E402

assert __version__ == "0.9.0", f"version mismatch: {__version__}"
print("PASS: adman version OK:", __version__)
