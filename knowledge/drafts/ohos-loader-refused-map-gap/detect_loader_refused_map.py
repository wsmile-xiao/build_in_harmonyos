#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OHOS 设备「依赖二进制存在却被拒绝映射」判据实现（知识包 ohos-loader-refused-map-gap）。

问题类别：消费者/测试运行期加载依赖失败，错误点名的 .so **文件存在**，
但设备加载器拒绝把它映射进进程；同设备上其它依赖内容可正常映射。

用法
----
  # ① 判读既有构建日志（conan create / W3 输出落文件后）
  python3 detect_loader_refused_map.py --log conan-create.log

  # ② 直接探测 soname（用 ctypes 真实尝试映射，最有力）
  python3 detect_loader_refused_map.py --probe libXft.so.2 libfontconfig.so.1

  # ③ 组合：先按日志点名，再逐个真实探测
  python3 detect_loader_refused_map.py --log conan-create.log --probe-named

  # 库搜索路径：默认取 $LD_LIBRARY_PATH + 系统目录；也可显式指定
  python3 detect_loader_refused_map.py --log x.log --lib-path /a/lib:/b/lib

退出码
------
  0  判为「存在但被拒绝映射」（设备映射策略面；按 §5.1 处置）
  1  判为「真缺库 / 真缺陷」（缺文件、名字写错、ELF 不可用等；必须修，不得放行）
  2  未发现加载错误（无需本知识包介入）

设计约束
--------
* 仅用标准库；不写死任何本机绝对路径（路径一律来自参数、环境变量或日志内容）。
* 判据见同目录 README.md §3：**依赖是否真缺**，而不是“日志里有没有 Permission denied”
  ——实测 musl exec 路径的消息形如 `<soname>: (needed by …)`（原因为空），
  只有 dlopen 路径才带 `Permission denied`。
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import sys

# musl exec 路径：`Error loading shared library <name>: <reason> (needed by <obj>)`
MUSL_LOAD_RE = re.compile(r"Error loading shared library (?P<name>[^\s:]+)\s*:\s*(?P<reason>[^(]*)")
# dlopen 路径（ctypes/dlerror 风格）：`<name>: Permission denied` / `<path>: Permission denied`
DLOPEN_RE = re.compile(r"(?P<name>[^\s:]+\.so[.\w-]*)\s*:\s*(?P<reason>Permission denied)")

# 出现这些原因说明是产物/打包自身问题，不是“设备拒绝映射”
REAL_DEFECT_REASONS = (
    "invalid elf header",
    "exec format error",
    "wrong elf class",
    "not a valid dynamic library",
    "no such file or directory",
    "cannot open shared object file",
)

DEFAULT_SYSTEM_DIRS = (
    "/lib",
    "/lib64",
    "/usr/lib",
    "/usr/lib64",
    "/system/lib64",
    "/vendor/lib64",
)


def system_dirs() -> list[str]:
    """平台自带库目录（用于“真缺库”判定时覆盖加载器默认搜索面）。"""
    return [d for d in DEFAULT_SYSTEM_DIRS if os.path.isdir(d)]


def search_dirs(lib_path_arg: str | None) -> list[str]:
    dirs: list[str] = []
    raw = lib_path_arg if lib_path_arg is not None else os.environ.get("LD_LIBRARY_PATH", "")
    for d in raw.split(":"):
        d = d.strip()
        if d and d not in dirs:
            dirs.append(d)
    for d in system_dirs():
        if d not in dirs:
            dirs.append(d)
    return dirs


def resolve(name: str, dirs: list[str]) -> str | None:
    """把 soname / 绝对路径解析为实际文件路径；解析不到返回 None。"""
    if os.sep in name:
        return name if os.path.exists(name) else None
    for d in dirs:
        cand = os.path.join(d, name)
        if os.path.exists(cand):
            return cand
    return None


def probe_load(path: str) -> tuple[str, str]:
    """真实尝试把文件映射进本进程（ctypes）。返回 (状态, 说明)。"""
    if not os.path.exists(path):
        return "missing", "文件不存在"
    try:
        ctypes.CDLL(path)
        return "ok", "可正常映射"
    except OSError as exc:  # 映射失败：Permission denied / invalid ELF / 依赖缺失级联
        return "refused", f"{type(exc).__name__}: {exc}"
    except Exception as exc:  # noqa: BLE001 - 诊断脚本，任何异常都只是证据
        return "error", f"{type(exc).__name__}: {exc}"


def parse_log(text: str) -> dict[str, str]:
    """抽取日志里点名的库名 -> 原因（原因可能为空字符串）。"""
    named: dict[str, str] = {}
    for m in MUSL_LOAD_RE.finditer(text):
        named.setdefault(m.group("name"), m.group("reason").strip())
    for m in DLOPEN_RE.finditer(text):
        named.setdefault(m.group("name"), m.group("reason").strip())
    return named


def classify(named: dict[str, str], dirs: list[str], do_probe: bool) -> tuple[int, list[dict]]:
    """按“依赖是否真缺”分类。返回 (退出码, 逐库记录)。"""
    records: list[dict] = []
    missing = 0
    refused = 0
    real_defect = 0

    for name, reason in sorted(named.items()):
        path = resolve(name, dirs)
        rec: dict = {"name": name, "reason_in_log": reason, "path": path}
        if path is None:
            rec["verdict"] = "missing"
            missing += 1
            records.append(rec)
            continue

        if do_probe:
            status, detail = probe_load(path)
            rec["probe"] = status
            rec["probe_detail"] = detail
            if status == "ok":
                rec["verdict"] = "loadable"
            elif status == "missing":
                rec["verdict"] = "missing"
                missing += 1
            else:
                rec["verdict"] = "present-but-refused"
                refused += 1
        else:
            rec["probe"] = "skipped"
            rec["verdict"] = "present-unverified"
            refused += 1

        low_reason = reason.lower()
        if any(bad in low_reason for bad in REAL_DEFECT_REASONS):
            rec["verdict"] = "real-defect"
            real_defect += 1
            refused = max(0, refused - 1)

        records.append(rec)

    if missing or real_defect:
        return 1, records
    if refused:
        return 0, records
    return 2, records


def render(records: list[dict], dirs: list[str], as_json: bool) -> None:
    if as_json:
        print(json.dumps({"search_dirs": dirs, "records": records}, ensure_ascii=False, indent=2))
        return
    print("== 依赖映射判据（loader-refused-map gap）==")
    print("   搜索路径: " + (":".join(dirs) if dirs else "(空)"))
    for rec in records:
        line = f"   - {rec['name']}: {rec['verdict']}"
        if rec.get("path"):
            line += f"  -> {rec['path']}"
        if rec.get("probe_detail"):
            line += f"  [{rec['probe']}: {rec['probe_detail']}]"
        if rec.get("reason_in_log"):
            line += f"  (log reason: {rec['reason_in_log'] or '空'})"
        print(line)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OHOS 依赖二进制被拒绝映射判据")
    ap.add_argument("--log", help="构建/运行日志文件（含 musl 加载错误）")
    ap.add_argument("--probe", nargs="*", default=[], help="直接探测的 soname 或绝对路径")
    ap.add_argument("--probe-named", action="store_true",
                    help="对日志点名的每个库再真实探测一次映射（最有力）")
    ap.add_argument("--lib-path", help="库搜索目录（冒号分隔）；默认 $LD_LIBRARY_PATH + 系统目录")
    ap.add_argument("--no-system-paths", action="store_true", help="只在 --lib-path/$LD_LIBRARY_PATH 中查找")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出（供 harness/CI 消费）")
    args = ap.parse_args(argv)

    dirs = search_dirs(args.lib_path)
    if args.no_system_paths:
        dirs = [d for d in dirs if d not in system_dirs()]

    named: dict[str, str] = {}
    if args.log:
        try:
            with open(args.log, "r", encoding="utf-8", errors="replace") as fh:
                named.update(parse_log(fh.read()))
        except OSError as exc:
            print(f"无法读取日志 {args.log}: {exc}", file=sys.stderr)
            return 2
    for name in args.probe:
        named.setdefault(name, "")

    if not named:
        print("未发现共享库加载错误（消费者可能已正常运行）=> 无需本知识包介入")
        return 2

    code, records = classify(named, dirs, do_probe=bool(args.probe or args.probe_named))
    render(records, dirs, args.json)

    if code == 0:
        print("判定：存在但被拒绝映射（设备映射策略面）——按 README §5.1 处置：")
        print("      测试脚本分类放行 + 符号级降级验证 + 在 notes/PR 如实记录证据。")
    elif code == 1:
        print("判定：真缺库/真缺陷（点名库解析不到，或 ELF 不可用）——必须修，不得放行：")
        print("      补齐依赖（R36）或修复产物（缺 DT_SONAME / 架构不符）后重跑。")
        for rec in records:
            if rec["verdict"] in ("missing", "real-defect"):
                print(f"      - {rec['name']}: {rec['verdict']}")
    else:
        print("判定：点名的库均可正常映射（或消费者成功）——无需介入。")
    return code


if __name__ == "__main__":
    sys.exit(main())
