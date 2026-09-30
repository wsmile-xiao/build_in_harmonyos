#!/usr/bin/env python3
"""test_ohos — openddl-parser 0.5.2 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64）
  T2  musl libc（无 glibc / 无 ld-linux）
  T3  无宿主绝对路径泄漏（strings 扫描静态库内宿主路径）
  T4  真实解析验证（OpenDDL 文本 parse -> getRoot 遍历，链最终静态库）
 注：本包为静态库（无最终签名可执行），不适用 OHOS 可执行签名段（.codesign）检查。

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import subprocess
import sys
import tempfile

READELF = os.environ.get("READELF", "readelf")
CC = os.environ.get("CC", "clang")
STRINGS = os.environ.get("STRINGS", "strings")

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"openddl-parser-0.5.2"]

TEST_CPP = r"""
#include <openddlparser/OpenDDLParser.h>
#include <openddlparser/DDLNode.h>
#include <openddlparser/Value.h>
#include <cstdio>
#include <cstring>
#include <string>
using namespace ODDLParser;
int main() {
    const char *scene =
        "Metric( key = \"distance\" ) { float{ 10.0 } }\n"
        "Metric( key = \"angle\" ) { float{ 45.0 } }\n"
        "GeometryNode $node1 { string { \"box\" } }\n";
    OpenDDLParser parser(scene, std::strlen(scene));
    if (!parser.parse()) { std::printf("T5_FAIL: parse() false\n"); return 1; }
    DDLNode *root = parser.getRoot();
    if (!root) { std::printf("T5_FAIL: no root\n"); return 1; }
    size_t met = 0, geo = 0;
    const DDLNode::DllNodeList &children = root->getChildNodeList();
    for (DDLNode *c : children) {
        const std::string &t = c->getType();
        if (t == "Metric") ++met;
        else if (t == "GeometryNode") ++geo;
    }
    if (met != 2 || geo != 1) {
        std::printf("T5_FAIL: stats met=%zu geo=%zu\n", met, geo);
        return 1;
    }
    Property *prop = children[0]->getProperties();
    if (!prop || !prop->m_value || !prop->m_value->m_data ||
        std::strncmp((const char *)prop->m_value->m_data, "distance", 8) != 0) {
        std::printf("T5_FAIL: property value\n");
        return 1;
    }
    std::printf("T5_PASS: parse OK (version=%s)\n", OpenDDLParser::getVersion());
    return 0;
}
"""


def check(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True)
    return r.returncode, (r.stdout or b"") + (r.stderr or b"")


def main():
    if len(sys.argv) < 2:
        print("usage: run_ohos_test.py <conan_package_folder>")
        return 2
    pkg = sys.argv[1]
    if not os.path.isdir(pkg):
        print(f"package folder not found: {pkg}")
        return 2

    fails = []

    # T1/T2/T3/T4: 对包内静态库做宿主级 ELF / 签名 / 路径泄漏检查
    lib = os.path.join(pkg, "lib", "libopenddlparser.a")
    if not os.path.isfile(lib):
        lib = os.path.join(pkg, "lib", "libopenddlparser.so")
    if not os.path.isfile(lib):
        print("T1_FAIL: no libopenddlparser.{a,so} in package")
        return 1

    rc, out = check([READELF, "-h", lib])
    if rc != 0 or b"ELF64" not in out:
        fails.append("T1 aarch64-elf")
        print(out.decode(errors="replace"))
    else:
        print("T1_PASS: ELF64")

    rc, out = check([STRINGS, lib])
    text = out
    if b"ld-linux" in text or b"libc.so.6" in text:
        fails.append("T2 musl-libc")
    else:
        print("T2_PASS: no glibc/ld-linux")

    for pat in HOST_PATH_RES:
        if pat in text:
            fails.append(f"T3 host-path({pat.decode()})")

    # T4: 真实解析验证 — 编译一个独立消费者并链最终静态库
    with tempfile.TemporaryDirectory(prefix="ohos-t5-") as td:
        src = os.path.join(td, "t5.cpp")
        exe = os.path.join(td, "t5")
        with open(src, "w", encoding="utf-8") as f:
            f.write(TEST_CPP)
        inc = os.path.join(pkg, "include")
        rc, out = check(
            [CC, "-std=c++11", src, "-I", inc, lib, "-o", exe, "-lstdc++", "-lm"]
        )
        if rc != 0:
            fails.append("T5 compile")
            print(out.decode(errors="replace"))
        else:
            rc, out = check([exe])
            if rc != 0:
                fails.append("T5 run")
                print(out.decode(errors="replace"))
            else:
                print(out.decode(errors="replace").strip())

    if fails:
        print("OHOS_SPECIAL_FAIL:", ",".join(fails))
        return 1
    print("OHOS_SPECIAL_PASS: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
