#!/usr/bin/env python3
"""deb2targz 消费者侧功能测试（R34：真实执行，非空壳断言）。

用法: python3 run_deb2targz_tests.py <package_folder> <outdir>
"""
import gzip
import io
import os
import subprocess
import sys
import tarfile

PKG = sys.argv[1]
OUT = sys.argv[2]
BIN = os.path.join(PKG, "bin", "deb2targz")
os.makedirs(OUT, exist_ok=True)

passed = failed = skipped = 0


def ok(m):
    global passed; passed += 1; print(f"  [PASS] {m}", flush=True)


def bad(m):
    global failed; failed += 1; print(f"  [FAIL] {m}", flush=True)


def skip(m):
    global skipped; skipped += 1; print(f"  [SKIP] {m}", flush=True)


def make_data_targz():
    """构造一个真实的 data.tar.gz（含两个文件）。"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for nm, data in (("usr/bin/hello", "#!/bin/sh\necho hi\n"),
                         ("etc/demo.conf", "key=value\n")):
            b = data.encode()
            ti = tarfile.TarInfo(nm)
            ti.size = len(b)
            tf.addfile(ti, io.BytesIO(b))
    return gzip.compress(buf.getvalue(), mtime=0)


def ar_entry(name, blob):
    """按 ar 格式拼一个成员（deb2targz 是逐字节解析，故可手工构造，无需 ar 命令）。"""
    hdr = (name.ljust(16) + "0".ljust(12) + "0".ljust(6) + "0".ljust(6)
           + "100644".ljust(8) + str(len(blob)).ljust(10) + "`\n")
    assert len(hdr) == 60, f"ar 头长度应为 60，实得 {len(hdr)}"
    out = hdr.encode() + blob
    if len(blob) % 2:
        out += b"\n"          # ar 成员按偶数对齐
    return out


def make_deb(data_tgz):
    """构造最小合法 .deb（ar 归档：debian-binary + control.tar.gz + data.tar.gz）。"""
    deb = b"!<arch>\n"
    deb += ar_entry("debian-binary", b"2.0\n")
    deb += ar_entry("control.tar.gz", gzip.compress(b"", mtime=0))
    deb += ar_entry("data.tar.gz", data_tgz)
    return deb


def run(args, cwd=None):
    return subprocess.run([BIN] + args, capture_output=True, text=True,
                          timeout=60, cwd=cwd)


print("== deb2targz 上游接口测试 ==")
print(f"  包目录: {PKG}", flush=True)

# ── 环境诊断（本包产品是 `#!/usr/bin/env perl` 脚本，perl 解析结果决定成败）──
# 实测教训：设备上可能存在多个 perl（本机即有系统 perl 与 conan perl 两个
# 5.42.2），若 PATH 未让依赖 perl 优先，`env perl` 会解析到另一个 perl，而它
# 去加载 conan perl 的 XS 模块 → "loadable library and perl binaries are
# mismatched"。故这里显式记录解析结果，失败时可一眼定位。
import shutil  # noqa: E402

resolved = shutil.which("perl")
print(f"  环境诊断: perl={resolved}", flush=True)
print(f"  环境诊断: PERL5LIB={os.environ.get('PERL5LIB', '(未设)')}", flush=True)
print(f"  环境诊断: PATH 首位={os.environ.get('PATH', '').split(os.pathsep)[0]}", flush=True)
if resolved:
    try:
        v = subprocess.run([resolved, "-e", "print $^X, ' ', $], '\\n'"],
                           capture_output=True, text=True, timeout=30)
        print(f"  环境诊断: perl 自报 {v.stdout.strip()}", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"  环境诊断: perl 自报失败 {type(e).__name__}", flush=True)

# ---------- ① 存在且可执行 ----------
if not (os.path.isfile(BIN) and os.access(BIN, os.X_OK)):
    bad("bin/deb2targz 不存在或不可执行")
else:
    ok("bin/deb2targz 存在且可执行")

if os.path.isfile(BIN):
    # shebang 必须是 env perl 且不含 -w（-w 会让 env 把 "perl -w" 当单个程序名）
    first = open(BIN, encoding="utf-8", errors="replace").readline().strip()
    if first == "#!/usr/bin/env perl":
        ok(f"shebang 已正确改写为 {first}")
    else:
        bad(f"shebang 不符: {first!r}（期望 '#!/usr/bin/env perl'）")
    if "-w" in first:
        bad("shebang 含 -w：env 会把它与 perl 视为单个程序名而失败")
    else:
        ok("shebang 未携带 -w（env 解析安全）")

# ---------- ② 负向：非 .deb 输入应被拒绝 ----------
workdir = os.path.join(OUT, "work")
os.makedirs(workdir, exist_ok=True)
notdeb = os.path.join(workdir, "not-a-deb.txt")
open(notdeb, "w").write("hello\n")
if os.path.isfile(BIN):
    r = run([notdeb], cwd=workdir)
    combined = (r.stdout or "") + (r.stderr or "")
    if "ignoring" in combined:
        ok("负向用例：非 .deb 输入被正确忽略（打印 ignoring）")
    else:
        bad(f"负向用例：非 .deb 输入未被拒绝（输出: {combined.strip()[:80]!r}）")
    out_should_not_exist = os.path.join(workdir, "not-a-deb.tar.gz")
    if not os.path.exists(out_should_not_exist):
        ok("负向用例：未对被忽略的输入产生输出文件")
    else:
        bad("负向用例：对被忽略的输入竟产生了输出文件")

# ---------- ③ 正向真实验证：.deb → .tar.gz 逐字节一致 ----------
if os.path.isfile(BIN):
    try:
        data_tgz = make_data_targz()
        deb_path = os.path.join(workdir, "probe.deb")
        open(deb_path, "wb").write(make_deb(data_tgz))
        r = run(["probe.deb"], cwd=workdir)
        produced = os.path.join(workdir, "probe.tar.gz")
        if r.returncode == 0 and os.path.isfile(produced):
            got = open(produced, "rb").read()
            if got == data_tgz:
                ok(f"真实转换 .deb → .tar.gz 成功，且与原始 data.tar.gz "
                   f"逐字节一致（{len(got)} 字节）")
            else:
                bad(f"转换输出与原始 data.tar.gz 不一致"
                    f"（得 {len(got)}B / 期望 {len(data_tgz)}B）")
        else:
            bad(f"转换执行失败 rc={r.returncode}: "
                f"{((r.stderr or '') + (r.stdout or '')).strip()[:120]}")
    except Exception as e:  # noqa: BLE001
        bad(f"正向验证异常: {type(e).__name__}: {str(e)[:100]}")

    # ---------- ④ 输出能被 tar 解开且含预期文件 ----------
    produced = os.path.join(workdir, "probe.tar.gz")
    if os.path.isfile(produced):
        try:
            with tarfile.open(produced, "r:gz") as tf:
                names = tf.getnames()
            want = {"usr/bin/hello", "etc/demo.conf"}
            if want.issubset(set(names)):
                ok(f"输出可被 tar 解开且含预期文件 {sorted(want)}")
            else:
                bad(f"输出缺少预期文件（实得 {names}）")
        except Exception as e:  # noqa: BLE001
            bad(f"输出无法用 tar 解开: {type(e).__name__}: {str(e)[:80]}")
    else:
        skip("输出文件不存在，跳过 tar 解包校验")

print()
print(f"RESULT: passed={passed} failed={failed} skipped={skipped}", flush=True)
sys.exit(1 if failed else 0)
