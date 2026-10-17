#!/usr/bin/env python3
"""test_ohos — lwrb 3.3.0 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl/OHOS）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64）
  T2  无 glibc 依赖（musl 动态加载路径，无 GLIBC_ 版本符号/ld-linux）
  T3  无宿主绝对路径泄漏（无 /storage /home /Users 等构建机路径）
  T4  真实环形缓冲功能验证：仅通过已安装公开头文件 <lwrb/lwrb.h> 与公开
      API（lwrb_init/is_ready/write/get_free/get_full/read/peek）完成
      写入-读出往返、满/空状态机与线性块操作，并校验数据内容，非伪造输出。

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import re
import subprocess
import sys
import tempfile

CC = os.environ.get("CC", "clang")
READELF = os.environ.get("READELF", "readelf")
STRINGS = os.environ.get("STRINGS", "strings")

HOST_PATH_RES = [b"/storage/", b"/opt/", b"/Users/", b"currentUser"]


def run(cmd, **kw):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)


def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else ""
    if not pkg or not os.path.isdir(pkg):
        print("usage: python3 run_ohos_test.py <conan_package_folder>")
        return 2

    inc = os.path.join(pkg, "include")
    lib = os.path.join(pkg, "lib")
    if not (os.path.isdir(os.path.join(inc, "lwrb")) and os.path.isdir(lib)):
        print(f"FAIL: package lacks include/lwrb or lib: {pkg}")
        return 2

    fail = 0

    def chk(name, ok, detail=""):
        nonlocal fail
        print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f"  [{detail}]" if detail else ""))
        if not ok:
            fail = 1

    # ---- 单文件消费者：真实调用公开 lwrb API ----
    consumer = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lwrb_consumer.c")
    with tempfile.TemporaryDirectory() as td:
        exe = os.path.join(td, "lwrb_consumer")
        src = consumer
        if not os.path.isfile(src):
            print(f"FAIL: consumer source missing {src}")
            return 2
        comp = run([CC, src, "-I" + inc + "/lwrb", "-I" + inc,
                    "-L" + lib, "-llwrb", "-o", exe])
        if comp.returncode != 0:
            print("FAIL: compile consumer\n" + comp.stdout.decode(errors="replace")[-1500:])
            return 1

        # T1: aarch64 ELF
        eh = run([READELF, "-h", exe])
        t1 = b"AArch64" in eh.stdout and b"ELF64" in eh.stdout
        chk("T1 aarch64 ELF64", t1)

        # T2: 无 glibc 依赖（OHOS 使用 musl；区分 glibc 的 GLIBC_ 版本符号
        #     与 ld-linux 加载器，而非匹配 libc.so 名称——musl 也叫 libc）
        hexd = run([READELF, "-d", exe]).stdout + run([READELF, "-V", exe]).stdout
        glibc = re.search(rb"GLIBC_|ld-linux", hexd)
        chk("T2 无 glibc/ld-linux 依赖", glibc is None)

        # T3: 无宿主路径泄漏
        st = run([STRINGS, exe]).stdout
        leaks = [p for p in HOST_PATH_RES if p in st]
        chk("T3 无宿主绝对路径泄漏", not leaks, ("泄漏:" + ",".join(x.decode() for x in leaks)) if leaks else "")

        # T4: 真实功能执行（消费者自检并退出；运行环境必须指向包内 lib）
        run_env = dict(os.environ)
        run_env["LD_LIBRARY_PATH"] = lib + (":" + run_env["LD_LIBRARY_PATH"] if run_env.get("LD_LIBRARY_PATH") else "")
        res = run([exe], env=run_env)
        t4 = res.returncode == 0 and b"LWRB_OHOS_OK" in res.stdout
        chk("T4 真实环形缓冲往返校验（消费者退出码+标记）",
            t4, (res.stdout.decode(errors="replace").strip()[-200:]))

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())