#!/usr/bin/env python3
"""Test driver for intltool-debian — R34 real artifact verification (no empty shell).

Verifies the 3 packaged Perl tools under <pkg>/bin/ (intltool-extract,
intltool-merge, intltool-update):
  A. exist and are executable
  B. pass `perl -wc` syntax check (upstream t/syntax.t equivalent)
  C. actually execute via the perl interpreter bridge and report version 0.35.0
  D. [鸿蒙特有] preserve upstream `#!/usr/bin/perl` shebang (not rewritten for
     the platform) — the HarmonyOS-specific E337 adaptation: HMDFS rejects
     shebang direct execution, so scripts keep upstream semantics and are run
     through the perl interpreter bridge.

Assertion mapping (for PR statistics table):
  - 通用功能断言（存在+可执行 / perl -wc / --version 真实执行）: A×3 + B×3 + C×3 = 9
  - 鸿蒙特有断言（shebang 保持，E337 适配）: D×3 = 3
  - 合计 12 断言（9 通用 + 3 鸿蒙特有）
"""
import os
import subprocess
import sys


TOOLS = ["intltool-extract", "intltool-merge", "intltool-update"]
# 上游脚本 shebang（保持不改写；E337 说明见文件头部）
UPSTREAM_SHEBANG_PREFIX = "#!/usr/bin/perl"


def main():
    pkg = sys.argv[1]
    bindir = os.path.join(pkg, "bin")
    failures = []
    # 断言计数器（供统计）
    counts = {"general": 0, "harmonyos": 0}

    # 用 conanrun 注入的 PERL 环境变量解析 perl 解释器（字面量 "perl" 在
    # PATH 首位是 intltool-debian 自己的 bin，且 perl 是符号链接，不可靠）
    perl = os.environ.get("PERL") or "perl"

    for tool in TOOLS:
        exe = os.path.join(bindir, tool)

        # A. 存在 + 可执行
        if not os.path.isfile(exe):
            failures.append(f"A:{tool}: {exe} not found")
        elif not os.access(exe, os.X_OK):
            failures.append(f"A:{tool}: {exe} not executable")
        counts["general"] += 1

        # B. 语法检查 via perl -wc（解释器桥）
        r = subprocess.run([perl, "-wc", exe],
                           capture_output=True, text=True)
        if r.returncode != 0:
            failures.append(f"B:{tool}: perl -wc failed: {r.stderr[:200]}")
        counts["general"] += 1

        # C. 真实执行 --version（解释器桥），断言输出含 0.35.0
        r = subprocess.run([perl, exe, "--version"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            failures.append(f"C:{tool}: --version rc={r.returncode}: "
                            f"{r.stderr[:200]}")
        elif "0.35.0" not in (r.stdout + r.stderr):
            failures.append(f"C:{tool}: --version lacks 0.35.0")
        counts["general"] += 1

        # D. [鸿蒙特有] shebang 保持上游 #!/usr/bin/perl（未被平台改写）
        with open(exe, "rb") as fh:
            first_line = fh.readline().decode("utf-8", "replace").rstrip("\n")
        if not first_line.startswith(UPSTREAM_SHEBANG_PREFIX):
            failures.append(
                f"D:{tool}: shebang '{first_line}' != "
                f"'{UPSTREAM_SHEBANG_PREFIX}' (upstream semantics not preserved)")
        counts["harmonyos"] += 1

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        passed = (counts['general'] + counts['harmonyos']) - len(failures)
        print(f"PASS: {passed}/"
              f"{counts['general'] + counts['harmonyos']}", file=sys.stderr)
        return 1

    print(f"OK: intltool-debian tools exist, pass perl -wc, --version reports "
          f"0.35.0, and upstream shebang preserved. "
          f"Assertions: general={counts['general']} harmonyos={counts['harmonyos']} "
          f"total={counts['general'] + counts['harmonyos']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())