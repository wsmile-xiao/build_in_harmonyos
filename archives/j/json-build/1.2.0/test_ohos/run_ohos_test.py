#!/usr/bin/env python3
"""test_ohos — json-build 1.2.0 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
区别于上游内置自测（test/test.c, test_auto.c）与 test_package 消费者用例：

  T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64 PIE）
  T2  musl libc（无 glibc / 无 ld-linux，符合 OHOS 运行时）
  T3  .codesign 段存在（OHOS 签名管线产出，可执行的前提）
  T4  无宿主绝对路径泄漏（含 RPATH/RUNPATH 检查）
  T5  真实 JSON 序列化验证：仅通过公开头文件 json-build.h 与 jsonb_*
      公开 API 构造嵌套对象/数组并校验输出字符串（非伪造输出）

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

def _which(name, candidates):
    """Find an executable: prefer existing absolute candidates, then the env
    value (resolved via shutil.which), then a bare-name fallback.

    NOTE: HMDFS 上 os.access(X_OK) 恒为 False（E046/R49），因此这里只做
    isfile 存在性判断不做可执行位判断；实际执行失败会由 subprocess 报错。
    """
    for c in candidates:
        if os.path.isfile(c):
            return c
    env_val = os.environ.get(name)
    if env_val:
        found = shutil.which(env_val)
        if found:
            return found
        return env_val
    found = shutil.which(name.lower())
    return found or candidates[0]


CC = _which("CC", ["/data/service/hnp/bin/clang", "clang"])
READELF = _which("READELF", ["/data/service/hnp/bin/readelf", "readelf"])
STRINGS = _which("STRINGS", ["/data/service/hnp/bin/strings", "strings"])

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"json-build-1.2.0"]

TEST_C = r"""
#include <stdio.h>
#include <string.h>
#include "json-build.h"

int main(void)
{
    jsonb b;
    char buf[1024];

    jsonb_init(&b);
    jsonb_object(&b, buf, sizeof(buf));
    {
        jsonb_key(&b, buf, sizeof(buf), "foo", strlen("foo"));
        jsonb_array(&b, buf, sizeof(buf));
        {
            jsonb_number(&b, buf, sizeof(buf), 1);
            jsonb_string(&b, buf, sizeof(buf), "hi", 2);
            jsonb_bool(&b, buf, sizeof(buf), 0);
            jsonb_null(&b, buf, sizeof(buf));
            jsonb_array_pop(&b, buf, sizeof(buf));
        }
        jsonb_object_pop(&b, buf, sizeof(buf));
    }

    if (strcmp(buf, "{\"foo\":[1,\"hi\",false,null]}") != 0) {
        fprintf(stderr, "FAIL: unexpected JSON output: %s\n", buf);
        return 1;
    }
    printf("json-build OHOS test OK: %s\n", buf);
    return 0;
}
"""


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else ""
    if not pkg or not os.path.isdir(pkg):
        print("usage: run_ohos_test.py <conan_package_folder>")
        return 2

    include = os.path.join(pkg, "include")
    if not os.path.isdir(include):
        # header-only 配方可能把头文件放在包根（includedirs=["."]）
        include = pkg
    header = os.path.join(include, "json-build.h")
    if not os.path.isfile(header):
        print("FAIL: json-build.h not found in package")
        return 2

    fail = 0

    def chk(name, ok):
        nonlocal fail
        print(("PASS" if ok else "FAIL") + ": " + name)
        if not ok:
            fail = 1

    print(f"--- json-build 1.2.0 HarmonyOS 专项验证 (pkg={pkg}) ---")

    # T1: aarch64 ELF
    with tempfile.TemporaryDirectory() as tmp:
        exe = os.path.join(tmp, "test_json_build")
        src = os.path.join(tmp, "test.c")
        with open(src, "w", encoding="utf-8") as f:
            f.write(TEST_C)
        cc = run([CC, "-std=c89", "-Wall", "-Wextra", "-Wpedantic",
                  "-I", include, src, "-o", exe])
        if cc.returncode != 0:
            print(cc.stderr.decode("utf-8", "replace"))
            chk("T5 编译消费者程序", False)
            return 1
        with open(exe, "rb") as f:
            elf_head = f.read(20)
        if elf_head[:4] == b"\x7fELF":
            # ELF class: 2 = ELF64, machine: 183 (0xB7) = AArch64
            elf_class = elf_head[4]
            elf_machine = elf_head[18] | (elf_head[19] << 8)
            chk("T1 aarch64 ELF (ELF64 AArch64)",
                elf_class == 2 and elf_machine == 183)
        else:
            chk("T1 aarch64 ELF (ELF64 AArch64)", False)

        # T2: musl libc（无 glibc / 无 ld-linux）
        dyn = run([READELF, "-d", exe])
        dyn_txt = dyn.stdout + dyn.stderr
        has_glibc = b"libc.so.6" in dyn_txt or b"ld-linux" in dyn_txt
        chk("T2 musl libc（无 glibc/ld-linux）", not has_glibc)

        # T3: .codesign 段存在（OHOS 签名管线）
        sec = run([READELF, "-S", exe])
        chk("T3 .codesign 段存在", b".codesign" in (sec.stdout + sec.stderr))

        # T4: 无宿主绝对路径泄漏
        strs = run([STRINGS, exe])
        leaks = [p for p in HOST_PATH_RES if p in strs.stdout]
        chk("T4 无宿主绝对路径泄漏", not leaks)

        # T5: 真实 JSON 序列化验证（运行消费者程序并核对输出）
        if elf_machine == 183:
            out = run([exe])
        else:
            qemu = os.environ.get("QEMU", "qemu-aarch64")
            out = run([qemu, exe])
        ok = (out.returncode == 0 and
              b'json-build OHOS test OK: {"foo":[1,"hi",false,null]}' in out.stdout)
        if not ok:
            print(out.stdout.decode("utf-8", "replace"))
            print(out.stderr.decode("utf-8", "replace"))
        chk("T5 真实 JSON 序列化验证", ok)

    print(f"--- json-build OHOS 专项: {('ALL PASS' if fail == 0 else 'FAILED')} ---")
    return fail


if __name__ == "__main__":
    sys.exit(main())
