#!/usr/bin/env python3
"""test_ohos — atomix 0.0-git7c75a1602e HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64）
  T2  musl libc（无 glibc / 无 ld-linux）
  T3  .codesign 段存在（OHOS 签名管线产出）
  T4  无宿主绝对路径泄漏（含 RPATH/RUNPATH 检查）
  T5  真实混音计算（构建声道数据 -> 播放 -> 混音 -> 停止淡出断言，
       仅依赖包内安装的公开头文件 atomix.h 与标准库，非伪造输出）

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

READELF = os.environ.get("READELF", "readelf")
# 优先解析真实可用的编译器：环境 CC 若只是裸名且不在 PATH 则回退到
# OHOS SDK 完整路径（本机已导出 CC=clang，须先验证 which 可解析）
def _resolve_cc():
    cc = os.environ.get("CC", "")
    if cc:
        resolved = shutil.which(cc)
        if resolved:
            return resolved
    ohos_cc = "/data/service/hnp/bin/clang"
    if os.path.exists(ohos_cc):
        return ohos_cc
    return cc or "clang"


CC = _resolve_cc()
STRINGS = os.environ.get("STRINGS", "strings")


def _resolve_tool(env_name, default):
    t = os.environ.get(env_name, default)
    if t:
        resolved = shutil.which(t)
        if resolved:
            return resolved
    for cand in ("/data/service/hnp/bin/" + default, default):
        if os.path.exists(cand):
            return cand
    return t or default


READELF = _resolve_tool("READELF", "readelf")
STRINGS = _resolve_tool("STRINGS", "strings")

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"atomix-0.0-git7c75a1602e"]

TEST_C = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ATOMIX_STATIC
#define ATOMIX_NO_SSE
#include "atomix.h"

static int run_checks(void)
{
    const int32_t frames = 4096;
    float *samples = (float *)calloc((size_t)frames * 2, sizeof(float));
    if (!samples) return 1;
    for (int32_t i = 0; i < frames; ++i) {
        samples[i * 2]     = 0.25f;
        samples[i * 2 + 1] = 0.25f;
    }

    struct atomix_sound *snd = atomixSoundNew(2, samples, frames);
    if (!snd) { free(samples); return 2; }
    if (atomixSoundLength(snd) <= 0) { free(samples); return 3; }

    struct atomix_mixer *mix = atomixMixerNew(1.0f, 64);
    if (!mix) { free(samples); return 4; }

    uint32_t id = atomixMixerPlay(mix, snd, ATOMIX_PLAY, 1.0f, 0.0f);
    if (id == 0) { free(samples); return 5; }

    /* 混音一帧：必须有可听输出。
     * 注意：fnum 是帧数，双声道每帧 2 个 float，故 512 帧需 1024 float 缓冲 */
    float out[1024];
    memset(out, 0, sizeof(out));
    if (atomixMixerMix(mix, out, 512) != 512) { free(samples); return 6; }
    int audible = 0;
    for (int i = 0; i < 1024; ++i)
        if (out[i] != 0.0f) { audible = 1; break; }
    if (!audible) { free(samples); return 7; }

    /* 停止 -> 淡出(64帧)过后必须全静音 */
    atomixMixerStopAll(mix);
    (void)atomixMixerMix(mix, out, 512);
    memset(out, 0, sizeof(out));
    (void)atomixMixerMix(mix, out, 512);
    for (int i = 0; i < 1024; ++i)
        if (out[i] != 0.0f) { free(samples); return 8; }

    /* gain/pan 合法性 */
    if (atomixMixerSetGainPan(mix, id, 0.5f, -1.0f) != 0) { free(samples); return 9; }

    free(samples);
    return 0;
}

int main(void)
{
    int rc = run_checks();
    printf("atomix T5: mixing checks %s\n", rc == 0 ? "PASS" : "FAIL");
    return rc;
}
"""


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print("usage: run_ohos_test.py <conan_package_folder>")
        sys.exit(2)
    pkg = os.path.abspath(sys.argv[1])
    include = os.path.join(pkg, "include")
    if not os.path.isfile(os.path.join(include, "atomix.h")):
        fail(f"package include atomix.h missing under {pkg}")

    # T5: 真实混音计算（链包内公开头文件，aarch64 消费者可执行文件）
    with tempfile.TemporaryDirectory(prefix="ohos") as td:
        src = os.path.join(td, "t5.c")
        exe = os.path.join(td, "t5_atomix")
        with open(src, "w") as f:
            f.write(TEST_C)
        c = run([CC, "-O2", "-I", include, src, "-o", exe])
        if c.returncode != 0:
            fail(f"T5 compile failed rc={c.returncode}: {c.stderr.decode(errors='replace')}")
        r = run([exe])
        if r.returncode != 0:
            fail(f"T5 runtime failed rc={r.returncode}: {r.stdout.decode(errors='replace')}")
        print(f"T5 PASS: {r.stdout.decode(errors='replace').strip()}")

        # T1: ELF64 AArch64
        e = run([READELF, "-h", exe])
        elf = e.stdout.decode(errors="replace")
        if "ELF64" not in elf or "AArch64" not in elf:
            fail(f"T1 not aarch64 ELF: {elf.splitlines()[0] if elf else 'no readelf -h'}")
        print("T1 PASS: ELF64 AArch64")

        # T2: musl, no glibc/ld-linux
        dyn = run([READELF, "-l", exe]).stdout.decode(errors="replace")
        if "ld-linux" in dyn:
            fail("T2 ld-linux interpreter present")
        st = run([STRINGS, exe]).stdout
        if b"GLIBC_" in st:
            fail("T2 GLIBC symbol version found")
        if b"/lib64/" in st or b"ld-linux" in st:
            fail("T2 glibc loader paths found")
        print("T2 PASS: musl (no glibc/ld-linux)")

        # T3: .codesign section (OHOS signing pipeline)
        s = run([READELF, "-S", exe]).stdout.decode(errors="replace")
        if ".codesign" not in s:
            fail("T3 .codesign section missing")
        print("T3 PASS: .codesign present")

        # T4: no host path leaks / RPATH-RUNPATH
        so = run([READELF, "-d", exe]).stdout
        if b"RPATH" in so or b"RUNPATH" in so:
            fail("T4 RPATH/RUNPATH present")
        for pat in HOST_PATH_RES:
            if pat in st:
                fail(f"T4 host path leak: {pat.decode()}")
        print("T4 PASS: no host paths, no RPATH/RUNPATH")

    print("ALL OHOS CHECKS PASS")


if __name__ == "__main__":
    main()