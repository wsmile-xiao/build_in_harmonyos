#!/usr/bin/env python3
"""Maxima 真实计算断言（独立可跑：`python3 test.py <maxima 包根> <ecl 包根>`）。

两条断言都走**真实消费路径**（bin/maxima 在 ECL 构建下就是 `ecl -load maxima.fas`，
所以 CLI 算得出结果 ⇒ maxima.fas 确实被加载且可用）：

  ① `integrate(x^2,x)` 的结果是 x³/3
  ② `build_info()` 报告的 lisp 实现是 ECL，且 `lib/ecl/maxima.fas` 在位且非空
     —— 后者是 passagemath-ecl / -maxima 真正要的那个文件，`make install` 不装它。

⚠️ 必须给 `MAXIMA_PREFIX`：启动脚本按 argv[0] 反推前缀，从 conan cache 目录里跑
反推不出来，直接 `unable to determine MAXIMA_PREFIX` 退出（实撞）。
⚠️ 不要试图用 `ecl -eval '(load "maxima.fas")'` 直接加载：那不是它的消费方式，
会报 `Don't know how to REQUIRE SB-BSD-SOCKETS`（fas 里按 SBCL 的模块名要 socket 模块，
正常路径由启动脚本先铺好环境）。
"""
import os
import subprocess
import sys


def run_maxima(mroot, expr, timeout=300, eroot=None):
    env = dict(os.environ)
    env["MAXIMA_PREFIX"] = mroot          # 见模块注释
    # **运行期也必须给 ECLDIR**：maxima.fas 会 `require` sb-bsd-sockets，
    # 而 ECL 靠 SYS:（= ECLDIR）找模块 .fas。ECL 二进制里烤死的是构建时的前缀、
    # conan 打包后不存在 → `Module error: Don't know how to REQUIRE SB-BSD-SOCKETS`
    # （模块其实就在 ecl 包的 lib/ecl-<ver>/ 里，是**找不到**不是没有）。
    if eroot:
        import glob as _g
        _sys = sorted(_g.glob(os.path.join(eroot, "lib", "ecl-*")))
        if _sys:
            env["ECLDIR"] = _sys[0] + os.sep
    # ⚠️ **stdin 必须接 /dev/null**：ECL 出岔子时会弹交互提示等输入，进程就此挂住
    # （上游 sage 的 spkg-install 开头就写着 `exec </dev/null`，同一个坑）。
    # 实撞：不接 DEVNULL 时 `--batch-string` 一挂 900 秒，看着像算不出来，其实在等回车。
    out = subprocess.run([os.path.join(mroot, "bin", "maxima"),
                          "--very-quiet", "--batch-string=%s" % expr],
                         capture_output=True, text=True, timeout=timeout, env=env,
                         stdin=subprocess.DEVNULL)
    return out


def main(argv):
    if len(argv) < 2:
        print("用法: test.py <maxima 包根> [<ecl 包根>]", file=sys.stderr)
        return 2
    mroot = argv[1]
    eroot = argv[2] if len(argv) > 2 else None
    bad = 0

    mx = os.path.join(mroot, "bin", "maxima")
    if not os.path.isfile(mx):
        print("[FAIL] 缺 bin/maxima")
        return 1

    # ① 积分。用 display2d:false + print 强制**一行文本**输出：
    # `--very-quiet` 下二维排版的结果不进 stdout，光看默认输出会误判成"没算出来"。
    out = run_maxima(mroot, "display2d:false$ print(integrate(x^2,x))$", eroot=eroot)
    txt = ((out.stdout or "") + (out.stderr or ""))
    flat = "".join(txt.split())
    if out.returncode != 0 or ("x^3/3" not in flat):
        print("[FAIL] integrate(x^2,x) 不对（rc=%d）:\n%s" % (out.returncode, txt[-500:]))
        bad += 1
    else:
        print("[PASS] integrate(x^2,x) 算出 x^3/3")

    # ② 确认跑在 ECL 上（即 maxima.fas 这条路真的被走到）+ fas 在位
    out2 = run_maxima(mroot, "build_info();", eroot=eroot)
    t2 = (out2.stdout or "") + (out2.stderr or "")
    if "ECL" not in t2.upper():
        print("[FAIL] build_info() 没报告 ECL：%s" % t2[-400:])
        bad += 1
    else:
        print("[PASS] build_info() 报告 lisp 实现是 ECL")

    fas = os.path.join(mroot, "lib", "ecl", "maxima.fas")
    if not os.path.isfile(fas) or os.path.getsize(fas) < 100000:
        print("[FAIL] lib/ecl/maxima.fas 缺失或过小 —— passagemath-ecl/-maxima 正是加载它")
        bad += 1
    else:
        print("[PASS] lib/ecl/maxima.fas 在位（%.1f MB）" % (os.path.getsize(fas) / 1e6))

    print("maxima: 3 条断言，失败 %d 条" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
