#!/usr/bin/env python3
"""Test that ace-window.el is properly installed and structurally valid.

R34 临时豁免（Temporary exemption from R34）：
- R34 要求 test_package 必须调用被测包的 API 或执行其二进制。
- 解除条件：本测试在无 Emacs 运行时的构建环境中，以「结构化实质验证」
  最大化逼近 R34 意图——除文件存在性/非空性外，还验证：
  ① 包元数据（Version / Package-Requires）与上游一致；
  ② 关键 API 定义存在（(provide 'ace-window) / (defun ace-window /
     (defun aw-select / (defun aw-window-list / (defcustom aw-keys /
     (require 'avy)）；
  ③ S-表达式括号平衡（捕捉截断/损坏/伪造 stub）；
  ④ 顶层定义数量阈值（防止仅有少量字符串标记的伪造文件通过）。
- 原因：ace-window 为纯 Emacs Lisp 包，实际调用 API 需 Emacs 运行时
  （`emacs -batch -l ace-window.el --eval "(ace-window)"`），而 emacs
  尚未完成 OHOS 移植（详见 notes.md，预期 3~6 个月）。
- 恢复路径：emacs 完成 OHOS 适配并发布到制品仓后，本测试须改为实际
  加载 ace-window.el 并调用其 API，方可移除本条豁免。
"""
import os
import re
import sys


def check_paren_balance(content):
    """验证 S-表达式括号平衡。忽略字符串/注释内的括号。

    返回 (balanced, depth, max_depth)；不平衡返回 (False, depth, max_depth)。
    """
    depth = 0
    max_depth = 0
    in_string = False
    in_comment = False
    i = 0
    n = len(content)
    while i < n:
        c = content[i]
        if in_comment:
            if c == "\n":
                in_comment = False
            i += 1
            continue
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if c == ";":
            in_comment = True
            i += 1
            continue
        if c == '"':
            in_string = True
            i += 1
            continue
        if c == "(":
            depth += 1
            max_depth = max(max_depth, depth)
        elif c == ")":
            depth -= 1
            if depth < 0:
                return False, depth, max_depth
        i += 1
    return depth == 0, depth, max_depth


def main():
    pkg_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    el_file = os.path.join(pkg_dir, "lib", "site-lisp", "ace-window.el")

    # 1. 存在性
    if not os.path.exists(el_file):
        sys.exit(f"ERROR: {el_file} not found")

    # 2. 非空 + 规模阈值（上游 952 行 / 34993 字节，阈值为 80%）
    size = os.path.getsize(el_file)
    if size == 0:
        sys.exit(f"ERROR: {el_file} is empty")
    if size < 27000:  # 34993 * 0.8 ≈ 27994，取 27000 容忍合理差异
        sys.exit(f"ERROR: {el_file} suspiciously small ({size} bytes < 27000)")

    with open(el_file, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    lines = content.splitlines()
    if len(lines) < 750:  # 上游 952 行，阈值为 80%
        sys.exit(f"ERROR: {el_file} suspiciously few lines ({len(lines)} < 750)")

    # 3. 包元数据与上游一致
    required_markers = [
        (";; Version: 0.10.0", "版本元数据"),
        (';; Package-Requires: ((avy "0.5.0"))', "依赖声明元数据"),
        ("(require 'avy)", "avy 依赖加载"),
        ("(provide 'ace-window)", "包 provide 声明"),
        ("(defun ace-window (arg)", "主 API ace-window"),
        ("(defun aw-select (mode-line &optional action)", "API aw-select"),
        ("(defun aw-window-list ()", "API aw-window-list"),
        ("(defcustom aw-keys", "自定义项 aw-keys"),
    ]
    missing = [name for marker, name in required_markers if marker not in content]
    if missing:
        sys.exit(f"ERROR: {el_file} missing required content: {', '.join(missing)}")

    # 4. S-表达式括号平衡（结构性验证，防止截断/损坏文件通过）
    balanced, depth, max_depth = check_paren_balance(content)
    if not balanced:
        sys.exit(f"ERROR: {el_file} unbalanced parentheses (depth={depth}, max={max_depth})")

    # 5. 顶层定义数量阈值（上游 73 个 defun/defcustom/defvar）
    top_defs = len(re.findall(r"^\((?:defun|defcustom|defvar)\s", content, re.M))
    if top_defs < 60:
        sys.exit(f"ERROR: {el_file} too few top-level defs ({top_defs} < 60)")

    print(
        f"PASS: {el_file} - {size} bytes, {len(lines)} lines, "
        f"{top_defs} top-level defs, parens balanced (max depth {max_depth}), "
        f"{len(required_markers)}/{len(required_markers)} content markers verified"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
