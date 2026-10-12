#!/usr/bin/env python3
"""speg 0.3 consumer test (R34): 实质调用 speg 的 PEG 解析 API。

speg 0.3 公开 API：speg.peg(text, rule) → 解析结果；解析失败抛 speg.ParseError。
文法规则是调用方传的可调用对象 p->(...)，规则内用 p(regex) 消费 token、
p.eof 判结尾（详见 speg/peg.py）。本测试解析一个简单整数文法，
并验证 ParseError 路径——不是只打印字符串的空壳测试。
"""
import sys


def main() -> int:
    import speg

    # --- 简单文法：整数 + 可选空白 + EOF ---
    def rule_int(p):
        p(r'[0-9]+')       # 消费一个或多个数字
        p(r' *')           # 消费尾部空白
        p(p.eof)           # 必须到文本末尾
        return True

    try:
        result = speg.peg('42', rule_int)
    except Exception as e:
        print(f"FAIL: speg.peg('42') raised: {e!r}", file=sys.stderr)
        return 1
    if result is not True:
        print(f"FAIL: unexpected result {result!r}", file=sys.stderr)
        return 1
    print("OK: speg.peg('42', rule_int) parsed (rule returned True)")

    # --- 文法回调中取 captured text（规则返回值由回调决定） ---
    def rule_num(p):
        return int(p(r'[0-9]+'))

    def rule_expr(p):
        v = rule_num(p)
        p(r' *')
        p(p.eof)
        return v

    try:
        v = speg.peg('123', rule_expr)
    except Exception as e:
        print(f"FAIL: speg.peg('123', rule_expr) raised: {e!r}",
              file=sys.stderr)
        return 1
    if v != 123:
        print(f"FAIL: expected 123, got {v!r}", file=sys.stderr)
        return 1
    print("OK: speg.peg('123', rule_expr) returned 123")

    # --- ParseError 路径（R34 实质调用——异常分支） ---
    try:
        speg.peg('12x', rule_expr)
    except speg.ParseError as e:
        print(f"OK: ParseError raised (msg={e.msg!r} line={e.line} "
              f"col={e.col})")
    except Exception as e:
        print(f"FAIL: expected speg.ParseError, got {type(e).__name__}: {e}",
              file=sys.stderr)
        return 1
    else:
        print("FAIL: speg.ParseError not raised for invalid input",
              file=sys.stderr)
        return 1

    # --- 端到端消费者用例：INI 风格多行配置解析 ---
    # 完整流程：多行文本 → 分节文法（with p: 回溯块 + 闭包数据收集 +
    # p.opt 可选空白）→ dict 数据提取 → 坏输入 ParseError 行定位。
    ini_text = (
        "[core]\n"
        "name = speg-demo\n"
        "threads = 4\n"
        "\n"
        "[net]\n"
        "host = 127.0.0.1\n"
        "port = 8080\n"
    )

    def make_ini_grammar(out):
        # out：闭包 dict，value 行解析结果实时写入（端到端数据提取）
        def value_line(p):
            key = p(r'[A-Za-z_][A-Za-z0-9_]*')
            p(r' *= *')
            out[key] = p(r'[^\n]+')
            return True

        def line(p):
            with p:                    # [section] 头（失败自动回溯）
                p(r'\[[^\]]*\]')
                p(r'[ \t]*')
                return True
            with p:                    # key = value 赋值行
                return value_line(p)
            p(r'\n')                   # 空行
            return True

        def doc(p):
            while p._states[-1].pos < len(p._s):
                line(p)
            p(p.eof)
            return True

        return doc

    parsed = {}
    try:
        speg.peg(ini_text, make_ini_grammar(parsed))
    except speg.ParseError as e:
        print(f"FAIL: e2e ini parse raised ParseError at line {e.line} "
              f"col {e.col}: {e.msg}", file=sys.stderr)
        return 1
    want = {"name": "speg-demo", "threads": "4",
            "host": "127.0.0.1", "port": "8080"}
    if parsed != want:
        print(f"FAIL: e2e data extraction mismatch: got {parsed!r}, "
              f"want {want!r}", file=sys.stderr)
        return 1
    print(f"OK: e2e ini config parsed, extracted {parsed}")

    # 坏输入：值行缺 key（"= bad"）→ 非小节头/赋值行/空行 → ParseError，
    # 且错误定位到第 7 行（port 所在行）
    bad_text = ini_text.replace("port = 8080", "= bad")
    try:
        speg.peg(bad_text, make_ini_grammar({}))
    except speg.ParseError as e:
        if e.line != 7:
            print(f"FAIL: e2e error locate expected line 7, got {e.line}",
                  file=sys.stderr)
            return 1
        print(f"OK: e2e bad input rejected, ParseError at line {e.line} "
              f"col {e.col} ({e.msg})")
    else:
        print("FAIL: e2e bad input not rejected", file=sys.stderr)
        return 1

    print("PASS: speg consumer test (3 assertions + 1 e2e consumer case)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
