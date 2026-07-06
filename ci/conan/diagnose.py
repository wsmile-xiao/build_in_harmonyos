#!/usr/bin/env python3
"""CI 错误诊断引擎 — 扫描构建日志, 匹配 hint_rules.json 规则, 输出可操作的修复建议。

用法:
    python3 diagnose.py <build_log_path> [hint_rules.json]

退出码:
    0 = 正常完成 (无论是否匹配到规则)
    1 = 参数错误或文件不存在

输出格式 (stdout):
    ─── 修复建议 ───
    [hint] 标题
           详细说明
    ─── end 修复建议 ───

如果未匹配任何规则, 输出兜底提示。
"""
import json
import re
import sys
import os

DEFAULT_RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "hint_rules.json")


def load_rules(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_vars(log_text, extract_spec):
    """从日志中用 extract 规则提取变量, 返回 {占位符: 值} 字典。"""
    if not extract_spec:
        return {}
    result = {}
    for var_name, sub_pattern in extract_spec.items():
        m = re.search(sub_pattern, log_text, re.IGNORECASE)
        if m:
            # 如果有捕获组取 group(1), 否则取 group(0)
            result[var_name] = m.group(1) if m.groups() else m.group(0)
    return result


def fill_template(template, variables):
    """用 variables 字典填充模板中的 {key} 占位符。"""
    try:
        return template.format(**variables)
    except (KeyError, IndexError):
        return template


def diagnose(log_path, rules_path):
    # 读取日志
    if not os.path.isfile(log_path):
        print(f"[diagnose] 日志文件不存在: {log_path}", file=sys.stderr)
        return 1
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        log_text = f.read()

    # 读取规则
    rules = load_rules(rules_path)

    print("─── 修复建议 ───")

    # 互斥规则: 高优先级规则命中后, 跳过低优先级规则, 避免重复提示
    EXCLUSIVE_GROUPS = {
        # github_timeout 命中后不再报 network_other
        "github_timeout": "network_other",
        # compile_linker 命中后不再报 compile_make
        "compile_linker": "compile_make",
    }

    matched = 0
    suppressed = set()
    for rule in rules:
        rid = rule.get("id", "unknown")
        if rid in suppressed:
            continue

        pattern = rule["pattern"]
        hint_template = rule["hint"]
        extract_spec = rule.get("extract", {})

        if re.search(pattern, log_text, re.IGNORECASE):
            variables = extract_vars(log_text, extract_spec)
            hint_text = fill_template(hint_template, variables)

            # 第一行用 [hint] 前缀, 后续行用缩进对齐
            hint_lines = hint_text.split("\n")
            print(f"[hint] {hint_lines[0]}")
            for line in hint_lines[1:]:
                print(f"       {line}")
            print()

            matched += 1

            # 如果当前规则有互斥的低优先级规则, 加入 suppress 列表
            if rid in EXCLUSIVE_GROUPS:
                suppressed.add(EXCLUSIVE_GROUPS[rid])

    if matched == 0:
        print("[hint] 未能自动诊断失败原因, 请查看上方完整构建日志")
        print("       常见排查: 1) conanfile.py 语法 2) conandata.yml URL/sha256 3) 系统依赖")

    print("─── end 修复建议 ───")
    return 0


def main():
    if len(sys.argv) < 2:
        print("用法: python3 diagnose.py <build_log_path> [hint_rules.json]", file=sys.stderr)
        return 1

    log_path = sys.argv[1]
    rules_path = sys.argv[2] if len(sys.argv) >= 3 else DEFAULT_RULES_PATH

    if not os.path.isfile(rules_path):
        print(f"[diagnose] 规则文件不存在: {rules_path}", file=sys.stderr)
        return 1

    return diagnose(log_path, rules_path)


if __name__ == "__main__":
    sys.exit(main())
