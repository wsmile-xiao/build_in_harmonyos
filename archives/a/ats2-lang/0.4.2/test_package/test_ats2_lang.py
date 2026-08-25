#!/usr/bin/env python3
"""ats2-lang consumer test (L0c + R34): standalone test source
executed via self.run from conanfile.py test().

R34: verify the packaged libats runtime is complete and linkable —
  1. libatslib.a exists and contains key runtime symbols
     (ATSLIB_056_prelude__fileref_get_file_charlst — required by
     compiled ATS programs, previously verified as the missing link)
  2. prelude/libats SATS+DATS headers exist (patscc needs them to
     compile ATS programs)
Note: no host ATS compiler is assumed (the package is the runtime
only) — the linkability check uses nm on the packaged static lib.

Usage: test_ats2_lang.py <patshome> <libdir>
"""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <patshome> <libdir>", file=sys.stderr)
        return 2
    patshome, libdir = sys.argv[1], sys.argv[2]
    lib = os.path.join(libdir, "libatslib.a")
    if not os.path.isfile(lib):
        raise AssertionError(f"libatslib.a missing in {libdir}")
    # R34: libatslib.a 含关键运行时符号（ATS 编译程序链接必需）
    # OHOS 的 nm 在 /data/service/hnp/bin/（PATH 未含——实测
    # FileNotFoundError: 'nm'）——用绝对路径
    nm_cmd = "/data/service/hnp/bin/nm"
    if not os.path.isfile(nm_cmd):
        raise AssertionError(f"nm not found: {nm_cmd}")
    nm = subprocess.run([nm_cmd, lib], capture_output=True, text=True,
                        timeout=60)
    if nm.returncode != 0:
        raise AssertionError(f"nm failed on {lib}: {nm.stderr[:200]}")
    # 关键符号：prelude 运行时节（ATSLIB_056_prelude__*——链接缺失会
    # 导致 'undefined symbol' 实测）——检查一组代表性定义符号
    key = "ATSLIB_056_prelude__fileref_get_file_charlst"
    if key not in nm.stdout:
        raise AssertionError(f"missing runtime symbol {key} in {lib}")
    # prelude/libats 头存在（patscc 编译 ATS 程序时经 PATSHOME 定位）
    for d in ("prelude", "libats"):
        if not os.path.isdir(os.path.join(patshome, d)):
            raise AssertionError(f"{d} missing in {patshome}")
    # 代表性头文件（prelude SATS + libats——stdio.sats 在
    # libats/libc/SATS/、float.sats 在 libats/SATS/Number/（实测位置））
    for h in ("prelude/SATS/list.sats", "libats/libc/SATS/stdio.sats",
              "libats/SATS/Number/float.sats"):
        if not os.path.isfile(os.path.join(patshome, h)):
            raise AssertionError(f"header missing: {h}")
    # review 建议（atomgit-bot Medium）：实际执行链接+运行——最小 C
    # 消费者引用 libatslib.a 的运行时符号（clang 编译链接——运行断言）
    # ——libatslib.a 可链接性 + 运行时可用性（不只符号/头文件存在）
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        csrc = os.path.join(td, "consumer.c")
        with open(csrc, "w") as f:
            f.write(f'''#include <stdio.h>
#include <stdlib.h>
/* 实际引用 libatslib.a 的运行时符号（review：不引用则 --as-needed 丢弃
   归档——链接成功只证明 clang 可用）——取地址强制链接器拉取归档成员——
   真实链接 libatslib.a（nm 确认该符号存在） */
extern void {key}(void);
/* libatslib.a 的未定义符号（nm -u 确认仅 3 个 ATS 运行时外部符号——
   ATS 编译器链接时补全——这里提供真实定义（malloc/free/realloc 包装）
   ——--defsym 的 VALUE 是表达式非符号别名（=malloc 求值报 symbol not
   found 实测）——源码定义才正确 */
void *atsruntime_malloc_undef(size_t n) {{ return malloc(n); }}
void atsruntime_mfree_undef(void *p) {{ free(p); }}
void *atsruntime_realloc_undef(void *p, size_t n) {{ return realloc(p, n); }}
int main(void) {{
    void *p = (void *)&{key};
    printf("ats2-lang consumer link-ok %p\\n", p);
    return 0;
}}
''')
        exe = os.path.join(td, "consumer")
        clang = "/data/service/hnp/bin/clang"
        # LD_LIBRARY_PATH 加 OHOS SDK llvm/lib（clang 默认链接器 lld 依赖
        # libxml2.so.16——CI 'Error loading shared library libxml2.so.16'
        # 实测（同 numpy #6386 根因）——加载成功才不崩溃）
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:"
            + env.get("LD_LIBRARY_PATH", ""))
        cc = subprocess.run(
            # C 消费者源码定义 atsruntime_*_undef（malloc/free/realloc 包装）
            # ——链接器解析 libatslib.a 的未定义符号——真实链接
            [clang, csrc, "-o", exe, lib],
            capture_output=True, text=True,
            timeout=120, env=env)
        if cc.returncode != 0:
            raise AssertionError(
                f"clang link consumer failed: {cc.stderr[:200]}")
        run = subprocess.run([exe], capture_output=True, text=True,
                             timeout=30, env=env)
        if run.returncode != 0 or "link-ok" not in run.stdout:
            raise AssertionError(
                f"consumer run failed: rc={run.returncode} "
                f"out={run.stdout[:100]} {run.stderr[:100]}")
        print("OK: ats2-lang consumer link+run (clang + libatslib.a)")
    print("OK: ats2-lang 0.4.2 (libatslib.a symbols + prelude/libats "
          "headers verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
