#!/usr/bin/env python3
"""twopaco 1.0.0 test_package 真实断言（独立可跑：python3 test_twopaco.py <pkg>）。

4 个用例全部真实调用被测二进制：
  1. twopaco --help（退出码 0 + 输出非空，防“静默跳过也报 PASS”）
  2. graphdump --help（同上）
  3. twopaco -f 10 -k 5 input.fa -o out.bin（产物存在且非空）
  4. graphdump -f seq out.bin -k 5（输出非空，每行 3 列，行数>0）

计数规则：discovered=4 固定为真实用例数，passed 为逐项断言通过数，
直接计数、无减法推导、无 returncode 猜测修正。失败项打印 FAIL 并以
exit 1 结束（conan create 随之失败，不伪造通过）。
"""
import os
import subprocess
import sys
import tempfile

failures = []


def run(args, cwd=None):
    proc = subprocess.run(args, capture_output=True, text=True, cwd=cwd, timeout=600)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main(argv):
    if len(argv) < 2:
        print("usage: test_twopaco.py <package_folder>", file=sys.stderr)
        return 2
    pkg = argv[1]
    twopaco = os.path.join(pkg, "bin", "twopaco")
    graphdump = os.path.join(pkg, "bin", "graphdump")
    for exe in (twopaco, graphdump):
        if not os.path.isfile(exe):
            print("[FAIL] missing binary: %s" % exe)
            print('HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,'
                  '"command":"python3 test_twopaco.py <pkg>","discovered":4,"passedCount":0}')
            return 1

    passed = 0

    # 用例 1：twopaco --help
    rc, out = run([twopaco, "--help"])
    if rc == 0 and len(out.strip()) > 0:
        print("PASS twopaco --help (exit 0, %d bytes)" % len(out.strip()))
        passed += 1
    else:
        failures.append("twopaco --help: rc=%d out=%r" % (rc, out.strip()[-300:]))

    # 用例 2：graphdump --help
    rc, out = run([graphdump, "--help"])
    if rc == 0 and len(out.strip()) > 0:
        print("PASS graphdump --help (exit 0, %d bytes)" % len(out.strip()))
        passed += 1
    else:
        failures.append("graphdump --help: rc=%d out=%r" % (rc, out.strip()[-300:]))

    # 用例 3+4：端到端建图 + 转储（确定性小 FASTA，避免随机 flakiness）
    work = tempfile.mkdtemp(prefix="twopaco-test-")
    fa = os.path.join(work, "input.fa")
    seq1 = ("ACGT" * 50)[:200]
    seq2 = ("ACGT" * 50)[:150] + "TGCA" * 12 + ("ACGT" * 50)[:200 - 48 - 150 + 48]
    seq2 = (seq2 + "A" * 200)[:200]
    with open(fa, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(">seq0\n%s\n>seq1\n%s\n" % (seq1, seq2))
    out_bin = os.path.join(work, "out.bin")
    rc, out = run([twopaco, "-f", "10", "-k", "5", fa, "-o", out_bin, "--tmpdir", work], cwd=work)
    if rc == 0 and os.path.isfile(out_bin) and os.path.getsize(out_bin) > 0:
        print("PASS twopaco end-to-end (out.bin %d bytes)" % os.path.getsize(out_bin))
        passed += 1
    else:
        size = os.path.getsize(out_bin) if os.path.isfile(out_bin) else -1
        failures.append("twopaco end-to-end: rc=%d out.bin size=%d log=%r" % (rc, size, out[-500:]))

        # 用例 4 依赖用例 3 产物：产物无效则用例 4 记失败（不静默跳过）。
        failures.append("graphdump -f seq: skipped due to missing/empty out.bin (counted as failed, not skipped)")

        discovered = 4
        for item in failures:
            print("FAIL:", item)
        print('HMBS_TEST_PACKAGE_RESULT={{"executed":true,"passed":false,'
              '"command":"python3 test_twopaco.py <pkg>","discovered":{0},'
              '"passedCount":{1}}}'.format(discovered, passed))
        return 1

    seq_out = os.path.join(work, "out.seq")
    with open(seq_out, "w", encoding="utf-8"):
        pass
    proc = subprocess.run([graphdump, "-f", "seq", out_bin, "-k", "5"],
                          capture_output=True, text=True, cwd=work, timeout=600)
    text = (proc.stdout or "").strip()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    ok = (proc.returncode == 0 and len(lines) > 0
          and all(len(ln.split()) == 3 for ln in lines))
    if ok:
        print("PASS graphdump -f seq (%d junction lines)" % len(lines))
        passed += 1
    else:
        failures.append("graphdump -f seq: rc=%d lines=%d sample=%r"
                        % (proc.returncode, len(lines), lines[:2]))

    discovered = 4
    if failures:
        for item in failures:
            print("FAIL:", item)
        print('HMBS_TEST_PACKAGE_RESULT={{"executed":true,"passed":false,'
              '"command":"python3 test_twopaco.py <pkg>","discovered":{0},'
              '"passedCount":{1}}}'.format(discovered, passed))
        return 1
    print("ALL test_package assertions passed")
    print('HMBS_TEST_PACKAGE_RESULT={{"executed":true,"passed":true,'
          '"command":"python3 test_twopaco.py <pkg>","discovered":{0},'
          '"passedCount":{0}}}'.format(discovered))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
