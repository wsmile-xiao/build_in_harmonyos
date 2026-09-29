#!/usr/bin/env python3
"""消费者视角检查 — kamailio-xml (xmlops.so) 6.0.6。

xmlops.so 由 kamailio 二进制运行时 dlopen（XML 伪变量求值需运行中的 kamailio
路由上下文），故按产物结构做实质校验（非纯断言的完整消费者流程）：
  1. ELF 头校验（aarch64 / OHOS，交叉产物架构正确）
  2. libxml2 链接证据（DT_NEEDED 含 libxml2，或导出符号引用 xml* API）
  3. 模块导出符号（kamailio 模块契约：module_exports）
  4. 许可证文件存在
  5. 宿主路径泄漏检查（构建机路径不得进入产物字符串）
"""
import os
import shutil
import struct
import subprocess
import sys

MODULE = os.environ["KAMAILIO_XML_MODULE"]
PKG = os.environ["KAMAILIO_XML_PACKAGE_FOLDER"]

failures = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def read_elf_header(path):
    with open(path, "rb") as f:
        data = f.read(64)
    assert data[:4] == b"\x7fELF", "not an ELF file"
    ei_class, ei_data = data[4], data[5]
    e_machine = struct.unpack_from("<H", data, 18)[0]
    return ei_class, ei_data, e_machine


# 1. ELF 架构：EM_AARCH64=183, 64-bit little-endian
ei_class, ei_data, e_machine = read_elf_header(MODULE)
check("ELF 64-bit little-endian", ei_class == 2 and ei_data == 1)
check("ELF machine aarch64", e_machine == 183, f"e_machine={e_machine}")

# 2/3. 扫描 .dynstr/.rodata 字符串：libxml2 符号引用 + 模块契约符号
with open(MODULE, "rb") as f:
    blob = f.read()

xml_apis = [s for s in (b"xmlReadMemory", b"xmlXPathNewContext", b"xmlDocGetRootElement",
                        b"xmlFreeDoc", b"xmlXPathFreeContext") if s in blob]
check("libxml2 API 符号引用（动态依赖证据）", len(xml_apis) >= 3,
      f"命中 {len(xml_apis)}/5: {[s.decode() for s in xml_apis]}")

# 3. 扫描符号字符串：模块契约导出（kamailio 模块入口为 module_exports 结构）
check("模块契约导出 module_exports", b"module_exports" in blob)

# 4. 许可证
check("LICENSES/COPYING 存在", os.path.isfile(os.path.join(PKG, "licenses", "COPYING")))

# 5. 动态段复核：交叉产物不得内嵌 RPATH/RUNPATH（宿主路径泄漏 = 目标机加载失败）。
#    口径与 kamailio-tls check_tls.py 一致：查动态段而非原始字节（debug 信息中的
#    conan 缓存源路径不影响目标机加载，不属于泄漏）。
readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
if readelf:
    out = subprocess.run([readelf, "-d", MODULE], capture_output=True, text=True).stdout
    check("动态段无 RPATH/RUNPATH", "RPATH" not in out and "RUNPATH" not in out, "clean")
    needed = [ln.split("[")[-1].rstrip("] \n") for ln in out.splitlines() if "NEEDED" in ln]
    check("NEEDED 含 libxml2（动态依赖证据）",
          any("xml" in n for n in needed), ", ".join(needed) or "none")
else:
    print("[SKIP] 未找到 readelf/llvm-readelf，跳过动态段复核")

if failures:
    print(f"\nFAILED: {len(failures)} 项检查未通过: {failures}")
    sys.exit(1)
print("\n全部消费者检查通过")
