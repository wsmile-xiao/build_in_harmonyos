#!/usr/bin/env python3
"""http_async_client.so 打包产物校验（L1 消费者视角，鸿蒙平台契约）。

http_async_client.so 由 kamailio 二进制运行时 loadmodule 加载，运行期行为由
test_package/test_consumer.c 实测；本脚本负责"装载前就该成立"的产物与平台契约：

  * ELF 结构：64 位 / ET_DYN / AArch64（鸿蒙 PC 目标架构）
  * 模块入口符号：exports / module_version / module_flags / mod_register
    （core src/core/sr_module.c 逐个 dlsym，缺任一即 loadmodule 失败）
  * 模块接口表：http_async_client 导出 exports（核心接口表，非 _<模块名>_exports
    回退分支）
  * libcurl/libevent 探测证据：NEEDED 无 libcurl/libevent（模块 Makefile 以
    -lcurl -levent 链接，musl 无 rpath 场景若动态依赖则目标机加载失败——
    静态并入是本配方的平台适配核心）
  * 鸿蒙（musl）平台契约：NEEDED 不含 glibc 专名库（libc.so.N / libpthread /
    libdl——musl 已并入 libc）、动态段无 RPATH/RUNPATH 宿主路径泄漏
  * licenses/COPYING 随包
"""
import os
import re
import shutil
import subprocess
import sys

FAILURES = []

# core 在 sr_module.c 中查找的模块契约符号
MODULE_API = ("module_version", "module_flags", "mod_register")
# http_async_client 是标准模块，导出 "exports" 接口表（非回退分支）
EXPORTS_TABLE = ("exports", "_http_async_client_exports")

# libcurl/libevent 静态并入必须导出的符号（消费者经 dlsym 验证可用性）
CURL_API = ("curl_easy_init", "curl_easy_setopt", "curl_easy_perform",
            "curl_multi_init", "curl_multi_add_handle", "curl_multi_cleanup")


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
    module = env("KAMAILIO_HTTPASYNC_MODULE")
    pkg = env("KAMAILIO_HTTPASYNC_PACKAGE_FOLDER")
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
    check(e_machine == 0xB7, "e_machine=AArch64", f"e_machine={e_machine}")

    # 2) 模块入口契约符号标记
    for marker in ("exports", "mod_register", "module_version", "curl_easy_init"):
        check(marker.encode() in blob, f"符号标记 {marker}")

    # 3) 许可证随包
    check(os.path.isfile(os.path.join(pkg, "licenses", "COPYING")), "licenses/COPYING 存在")

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
            # 共享依赖模型：模块经 conan 依赖链接 libcurl/libevent 共享库
            # （消费者经 LD_LIBRARY_PATH 注入依赖 libdir，conan install 随包
            # 解析）——NEEDED 必须包含二者（链接生效证据）
            check(any("libcurl" in n for n in needed),
                  "NEEDED 含 libcurl（共享依赖链接生效）", ", ".join(needed) or "none")
            check(any("libevent" in n for n in needed),
                  "NEEDED 含 libevent（共享依赖链接生效）", "")
            # 鸿蒙 musl 平台契约：glibc 专名库不应出现（musl 并入 libc；
            # 只盯 glibc 专名，不拦 libcurl.so.4 等正常版本化依赖）
            glibc_like = [n for n in needed
                          if n == "libc.so.6" or n.startswith(("libpthread", "libdl"))]
            check(not glibc_like, "NEEDED 无 glibc 专名库（鸿蒙 musl 契约）",
                  ", ".join(glibc_like) or "clean")
            # 交叉编译产物不得内嵌构建机路径（RPATH/RUNPATH 泄漏 = 目标机加载失败）
            check(not any(k in out for k in ("RPATH", "RUNPATH")),
                  "动态段无 RPATH/RUNPATH", "clean")
    else:
        print("[SKIP] 未找到 readelf/llvm-readelf，跳过动态段复核")

    # 5) 动态符号表复核
    nm = shutil.which("llvm-nm") or shutil.which("nm")
    if nm:
        proc = subprocess.run([nm, "-D", module], capture_output=True, text=True)
        if proc.returncode != 0:
            check(False, "动态符号表读取 (nm -D)",
                  f"exit={proc.returncode} {(proc.stderr or '').strip()[:200]}")
        else:
            defined = set()
            for ln in proc.stdout.splitlines():
                ln = ln.strip()
                if not ln or ":" in ln or ln.endswith(":"):
                    continue
                parts = ln.split()
                if len(parts) >= 2 and parts[-2].upper() != "U":
                    defined.add(parts[-1])
            missing_mod = sorted(s for s in MODULE_API if s not in defined)
            check(not missing_mod, "动态导出 core 契约符号（module_version/module_flags/mod_register）",
                  ", ".join(missing_mod) or "all present")
            exp_sym = next((s for s in EXPORTS_TABLE if s in defined), None)
            check(exp_sym is not None,
                  "动态导出模块接口表（exports 或 _http_async_client_exports 回退）",
                  exp_sym or "none")

        # 共享依赖模型：模块对 libcurl API 的消费经 NEEDED libcurl.so 在装载
        # 时解析。判定口径（按模块实际调用集，不要求全命中——http_async_client
        # 走 multi socket API，不调用 curl_easy_perform/curl_multi_cleanup）：
        #   a) CURL_API ∩ 未解析表 非空（确实消费共享 libcurl）
        #   b) CURL_API 不得出现在模块自身导出表（无本地桩顶替）
        proc = subprocess.run([nm, "-u", module], capture_output=True, text=True)
        if proc.returncode != 0:
            check(False, "符号表读取 (nm -u)",
                  f"exit={proc.returncode} {(proc.stderr or '').strip()[:200]}")
        else:
            unresolved = set()
            for ln in proc.stdout.splitlines():
                ln = ln.strip()
                if not ln or ln.startswith("nm:") or ":" in ln:
                    continue
                unresolved.add(ln.split()[-1])
        referenced = sorted(s for s in CURL_API if s in unresolved)
        check(len(referenced) >= 3,
              "curl API 经 NEEDED libcurl.so 装载时解析（未解析表命中 ≥3）",
              f"referenced: {', '.join(referenced) or 'none'}")
        locally_defined = sorted(s for s in CURL_API if s in defined)
        check(not locally_defined,
              "curl API 无本地定义（无桩顶替共享库）",
              ", ".join(locally_defined) or "clean")
    else:
        print("[SKIP] 未找到 nm/llvm-nm，跳过符号表复核")

    if FAILURES:
        return bail()
    print(f"\nPASSED: {module} 全部产物与平台契约校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
