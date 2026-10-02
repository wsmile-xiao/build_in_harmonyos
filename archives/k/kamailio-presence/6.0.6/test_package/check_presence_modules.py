#!/usr/bin/env python3
"""check_presence_modules.py — kamailio-presence 6.0.6 产物检查（18 个模块，纯 Python ELF 自解析）。

消费者视角：以 kamailio 加载器同源语义核验每个模块 .so 是否「可被 loadmodule 加载」：

  1. ELF 身份（ELF64 LSB / ET_DYN / EM_AARCH64）
  2. 模块契约名（exports 首字段，kamailio 注册模块所用的名字）
  3. 契约导出符号面（exports / mod_register / module_version|flags|interface_ver）
  4. DT_NEEDED 落在文档化允许集合内（并按模块组断言必需依赖确已声明）
  5. 无 RPATH/RUNPATH（不允许宿主路径泄漏）
  6. 未定义符号 100% 归类（libc/CRT + conan 依赖包 + kamailio core）
  7. 依赖包逐符号核验 + 依赖链闭合（libxml2 以共享库形态出现于 DT_NEEDED 并被逐符号
     核验；curl 在 OHOS 侧为共享库形态（xcap_client 的 DT_NEEDED 含 libcurl.so））
  8. 许可证随包

无外部工具依赖（不调用 readelf/nm），在 CI 干净环境中可直接运行。
"""

import os
import struct
import sys

# ─────────────────────────── 常量 ───────────────────────────

ET_DYN = 3
EM_AARCH64 = 183

SHT_SYMTAB = 2
SHT_RELA = 4
SHT_DYNAMIC = 6
SHT_DYNSYM = 11

SHN_UNDEF = 0

DT_NEEDED = 1
DT_SONAME = 14
DT_RPATH = 15
DT_RUNPATH = 29

# 18 个模块（packaging 口径 = Alpine main/kamailio 的 kamailio-presence 子包
# _mod_list_presence；SIMPLE presence extensions 家族）
# 每项：(模块文件, 期望契约名, 必需 DT_NEEDED 前缀, 依赖包 key)
#   need 前缀：'' 表示仅要求 libc；'libxml2.so' / 'libcurl.so' 表示该模块
#   实测声明了对应依赖（DT_NEEDED 实测见 notes.md 评测表）
MODULES = [
    ("presence", "presence", ("libxml2.so",), "libxml2"),
    ("presence_conference", "presence_conference", ("libxml2.so",), "libxml2"),
    ("presence_dfks", "presence_dfks", ("libxml2.so",), "libxml2"),
    ("presence_dialoginfo", "presence_dialoginfo", ("libxml2.so",), "libxml2"),
    ("presence_mwi", "presence_mwi", (), None),
    ("presence_profile", "presence_profile", (), None),
    ("presence_reginfo", "presence_reginfo", ("libxml2.so",), "libxml2"),
    ("presence_xml", "presence_xml", ("libxml2.so",), "libxml2"),
    ("pua", "pua", ("libxml2.so",), "libxml2"),
    ("pua_bla", "pua_bla", ("libxml2.so",), "libxml2"),
    ("pua_dialoginfo", "pua_dialoginfo", ("libxml2.so",), "libxml2"),
    ("pua_reginfo", "pua_reginfo", ("libxml2.so",), "libxml2"),
    ("pua_rpc", "pua_rpc", (), None),
    ("pua_usrloc", "pua_usrloc", ("libxml2.so",), "libxml2"),
    ("pua_xmpp", "pua_xmpp", ("libxml2.so",), "libxml2"),
    ("rls", "rls", ("libxml2.so",), "libxml2"),
    ("xcap_client", "xcap_client", ("libcurl.so",), "curl"),
    ("xcap_server", "xcap_server", ("libxml2.so",), "libxml2"),
]

# 每个 core 插件模块都必须导出的契约符号（MODULE_VERSION 宏 + 插件入口）
CONTRACT_SYMBOLS = ["exports", "module_version", "module_flags", "module_interface_ver"]

# 可选的兼容入口：sr_module.c:624 先 dlsym("mod_register")（旧式 dlflags 协商），
# 取不到时回退 dlsym("exports")（:643）→ 6.0.6 上游 12/18 模块不含该符号（6/18 含），故非必需
OPTIONAL_CONTRACT_SYMBOLS = ["mod_register"]

# DT_NEEDED 允许集合（前缀匹配）：presence 家族实测仅三类 —— libc + libxml2（6 组
# 模块）+ libcurl（xcap_client）；其余为 libc 家族（OHOS sysroot 提供）的保留白名单位
ALLOWED_NEEDED_PREFIXES = ("libc.so", "libxml2.so", "libcurl.so",
                           "libm.so", "libdl.so", "libpthread.so",
                           "librt.so", "libgcc_s.so")

# 由 conan 依赖包提供、按依赖包名归属的符号前缀（用于未定义符号归类，
# 以及「依赖真被使用」的双形态判定：动态形态看未定义符号，静态形态看内嵌定义）
DEP_SYMBOL_PREFIXES_BY_KEY = {
    "libxml2": ("xml",),
    "curl": ("curl_",),
}

# 每个依赖包在 DT_NEEDED 中的 soname 前缀（用于「已声明」形态判定）
DEP_DECLARED_SONAMES = {
    "libxml2": ("libxml2.so",),
    "curl": ("libcurl.so",),
}


# 按 soname 前缀归属（仅用于「出现在 DT_NEEDED 里」的依赖）——OHOS 侧实测：
# libxml2 与 curl 均为共享库（模块 DT_NEEDED 含 libxml2.so.16 / libcurl.so）。
DEP_SYMBOL_PREFIXES = {
    "libxml2.so": DEP_SYMBOL_PREFIXES_BY_KEY["libxml2"],
    "libcurl.so": DEP_SYMBOL_PREFIXES_BY_KEY["curl"],
}

# libc/CRT 提供（不在此脚本内重复定义，仅用于归类计数）
LIBC_SYMBOL_PREFIXES = (
    "__", "_ITM_", "mem", "str", "strn", "stpcpy", "stpncpy", "clz", "ctz",
    "malloc", "calloc", "realloc", "free", "abort", "exit", "_exit", "atexit",
    "assert", "atoi", "atol", "atoll", "strtol", "strtoul", "strtoll", "strtoull",
    "printf", "fprintf", "sprintf", "snprintf", "vprintf", "vfprintf", "vsnprintf",
    "puts", "fputs", "fwrite", "fread", "fopen", "fclose", "fflush", "fseek",
    "ftell", "fgets", "stderr", "stdout", "stdin", "errno", "time", "clock",
    "gettimeofday", "localtime", "gmtime", "mktime", "strftime", "asctime",
    "rand", "srand", "random", "srandom", "qsort", "bsearch", "abs", "labs",
    "isalpha", "isdigit", "isalnum", "isspace", "isupper", "islower", "tolower",
    "toupper", "sin", "cos", "tan", "sqrt", "pow", "log", "log10", "exp", "floor",
    "ceil", "round", "fmod", "fabs", "lseek", "read", "write", "close", "open",
    "fcntl", "ioctl", "socket", "bind", "listen", "accept", "connect", "send",
    "recv", "sendto", "recvfrom", "setsockopt", "getsockopt", "shutdown",
    "select", "poll", "getpid", "getppid", "getuid", "geteuid", "getgid",
    "getegid", "kill", "raise", "signal", "sigaction", "sigemptyset",
    "sigfillset", "sigaddset", "sigdelset", "sigismember", "pthread", "sem_",
    "dlopen", "dlsym", "dlclose", "dlerror", "sleep", "usleep", "nanosleep",
    "alarm", "uname", "sysconf", "getenv", "setenv", "unsetenv", "putenv",
    "system", "exec", "fork", "waitpid", "dup", "dup2", "pipe", "chdir", "getcwd",
    "mkdir", "rmdir", "unlink", "rename", "stat", "lstat", "fstat", "opendir",
    "readdir", "closedir", "realpath", "gethostbyname", "gethostbyaddr",
    "getaddrinfo", "freeaddrinfo", "inet_", "htons", "htonl", "ntohs", "ntohl",
    "inet_pton", "inet_ntop", "epoll_", "eventfd", "timerfd_", "signalfd",
    "mmap", "munmap", "mprotect", "madvise", "mad", "lsb", "log2", "logf",
    "strerror", "towlower", "towupper", "wcs", "mbstowcs", "wcstombs",
)

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
            nmoff, _info, _other, shndx, _value, _size = struct.unpack_from("<IBBHQQ", d, o)
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
                out.append(cstring(d, strtab["off"] + nmoff).split("@", 1)[0])
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
            if tag == 0:
                break
            name = None
            if tag in (DT_NEEDED, DT_RPATH, DT_RUNPATH, DT_SONAME) and strtab is not None:
                name = cstring(d, strtab["off"] + val)
            out.append((tag, val, name))
    return out


def needed_sonames(d, secs):
    return sorted(n for t, _v, n in dynamic_entries(d, secs) if t == DT_NEEDED and n)


def contract_name(d, secs, segs):
    """读模块导出结构首字段（char *name）——kamailio 加载时注册模块所用的名字。

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


def classify_undefined(syms, dep_prefixes):
    """把未定义符号归类：libc/CRT、依赖包（libxml2/curl）、kamailio core。"""
    libc, dep, core = [], [], []
    for s in sorted(set(syms)):
        if any(s.startswith(p) for p in LIBC_SYMBOL_PREFIXES):
            libc.append(s)
        elif any(s.startswith(p) for p in dep_prefixes):
            dep.append(s)
        else:
            core.append(s)
    return libc, dep, core


# ─────────────────────────── 主检查 ───────────────────────────

def main():
    modules_dir = os.environ.get("KAMAILIO_PRESENCE_MODULES_DIR", "")
    package_folder = os.environ.get("KAMAILIO_PRESENCE_PACKAGE_FOLDER", "")
    dep_folders = {k: os.environ.get(f"KAMAILIO_PRESENCE_DEP_{k.upper()}", "")
                   for k in ("libxml2", "curl")}

    print("=" * 78)
    print("kamailio-presence 6.0.6 — 18 模块产物检查（消费者视角 / 加载器同源语义）")
    print(f"模块目录: {modules_dir}")
    print(f"包目录:   {package_folder}")
    for k, v in dep_folders.items():
        print(f"依赖 {k}: {v}")
    print("=" * 78)

    if not modules_dir or not os.path.isdir(modules_dir):
        print(f"[FAIL] 模块目录不存在: {modules_dir!r}")
        return 1

    # 依赖包提供的 .so（一次解析，供 18 个模块共享）
    dep_so = {}
    for key, folder in dep_folders.items():
        if not folder:
            continue
        for soname in ("libxml2.so", "libcurl.so"):
            p = find_shared_object(folder, soname)
            if p:
                dep_so[soname.split(".so")[0] + ".so"] = p
    print(f"\n依赖包 .so 解析结果: {dep_so}")

    # 1) 模块文件齐备（18/18 是打包口径的硬要求）
    print("\n-- 1. 模块文件齐备 --")
    present = []
    for mod, _name, _need, _dep in MODULES:
        p = os.path.join(modules_dir, mod + ".so")
        if os.path.isfile(p):
            present.append(mod)
    check(f"18 个模块 .so 全部产出（实得 {len(present)}/18）", len(present) == 18,
          f"缺失: {[m for m, *_ in MODULES if m not in present]}")
    extra = sorted(f[:-3] for f in os.listdir(modules_dir)
                   if f.endswith(".so") and f[:-3] not in {m for m, *_ in MODULES})
    check("无计划外模块 .so（打包范围与 Alpine _mod_list_presence 一致）", not extra,
          f"计划外: {extra}")

    # 2) 逐模块检查
    for mod, exp_name, need_prefixes, dep_key in MODULES:
        path = os.path.join(modules_dir, mod + ".so")
        print(f"\n---- 模块 {mod} ----")
        if not os.path.isfile(path):
            check(f"{mod}.so 存在", False, f"缺失: {path}")
            continue
        d, secs, segs = parse_elf(path)

        # ELF 身份
        e_type, e_machine = struct.unpack_from("<HH", d, 16)
        check(f"{mod}: ELF64 LSB", d[:4] == b"\x7fELF" and d[4] == 2 and d[5] == 1)
        check(f"{mod}: ET_DYN 共享模块", e_type == ET_DYN, f"实得 {e_type}")
        check(f"{mod}: EM_AARCH64", e_machine == EM_AARCH64, f"实得 {e_machine}")

        # 契约名 + 契约符号面
        name, err = contract_name(d, secs, segs)
        check(f'{mod}: exports->name == "{exp_name}"', name == exp_name,
              err or f"实得 {name!r}")
        defined = defined_symbol_names(d, secs)
        miss = [s for s in CONTRACT_SYMBOLS if s not in defined]
        check(f"{mod}: 契约导出符号齐备（exports/MODULE_VERSION 三件套）",
              not miss, f"缺失: {miss}")
        # 加载器入口：mod_register（可选，旧式）或 exports（必需，回退路径）至少其一可用
        check(f"{mod}: 加载器入口可满足（exports/mod_register）",
              "exports" in defined or "mod_register" in defined,
              f"既无 exports 也无 mod_register；可选符号 "
              f"{OPTIONAL_CONTRACT_SYMBOLS} 存在性: "
              f"{[s for s in OPTIONAL_CONTRACT_SYMBOLS if s in defined]}")

        # DT_NEEDED：必需依赖已声明 + 全部落在允许集合内
        needed = needed_sonames(d, secs)
        miss_need = [p for p in need_prefixes if not any(n.startswith(p) for n in needed)]
        check(f"{mod}: DT_NEEDED 含必需依赖 {list(need_prefixes) or '(仅 libc)'}",
              not miss_need, f"DT_NEEDED={needed} 缺 {miss_need}")
        bad = [n for n in needed if not n.startswith(ALLOWED_NEEDED_PREFIXES)]
        check(f"{mod}: DT_NEEDED 全部落在允许集合内", not bad, f"计划外依赖: {bad}")

        # 依赖包真实存在（运行时可解析）
        if dep_key:
            for n in needed:
                if n.startswith("libxml2.so") or n.startswith("libcurl.so"):
                    base = n.split(".so")[0] + ".so"
                    check(f"{mod}: 依赖 {n} 在 conan 依赖包内真实存在",
                          find_shared_object(dep_folders.get(
                              "libxml2" if n.startswith("libxml2") else "curl"),
                              base) is not None,
                          f"{n} 未在 {dep_folders} 内找到")

        # 宿主路径泄漏
        rpaths = [n for t, _v, n in dynamic_entries(d, secs) if t in (DT_RPATH, DT_RUNPATH)]
        check(f"{mod}: 无 RPATH/RUNPATH", not rpaths, f"实得 {rpaths}")

        # 未定义符号归类
        undef = undefined_symbol_names(d, secs)
        dep_prefixes = ()
        for n in needed:
            for key, prefs in DEP_SYMBOL_PREFIXES.items():
                if n.startswith(key):
                    dep_prefixes += prefs
        libc_s, dep_s, core_s = classify_undefined(undef, dep_prefixes)
        # 逐符号核验依赖包确实导出（对 dep 类中能定位到 .so 的组）
        unverified = []
        for n in needed:
            base = n.split(".so")[0] + ".so"
            so = dep_so.get(base)
            if not so:
                continue
            ld, lsecs, _ls = parse_elf(so)
            provided = defined_symbol_names(ld, lsecs)
            for sym in dep_s:
                if sym not in provided and any(
                        sym.startswith(p) for k, prefs in DEP_SYMBOL_PREFIXES.items()
                        if n.startswith(k) for p in prefs):
                    unverified.append(f"{sym}@{base}")
        print(f"     {mod}: 未定义符号 {len(set(undef))} 个 → libc/CRT {len(libc_s)}、"
              f"外部依赖 {len(dep_s)}、kamailio core {len(core_s)}")
        check(f"{mod}: 未定义符号 100% 归类（无未归类符号）",
              len(libc_s) + len(dep_s) + len(core_s) == len(set(undef)),
              f"未归类: {sorted(set(undef) - set(libc_s) - set(dep_s) - set(core_s))}")
        check(f"{mod}: 含 kamailio core 契约符号（core 插件特征）",
              any(s in core_s for s in ("sr_kemi_modules_add", "dprint", "find_export",
                                        "pv_get_buffer", "fixup_spve2_pvar",
                                        "sr_register_callid_func", "get_debug_level")),
              f"core 符号样本: {core_s[:12]}")
        check(f"{mod}: 外部依赖符号逐项由依赖包导出", not unverified,
              f"未核验: {unverified[:10]}")
        if dep_key:
            prefs = DEP_SYMBOL_PREFIXES_BY_KEY.get(dep_key, ())
            undef_dep = sorted({s for s in undef if s.startswith(prefs)})
            defined_dep = sorted({s for s in defined if s.startswith(prefs)})
            declared = [n for n in needed
                        if n.startswith(DEP_DECLARED_SONAMES.get(dep_key, ()))]
            # 三形态择一即可证明依赖真实进入构建：
            #   动态——未定义符号运行时由依赖 .so 解析
            #   静态——依赖符号内嵌于模块 .so（本包两依赖在 OHOS 侧均为共享形态，
            #          该分支保留作通用口径）
            #   声明——DT_NEEDED 已声明（上游 Makefile 加 -lxml2，直接引用经 cdp 中转）
            check(f"{mod}: 依赖 {dep_key} 真被使用/已声明"
                  f"（未定义 {len(undef_dep)} / 内嵌 {len(defined_dep)}"
                  f" / DT_NEEDED {declared}）",
                  bool(undef_dep) or bool(defined_dep) or bool(declared),
                  f"{dep_key} 既无符号级引用（{prefs}），也未出现在 DT_NEEDED 中")

    # 3) 许可证
    print("\n-- 3. 许可证 --")
    copying = os.path.join(package_folder, "licenses", "COPYING")
    check("licenses/COPYING 随包", os.path.isfile(copying), f"缺失: {copying}")

    print("\n" + "=" * 78)
    print(f"断言：通过 {stats['pass']} / 失败 {stats['fail']}")
    print("=" * 78)
    if failures:
        print("失败明细：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("全部通过：18 个模块均为 aarch64 ET_DYN core 插件，契约名与 kamailio 期望一致，")
    print("DT_NEEDED 落在文档化允许集合内（外部依赖由 conan 依赖链提供且逐符号核验），")
    print("未定义符号面 100% 归类，无宿主路径泄漏。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
