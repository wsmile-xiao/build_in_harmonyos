"""test_package/kbtin_behavior.py — DRAFT。消费者测试：以**使用者身份驱动已安装的 KBtin 二进制**，
用上游自己登记的输入/输出对做逐字断言（AGENTS §10：只打印/只查文件不合格；退出码由断言决定）。

输入/期望**全部逐字抄自上游语料**（miredo 同法）：官方件 tests/data/<name>.in / .out。
每条都用上游 runner 的同一调用形态：KBtin -p -q <setup> < <name>.in（tests/runtest.sh:9）。
"""
import os
import subprocess
import sys

# (用例名, stdin, 期望 stdout) —— 六条，全部无网络、无 IRC 服务器依赖
CASES = [
    ("shell", "#shell echo 'abc'\n", "abc\n"),
    ("strwidth", "#strw x foo~4~bar;#show $x\n", "6\n"),
    ("tabbed_args", "#var foo\t{a b}\n#show {[$foo]}\n", "[a b]\n"),
    ("system", "#var x abc\n#sys echo '$x'\n#sys {echo '$x'}\n", "abc\nabc\n"),
    ("recursion-guard", "#alias x x\nx\n", "#TOO DEEP RECURSION.\n"),
    ("end-without-session", "#end\n", ""),
]

SETUP = "#mess all 0\n"          # 与上游 tests/setup 的第一行一致（去掉 30 tick 延时器）


def main(kbtin, workdir):
    setup = os.path.join(workdir, "setup")
    with open(setup, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(SETUP)

    env = dict(os.environ)
    env.setdefault("TERM", "dumb")          # 无控制终端时给一个确定值，不靠继承
    passed = failed = 0
    for name, stdin_data, expected in CASES:
        try:
            r = subprocess.run([kbtin, "-p", "-q", setup], input=stdin_data,
                               capture_output=True, text=True, timeout=60, env=env, cwd=workdir)
            got = r.stdout
            ok = (got == expected)
        except Exception as exc:  # noqa: BLE001
            ok, got, r = False, f"<exception {type(exc).__name__}: {exc}>", None
        if ok:
            print(f"PASS {passed + failed + 1} {name}: 输出逐字相等 {len(expected)}B")
            passed += 1
        else:
            print(f"FAIL {passed + failed + 1} {name}: want {expected!r} got {got!r} "
                  f"rc={getattr(r, 'returncode', None)} stderr={getattr(r, 'stderr', '')[:160]!r}")
            failed += 1
    print(f"KBtin consumer suite: PASS={passed} FAIL={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
