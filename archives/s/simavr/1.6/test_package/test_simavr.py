#!/usr/bin/env python3
"""simavr consumer test (R34): link a real consumer against libsimavr.

Compiles a C program that *calls* real libsimavr symbols
(avr_make_mcu_by_name/avr_init/avr_run) and links libsimavr.a +
libelf (sim_elf.o dependency) WITHOUT --unresolved-symbols=ignore-all —
a broken archive (missing headers/symbols) MUST fail the link (AI
review: fake-pass layers removed).

Usage: test_simavr.py <package-folder> <libelf-lib-dir>
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_simavr.py <package-folder> "
                         "[<libelf-lib-dir>]")
    pkg = sys.argv[1]
    elflib = sys.argv[2] if len(sys.argv) > 2 else ""
    # 直接绝对 clang 路径：CI 环境设了 CC=clang（相对名）——os.environ.get
    # ('CC') 返回非空 'clang'，subprocess.run 抛 FileNotFoundError（CI #28938
    # 实证，上一轮 or 回退逻辑仍被 CC=clang 劫持）。不读环境 CC，硬编码
    # /data/service/hnp/bin/clang（与 gbdk 配方同款）。
    cc = "/data/service/hnp/bin/clang"
    inc = os.path.join(pkg, "include")
    lib = os.path.join(pkg, "lib")
    if not os.path.isdir(os.path.join(inc, "simavr")):
        raise AssertionError(f"simavr headers missing under {inc}")
    if not os.path.isfile(os.path.join(lib, "libsimavr.a")):
        raise AssertionError(f"libsimavr.a missing under {lib}")
    # real consumer: references actual libsimavr API symbols (not just an
    # include + printf) so the link must resolve them from libsimavr.a
    src = (
        "/* simavr consumer: call real libsimavr API symbols */\n"
        "#include <simavr/avr/avr_mcu_section.h>\n"
        "#include <simavr/sim/sim_avr.h>\n"
        "#include <simavr/sim/sim_elf.h>\n"
        "#include <stdio.h>\n"
        "int main(void) {\n"
        "    avr_t *avr = avr_make_mcu_by_name(\"atmega128\");\n"
        "    if (!avr) { printf(\"no mcu\\n\"); return 1; }\n"
        "    avr_init(avr);\n"
        "    avr_terminate(avr);\n"
        "    printf(\"simavr api ok\\n\");\n"
        "    return 0;\n"
        "}\n")
    c_file = os.path.join(pkg, "test_simavr_consumer.c")
    with open(c_file, "w") as f:
        f.write(src)
    out = os.path.join(pkg, "test_simavr_consumer")
    cmd = [cc, c_file, "-I", inc, "-L", lib, "-lsimavr"]
    if elflib:
        cmd += ["-L", elflib, "-lelf"]
    cmd += ["-o", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    # real link: ANY failure (undefined symbol, missing lib, ...) fails
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise AssertionError(f"consumer link failed (rc={r.returncode})")
    if not os.path.isfile(out) or os.path.getsize(out) == 0:
        raise AssertionError(f"no consumer binary produced: {out}")
    print("OK: simavr 1.6 real API ok "
          "(consumer links libsimavr.a + resolves symbols)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
