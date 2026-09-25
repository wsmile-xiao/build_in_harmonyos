#!/usr/bin/env python3
"""test_blendsel.py — blendsel test_package 验证脚本（OHOS conanrun 环境实跑）.

用法（由 test_package/conanfile.py 的 test() 调用）:
    python3 test_blendsel.py <pkg_folder> <blendsel> <perl_bin> <perl_pkg_folder>

8 项独立断言，逐项打印 PASS 计数；任一失败即非零退出：
  1. bin/blendsel 存在、可执行、shebang 为 #!/usr/bin/env perl
  2. 包布局完整（bin/ + lib/blendsel + share/blendsel，6 个关键文件非空）
  3. share/blendsel/descs/debian-tasks.desc 可读且含 med-blend 任务数据
  4. perl -c 语法校验通过（补丁 Locale::gettext 可选加载后可编译）
  5. perl 解释器为 conan 依赖 perl/5.42.2 制品路径（realpath 前缀校验）
  6. perl --version 报告 v5.42.2（与声明依赖一致，排除系统 perl）
  7. --task-packages=med-blend 输出 task-med-blend 且 exit 0（数据链+前缀推导）
  8. 未知选项输出 usage（含 "blendsel [OPTIONS"）且 exit 非 0
"""
import os
import subprocess
import sys


class CheckFailure(Exception):
    pass


def expect(cond, msg):
    if not cond:
        raise CheckFailure(msg)


def run(cmd, env):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              env=env, timeout=60)
    except subprocess.TimeoutExpired:
        raise CheckFailure("timeout after 60s: " + " ".join(cmd))


def main():
    if len(sys.argv) < 5:
        print("usage: test_blendsel.py <pkg_folder> <blendsel> "
              "<perl_bin> <perl_pkg_folder>", file=sys.stderr)
        return 2
    pkg_folder, blendsel, perl_bin, perl_pkg_folder = sys.argv[1:5]
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(perl_bin) + os.pathsep + env.get("PATH", "")

    def c1_shebang():
        expect(os.path.isfile(blendsel), f"not a file: {blendsel}")
        expect(os.access(blendsel, os.X_OK), f"not executable: {blendsel}")
        with open(blendsel, encoding="utf-8", errors="replace") as fh:
            first = fh.readline().strip()
        expect(first == "#!/usr/bin/env perl",
               f"unexpected shebang: {first!r}")
        return first

    def c2_layout():
        rels = ["bin/blendsel",
                "lib/blendsel/blendsel-debconf",
                "lib/blendsel/packages/list",
                "lib/blendsel/tests/debconf",
                "lib/blendsel/tests/new-install",
                "share/blendsel/descs/debian-tasks.desc"]
        for rel in rels:
            path = os.path.join(pkg_folder, rel)
            expect(os.path.isfile(path), f"missing file: {rel}")
            expect(os.path.getsize(path) > 0, f"empty file: {rel}")
        return f"bin/ + lib/blendsel + share/blendsel ({len(rels)} files)"

    def c3_desc_data():
        desc = os.path.join(pkg_folder, "share", "blendsel", "descs",
                            "debian-tasks.desc")
        with open(desc, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        expect("Task: med-blend" in text, "Task: med-blend missing in desc")
        expect("task-med-blend" in text, "task-med-blend key missing in desc")
        return "debian-tasks.desc readable, med-blend task present"

    def c4_perl_c():
        r = run([perl_bin, "-c", blendsel], env)
        expect(r.returncode == 0,
               f"perl -c rc={r.returncode}: {r.stderr.strip()}")
        last = r.stderr.strip().splitlines()
        return last[-1] if last else "syntax OK"

    def c5_perl_provenance():
        real_bin = os.path.realpath(perl_bin)
        real_pkg = os.path.realpath(perl_pkg_folder)
        expect(os.path.commonpath([real_bin, real_pkg]) == real_pkg,
               f"perl {real_bin} not under conan perl package {real_pkg}")
        return f"{real_bin} (conan perl package)"

    def c6_perl_version():
        r = run([perl_bin, "--version"], env)
        out = r.stdout + r.stderr
        expect("v5.42.2" in out, f"perl version mismatch: {out.strip()[:120]}")
        return "v5.42.2"

    def c7_task_packages():
        r = run([blendsel, "--task-packages=med-blend"], env)
        expect(r.returncode == 0,
               f"rc={r.returncode}: {r.stdout!r} {r.stderr!r}")
        expect("task-med-blend" in r.stdout,
               f"output missing task-med-blend: {r.stdout!r}")
        return r.stdout.strip()

    def c8_usage():
        r = run([blendsel, "--definitely-not-an-option"], env)
        out = r.stdout + r.stderr
        expect("blendsel [OPTIONS" in out, f"no usage output: {out[:120]!r}")
        expect(r.returncode != 0, "unknown option unexpectedly exit 0")
        return f"usage printed (rc={r.returncode})"

    checks = [
        ("bin/blendsel shebang is #!/usr/bin/env perl", c1_shebang),
        ("package layout bin/ + lib/blendsel + share/blendsel complete",
         c2_layout),
        ("share/blendsel/descs/debian-tasks.desc data readable", c3_desc_data),
        ("perl -c syntax check", c4_perl_c),
        ("perl interpreter from conan perl/5.42.2 package",
         c5_perl_provenance),
        ("perl --version == v5.42.2", c6_perl_version),
        ("--task-packages=med-blend -> task-med-blend (data chain)",
         c7_task_packages),
        ("unknown option prints usage (rc != 0)", c8_usage),
    ]
    total = len(checks)
    passed = 0
    for idx, (label, fn) in enumerate(checks, 1):
        try:
            detail = fn()
            passed += 1
            print(f"PASS {idx}/{total}: {label} -- {detail}")
        except CheckFailure as exc:
            print(f"FAIL {idx}/{total}: {label} -- {exc}", file=sys.stderr)
    print(f"RESULT: {passed}/{total} assertions passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
