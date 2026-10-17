#!/usr/bin/env python3
"""kamailio-db 6.0.6 产物检查（消费者视角，33 个模块 .so）— HarmonyOS PC / aarch64。

检查口径
--------
kamailio 模块 .so 由 kamailio 主程序运行时 loadmodule（dlopen）加载，core 符号由
主程序提供，因此模块**脱离主程序无法独立完成 dlopen 符号解析**。本检查按"加载器
同源语义"逐项验证产物本身，全部断言基于产物的真实字节（自解析 ELF，不依赖外部工具）：

  [1]  模块齐全性：33/33 个 .so 存在，名称集合与配方 MODULES 精确一致
  [H1] OHOS ABI 契约：每模块 64-bit / 小端 / ET_DYN / EM_AARCH64            （鸿蒙特有）
  [H2] OHOS 依赖自洽：DT_NEEDED ⊆ {libc.so}（无宿主/第三方 .so 泄漏）       （鸿蒙特有）
  [H3] RPATH 卫生：无 RPATH/RUNPATH（宿主路径泄漏会导致目标机加载失败）
  [H4] kamailio 模块接口：自解析 ELF 读取导出结构 `struct module_exports` 首字段
       `char *name`，与 kamailio 期望的模块名逐一比对（kamailio 加载时读该字段注册）
  [H5] 模块目标标识：`kamailio 6.0.6 (aarch64/linux)`（与 OHOS 上 core 口径一致）（鸿蒙特有）
  [H6] 编译标志集合：不含 USE_SCTP / HAVE_RESOLV_RES（同 OHOS core 口径）    （鸿蒙特有）
  [7]  许可证随包

退出码：0 = 全通过；1 = 存在失败项。
"""
import os
import struct
import sys

PACKAGE_FOLDER = os.environ.get("KAMAILIO_DB_PACKAGE_FOLDER", "")
MODULES_DIR = os.path.join(PACKAGE_FOLDER, "lib", "kamailio", "modules")

# 与 conanfile.py MODULES 一致（Alpine main/kamailio APKBUILD _mod_list_db）
MODULES = (
    "acc", "alias_db", "auth_db", "avpops", "cfg_db", "db_cluster", "db_flatstore",
    "dialog", "dispatcher", "domain", "drouting", "group", "htable", "imc", "matrix",
    "mohqueue", "msilo", "mtree", "pdt", "permissions", "pipelimit", "prefix_route",
    "p_usrloc", "registrar", "sipcapture", "siptrace", "speeddial", "sqlops",
    "topos_htable", "uac", "uri_db", "userblocklist", "usrloc",
)

# 33 个模块的导出契约名 == 目录名（实测，无 override）
CONTRACT_NAME_OVERRIDE = {}

# 允许的 DT_NEEDED：仅 OHOS musl 系统库 libc.so（本包 33 模块全为系统同名库之外
# 的无第三方依赖模块；dispatcher 的 Makefile LIBS=-lm 在 OHOS musl 下并入 libc）
ALLOWED_NEEDED = {"libc.so"}

# OHOS 上 core 的目标标识与应当**缺席**的编译标志
EXPECTED_TARGET_ID = "kamailio 6.0.6 (aarch64/linux)"
FORBIDDEN_FLAGS = ("USE_SCTP", "HAVE_RESOLV_RES")

SHT_SYMTAB, SHT_RELA, SHT_DYNAMIC, SHT_DYNSYM = 2, 4, 6, 11
DT_NEEDED, DT_RPATH, DT_RUNPATH = 1, 15, 29
EM_AARCH64 = 183
ET_DYN = 3

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
        p_offset, p_vaddr, _pp, p_filesz = struct.unpack_from("<QQQQ", d, o + 8)
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


def relocations(d, secs):
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
            if tag in (DT_NEEDED, DT_RPATH, DT_RUNPATH) and strtab is not None:
                name = cstring(d, strtab["off"] + val)
            out.append((tag, val, name))
    return out


def contract_name(d, secs, segs):
    """读取模块导出结构首字段（char *name）——kamailio 加载时注册模块所用的名字。"""
    entry = [s for s in all_symbols(d, secs) if s[0] == "exports" and s[1] != 0]
    if not entry:
        return None, "缺少 exports 导出符号"
    value = entry[0][2]
    rl = relocations(d, secs)
    target = rl[value][1] if value in rl else None
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


# ─────────────────────────── 检查项 ───────────────────────────

def module_problems(path, module):
    """返回 (problems, contract, needed, target_id_ok, forbidden)"""
    problems = []
    d, secs, segs = parse_elf(path)

    if d[:4] != b"\x7fELF":
        return ["非 ELF 文件"], None, [], False, []
    if d[4] != 2 or d[5] != 1:
        problems.append("非 64-bit 小端")
    e_type, e_machine = struct.unpack_from("<HH", d, 16)
    if e_type != ET_DYN:
        problems.append(f"e_type={e_type}（期望 ET_DYN）")
    if e_machine != EM_AARCH64:
        problems.append(f"e_machine={e_machine}（期望 AArch64={EM_AARCH64}）")

    name, err = contract_name(d, secs, segs)
    expected = CONTRACT_NAME_OVERRIDE.get(module, module)
    if err:
        problems.append(err)
    elif name != expected:
        problems.append(f"契约名 {name!r} != 期望 {expected!r}")

    needed = []
    for tag, _val, dep in dynamic_entries(d, secs):
        if tag == DT_NEEDED and dep:
            needed.append(dep)
            if dep not in ALLOWED_NEEDED:
                problems.append(f"DT_NEEDED 出现非预期动态依赖 {dep}")
        elif tag in (DT_RPATH, DT_RUNPATH):
            problems.append(f"存在 {'RPATH' if tag == DT_RPATH else 'RUNPATH'}：宿主路径泄漏")

    target_ok = EXPECTED_TARGET_ID.encode() in d
    forbidden = [f for f in FORBIDDEN_FLAGS if f.encode() in d]
    return problems, name, needed, target_ok, forbidden


def main():
    print("=" * 76)
    print("kamailio-db 6.0.6 — 产物检查（消费者视角 / 加载器同源语义 / OHOS aarch64）")
    print(f"包目录: {PACKAGE_FOLDER}")
    print("=" * 76)

    if not os.path.isdir(MODULES_DIR):
        print(f"[FAIL] 模块目录不存在: {MODULES_DIR}")
        return 1

    # [1] 模块齐全性
    present = sorted(f[:-3] for f in os.listdir(MODULES_DIR) if f.endswith(".so"))
    expected = sorted(MODULES)
    check(f"[1] {len(MODULES)} 个 DB 模块全部打包（实际 {len(present)} 个；Alpine _mod_list_db 口径）",
          present == expected, f"期望 {expected}；实际 {present}")

    # [H1]-[H4] 逐模块
    print(f"\n-- [H1][H2][H3][H4][H5][H6] 逐模块检查（{len(MODULES)} 项）--")
    contracts = {}
    target_ids_ok = []
    forbidden_seen = {}
    for module in MODULES:
        path = os.path.join(MODULES_DIR, f"{module}.so")
        if not os.path.isfile(path):
            check(f"{module}.so", False, "文件缺失")
            continue
        problems, name, needed, target_ok, forbidden = module_problems(path, module)
        contracts[module] = name or "-"
        target_ids_ok.append((module, target_ok))
        if forbidden:
            forbidden_seen[module] = forbidden
        check(f"{module}.so（[H1]ELF64/aarch64/ET_DYN + [H2]NEEDED⊆{{libc.so}} + "
              f"[H3]无RPATH + [H4]契约名）",
              not problems,
              f"契约名={name!r}, NEEDED={sorted(set(needed))}" if not problems else "; ".join(problems))

    # [H5] 目标标识
    print("\n-- 鸿蒙平台契约（全局）--")
    bad_ids = [m for m, ok in target_ids_ok if not ok]
    check(f"[H5] 全部模块目标标识为 {EXPECTED_TARGET_ID!r}"
          "（与 OHOS 上 core 口径一致；不一致 kamailio 将拒绝加载）",
          not bad_ids and len(target_ids_ok) == len(MODULES),
          f"不符合的模块: {bad_ids or '（缺失）'}")

    # [H6] 编译标志集合
    check("[H6] 全部模块编译标志集合不含 " + " / ".join(FORBIDDEN_FLAGS)
          + "（OHOS 无 SCTP 头、libc 无 _res，须与 core 一致）",
          not forbidden_seen, f"命中: {forbidden_seen}")

    # [7] 许可证
    print("\n-- 许可证 --")
    copying = os.path.join(PACKAGE_FOLDER, "licenses", "COPYING")
    check("[7] licenses/COPYING 随包", os.path.isfile(copying), f"缺失: {copying}")

    # 汇总
    print("\n" + "=" * 76)
    print(f"断言：通过 {stats['pass']} / 失败 {stats['fail']}")
    print("模块导出契约名（exports->name）：")
    for i in range(0, len(MODULES), 4):
        row = MODULES[i:i + 4]
        print("    " + "  ".join(f"{m:16s} -> {contracts.get(m, '(缺失)'):16s}" for m in row))
    print("=" * 76)
    if failures:
        print("失败明细：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"全部通过：{len(MODULES)} 个模块均为 aarch64 ET_DYN 共享模块，"
          "契约名与 kamailio 期望一致，")
    print("依赖闭合于 OHOS libc（无宿主/第三方 .so 泄漏），无 RPATH，")
    print("目标标识与编译标志集合与 OHOS 上 core 口径一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
