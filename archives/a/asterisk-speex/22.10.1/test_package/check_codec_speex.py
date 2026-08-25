#!/usr/bin/env python3
"""asterisk-speex test_package 消费者测试（R34 实质验证）。

对已安装的 codec_speex.so 做真实、可失败的检查：
1. ELF 头合法性（魔数/64位/小端/aarch64）
2. 动态段 DT_NEEDED 解析（llvm-readelf）：libc.so 必须存在
3. 符号表解析（llvm-readelf --syms）：load_module/unload_module 必须已定义
4. speex 功能符号/字符串存在性（speex_encode/speex_preprocess_ctl——
   静态链入模块，证明 libspeex + libspeexdsp 已实际链接进产物）
5. 可选 dlopen 尝试：诚实说明 Asterisk 模块在 asterisk 进程外加载的预期失败
"""
import os
import struct
import subprocess
import sys
import shutil

mod = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codec_speex.so")
if not os.path.isfile(mod):
    mod = os.path.join(os.environ.get("TEST_CODEC_SPEEX_MOD", ""), "codec_speex.so")

failures = []

# --- 1. 文件存在且非空 ---
if not os.path.isfile(mod) or os.path.getsize(mod) < 10000:
    failures.append(f"module missing or too small: {mod}")
    print(f"FAIL: {failures[-1]}")
    sys.exit(1)
print(f"PASS: module present ({os.path.getsize(mod)} bytes): {mod}")

with open(mod, "rb") as f:
    data = f.read()

# --- 2. ELF 魔数 / 类 / 端序 ---
if data[:4] != b"\x7fELF":
    failures.append("not an ELF file (bad magic)")
else:
    print("PASS: ELF magic ok")
    ei_class, ei_data = data[4], data[5]
    if ei_class != 2:
        failures.append(f"not ELF64 (EI_CLASS={ei_class})")
    else:
        print("PASS: ELF64 class")
    if ei_data != 1:
        failures.append(f"not little-endian (EI_DATA={ei_data})")
    else:
        print("PASS: little-endian")

# --- 3. e_machine aarch64 (183) ---
if len(data) >= 20:
    e_machine = struct.unpack_from("<H", data, 18)[0]
    if e_machine == 183:
        print("PASS: aarch64 machine type")
    else:
        failures.append(f"unexpected e_machine={e_machine} (want 183 aarch64)")

# --- 4. DT_NEEDED 解析（真实 ELF 动态段，非裸子串） ---
needed = []
llvm = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
if os.path.isfile(llvm):
    try:
        out = subprocess.check_output([llvm, "--dynamic", mod], text=True, timeout=10)
        for line in out.splitlines():
            if "NEEDED" in line and "[" in line:
                lib = line.split("[", 1)[1].split("]", 1)[0]
                needed.append(lib)
        print(f"INFO: DT_NEEDED = {needed}")
        if "libc.so" in needed:
            print("PASS: DT_NEEDED contains libc.so")
        else:
            failures.append(f"DT_NEEDED missing libc.so: {needed}")
        # speex 预期静态链接（本包发布静态 libspeex.a/libspeexdsp.a）→ 不在 DT_NEEDED，
        # 用符号/字符串证明功能代码已编译进模块（见第 6 步）。
        has_dyn_speex = any("speex" in n.lower() for n in needed)
        if has_dyn_speex:
            print(f"INFO: DT_NEEDED shows dynamic speex linkage: {needed}")
        else:
            print("INFO: DT_NEEDED has no speex (statically linked as designed); verified via symbols")
    except Exception as e:
        failures.append(f"llvm-readelf --dynamic failed: {e}")
else:
    failures.append(f"llvm-readelf not found at {llvm}")

# --- 5. 符号表：load_module / unload_module 必须已定义（可失败断言） ---
syms_output = ""
for tool in [llvm, shutil.which("readelf") or "readelf"]:
    if os.path.isfile(tool):
        try:
            syms_output = subprocess.check_output([tool, "--syms", mod], text=True, timeout=10)
            break
        except Exception:
            continue

if not syms_output:
    failures.append("could not read symbol table (no llvm-readelf/readelf)")
else:
    has_load = False
    has_unload = False
    for line in syms_output.splitlines():
        if " load_module" in line and " UND " not in line:
            has_load = True
        if " unload_module" in line and " UND " not in line:
            has_unload = True
    if has_load:
        print("PASS: symbol load_module defined")
    else:
        failures.append("missing defined symbol: load_module (Asterisk module entry)")
    if has_unload:
        print("PASS: symbol unload_module defined")
    else:
        failures.append("missing defined symbol: unload_module")
    # speex 功能符号存在性（静态链接证明）
    speex_syms = [s for s in syms_output.splitlines()
                  if any(k in s for k in ("speex_encode", "speex_decoder", "speex_preprocess"))]
    print(f"INFO: speex symbols in symtab: {len(speex_syms)}")
    if speex_syms:
        print("PASS: speex functional symbols present (libspeex/libspeexdsp linked in)")
    elif b"speex_preprocess_ctl" in data or b"speex_encoder" in data:
        print("PASS: speex functional strings present in module (inlined symbols)")
    else:
        failures.append("no speex symbols/strings found in module (speex not linked)")

# --- 6. dlopen 诚实尝试（Asterisk 模块预期在 asterisk 进程外加载失败） ---
try:
    import ctypes
    try:
        ctypes.CDLL(mod)
        print("PASS: dlopen succeeded (module is self-contained)")
    except OSError as e:
        msg = str(e)
        if "undefined symbol" in msg or "ast_" in msg:
            print(f"INFO: dlopen outside asterisk failed as expected (unresolved core symbols): {msg[:200]}")
            print("      -> module is designed to be loaded by asterisk binary; this is not a test failure")
        else:
            print(f"INFO: dlopen failed: {msg[:300]}")
except Exception as e:
    print(f"INFO: dlopen check skipped: {e}")

if failures:
    print("\n=== TEST FAILURES ===")
    for x in failures:
        print(" -", x)
    sys.exit(1)

print("\nALL CHECKS PASSED: codec_speex.so is a valid aarch64 ELF module with speex linked in")
