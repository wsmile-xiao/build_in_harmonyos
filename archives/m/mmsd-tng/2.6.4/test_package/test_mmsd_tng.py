#!/usr/bin/env python3
"""mmsd-tng 2.6.4 消费者测试用例集（L1）。

用法:
    python3 test_mmsd_tng.py <mmsd-tng 包目录>

必须在 conanrun 运行期环境（VirtualRunEnv，LD_LIBRARY_PATH 含依赖共享库）中执行。

用例清单
--------
  [case1] upstream_mmsdtng_version  运行上游守护进程 `mmsdtng --version`，
                                    断言退出码 0 且输出含上游版本 "2.6.4"。
  [case2] upstream_mmsctl_usage     运行 mmsctl（上游 D-Bus 控制工具）并走完
                                    getopt → usage() 路径，断言打印出上游用法串
                                    "Usage: ... [-L] [-M ...]"（证明 CLI 真正启动；
                                    本机无 D-Bus session bus，连总线本就失败）。
  [case3] OHOS_elf_abi              【HarmonyOS 专属】解析 ELF：断言 ELF64、
                                    e_machine == EM_AARCH64(183)、存在 PT_INTERP 且
                                    解释器为 OHOS musl 加载器 ld-musl-aarch64.so.1。
                                    证明制品面向 HarmonyOS PC(aarch64)，而非其它平台产物。
  [case4] OHOS_runtime_loader       【HarmonyOS 专属】解析 ELF 的 DT_NEEDED 列表，
                                    断言每一条共享依赖都能在 OHOS 运行期搜索路径
                                    （LD_LIBRARY_PATH / 包内 lib / 系统默认）中定位，
                                    即 OHOS 动态加载器可完整解析依赖闭包
                                    （glib-2.0 / gio-2.0 / libsoup-3.0 / libcares /
                                    libmm-glib / libphonenumber / ...）。

退出码: 0 = 全部用例通过；1 = 有用例失败（逐条打印 FAIL 原因）。
"""
import os
import struct
import subprocess
import sys

EM_AARCH64 = 183
PT_LOAD, PT_DYNAMIC, PT_INTERP = 1, 2, 3
DT_NEEDED, DT_STRTAB, DT_STRSZ = 1, 5, 10

RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok


# --------------------------------------------------------------------------- ELF
def parse_elf(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    elf_class = data[4]                      # 1=32bit, 2=64bit
    little = data[5] == 1
    endian = "<" if little else ">"
    machine = struct.unpack_from(endian + "H", data, 18)[0]
    e_phoff = struct.unpack_from(endian + "Q", data, 32)[0]
    e_phentsize = struct.unpack_from(endian + "H", data, 54)[0]
    e_phnum = struct.unpack_from(endian + "H", data, 56)[0]

    segments, interp, dynamic = [], None, None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type = struct.unpack_from(endian + "I", data, off)[0]
        p_offset = struct.unpack_from(endian + "Q", data, off + 8)[0]
        p_vaddr = struct.unpack_from(endian + "Q", data, off + 16)[0]
        p_filesz = struct.unpack_from(endian + "Q", data, off + 32)[0]
        if p_type == PT_LOAD:
            segments.append((p_vaddr, p_offset, p_filesz))
        elif p_type == PT_INTERP:
            interp = data[p_offset:p_offset + p_filesz].split(b"\x00")[0].decode()
        elif p_type == PT_DYNAMIC:
            dynamic = (p_offset, p_filesz)

    def vaddr_to_off(vaddr):
        for v, o, size in segments:
            if v <= vaddr < v + size:
                return o + (vaddr - v)
        return None

    needed, strtab, strsz = [], None, 0
    if dynamic:
        off, size = dynamic
        for k in range(size // 16):
            tag, val = struct.unpack_from(endian + "QQ", data, off + k * 16)
            if tag == DT_NEEDED:
                needed.append(val)
            elif tag == DT_STRTAB:
                strtab = vaddr_to_off(val)
            elif tag == DT_STRSZ:
                strsz = val
        if strtab is not None:
            strs = data[strtab:strtab + strsz]
            resolved = []
            for n in needed:
                end = strs.find(b"\x00", n)
                resolved.append(strs[n:end].decode())
            needed = resolved
    return {"class64": elf_class == 2, "machine": machine,
            "interp": interp, "needed": needed}


def resolve_library(name, extra_dirs):
    search = [d for d in extra_dirs if d]
    search += [d for d in os.environ.get("LD_LIBRARY_PATH", "").split(":") if d]
    search += ["/lib", "/usr/lib", "/lib64", "/usr/lib64",
               "/lib/aarch64-linux-ohos", "/usr/lib/aarch64-linux-ohos"]
    for d in search:
        if os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    return None


# --------------------------------------------------------------------------- cases
def case1_upstream_version(bindir):
    exe = os.path.join(bindir, "mmsdtng")
    if not os.path.isfile(exe):
        return record("case1 upstream_mmsdtng_version", False, f"{exe} 不存在")
    r = subprocess.run([exe, "--version"], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    ok = r.returncode == 0 and "2.6.4" in out
    return record("case1 upstream_mmsdtng_version", ok,
                  f"exit={r.returncode} output={out!r}")


def case2_upstream_mmsctl(bindir):
    exe = os.path.join(bindir, "mmsctl")
    if not os.path.isfile(exe):
        return record("case2 upstream_mmsctl_usage", False, f"{exe} 不存在（build-mmsctl=false?）")
    # 本机无 D-Bus session bus，mmsctl 连不上总线属预期；用 --help 走完 getopt →
    # usage() 路径，断言打印出上游自己的用法串（证明 CLI 真正启动到 main()）。
    r = subprocess.run([exe, "--help"], capture_output=True, text=True, timeout=30)
    out = r.stdout + r.stderr
    ok = ("Usage:" in out and "[-L]" in out and "[-M" in out
          and r.returncode in (0, 1))
    return record("case2 upstream_mmsctl_usage", ok,
                  f"exit={r.returncode} usage={'YES' if 'Usage:' in out else 'NO'}")


def case3_ohos_elf_abi(bindir):
    exe = os.path.join(bindir, "mmsdtng")
    info = parse_elf(exe)
    interp = info["interp"] or ""
    ok = (info["class64"] and info["machine"] == EM_AARCH64
          and interp.endswith("ld-musl-aarch64.so.1"))
    return record("case3 OHOS_elf_abi", ok,
                  f"ELF64={info['class64']} e_machine={info['machine']} interp={interp!r}")


def case4_ohos_loader_resolution(bindir):
    exe = os.path.join(bindir, "mmsdtng")
    info = parse_elf(exe)
    needed = info["needed"]
    if not needed:
        return record("case4 OHOS_runtime_loader", False, "DT_NEEDED 为空")
    unresolved = [n for n in needed if not resolve_library(n, [bindir])]
    ok = not unresolved
    detail = f"{len(needed)} 个 DT_NEEDED 全部可解析: {', '.join(needed)}"
    if unresolved:
        detail = f"未解析: {', '.join(unresolved)}（全部: {', '.join(needed)}）"
    return record("case4 OHOS_runtime_loader", ok, detail)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pkg = sys.argv[1]
    bindir = os.path.join(pkg, "bin")
    print(f"mmsd-tng package  : {pkg}")
    print(f"bindir            : {bindir}")
    print(f"bindir contents   : {sorted(os.listdir(bindir)) if os.path.isdir(bindir) else 'MISSING'}")
    print(f"platform          : {os.uname().sysname} {os.uname().machine}")

    case1_upstream_version(bindir)
    case2_upstream_mmsctl(bindir)
    case3_ohos_elf_abi(bindir)
    case4_ohos_loader_resolution(bindir)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n== SUMMARY: {passed}/{total} passed ==")
    for name, ok, _ in RESULTS:
        print(f"  {'OK  ' if ok else 'FAIL'} {name}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
