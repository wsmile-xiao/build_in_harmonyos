#!/usr/bin/env python3
"""opalmod 消费者侧功能测试（R34：真实调用上游导出函数，非空壳断言）。

用法: python3 run_opalmod_tests.py <package_folder> <outdir>
"""
import os
import shutil
import subprocess
import sys
import tempfile

PKG = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)

passed = failed = skipped = 0


def ok(m):
    global passed; passed += 1; print(f"  [PASS] {m}", flush=True)


def bad(m):
    global failed; failed += 1; print(f"  [FAIL] {m}", flush=True)


def skip(m):
    global skipped; skipped += 1; print(f"  [SKIP] {m}", flush=True)


PERL = shutil.which("perl") or "perl"


def run_perl(code, expect_ok=True):
    """跑一段 perl 代码，返回 (rc, stdout, stderr)。"""
    r = subprocess.run([PERL, "-e", code], capture_output=True, text=True,
                       timeout=60)
    return r.returncode, (r.stdout or ""), (r.stderr or "")


print("== opalmod 上游接口测试 ==")
print(f"  包目录: {PKG}", flush=True)
print(f"  perl: {PERL}", flush=True)
print(f"  PERL5LIB={os.environ.get('PERL5LIB', '(未设)')}", flush=True)

# ---------- ① 包内确有 OpaL 模块 ----------
found = []
for root, _dirs, files in os.walk(PKG):
    if os.path.basename(root) == "OpaL":
        found += [f for f in files if f.endswith(".pm")]
if found:
    ok(f"包内找到 {len(found)} 个 OpaL 模块: {sorted(found)[:6]}")
else:
    bad("包内未找到任何 OpaL/*.pm")

# ---------- ② 5 个子模块均可加载 ----------
for part in ("where", "read", "dir", "manipulate", "action"):
    rc, out, err = run_perl(f"use OpaL::{part}; print 'LOADED\\n';")
    if rc == 0 and "LOADED" in out:
        ok(f"OpaL::{part} 可被真实加载")
    else:
        bad(f"OpaL::{part} 加载失败: {(err or out).strip()[:110]}")

# ---------- ③ 真实功能调用 ----------
# 3a. OpaL::where::which() 能定位可执行文件
rc, out, err = run_perl(
    "use OpaL::where qw(which); my $p = which('perl'); "
    "print defined($p) && -e $p ? \"FOUND:$p\\n\" : \"NOTFOUND\\n\";")
if rc == 0 and out.startswith("FOUND:"):
    ok(f"OpaL::where::which('perl') 真实定位到 {out.strip().split(':', 1)[1][:70]}")
else:
    bad(f"OpaL::where::which 未定位到 perl: {(err or out).strip()[:110]}")

# 3b. OpaL::read::readscalarfile() 读取真实内容
tmpf = os.path.join(OUT, "sample.txt")
with open(tmpf, "w") as fh:
    fh.write("opalmod-selftest-42\n")
rc, out, err = run_perl(
    f"use OpaL::read qw(readscalarfile); "
    f"my $s = readscalarfile('{tmpf}'); "
    f"print defined($s) && $s =~ /opalmod-selftest-42/ ? \"CONTENT_OK\\n\" : 'BAD:'.(defined $s ? $s : 'undef').\"\\n\";")
if rc == 0 and "CONTENT_OK" in out:
    ok("OpaL::read::readscalarfile 真实读到预期内容")
else:
    bad(f"OpaL::read::readscalarfile 未读到预期内容: {(err or out).strip()[:110]}")

# 3c. OpaL::dir::getdirlist() 列出真实目录项
tmpd = tempfile.mkdtemp(prefix="opalmod_", dir=OUT)
for nm in ("a.txt", "b.txt"):
    open(os.path.join(tmpd, nm), "w").close()
# ⚠️ 不要写成 `print (cond) ? A : B` —— Perl 会解析为 `(print(cond)) ? A : B`，
#    只打印布尔的 "1" 而丢弃 A/B（实测踩过）。这里先算好再打印。
rc, out, err = run_perl(
    f"use OpaL::dir qw(getdirlist); "
    f"my @l = getdirlist('{tmpd}'); my $j = join(',', @l); "
    f"my $ok = ($j =~ /a\\.txt/ && $j =~ /b\\.txt/) ? 'OK' : 'BAD'; "
    f"print \"DIR_$ok:$j\\n\";")
if rc == 0 and out.startswith("DIR_OK"):
    ok(f"OpaL::dir::getdirlist 真实列出目录项（{out.strip().split(':', 1)[1][:50]}）")
else:
    bad(f"OpaL::dir::getdirlist 结果不符: {(err or out).strip()[:110]}")

# 3d. OpaL::action 的 debug level 取值往返
rc, out, err = run_perl(
    "use OpaL::action qw(setDebugLevel getDebugLevel); "
    "setDebugLevel(3); my $v = getDebugLevel(); "
    "print $v == 3 ? \"LEVEL_OK\\n\" : \"LEVEL_BAD:$v\\n\";")
if rc == 0 and "LEVEL_OK" in out:
    ok("OpaL::action set/getDebugLevel 往返一致（3 → 3）")
else:
    bad(f"OpaL::action 调试级别往返失败: {(err or out).strip()[:110]}")

# ---------- ④ 负向用例（证明断言非恒真）----------
rc, out, err = run_perl("use OpaL::definitely_no_such_module_xyz; print 'LOADED\\n';")
if rc != 0:
    ok("负向用例：加载不存在的模块正确失败（断言非恒真）")
else:
    bad("负向用例失败：不存在的模块竟加载成功")

print()
print(f"RESULT: passed={passed} failed={failed} skipped={skipped}", flush=True)
sys.exit(1 if failed else 0)
