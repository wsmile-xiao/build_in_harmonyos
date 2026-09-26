#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fake_conan.py — dep-binary-probe 离线测试用的 conan stub（不参与生产流程）。

行为完全由"被请求的引用名"驱动，使探测分类、退出码与兜底检测都能在
无网络、无真实 conan 的条件下验证：

===================  ==================================================
goodlib/1.0.0        二进制可用（rc=0）
badlib/1.0.0         配方在仓、二进制缺失（Missing binary + 固定 package_id）
nosuchlib/1.0.0      配方缺失（检索不到）
flakylib/1.0.0       远端通道故障（remote not available）
cmake/4.4.3          作为 build 上下文工具，同样"配方在仓、二进制缺失"，
                     用于验证 --check-fallback 能识别源码兜底断裂
===================  ==================================================
"""

import json
import os
import sys

MISSING_BINARY = {
    "badlib/1.0.0": "50c1715c9d6630244edc1e29caf86880dfcc7907",
    "badlib/1.1.0": "50c1715c9d6630244edc1e29caf86880dfcc7907",  # 跨版本同 package_id
    "cmake/4.4.3": "6c4d2dcb1ee5ca8e7b6b1b7c5b2f0d9a4b3c2d1e",
}
RECIPE_MISSING = {"nosuchlib/1.0.0"}
REMOTE_ERROR = {"flakylib/1.0.0"}
# 构建上下文节点（--check-fallback 的输入）
BUILD_TOOLS = (
    ("cmake/4.4.3", "Build"),
    ("ninja/1.12.0", "Download"),
)


def _ref_of(argv):
    for arg in argv:
        if arg.startswith("--requires="):
            return arg.split("=", 1)[1]
    return ""


def main(argv):
    if argv[:2] == ["config", "home"]:
        print(os.environ.get("FAKE_CONAN_HOME", "/nonexistent/conan-home"))
        return 0
    if argv[:2] == ["remote", "add"]:
        return 0
    if argv[:1] == ["install"]:
        ref = _ref_of(argv)
        if ref in RECIPE_MISSING:
            print("ERROR: Unable to find package '%s' in remotes" % ref)
            return 1
        if ref in REMOTE_ERROR:
            print(
                "ERROR: Failed checking for binary '%s' in remote 'ohpcd': remote not available" % ref
            )
            return 1
        if ref in MISSING_BINARY:
            print("ERROR: Missing binary: %s:%s" % (ref, MISSING_BINARY[ref]))
            print("ERROR: Missing prebuilt package for '%s'" % ref)
            print("Try to build from source with 'conan install --build=missing'")
            return 1
        print("%s: Downloading package revision..." % ref)
        return 0
    if argv[:2] == ["graph", "info"]:
        ref = _ref_of(argv)
        nodes = {"0": {"ref": ref, "context": "host", "binary": "Build"}}
        for idx, (tool_ref, binary) in enumerate(BUILD_TOOLS, start=1):
            nodes[str(idx)] = {"ref": tool_ref, "context": "build", "binary": binary}
        print(json.dumps({"graph": {"nodes": nodes}}))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
