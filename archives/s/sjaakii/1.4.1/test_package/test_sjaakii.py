#!/usr/bin/env python3
"""sjaakii 1.4.1 上游测试面执行器：`test movegen`（7 变体 perft 参考计数）。

- 输入驱动：stdin 喂 `test movegen` + `quit`，无需 tty（引擎只在 tty 下初始化 readline）
- 限时用 python subprocess timeout（toybox timeout 不杀进程树，device-facts §一.25）
- XDG_CONFIG_HOME 指到 cwd 下沙箱目录：引擎 atexit 会写 sjaakii.conf（§2 禁写真实 HOME）
- 判据（全部满足才算 PASS）：
    rc == 0
    输出含 "Ok."（test_movegen 全部 7 变体跑完才打印）
    输出不含 "*** Failed"（任一参考位点不等即打印并中止）
    最长连续点串 == 72（每个参考位点打一个 '.'；Release 构建 7 变体合计 72：
      chess 50 + spartan 7 + shogi 3 + xiangqi 3 + seirawan 4 + sittuyin 2 + crazyhouse 3；
      源码另有 12 个 #ifdef DEBUGMODE 位点，WANT_ASSERT=off（上游默认）不编译）
    banner 含 "1.4.1" 与 "(aarch64)"（ARCHSTR 补丁实证）
"""
import os
import re
import subprocess
import sys

EXPECT_DOTS = 72
VARIANT_TABLE = [
    ("chess", 50), ("spartan", 7), ("shogi", 3), ("xiangqi", 3),
    ("seirawan", 4), ("sittuyin", 2), ("crazyhouse", 3),
]
TIMEOUT_SEC = 2400


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        fail("usage: test_sjaakii.py <bin_dir>")
    bin_dir = sys.argv[1]
    exe = os.path.join(bin_dir, "sjaakii")
    if not os.path.isfile(exe) or not os.access(exe, os.X_OK):
        fail(f"binary missing or not executable: {exe}")

    # 沙箱配置目录：引擎退出时 atexit 写 sjaakii.conf（cfgpath 优先 XDG_CONFIG_HOME）
    xdg = os.path.abspath(os.path.join(os.getcwd(), "xdg-config-sjaakii"))
    os.makedirs(xdg, exist_ok=True)
    env = dict(os.environ)
    env["XDG_CONFIG_HOME"] = xdg

    try:
        p = subprocess.run(
            [exe],
            input="test movegen\nquit\n",
            capture_output=True, text=True,
            timeout=TIMEOUT_SEC, env=env, cwd=os.getcwd(),
        )
    except subprocess.TimeoutExpired:
        fail(f"`test movegen` 超过 {TIMEOUT_SEC}s 未返回")

    out = p.stdout + p.stderr
    print("--- sjaakii `test movegen` output ---")
    print(out)
    print(f"--- rc={p.returncode} ---")

    if p.returncode != 0:
        fail(f"engine rc={p.returncode}")
    if "*** Failed" in out:
        fail("perft 参考计数不匹配（输出含 '*** Failed'）")
    if "Ok." not in out:
        fail("输出缺少 'Ok.'（test_movegen 未跑完全部 7 变体）")

    runs = [len(m.group(0)) for m in re.finditer(r"\.+", out)]
    dots = max(runs) if runs else 0
    if dots != EXPECT_DOTS:
        fail(f"连续点串 {dots} != 期望 {EXPECT_DOTS}（参考位点执行数不符）")

    if "1.4.1" not in out:
        fail("banner 缺版本 1.4.1")
    if "(aarch64)" not in out:
        fail("banner 缺 (aarch64)（ARCHSTR 补丁未生效）")

    print("\nper-variant rc 留档（单命令顺序执行，首败即止；全过 → 7/7 rc=0）:")
    for name, n in VARIANT_TABLE:
        print(f"  PASS  {name:<11} positions={n}")
    print(f"TOTAL  PASS=72 FAIL=0 SKIP=0 NOT_RUN=0 (7 variants, {dots} dots)")
    print("sjaakii test movegen: OK")


if __name__ == "__main__":
    main()
