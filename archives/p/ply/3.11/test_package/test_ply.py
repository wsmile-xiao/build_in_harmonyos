#!/usr/bin/env python3
"""ply consumer test (R34): module importable from the packaged site-packages
+ real lexer/parser construction and execution (not an import-only smoke test).

The inner script builds an actual lexer and an actual LALR(1) parser with
ply.lex / ply.yacc and evaluates an arithmetic expression, so a broken or
empty package cannot pass.
"""
import os
import subprocess
import sys

SMOKE_PY = r'''
import sys
sys.path[0:0] = __import__("os").environ["PYTHONPATH"].split(":")

import ply
import ply.lex as lex
import ply.yacc as yacc

print("ply", ply.__version__)
assert ply.__version__ == "3.11", ply.__version__

# ---- 真实 lexer：算术词法分析 ----
tokens = ("NUM", "PLUS", "TIMES")

t_PLUS = r"\+"
t_TIMES = r"\*"
t_ignore = " \t"


def t_NUM(t):
    r"\d+"
    t.value = int(t.value)
    return t


def t_error(t):
    raise ValueError("illegal character %r" % t.value[0])


lexer = lex.lex()
lexer.input("2 + 3 * 4")
seen = [(tok.type, tok.value) for tok in lexer]
assert seen == [("NUM", 2), ("PLUS", "+"), ("NUM", 3), ("TIMES", "*"),
                ("NUM", 4)], seen

# ---- 真实 LALR(1) parser：求值 ----
precedence = (("left", "PLUS"), ("left", "TIMES"))


def p_expr_binop(p):
    """expr : expr PLUS expr
            | expr TIMES expr"""
    p[0] = p[1] + p[3] if p[2] == "+" else p[1] * p[3]


def p_expr_num(p):
    "expr : NUM"
    p[0] = p[1]


def p_error(p):
    raise ValueError("syntax error at %r" % (p,))


parser = yacc.yacc(debug=False, write_tables=False)
result = parser.parse("2 + 3 * 4", lexer=lexer.clone())
assert result == 14, result

print("OK: ply lexer+parser evaluated 2 + 3 * 4 ==", result)
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    mod = os.path.join(site, "ply", "__init__.py")
    if not os.path.isfile(mod):
        print(f"FAIL: ply module missing: {mod}", file=sys.stderr)
        return 1
    env = dict(os.environ)
    env["PYTHONPATH"] = site
    py = sys.executable
    # 必须落到真实脚本文件再执行，不能用 `python -c`：
    # ply 的 lex.lex()/yacc.yacc() 通过 inspect.getfile() 定位**调用者模块**
    # 来读取词法/语法规则（反射收集 t_* / p_* 名字），`-c` 下 __main__ 是
    # 内建模块，inspect 会抛 "is a built-in module" TypeError。
    import tempfile
    with tempfile.TemporaryDirectory(prefix="ply-smoke-") as td:
        script = os.path.join(td, "smoke_ply.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(SMOKE_PY)
        r = subprocess.run([py, script], capture_output=True,
                           text=True, env=env, cwd=td)
    if r.returncode != 0:
        print(f"FAIL: ply lexer/parser: {r.stderr}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: ply module + real lexer/parser works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
