#!/usr/bin/env python3
"""kamailio-ev 6.0.6 产物检查（消费者视角）— HarmonyOS PC / aarch64。

检查口径
--------
evapi.so 是 kamailio 的 **core 插件**（loadmodule/dlopen 加载），其 core 符号由 kamailio
主程序提供、libev 符号由 conan 依赖包提供，因此它**脱离主程序无法独立 dlopen**。本检查
按「加载器同源语义」逐项验证产物本身（纯 Python 自解析 ELF，不依赖外部工具），端到端
dlopen 路径由 test_evapi_e2e.c 覆盖：

  1. ELF 身份：64-bit / 小端 / ET_DYN / EM_AARCH64
  2. 模块契约：自解析 ELF 读取导出结构 `struct module_exports` 首字段 `char *name`，
     须为 kamailio 期望的 "evapi"
  3. 导出符号面：exports / mod_register / module_version / module_flags /
     module_interface_ver / evapi_* 运行期入口
  4. 依赖声明：DT_NEEDED == {libc.so, libev.so}（文档化允许集合），且 libev.so 必须真实
     存在于 conan 依赖包 lib 目录（运行时可解析）
  5. 无 RPATH/RUNPATH（宿主路径泄漏会导致目标机加载失败）
  6. 依赖闭合（关键）：evapi.so 的全部未定义符号必须分属四组之一——libc/CRT、
     libev.so（逐符号核验其确实在依赖包 .dynsym 中定义）、kamailio core（由主程序提供）。
     任何落空符号 → FAIL。另核验 libev.so 自身的 DT_NEEDED 仅落在 libc 内（依赖链闭合）。
  7. 许可证随包（licenses/COPYING 为 GPL 文本）

退出码：0 = 全通过；1 = 存在失败项。
"""
import os
import struct
import sys

MODULE = os.environ.get("KAMAILIO_EVAPI_MODULE", "")
PACKAGE_FOLDER = os.environ.get("KAMAILIO_EVAPI_PACKAGE_FOLDER", "")
LIBEV_PACKAGE_FOLDER = os.environ.get("LIBEV_PACKAGE_FOLDER", "")

EXPECTED_MODULE_NAME = "evapi"

# 导出符号面（nm -D --defined-only 实测，模块对外契约）
EXPECTED_EXPORTS = (
    "exports", "mod_register",
    "module_version", "module_flags", "module_interface_ver",
    "evapi_run_dispatcher", "evapi_run_worker", "evapi_recv_client", "evapi_accept_client",
    "evapi_relay", "evapi_relay_unicast", "evapi_relay_multicast",
    "evapi_set_tag", "evapi_cfg_close", "evapi_close_connection",
    "evapi_queue_init", "evapi_queue_add", "evapi_queue_get",
    "evapi_clients_init", "evapi_env_reset", "evapi_init_environment", "evapi_run_cfg_route",
    "evapi_init_notify_sockets", "evapi_close_notify_sockets_parent",
    "evapi_close_notify_sockets_child", "evapi_dispatch_notify", "evapi_recv_notify",
    "pv_parse_evapi_name", "pv_get_evapi", "pv_set_evapi",
)

# DT_NEEDED 允许集合（文档化口径）：
#   libc.so  —— OHOS musl 系统运行库
#   libev.so —— 模块的事件循环后端（libev），由 conan 依赖 libev/4.33 提供
#                （非系统同名库：OHOS sysroot 内不含 libev，按仓库口径由 conan 依赖链
#                 管理动态依赖；libev 包不提供 SONAME，故 DT_NEEDED 记录为 libev.so）
EXPECTED_NEEDED = {"libc.so", "libev.so"}

# libc/CRT 提供（不由本包负责）
LIBC_SYMBOLS = {
    "__at_fini", "__cxa_finalize", "__deregister_frame_info", "__register_frame_info",
    "accept", "atoi", "bind", "close", "exit", "fcntl", "fprintf", "free", "freeaddrinfo",
    "gai_strerror", "getaddrinfo", "getpid", "inet_ntop", "listen", "malloc", "memcpy",
    "memset", "ntohs", "perror", "read", "recv", "sched_yield", "select", "setsockopt",
    "snprintf", "socket", "socketpair", "stderr", "strchr", "strlen", "strncmp", "strncpy",
    "write",
}

# libev.so 提供（evapi 模块的事件循环 API；逐符号核验依赖包是否导出）
LIBEV_SYMBOLS = {"ev_default_loop", "ev_io_start", "ev_io_stop", "ev_run"}

# kamailio core 提供（由 kamailio 主程序在 loadmodule 时提供；口径见
# test_package/kamailio_core_stub.c 头注释，e2e 用最小桩层复现该符号面）
CORE_SYMBOLS = {
    "_atomic_lock_set", "_km_log_func", "_ksr_slog_func", "_shm_root",
    "cfg_block_size", "cfg_child_cb", "cfg_child_cb_first", "cfg_child_cb_last",
    "cfg_child_init", "cfg_ginst_count", "cfg_global", "cfg_global_lock", "cfg_group",
    "cfg_local", "cfg_move_handle", "cfg_register_child",
    "dprint_color", "dprint_color_reset", "dprint_crit",
    "event_rt", "faked_msg_get_new", "faked_msg_init", "find_export",
    "fixup_free_spve_all", "fixup_free_spve_null", "fixup_free_vstr_all",
    "fixup_spve_all", "fixup_spve_null", "fixup_vstr_all",
    "fork_process", "free_sip_msg", "get_debug_facility", "get_debug_level",
    "get_str_fparam", "init_child", "ksr_msg_env_reset", "log_color", "log_level_info",
    "log_prefix_val", "log_stderr", "my_pid", "process_no",
    "pv_get_null", "pv_get_sintval", "pv_get_strval", "pv_get_strzval",
    "pv_printf_mode", "pv_printf_size", "register_procs",
    "route_lookup", "route_type", "run_top_route",
    "sr_kemi_eng_get", "sr_kemi_modules_add", "sr_kemi_route", "ut_buf_int2str",
}

SHT_SYMTAB, SHT_RELA, SHT_DYNAMIC, SHT_DYNSYM = 2, 4, 6, 11
DT_NEEDED, DT_RPATH, DT_RUNPATH, DT_SONAME = 1, 15, 29, 14
EM_AARCH64 = 183
ET_DYN = 3
SHN_UNDEF = 0

stats = {"pass": 0, "fail": 0}
failures = []


def check(label, ok, detail=""):
    if ok:
        stats["pass"] += 1
        print(f"  [ok]   {label}")
    else:
        stats["fail"] += 1
        failures.append(f"{label} — {detail}")
        print(f"  [FAIL] {label}: {detail}")


# ─────────────────────────── ELF 自解析 ───────────────────────────

def parse_elf(path):
    with open(path, "rb") as fh:
        d = fh.read()
    e_phoff, = struct.unpack_from("<Q", d, 0x20)
    e_phentsize, = struct.unpack_from("<H", d, 0x36)
    e_phnum, = struct.unpack_from("<H", d, 0x38)
    e_shoff, = struct.unpack_from("<Q", d, 0x28)
    e_shentsize, = struct.unpack_from("<H", d, 0x3A)
    e_shnum, = struct.unpack_from("<H", d, 0x3C)

    segs = []
    for i in range(e_phnum):
        o = e_phoff + i * e_phentsize
        p_type, = struct.unpack_from("<I", d, o)
        p_offset, p_vaddr, _p_paddr, p_filesz = struct.unpack_from("<QQQQ", d, o + 8)
        if p_type == 1 and p_filesz:            # PT_LOAD
            segs.append((p_vaddr, p_offset, p_filesz))

    secs = []
    for i in range(e_shnum):
        o = e_shoff + i * e_shentsize
        _nm, typ, _fl, addr, off, size, link = struct.unpack_from("<IIQQQQI", d, o)
        secs.append({"type": typ, "addr": addr, "off": off, "size": size, "link": link})
    return d, secs, segs


def vaddr_to_offset(segs, vaddr):
    for v, off, size in segs:
        if v <= vaddr < v + size:
            return off + (vaddr - v)
    return None


def cstring(d, off):
    end = d.index(b"\0", off)
    return d[off:end].decode("utf-8", "replace")


def all_symbols(d, secs):
    """返回 [(name, shndx, value)]，合并 .symtab 与 .dynsym。"""
    out = []
    for s in secs:
        if s["type"] not in (SHT_SYMTAB, SHT_DYNSYM):
            continue
        strtab = secs[s["link"]] if s["link"] < len(secs) else None
        if strtab is None:
            continue
        for i in range(s["size"] // 24):
            o = s["off"] + i * 24
            nmoff, _info, _other, shndx, value, _size = struct.unpack_from("<IBBHQQ", d, o)
            name = cstring(d, strtab["off"] + nmoff) if nmoff else ""
            out.append((name, shndx, value))
    return out


def defined_symbol_names(d, secs):
    """动态符号表中已定义的符号名（供依赖包 .dynsym 核验）。"""
    out = set()
    for s in secs:
        if s["type"] != SHT_DYNSYM:
            continue
        strtab = secs[s["link"]] if s["link"] < len(secs) else None
        if strtab is None:
            continue
        for i in range(s["size"] // 24):
            o = s["off"] + i * 24
            nmoff, info, _other, shndx, _value, _size = struct.unpack_from("<IBBHQQ", d, o)
            if shndx != SHN_UNDEF and nmoff:
                out.add(cstring(d, strtab["off"] + nmoff))
    return out


def undefined_symbol_names(d, secs):
    """动态符号表中的未定义符号名（去掉 @版本 后缀）。"""
    out = []
    for s in secs:
        if s["type"] != SHT_DYNSYM:
            continue
        strtab = secs[s["link"]] if s["link"] < len(secs) else None
        if strtab is None:
            continue
        for i in range(s["size"] // 24):
            o = s["off"] + i * 24
            nmoff, _info, _other, shndx, _value, _size = struct.unpack_from("<IBBHQQ", d, o)
            if shndx == SHN_UNDEF and nmoff:
                name = cstring(d, strtab["off"] + nmoff)
                out.append(name.split("@", 1)[0])
    return out


def relocations(d, secs):
    """{r_offset: (r_type, r_addend)}（AArch64 RELA：数据指针值在 addend 中）"""
    m = {}
    for s in secs:
        if s["type"] != SHT_RELA:
            continue
        for i in range(s["size"] // 24):
            o = s["off"] + i * 24
            r_offset, r_info, r_addend = struct.unpack_from("<QQq", d, o)
            m[r_offset] = (r_info & 0xFFFFFFFF, r_addend)
    return m


def dynamic_entries(d, secs):
    """返回 [(tag, value, name|None)]，name 取自 .dynamic 链接的字符串表。"""
    out = []
    for s in secs:
        if s["type"] != SHT_DYNAMIC:
            continue
        strtab = secs[s["link"]] if s["link"] < len(secs) else None
        for i in range(s["size"] // 16):
            o = s["off"] + i * 16
            tag, val = struct.unpack_from("<qQ", d, o)
            name = None
            if tag in (DT_NEEDED, DT_RPATH, DT_RUNPATH, DT_SONAME) and strtab is not None:
                name = cstring(d, strtab["off"] + val)
            elif tag == 0:
                break
            out.append((tag, val, name))
    return out


def contract_name(d, secs, segs):
    """读取出模块导出结构首字段（char *name）——kamailio 加载时注册模块所用的名字。

    该字段为数据指针：对 ET_DYN 而言其值由 RELATIVE 重定位填充，addend 记录目标
    虚拟地址（lld 在字段内存中可能留 0），故优先取重定位 addend，回退读字段原始值。
    """
    entry = [s for s in all_symbols(d, secs) if s[0] == "exports" and s[1] != SHN_UNDEF]
    if not entry:
        return None, "缺少 exports 导出符号"
    value = entry[0][2]
    relocs = relocations(d, secs)
    target = relocs[value][1] if value in relocs else None
    if not target:
        off = vaddr_to_offset(segs, value)
        if off is None:
            return None, f"exports 地址 {value:#x} 无法映射到文件"
        target, = struct.unpack_from("<Q", d, off)
    if not target:
        return None, "exports->name 为空"
    off = vaddr_to_offset(segs, target)
    if off is None:
        return None, f"name 指针 {target:#x} 无法映射到文件"
    return cstring(d, off), ""


def find_shared_object(folder, soname):
    """在包目录中查找可满足 DT_NEEDED 的文件（含 .so / .so.N / .so.N.M.K 变体）。"""
    if not folder or not os.path.isdir(folder):
        return None
    base = soname.split(".so")[0] + ".so"
    for root, _dirs, files in os.walk(folder):
        for f in files:
            if f == soname or f == base or f.startswith(base + "."):
                return os.path.join(root, f)
    return None


# ─────────────────────────── 检查项 ───────────────────────────

def main():
    print("=" * 76)
    print("kamailio-ev 6.0.6 — 产物检查（消费者视角 / 加载器同源语义）")
    print(f"模块: {MODULE}")
    print(f"包目录: {PACKAGE_FOLDER}")
    print(f"libev 依赖包: {LIBEV_PACKAGE_FOLDER}")
    print("=" * 76)

    if not MODULE or not os.path.isfile(MODULE):
        print(f"[FAIL] 未找到模块文件: {MODULE!r}")
        return 1

    d, secs, segs = parse_elf(MODULE)

    # 1. ELF 身份
    print("\n-- 1. ELF 身份 --")
    check("文件为 ELF", d[:4] == b"\x7fELF")
    check("64-bit 小端", d[4] == 2 and d[5] == 1)
    e_type, e_machine = struct.unpack_from("<HH", d, 16)
    check(f"e_type == ET_DYN({ET_DYN})（共享模块）", e_type == ET_DYN, f"实得 {e_type}")
    check(f"e_machine == EM_AARCH64({EM_AARCH64})", e_machine == EM_AARCH64,
          f"实得 {e_machine}")

    # 2. 模块契约名
    print("\n-- 2. 模块契约（exports->name，kamailio 加载器注册依据）--")
    name, err = contract_name(d, secs, segs)
    check(f'exports->name == "{EXPECTED_MODULE_NAME}"', name == EXPECTED_MODULE_NAME,
          err or f"实得 {name!r}")

    # 3. 导出符号面
    print("\n-- 3. 导出符号面 --")
    defined = defined_symbol_names(d, secs)
    missing_exports = [s for s in EXPECTED_EXPORTS if s not in defined]
    check(f"{len(EXPECTED_EXPORTS)} 个契约导出符号齐备", not missing_exports,
          f"缺失: {missing_exports}")

    # 4. 依赖声明
    print("\n-- 4. 依赖声明（DT_NEEDED）--")
    needed = sorted(n for t, _v, n in dynamic_entries(d, secs) if t == DT_NEEDED and n)
    check(f"DT_NEEDED == {sorted(EXPECTED_NEEDED)}", set(needed) == EXPECTED_NEEDED,
          f"实得 {needed}")
    libev_so = find_shared_object(LIBEV_PACKAGE_FOLDER, "libev.so")
    check("DT_NEEDED 的 libev.so 在 conan 依赖包内真实存在（运行时可解析）",
          libev_so is not None,
          f"在 {LIBEV_PACKAGE_FOLDER!r} 内未找到 libev.so（含 .so.N 变体）")

    # 5. 宿主路径泄漏
    print("\n-- 5. 宿主路径泄漏（RPATH/RUNPATH）--")
    rpaths = [n for t, _v, n in dynamic_entries(d, secs) if t in (DT_RPATH, DT_RUNPATH)]
    check("无 RPATH/RUNPATH", not rpaths, f"实得 {rpaths}")

    # 6. 依赖闭合：逐符号分类
    print("\n-- 6. 依赖闭合（未定义符号逐项归类）--")
    undef = undefined_symbol_names(d, secs)
    ev_syms = sorted({s for s in undef if s.startswith("ev_")})
    libc_syms = sorted({s for s in undef if s in LIBC_SYMBOLS})
    core_syms = sorted({s for s in undef if s in CORE_SYMBOLS})
    unclassified = sorted(set(undef) - set(ev_syms) - set(libc_syms) - set(core_syms))
    print(f"     未定义符号共 {len(set(undef))} 个：libc/CRT {len(libc_syms)}、"
          f"libev {len(ev_syms)}、kamailio core {len(core_syms)}")
    check("全部未定义符号均落入文档化三类（libc/CRT、libev、kamailio core）",
          not unclassified, f"未归类符号: {unclassified}")
    check("未定义符号面含 libev 事件循环符号（ev_*，动态依赖确被引用）",
          len(ev_syms) >= 4, f"实得 {len(ev_syms)} 个: {ev_syms}")
    check("未定义符号面含 kamailio core 契约符号（sr_kemi_modules_add/route_lookup 等，core 插件特征）",
          "sr_kemi_modules_add" in core_syms and "route_lookup" in core_syms,
          f"实得 core 符号: {core_syms}")

    # 6b. 逐符号核验 libev 依赖包确实导出这些符号 + 依赖链闭合
    if libev_so:
        ld, lsecs, _lsegs = parse_elf(libev_so)
        provided = defined_symbol_names(ld, lsecs)
        unresolved = [s for s in ev_syms if s not in provided]
        check(f"libev 依赖包导出全部 {len(ev_syms)} 个被引用的 ev_* 符号",
              not unresolved, f"{os.path.basename(libev_so)} 缺失: {unresolved}")
        libev_needed = sorted(n for t, _v, n in dynamic_entries(ld, lsecs)
                              if t == DT_NEEDED and n)
        check("libev.so 自身 DT_NEEDED 仅落在 libc（依赖链闭合，无未提供的外部库）",
              set(libev_needed) <= {"libc.so"} and libev_needed,
              f"libev.so 的 DT_NEEDED={libev_needed}")
        # 依赖链闭合的充分条件即上一条（DT_NEEDED ⊆ {libc.so}）：libev.so 其余未定义符号
        # （epoll/inotify/signalfd/timerfd 等）全部由 libc.so 在运行时解析，故无需逐一
        # 维护 libc 白名单（模块侧白名单口径不适用于依赖库）。此处补验目标平台一致性。
        l_type, l_machine = struct.unpack_from("<HH", ld, 16)
        check("libev.so 与模块同为 aarch64 ET_DYN（目标平台一致）",
              l_type == ET_DYN and l_machine == EM_AARCH64,
              f"libev.so e_type={l_type} e_machine={l_machine}")
        libev_rpaths = [n for t, _v, n in dynamic_entries(ld, lsecs)
                        if t in (DT_RPATH, DT_RUNPATH)]
        check("libev.so 无 RPATH/RUNPATH（宿主路径未泄漏进运行时依赖）",
              not libev_rpaths, f"实得 {libev_rpaths}")
    else:
        check("libev 依赖包可用（跳过符号核验）", False, "未找到 libev.so")

    # 7. 许可证
    print("\n-- 7. 许可证 --")
    copying = os.path.join(PACKAGE_FOLDER, "licenses", "COPYING")
    check("licenses/COPYING 随包", os.path.isfile(copying), f"缺失: {copying}")

    # 汇总
    print("\n" + "=" * 76)
    print(f"断言：通过 {stats['pass']} / 失败 {stats['fail']}")
    print("=" * 76)
    if failures:
        print("失败明细：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("全部通过：evapi.so 为 aarch64 ET_DYN core 插件，模块契约名与 kamailio 期望一致，")
    print("依赖落在文档化允许集合内（libev.so 由 conan 依赖链提供且符号逐项核验），")
    print("未定义符号面 100% 归类，无宿主路径泄漏。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
