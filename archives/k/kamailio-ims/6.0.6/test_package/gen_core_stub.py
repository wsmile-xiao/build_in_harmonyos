#!/usr/bin/env python3
"""gen_core_stub.py — 按被测模块的未定义符号面，自动生成 kamailio core 符号弱桩。

背景：OHOS/musl 加载器不做惰性绑定（dlopen 等价 RTLD_NOW）。16 个 IMS 模块作为
core 插件，dlopen 时引用的全部 core 符号（dprint/fixup_*/pv_*/faked_msg/...）在
测试进程内必须可解析。逐个手写数百个桩不现实且易漏，故在测试时由本脚本从被测
.so 的 .dynsym 提取未定义符号，扣除「已由 libc/依赖包提供」的部分，剩余 core
符号生成为**弱定义**（`__attribute__((weak))`）：

  - 弱定义与 kamailio_core_stub.c 的强定义语义项共存，强定义胜出 → 真正被执行的
    路径仍走真实语义；未被执行的 core API 只需「可解析」即可。
  - 弱定义与静态库（libclang_rt 等）中的强定义不冲突：归档成员不会被拉入，
    避免重复定义链接错误。

符号类型取自引用方 .dynsym 的 st_info（STT_FUNC → 返回 0 的函数；
OBJECT/NOTYPE → 大块零填充缓冲），从而数据符号读到的是稳定的零值而非随机地址。

用法:
  python3 gen_core_stub.py --modules-dir <dir> --out <file.c>
                           [--provided-so <libc.so> ...] [--modules a b c]
"""

import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_ims_modules import (DEP_SYMBOL_PREFIXES, LIBC_SYMBOL_PREFIXES,  # noqa: E402
                               MODULES, SHN_UNDEF, SHT_DYNSYM,
                               defined_symbol_names, parse_elf)

STT_NOTYPE, STT_OBJECT, STT_FUNC, STT_IFUNC = 0, 1, 2, 10

SHT_RELA, SHT_REL = 4, 9

# aarch64 重定位类型中可判定「该符号被当函数调用」的集合。实测：本包 16 个模块的
# .dynsym 未定义符号 st_info 多为 STT_NOTYPE（0）→ 仅看 stt 会把全部 core 符号
# 误判为数据（曾导致 0 函数桩 + dlopen 未定义符号失败），故以重定位用途为准。
AARCH64_FUNC_RELOCS = {
    282,  # R_AARCH64_JUMP26
    283,  # R_AARCH64_CALL26
    311,  # R_AARCH64_PLT32
    1026,  # R_AARCH64_JUMP_SLOT（PLT 调用）
}

# 绝不可桩化的名字（由测试可执行文件自身/CRT 提供，或桩化会破坏加载语义）
NEVER_STUB = {
    "_init", "_fini", "_start", "__libc_start_main", "__cxa_finalize",
    "__dso_handle", "__stack_chk_fail", "__stack_chk_guard",
    # kamailio 6.x 内存 API 表全局：模块经 `_shm_root.xmalloc(...)` 分配（memapi.h）。
    # 若在此生成全零占位，函数指针为 NULL → 模块内首次分配 SIGSEGV
    # （实测 spi_add 内 `blr x8`，x8=[_shm_root+24]=0）。改由 kamailio_core_stub.c
    # 提供逐字段对齐的真实语义实现（libc malloc/free 后端）。
    "_shm_root", "_pkg_root",
}

# 与 libc 前缀同名、但确属 kamailio core 的符号：前缀过滤的例外。实测（16 模块
# .dynsym 未定义符号面）：下列 17 个符号因 fork_/free_*/log_*/str2*/str_search/
# exec_* 等 libc 前缀被误判为「libc 已提供」而跳过 → cdp.so dlopen(RTLD_NOW) 直接报
# "fork_process: symbol not found"。判定依据：这些符号并不在 sysroot libc.so 的已定义
# 符号集中（真实 libc 符号已由 provided 集先行扣除），属二次误伤。
CORE_PREFIX_EXCEPTIONS = {
    "exec_post_script_cb", "exec_pre_script_cb", "fork_process", "fork_sync_timer",
    "free_params", "free_rr", "free_sdp", "free_sip_msg",
    "log_color", "log_level_info", "log_prefix_val", "log_stderr",
    "str2ip6buf", "str2ipbuf", "str2ipxbuf", "str2q", "str_search",
}

# 遮蔽硬闸：这些符号若被桩化，会以「零返回值」顶替 libc 真实实现并**静默**破坏
# 用例语义（如 strlen 恒 0）。出现即说明 libc 提供方 .so 未找到 → 拒绝生成。
MUST_NOT_STUB = {
    "strlen", "strcmp", "strncmp", "strcpy", "strncpy", "strchr", "strrchr",
    "strdup", "strstr", "memset", "memcpy", "memmove", "memcmp", "malloc",
    "calloc", "free", "realloc", "snprintf", "sprintf", "printf", "fprintf",
    "pthread_mutex_lock", "pthread_mutex_unlock", "pthread_create", "open",
    "close", "read", "write", "socket", "sendto", "recvfrom", "getpid",
}


def reloc_types_by_sym(d, secs, dynsym_index):
    """{dynsym 符号索引: {重定位类型}}——只取 sh_link 指向该 .dynsym 的重定位节。"""
    out = {}
    for s in secs:
        if s["type"] not in (SHT_RELA, SHT_REL) or s.get("link") != dynsym_index:
            continue
        ent = 24 if s["type"] == SHT_RELA else 16
        for i in range(s["size"] // ent):
            o = s["off"] + i * ent
            _roff, info = struct.unpack_from("<QQ", d, o)
            out.setdefault(info >> 32, set()).add(info & 0xFFFFFFFF)
    return out


def collect_undefined(modules_dir, modules):
    """返回 {symbol: kind}，kind ∈ {'func','object'}（同名冲突时 func 优先）。"""
    out = {}
    for mod in modules:
        path = os.path.join(modules_dir, mod + ".so")
        if not os.path.isfile(path):
            continue
        d, secs, _segs = parse_elf(path)
        for idx, s in enumerate(secs):
            if s["type"] != SHT_DYNSYM:
                continue
            strtab = secs[s["link"]] if s["link"] < len(secs) else None
            if strtab is None:
                continue
            relocs = reloc_types_by_sym(d, secs, idx)
            for i in range(s["size"] // 24):
                o = s["off"] + i * 24
                nmoff, info, _other, shndx, _val, _size = struct.unpack_from(
                    "<IBBHQQ", d, o)
                if shndx != SHN_UNDEF or not nmoff:
                    continue
                end = d.index(b"\0", strtab["off"] + nmoff)
                name = d[strtab["off"] + nmoff:end].decode("utf-8", "replace")
                name = name.split("@", 1)[0]
                if not name or name in NEVER_STUB:
                    continue
                stt = info & 0xF
                by_reloc = bool(relocs.get(i, set()) & AARCH64_FUNC_RELOCS)
                kind = "func" if (stt in (STT_FUNC, STT_IFUNC) or by_reloc) else "object"
                if name in out and out[name] == "func":
                    continue
                out[name] = kind
    return out


def provided_symbols(paths):
    """已被 libc / 依赖包 / 加载器提供的符号名集合（这些不得桩化——重复定义会改变
    真实解析结果，甚至遮蔽 libc 实现）。"""
    provided = set()
    for p in paths:
        if not p or not os.path.isfile(p):
            continue
        d, secs, _segs = parse_elf(p)
        provided |= defined_symbol_names(d, secs)
    return provided


def emit(symbols, out_path, modules_dir, provided):
    funcs = sorted(s for s, k in symbols.items() if k == "func")
    objs = sorted(s for s, k in symbols.items() if k == "object")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("/* 本文件由 gen_core_stub.py 自动生成——请勿手工编辑。\n"
                 " *\n"
                 f" * 来源：{modules_dir} 下 {len(MODULES)} 个 IMS 模块 .so 的 .dynsym 未定义符号面，\n"
                 " * 扣除 libc/依赖包已提供的部分后的 kamailio core 符号。\n"
                 " *\n"
                 f" * 弱桩：函数 {len(funcs)} 个、数据 {len(objs)} 个；"
                 f"已由 libc/依赖包提供而跳过的符号 {len(provided)} 个。\n"
                 " * 弱定义与 kamailio_core_stub.c 的强定义共存（强定义胜出），\n"
                 " * 与静态库中的强定义不冲突（归档成员不被拉入）。\n"
                 " */\n\n"
                 "#include <stddef.h>\n\n"
                 "#define KAM_WEAK __attribute__((weak))\n\n")
        fh.write("/* ---- 函数符号：返回 0（调用方按 ABI 取 x0，指针/整型均得 0） ---- */\n")
        for s in funcs:
            fh.write(f"KAM_WEAK long {s}(void);\n")
        fh.write("\n")
        for s in funcs:
            fh.write(f"KAM_WEAK long {s}(void) {{ return 0; }}\n")
        fh.write("\n/* ---- 数据符号：零填充缓冲（读得稳定零值，避免野指针） ---- */\n")
        for s in objs:
            fh.write(f"KAM_WEAK unsigned char {s}[32768] __attribute__((aligned(16)));\n")
        fh.write(f"\n/* 函数 {len(funcs)} 个、数据 {len(objs)} 个 —— 结束 */\n")
    return funcs, objs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modules-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--provided-so", action="append", default=[])
    ap.add_argument("--force-stub", action="append", default=[],
                    help="强制桩化的符号（覆盖 libc/依赖前缀判定，用于被误判的 core 符号）")
    ap.add_argument("--modules", nargs="*", default=None)
    ap.add_argument("--print-skipped", action="store_true")
    a = ap.parse_args()

    modules = a.modules or [m for m, *_ in MODULES]
    present = [m for m in modules if os.path.isfile(os.path.join(a.modules_dir, m + ".so"))]
    print(f"[gen_core_stub] 扫描模块 {len(present)}/{len(modules)} 个：{a.modules_dir}")
    undef = collect_undefined(a.modules_dir, present)
    provided = provided_symbols(a.provided_so)
    print(f"[gen_core_stub] 未定义符号 {len(undef)} 个；libc/依赖包 .so 提供 {len(provided)} 个")

    # 二次过滤：libc/CRT 与依赖包前缀的符号不得桩化——桩化会以零返回值顶替真实实现，
    # 静默破坏用例语义（--force-stub 可对被误判的 core 符号强制桩化）。
    forced = set(a.force_stub or [])
    dep_prefixes = tuple(p for v in DEP_SYMBOL_PREFIXES.values() for p in v)
    remaining = {s: k for s, k in undef.items() if s not in provided}
    libc_like = {s for s in remaining
                 if any(s.startswith(p) for p in LIBC_SYMBOL_PREFIXES)}
    libc_like -= CORE_PREFIX_EXCEPTIONS
    dep_like = {s for s in remaining
                if any(s.startswith(p) for p in dep_prefixes)}
    todo = {s: k for s, k in remaining.items()
            if s in forced or (s not in libc_like and s not in dep_like)}
    print(f"[gen_core_stub] 前缀再扣除：libc/CRT {len(libc_like)} 个、依赖包 {len(dep_like)} 个；"
          f"强制桩化 {len(forced)} 个；待桩化 {len(todo)} 个")

    if a.print_skipped:
        print("[gen_core_stub] libc/CRT 前缀跳过:", sorted(libc_like))
        print("[gen_core_stub] 依赖包前缀跳过:", sorted(dep_like))

    bad = sorted(s for s in todo if s in MUST_NOT_STUB)
    if bad:
        print("[gen_core_stub] 错误：未找到 libc 提供方 .so，以下 libc 符号将被桩化并"
              f"静默顶替真实实现：{bad}", file=sys.stderr)
        print("[gen_core_stub] 修正：用 --provided-so 指定 sysroot 下的 libc.so。拒绝生成。",
              file=sys.stderr)
        return 3

    funcs, objs = emit(todo, a.out, a.modules_dir, provided)
    print(f"[gen_core_stub] 生成弱桩：函数 {len(funcs)} 个、数据 {len(objs)} 个 → {a.out}")
    print(f"[gen_core_stub] 数据符号: {objs if len(objs) <= 40 else objs[:40]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
