#!/usr/bin/env python3
"""kamailio-extras 6.0.6 产物检查（消费者视角，31 个模块 .so）— HarmonyOS PC / aarch64。

检查口径
--------
kamailio 模块 .so 由 kamailio 主程序运行时 loadmodule（dlopen）加载，核心符号
（core API）由主程序提供，因此模块**脱离主程序无法独立 dlopen**。本检查按
"加载器同源语义"逐项验证产物本身：

  1. 模块齐全性：31/31 个 .so 存在，名称集合与配方 MODULES 精确一致
  2. ELF 身份：每模块 64-bit / 小端 / ET_DYN / EM_AARCH64
  3. 模块契约：自解析 ELF（PT_LOAD + .dynsym/.symtab + .rela.dyn）读取导出结构
     `struct module_exports` 首字段 `char *name`，与 kamailio 期望的模块名逐一
     比对（kamailio 加载时正是读该字段注册模块）
  4. 依赖闭合：DT_NEEDED 必须落在文档化允许集合内（31 个模块 = libc.so；cnxcc 另有
     conan 依赖 libevent.so）。hiredis 必须**静态链入**（其包仅提供 libhiredis.a），
     并以其 API 符号存在为证
  5. 无 RPATH/RUNPATH（宿主路径泄漏会导致目标机加载失败）
  6. 许可证随包

断言全部基于产物真实字节，不依赖外部工具（自解析 ELF），非纯断言。
退出码：0 = 全通过；1 = 存在失败项。
"""
import os
import struct
import sys

PACKAGE_FOLDER = os.environ.get("KAMAILIO_EXTRAS_PACKAGE_FOLDER", "")
MODULES_DIR = os.path.join(PACKAGE_FOLDER, "lib", "kamailio", "modules")

# 与 conanfile.py MODULES 一致（Alpine main/kamailio APKBUILD _mod_list_extras）
MODULES = (
    "auth_diameter", "auth_xkeys", "call_control", "call_obj", "cnxcc", "dmq",
    "dmq_usrloc", "domainpolicy", "file_out", "influxdbc", "log_custom", "msrp",
    "nosip", "pdb", "pvtpl", "qos", "rtjson", "sca", "seas", "sms", "ss7ops",
    "sst", "statsd", "tcpops", "timer", "tmrec", "tsilo", "uac_redirect",
    "xhttp", "xhttp_rpc", "xprint",
)

# 上游事实：文件名 ss7ops.so，模块内声明名为 "ss7"
# （src/modules/ss7ops/ss7ops_mod.c:95 —— "ss7", /*!< module name */）
CONTRACT_NAME_OVERRIDE = {"ss7ops": "ss7"}

# cnxcc 静态链入 hiredis 的 API 符号（hiredis 包仅提供 libhiredis.a）
CNXCC_HIREDIS_SYMBOLS = ("redisConnect", "redisCommand")

# DT_NEEDED 允许集合（文档化口径）
#   libc.so    —— 所有模块恒有（OHOS musl 系统运行库）
#   libevent.so—— 仅 cnxcc：编译期由 conan libevent/2.1.13 提供；OHOS 侧该包只发布
#                 .so（无 .a），且 OHOS sysroot 内不含 libevent → 非"系统同名库"，
#                 按仓库口径（非系统同名库默认动态、由 conan 依赖链管理）允许动态
#   libhiredis.so **不在**允许集合：hiredis 必须静态链入（包内仅 .a）
ALLOWED_NEEDED = {"libc.so"}
ALLOWED_NEEDED_BY_MODULE = {"cnxcc": {"libevent.so"}}

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


def relocations(d, secs):
    """{r_offset: r_addend}（AArch64 RELA：数据指针的值在 addend 中）"""
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
            if tag in (DT_NEEDED, DT_RPATH, DT_RUNPATH) and strtab is not None:
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
    entry = [s for s in all_symbols(d, secs) if s[0] == "exports" and s[1] != 0]
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


# ─────────────────────────── 检查项 ───────────────────────────

def module_problems(path, module):
    problems = []
    d, secs, segs = parse_elf(path)

    if d[:4] != b"\x7fELF":
        return ["非 ELF 文件"], None
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

    allowed = ALLOWED_NEEDED | ALLOWED_NEEDED_BY_MODULE.get(module, set())
    for tag, _val, dep in dynamic_entries(d, secs):
        if tag == DT_NEEDED and dep:
            if dep not in allowed:
                problems.append(
                    f"DT_NEEDED 出现非预期动态依赖 {dep}（允许集合 {sorted(allowed)}）")
        elif tag in (DT_RPATH, DT_RUNPATH):
            problems.append(f"存在 {'RPATH' if tag == DT_RPATH else 'RUNPATH'}：宿主路径泄漏")

    return problems, name


def main():
    print("=" * 74)
    print("kamailio-extras 6.0.6 — 产物检查（消费者视角 / 加载器同源语义）")
    print(f"包目录: {PACKAGE_FOLDER}")
    print("=" * 74)

    if not os.path.isdir(MODULES_DIR):
        print(f"[FAIL] 模块目录不存在: {MODULES_DIR}")
        return 1

    # 1. 模块齐全性
    present = sorted(f[:-3] for f in os.listdir(MODULES_DIR) if f.endswith(".so"))
    expected = sorted(MODULES)
    check(f"31 个 extras 模块全部打包（{len(present)} 个）", present == expected,
          f"期望 {expected}；实际 {present}")

    # 2. 逐模块：ELF 身份 + 模块契约 + 依赖闭合 + 宿主路径
    print(f"\n-- 逐模块检查（{len(MODULES)} 项）--")
    contracts = {}
    for module in MODULES:
        path = os.path.join(MODULES_DIR, f"{module}.so")
        if not os.path.isfile(path):
            check(f"{module}.so", False, "文件缺失")
            continue
        problems, name = module_problems(path, module)
        contracts[module] = name or "-"
        detail = f"契约名={name!r}" if not problems else "; ".join(problems)
        check(f"{module}.so（ELF aarch64/ET_DYN + 模块契约 + 依赖闭合 + 无 RPATH）",
              not problems, detail)

    # 3. cnxcc 依赖链入方式证据
    print("\n-- cnxcc 依赖链入方式 --")
    cnxcc = os.path.join(MODULES_DIR, "cnxcc.so")
    if os.path.isfile(cnxcc):
        d, secs, _segs = parse_elf(cnxcc)
        defined = {s[0] for s in all_symbols(d, secs) if s[1] != 0}
        missing = [s for s in CNXCC_HIREDIS_SYMBOLS if s not in defined]
        check("cnxcc 静态链入 hiredis API 符号（符号已在 .dynsym 定义）", not missing,
              f"缺失符号: {missing}")
        needed = sorted(dep for tag, _v, dep in dynamic_entries(d, secs)
                        if tag == DT_NEEDED and dep)
        check("cnxcc 无 libhiredis.so 动态依赖（hiredis 静态链入）",
              "libhiredis.so" not in needed, f"DT_NEEDED={needed}")
        check("cnxcc 动态依赖 ⊆ {libc.so, libevent.so}（libevent 由 conan 依赖链提供）",
              set(needed) <= (ALLOWED_NEEDED | ALLOWED_NEEDED_BY_MODULE["cnxcc"]),
              f"DT_NEEDED={needed}")
    else:
        check("cnxcc.so 存在", False, "文件缺失")

    # 4. 许可证
    print("\n-- 许可证 --")
    copying = os.path.join(PACKAGE_FOLDER, "licenses", "COPYING")
    check("licenses/COPYING 随包", os.path.isfile(copying), f"缺失: {copying}")

    # 汇总
    print("\n" + "=" * 74)
    print(f"断言：通过 {stats['pass']} / 失败 {stats['fail']}")
    print("模块契约名（exports->name）：")
    for module in MODULES:
        print(f"    {module:16s} -> {contracts.get(module, '(缺失)')}")
    print("=" * 74)
    if failures:
        print("失败明细：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("全部通过：31 个模块均为 aarch64 ET_DYN 共享模块，契约名与 kamailio 期望一致，")
    print("依赖落在文档化允许集合内（hiredis 静态链入；cnxcc 的 libevent 由 conan 依赖链")
    print("提供）且无宿主路径泄漏。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
