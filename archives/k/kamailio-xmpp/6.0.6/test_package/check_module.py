#!/usr/bin/env python3
"""xmpp.so 打包产物校验（L1 消费者视角，鸿蒙平台契约）。

xmpp.so 由 kamailio 二进制运行时 loadmodule 加载，运行期行为由
test_package/test_consumer.c 实测；本脚本负责「装载前就该成立」的产物与平台契约：

  * ELF 结构：64 位 / ET_DYN / AArch64（鸿蒙 PC 目标架构）                    [H]
  * 模块入口符号：exports / module_version / module_flags
    （core src/core/sr_module.c 逐个 dlsym；mod_register 为可选符号，缺省即跳过）
  * 装载契约串：SER_FULL_VERSION="kamailio 6.0.6 (aarch64/linux)" 与
    SER_COMPILE_FLAGS（USE_TCP 在、USE_SCTP 不在、HAVE_RESOLV_RES 不在）
    —— core 侧对二者做严格 strcmp，口径不符即拒绝加载                     [H]
  * expat 链接证据：DT_NEEDED 含 libexpat.so + 未解析表命中外链 XML_* API，
    且模块自身不定义 XML_*（无本地桩顶替共享库）
  * 鸿蒙（musl）平台契约：NEEDED 不含 glibc 专名库（libc.so.N / libpthread /
    libdl——musl 已并入 libc）；NEEDED 全为裸文件名（无绝对路径 = 可重定位）；
    动态段无 RPATH/RUNPATH（交叉产物不得内嵌构建机路径）                    [H]
  * licenses/COPYING 与模块 README 文档随包
"""
import os
import re
import shutil
import subprocess
import sys

FAILURES = []

# core 在 sr_module.c 中查找的模块契约符号（mod_register 为可选，dlsym 失败即跳过）
MODULE_API = ("module_version", "module_flags")
EXPORTS_TABLE = ("exports", "_xmpp_exports")

# expat API：模块内部 XMPP stanza 解析（xode）真实调用集
EXPAT_API = ("XML_ParserCreate", "XML_Parse", "XML_SetElementHandler",
             "XML_SetCharacterDataHandler", "XML_ParserFree",
             "XML_GetErrorCode", "XML_ErrorString", "XML_SetUserData")

# 期望的装载契约串（core/sr_module.c strcmp 项，实测 core 侧同值）
EXPECTED_VERSION = "kamailio 6.0.6 (aarch64/linux)"


def check(cond, label, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(label)


def env(name):
    val = os.environ.get(name)
    if not val:
        check(False, f"环境变量 {name}",
              "未注入（检查 test_package/conanfile.py 的 Environment 定义）")
    return val


def bail():
    print(f"\nFAILED: {len(FAILURES)} 项 — {FAILURES}")
    return 1


def main():
    module = env("KAMAILIO_XMPP_MODULE")
    pkg = env("KAMAILIO_XMPP_PACKAGE_FOLDER")
    if FAILURES:
        return bail()

    if not os.path.isfile(module):
        check(False, "产物存在", f"{module} 不存在")
        return bail()

    with open(module, "rb") as fh:
        blob = fh.read()
    print(f"artifact: {module} ({len(blob)} bytes)")

    if len(blob) < 64:
        check(False, "ELF 头长度", f"{len(blob)} 字节 < 64 字节（截断或空产物）")
        return bail()

    # 1) ELF 结构
    check(blob[:4] == b"\x7fELF", "ELF 魔数")
    check(blob[4] == 2, "ELFCLASS64", f"ei_class={blob[4]}")
    e_type = int.from_bytes(blob[16:18], "little")
    check(e_type == 3, "ET_DYN（共享对象）", f"e_type={e_type}")
    e_machine = int.from_bytes(blob[18:20], "little")
    check(e_machine == 0xB7, "[H] e_machine=AArch64（鸿蒙 PC 目标架构）",
          f"e_machine={e_machine}")

    # 2) 装载契约串（core 严格 strcmp 项）
    check(EXPECTED_VERSION.encode() in blob,
          "[H] 目标标识 kamailio 6.0.6 (aarch64/linux)（core 装载 strcmp 项）")
    version_ok = b"USE_TCP" in blob and b"F_MALLOC" in blob
    no_sctp = b"USE_SCTP" not in blob
    no_resolv_res = b"HAVE_RESOLV_RES" not in blob
    check(version_ok,
          "[H] 编译标志串含 USE_TCP/F_MALLOC（core 同口径构建设置存在）")
    check(no_sctp,
          "[H] 编译标志串不含 USE_SCTP（OHOS sysroot 无 netinet/sctp.h）")
    check(no_resolv_res,
          "[H] 编译标志串不含 HAVE_RESOLV_RES（OHOS libc 无 _res）")

    # 3) 许可证与文档随包
    check(os.path.isfile(os.path.join(pkg, "licenses", "COPYING")), "licenses/COPYING 存在")
    check(os.path.isfile(os.path.join(pkg, "share", "kamailio", "doc", "xmpp", "README")),
          "share/kamailio/doc/xmpp/README 存在")

    # 4) 动态段复核
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    needed = []
    if readelf:
        proc = subprocess.run([readelf, "-d", module], capture_output=True, text=True)
        if proc.returncode != 0:
            check(False, "动态段读取 (readelf -d)",
                  f"exit={proc.returncode} {(proc.stderr or '').strip()[:200]}")
        else:
            out = proc.stdout
            needed = [ln.split("[")[-1].rstrip("] \n") for ln in out.splitlines()
                      if "NEEDED" in ln]
            check(any(n == "libexpat.so" for n in needed),
                  "NEEDED 含 libexpat.so（expat 依赖链接生效）", ", ".join(needed) or "none")
            # 鸿蒙 musl 平台契约：glibc 专名库不应出现
            glibc_like = [n for n in needed
                          if n == "libc.so.6" or n.startswith(("libpthread", "libdl"))]
            check(not glibc_like, "[H] NEEDED 无 glibc 专名库（鸿蒙 musl 契约）",
                  ", ".join(glibc_like) or "clean")
            # NEEDED 必须为裸文件名：绝对/相对路径 = 绑定构建机目录结构，换环境即加载失败
            nonbare = [n for n in needed if "/" in n]
            check(not nonbare, "[H] NEEDED 全为裸文件名（可重定位，无绝对路径烤死）",
                  ", ".join(nonbare) or "clean")
            check("libc.so" in needed, "[H] NEEDED 含 libc.so（musl 统一 libc）",
                  ", ".join(needed) or "none")
            check(not any(k in out for k in ("RPATH", "RUNPATH")),
                  "[H] 动态段无 RPATH/RUNPATH（无构建机路径泄漏）", "clean")
    else:
        print("[SKIP] 未找到 readelf/llvm-readelf，跳过动态段复核")

    # 5) 动态符号表复核
    nm = shutil.which("llvm-nm") or shutil.which("nm")
    if nm:
        proc = subprocess.run([nm, "-D", module], capture_output=True, text=True)
        defined = set()
        if proc.returncode != 0:
            check(False, "动态符号表读取 (nm -D)",
                  f"exit={proc.returncode} {(proc.stderr or '').strip()[:200]}")
        else:
            for ln in proc.stdout.splitlines():
                ln = ln.strip()
                if not ln or ln.endswith(":"):
                    continue
                parts = ln.split()
                if len(parts) >= 2 and parts[-2].upper() != "U":
                    defined.add(parts[-1])
            missing_mod = sorted(s for s in MODULE_API if s not in defined)
            check(not missing_mod, "动态导出 core 契约符号（module_version/module_flags）",
                  ", ".join(missing_mod) or "all present")
            exp_sym = next((s for s in EXPORTS_TABLE if s in defined), None)
            check(exp_sym is not None,
                  "动态导出模块接口表（exports 或 _xmpp_exports 回退）", exp_sym or "none")

        # expat 消费口径：模块确实使用共享 libexpat（未解析表命中 + 自身不定义 XML_*）
        proc = subprocess.run([nm, "-u", module], capture_output=True, text=True)
        if proc.returncode != 0:
            check(False, "符号表读取 (nm -u)",
                  f"exit={proc.returncode} {(proc.stderr or '').strip()[:200]}")
        else:
            unresolved = set()
            for ln in proc.stdout.splitlines():
                ln = ln.strip()
                if not ln or ln.startswith("nm:") or ln.endswith(":"):
                    continue
                unresolved.add(ln.split()[-1])
            referenced = sorted(s for s in EXPAT_API if s in unresolved)
            check(len(referenced) >= 3,
                  "expat API 经 NEEDED libexpat.so 装载时解析（未解析表命中 ≥3）",
                  f"referenced: {', '.join(referenced) or 'none'}")
            locally_defined = sorted(s for s in EXPAT_API if s in defined)
            check(not locally_defined,
                  "expat API 无本地定义（无桩顶替共享库）",
                  ", ".join(locally_defined) or "clean")
    else:
        print("[SKIP] 未找到 nm/llvm-nm，跳过符号表复核")

    if FAILURES:
        return bail()
    print(f"\nPASSED: {module} 全部产物与平台契约校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
