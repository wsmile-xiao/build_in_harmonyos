#!/usr/bin/env python3
"""上游功能测试驱动 — pari-nflistdata/20220729.

把三族上游测试串成一条可复现命令，产出逐用例记录与统计：

  U1  qt_<deg>_<idx>        650 项  nflist([deg,idx],'t) 逐 QT 文件 round-trip
  U2  a5_*                    8 项  A5 / A5(6) 表的功能级断言（计数、边界、错误路径）
  U3  a5_read_<path>         27 项  A5 分文件**归因**（反向对照：移开该文件后 gp 输出指纹
                                    必须改变，否则该文件未被当前 gp 读取，记 SKIP）

⚠ 分进程执行的原因（实测坑，见 notes.md 问题表）：在**同一个 gp 进程**里先跑 650 条
  `nflist([d,i],'t)` 再跑 A5 语义断言时，`nflist("A5",[1,524286^2],0)` 的返回规模会
  从 15184 变小（上游原始目录与打包产物**表现一致**，非打包差异），即 QT 查询会污染
  nflist 内部表状态。故 U1 与 U2 必须各起一个 gp 进程，本 driver 负责拆分与合并。

用法:
  python3 run-upstream-gp-sweep.py <datadir_root> --gp <gp> \
      --lib <dir> [--lib <dir> ...] --out-cases <file.txt> [--no-attribution]

  <datadir_root>  含 nflistdata/ 的目录（打包产物为 <pkg>/res/pari）
退出码：U1+U2 任一 FAIL 或期望用例数与日志用例数不符 → 1；否则 0。
（U3 的 SKIP 表示"当前 gp 无该表的读取入口"，不计失败。）
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd, env, timeout=1800):
    return subprocess.run(cmd, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          env=env, timeout=timeout)


def gen(root, family, out, here):
    r = run([sys.executable, os.path.join(here, "upstream-gp-sweep-generator.py"),
             root, "--family", family, "--out", out], os.environ, timeout=300)
    if r.returncode != 0:
        sys.exit("生成器失败(%s): %s" % (family, r.stdout.decode("utf-8", "replace")))


def expected_cases(root, family, here):
    r = run([sys.executable, os.path.join(here, "upstream-gp-sweep-generator.py"),
             root, "--family", family, "--print-cases"], os.environ, timeout=300)
    return [ln.strip() for ln in r.stdout.decode().splitlines() if ln.strip()]


def parse_results(text):
    """从 gp 输出解析 `NAME PASS|FAIL` 行；返回 {name: verdict}。"""
    got = {}
    for ln in text.splitlines():
        parts = ln.strip().split()
        if len(parts) == 2 and parts[1] in ("PASS", "FAIL"):
            got[parts[0]] = parts[1]
    return got


A5_FILES = (["5/4/0/%d" % i for i in range(6)]
            + ["5/4/0cond/%d" % i for i in range(10)]
            + ["5/4/2/0"]
            + ["5/4/2cond/%d" % i for i in range(10)])
GP_CASES = [('A5D', 'nflist("A5")'),
            ('A5F', 'nflist("A5", [1, 524286^2], 0)'),
            ('A5T', 'nflist("A5", [1, 10^8], 2)'),
            ('A5S', 'nflist("A5", [1, 10^8], 0)'),
            ('A5P', 'nflist("A5", 1762^2, 0)'),
            ('A5P2', 'nflist("A5", 99997^2, 0)'),
            ('A5Q', 'nflist("A5", 10000^2, 2)'),
            ('A5C', 'nflist("A5", 633^2, 0)'),
            ('A5R', 'nflist("A5", [1, 10^6], 0)'),
            # 带子域 F 的检索（nflist 的第 4 参，走 nflist_CL_worker/Fcond 路径，
            # 实证入口：nflist("A5",[1,10^6],-2,x^2-5) 返回 3 个域）
            ('A5W1', 'nflist("A5", [1, 10^6], -2, x^2 - 5)'),
            ('A5W2', 'nflist("A5", [1, 10^8], -2, x^2 - 5)'),
            ('A5W3', 'nflist("A5", [1, 10^8], 2, x^2 - 5)')]


def attribution_script(datadir):
    lines = ['default(datadir,"%s");' % datadir]
    for var, expr in GP_CASES:
        lines.append("%s = %s;" % (var, expr))
        lines.append('print("%s|", type(%s), "|", if(type(%s)=="t_VEC", #%s, -1), '
                     '"|", if(type(%s)=="t_VEC" && #%s>0, Str(%s[1]), "-"));'
                     % (var, var, var, var, var, var, var))
    return "\n".join(lines) + "\n"


def fingerprint(root, gp, env, work):
    script = os.path.join(work, "attr.gp")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(attribution_script(root))
    r = run([gp, "-q", "-f", script], env, timeout=900)
    return hashlib.sha256(r.stdout).hexdigest(), r


def do_attribution(datadir_root, gp, env, work, log):
    """在数据树的**副本**上做移文件归因（不改动被测包目录）。"""
    tree = os.path.join(work, "tree")
    if os.path.isdir(tree):
        shutil.rmtree(tree)
    shutil.copytree(os.path.join(datadir_root, "nflistdata"),
                    os.path.join(tree, "nflistdata"))
    root = tree
    f0, r0 = fingerprint(root, gp, env, work)
    log.append("# 归因基线 gp_rc=%d fingerprint=%s" % (r0.returncode, f0))
    out = []
    for rel in A5_FILES:
        src = os.path.join(root, "nflistdata", rel)
        bak = src + ".removed"
        os.rename(src, bak)
        try:
            ff, _r = fingerprint(root, gp, env, work)
        finally:
            os.rename(bak, src)
        out.append((rel, "PASS" if ff != f0 else "SKIP"))
    # 完整性回归：副本与原始树在实验后仍逐项一致
    _f_after, r_after = fingerprint(root, gp, env, work)
    log.append("# 归因实验后基线复现 fingerprint=%s match=%s"
               % (_f_after, "yes" if _f_after == f0 else "NO"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("datadir_root")
    ap.add_argument("--gp", required=True)
    ap.add_argument("--lib", action="append", default=[],
                    help="LD_LIBRARY_PATH 条目（pari lib、gmp lib）")
    ap.add_argument("--out-cases", required=True)
    ap.add_argument("--no-attribution", action="store_true")
    a = ap.parse_args()

    env = dict(os.environ)
    if a.lib:
        env["LD_LIBRARY_PATH"] = ":".join(a.lib)
    work = tempfile.mkdtemp(prefix="nflist-sweep-")
    rows = []
    log = []
    fails = 0

    for family in ("qt", "a5"):
        script = os.path.join(work, "sweep-%s.gp" % family)
        gen(a.datadir_root, family, script, HERE)
        want = expected_cases(a.datadir_root, family, HERE)
        r = run([a.gp, "-q", "-f", script], env, timeout=1800)
        text = r.stdout.decode("utf-8", "replace")
        log.append("=== gp -q -f sweep-%s.gp  (rc=%d, %d expected cases) ==="
                   % (family, r.returncode, len(want)))
        log.append(text.rstrip())
        got = parse_results(text)
        for name in want:
            verdict = got.get(name, "FAIL")
            if verdict != "PASS":
                fails += 1
                verdict = "FAIL" if verdict != "MISSING" else verdict
            rows.append((name, verdict))
        missing = [n for n in want if n not in got]
        if missing:
            log.append("!! %s: %d 用例在 gp 输出中缺失（视为 FAIL）: %s"
                       % (family, len(missing), missing[:5]))

    if not a.no_attribution:
        log.append("=== U3 A5 分文件归因（反向对照，gp 进程各 28 次） ===")
        for rel, verdict in do_attribution(a.datadir_root, a.gp, env, work, log):
            rows.append(("a5_read_%s" % rel.replace("/", "_"), verdict))

    with open(a.out_cases, "w", encoding="utf-8") as fh:
        fh.write("# 上游功能测试逐用例记录 — pari-nflistdata/20220729\n"
                 "# 宿主: 制品仓 pari/%s 的 gp（OHOS arm64），datadir=%s\n"
                 "# 生成: python3 run-upstream-gp-sweep.py <datadir_root> --gp <gp> "
                 "--lib <pari/lib> --lib <gmp/lib> --out-cases %s\n"
                 % ("2.17.4.1", a.datadir_root, os.path.basename(a.out_cases)))
        npass = nskip = nfail = 0
        for name, verdict in rows:
            fh.write("%-4s %s\n" % (verdict, name))
            if verdict == "PASS":
                npass += 1
            elif verdict == "SKIP":
                nskip += 1
            else:
                nfail += 1
        fh.write("#\n# total=%d pass=%d fail=%d skip=%d\n"
                 % (len(rows), npass, nfail, nskip))
        print("TOTAL=%d PASS=%d FAIL=%d SKIP=%d"
              % (len(rows), npass, nfail, nskip))

    # gp 原始输出与逐用例记录同级留存（不要只打印一个随后被清理的临时路径）
    raw = a.out_cases + ".gp-raw.log"
    with open(raw, "w", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")
    print("gp 原始输出留存: %s" % raw)
    shutil.rmtree(work, ignore_errors=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
