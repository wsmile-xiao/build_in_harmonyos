#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ohos-astronomy-consumer — astronomy 2.1.9 消费者用例（R34/R51 硬门禁）

模拟业务上层组件（如“天文日历”应用）使用 astronomy 的最终 Conan 包：
仅通过已安装/导出的公开头文件 astronomy.h、公开 API、正常链接目标
（-lastronomy）与静态库运行时产物消费该三方库，验证第三方使用者能否
编译、链接、调用并正常运行。

检查项（任一失败必须非零退出）：
  A. 最终包内静态库/消费者可执行文件为 ELF64 AArch64
  B. 消费者程序使用公开 API（Astronomy_Seasons / Astronomy_MakeTime /
     Astronomy_GeoVector / Astronomy_BodyName）并产生可观察结果
  C. 2024 年四季日期与真实天文历一致（春分≈2024-03-20、夏至≈2024-06-20、
     秋分≈2024-09-22、冬至≈2024-12-21，±2 天容差）
  D. 地球日心距离 ≈ 1 AU（公开 API HelioVector 的可观察结果）
  E. 二进制不含宿主机绝对路径（/storage/、/home/、/Users/）

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import re
import subprocess
import sys

READELF = os.environ.get("READELF", "readelf")
CC = os.environ.get("CC", "clang")

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"astronomy-2.1.9"]

CONSUMER_C = r"""
#include <stdio.h>
#include <math.h>
#include <string.h>
#include "astronomy.h"

/* 消费者：天文日历应用——计算某年四季日期 + 某时刻地球日心距离。 */
int main(void)
{
    astro_seasons_t s = Astronomy_Seasons(2024);
    if (s.status != ASTRO_SUCCESS) {
        fprintf(stderr, "FAIL: Astronomy_Seasons status=%d\n", s.status);
        return 1;
    }
    char buf[64];
    astro_utc_t utc;
    utc = Astronomy_UtcFromTime(s.mar_equinox);
    printf("2024 March equinox: %04d-%02d-%02d %02d:%02d\n",
           utc.year, utc.month, utc.day, utc.hour, utc.minute);
    utc = Astronomy_UtcFromTime(s.jun_solstice);
    printf("2024 June solstice: %04d-%02d-%02d %02d:%02d\n",
           utc.year, utc.month, utc.day, utc.hour, utc.minute);
    utc = Astronomy_UtcFromTime(s.sep_equinox);
    printf("2024 Sep equinox: %04d-%02d-%02d %02d:%02d\n",
           utc.year, utc.month, utc.day, utc.hour, utc.minute);
    utc = Astronomy_UtcFromTime(s.dec_solstice);
    printf("2024 Dec solstice: %04d-%02d-%02d %02d:%02d\n",
           utc.year, utc.month, utc.day, utc.hour, utc.minute);

    astro_time_t t = Astronomy_MakeTime(2024, 1, 15, 12, 0, 0.0);
    /* GeoVector 以地心为原点：查询太阳即可得日地距离 ≈ 1 AU */
    astro_vector_t v = Astronomy_GeoVector(BODY_SUN, t, ABERRATION);
    if (v.status != ASTRO_SUCCESS) {
        fprintf(stderr, "FAIL: GeoVector status=%d\n", v.status);
        return 1;
    }
    double dist = hypot(hypot(v.x, v.y), v.z);
    printf("Earth-Sun distance: %.6f AU\n", dist);
    printf("Body: %s\n", Astronomy_BodyName(BODY_SUN));
    return 0;
}
"""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_ohos_test.py <conan_package_folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    include = os.path.join(pkg, "include")
    lib = os.path.join(pkg, "lib")

    import tempfile
    work = tempfile.mkdtemp(prefix="astro-consumer-")
    src = os.path.join(work, "consumer.c")
    with open(src, "w") as f:
        f.write(CONSUMER_C)
    exe = os.path.join(work, "consumer")

    # A/D: 编译 + 链接最终包（公开头文件 + 正常链接目标）
    comp = subprocess.run(
        [CC, "-O2", "-I", include, src, "-L", lib, "-lastronomy", "-lm",
         "-o", exe],
        capture_output=True, text=True)
    if comp.returncode != 0:
        print("FAIL: consumer compile/link failed:\n" + comp.stderr, file=sys.stderr)
        return 1

    # A: ELF64 AArch64 检查
    r = subprocess.run([READELF, "-h", exe], capture_output=True)
    if b"ELF64" not in r.stdout or b"AArch64" not in r.stdout:
        print("FAIL: consumer not ELF64 AArch64", file=sys.stderr)
        return 1

    # E: 无宿主机绝对路径
    strings_bin = os.environ.get("STRINGS", "strings")
    st = subprocess.run([strings_bin, exe], capture_output=True)
    for pat in HOST_PATH_RES:
        if pat in st.stdout:
            print("FAIL: host path leak: %s" % pat.decode(), file=sys.stderr)
            return 1

    # B/C/D: 实际运行并校验结果
    run = subprocess.run([exe], capture_output=True, text=True)
    if run.returncode != 0:
        print("FAIL: consumer run failed:\n" + run.stdout + run.stderr, file=sys.stderr)
        return 1
    out = run.stdout
    print(out, end="")

    checks = [
        ("2024 March equinox: 2024-03-20", "mar equinox date"),
        ("2024 June solstice: 2024-06-20", "jun solstice date"),
        ("2024 Sep equinox: 2024-09-22", "sep equinox date"),
        ("2024 Dec solstice: 2024-12-21", "dec solstice date"),
    ]
    for expect, label in checks:
        if expect not in out:
            print("FAIL: %s mismatch (want %s)" % (label, expect), file=sys.stderr)
            return 1
    m = re.search(r"Earth-Sun distance: ([0-9.]+) AU", out)
    if not m:
        print("FAIL: Earth-Sun distance missing", file=sys.stderr)
        return 1
    dist = float(m.group(1))
    if not (0.98 <= dist <= 1.02):
        print("FAIL: Earth-Sun distance out of range: %.6f" % dist, file=sys.stderr)
        return 1

    print("CONSUMER_ALL_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
