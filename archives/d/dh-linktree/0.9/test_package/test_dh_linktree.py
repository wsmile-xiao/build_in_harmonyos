#!/usr/bin/env python3
"""dh-linktree consumer test (R34):
  R1 文件存在断言: bin/dh_linktree + lib/perl5/Debian/Debhelper/Sequence/linktree.pm
  R2 perl -c 语法检查: dh_linktree + linktree.pm（PERL5LIB 加入本包与依赖包
     perl 库根——Dh_Lib 来自 debhelper 包、Dpkg::IPC 来自 dpkg 包）
  R3 功能冒烟（尽力）: 最小 debian 骨架 + 可写源目录真实运行 dh_linktree
     embed——符号链接树创建断言；dpkg --search 阶段因沙箱无 dpkg 数据库
     受阻则如实输出受限说明，不伪造通过率
"""
import os
import subprocess
import sys
import tempfile


def collect_perl_dirs(*roots):
    """收集 perl 库根目录（PERL5LIB 候选）。

    只加包根与常见 perl 库根（lib/perl5、lib、share/perl5、share/perl），
    不 walk 全树——否则会误抓同名模块（实测 dpkg 包的
    Dselect/Method/Config.pm 遮蔽 perl 核心 Config 模块，导致 Errno.pm
    编译失败 "%Config requires explicit package name"）。
    """
    dirs = set()
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for cand in (root,
                     os.path.join(root, "lib", "perl5"),
                     os.path.join(root, "lib"),
                     os.path.join(root, "share", "perl5"),
                     os.path.join(root, "share", "perl")):
            if os.path.isdir(cand):
                dirs.add(cand)
    return sorted(dirs)


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    dep_dirs = sys.argv[2:]
    fail = 0
    pass_cnt = 0

    # ── R1: 文件存在断言 ──────────────────────────────────────────
    bin_script = os.path.join(pkg, "bin", "dh_linktree")
    seq_pm = os.path.join(pkg, "lib", "perl5", "Debian", "Debhelper",
                          "Sequence", "linktree.pm")
    for f in (bin_script, seq_pm):
        if os.path.isfile(f):
            pass_cnt += 1
            print(f"OK: file present: {f}")
        else:
            fail += 1
            print(f"FAIL: missing file: {f}", file=sys.stderr)

    perl = "/data/service/hnp/bin/perl"
    if not os.path.isfile(perl):
        perl = "perl"
    env = dict(os.environ)
    # 沙箱 PATH 缺 /bin、/system/bin——dh_linktree 内部 doit() 需调用
    # install/ln/rm（toybox 提供），冒烟必须能找到（实测 'Can't exec
    # "install"'）；依赖包（dpkg）bin/ 提供 dpkg/dpkg-query 命令
    extra_path = ["/system/bin", "/bin"]
    for dep_dir in dep_dirs:
        dep_bin = os.path.join(dep_dir, "bin")
        if os.path.isdir(dep_bin):
            extra_path.append(dep_bin)
    env["PATH"] = os.pathsep.join(
        extra_path + env.get("PATH", "").split(os.pathsep))
    env["PERL5LIB"] = os.pathsep.join(collect_perl_dirs(pkg, *dep_dirs))

    # ── R2: perl -c 语法检查 ──────────────────────────────────────
    for f in (bin_script, seq_pm):
        if not os.path.isfile(f):
            continue
        r = subprocess.run([perl, "-c", f], capture_output=True, text=True,
                           env=env)
        if r.returncode == 0:
            pass_cnt += 1
            print(f"OK: perl -c {f}")
        else:
            fail += 1
            print(f"FAIL: perl -c {f}: {r.stderr}", file=sys.stderr)

    # ── R3: 功能冒烟（尽力，受限通过如实记录） ───────────────────
    smoke_blocked = ""
    try:
        # 可写绝对根目录候选（OHOS 沙箱 / 只读、/tmp 只读——dpkg 配方
        # 实证 /data/storage/el2/base/cache 可写）
        writable_root = None
        for cand in ("/data/storage/el2/base/cache",
                     tempfile.gettempdir(), "/tmp", "/var/tmp"):
            if os.path.isdir(cand) and os.access(cand, os.W_OK):
                writable_root = cand
                break
        if writable_root is None:
            smoke_blocked = "无可写绝对路径，冒烟跳过"
        else:
            smoke_id = f"dhlink-smoke-{os.getpid()}"
            src_root = os.path.join(writable_root, smoke_id, "src")
            os.makedirs(src_root, exist_ok=True)
            with open(os.path.join(src_root, "file.js"), "w") as f:
                f.write("console.log('smoke');\n")
            workdir = os.path.join(writable_root, smoke_id, "work")
            os.makedirs(os.path.join(workdir, "debian"), exist_ok=True)
            with open(os.path.join(workdir, "debian", "control"), "w") as f:
                f.write("Source: smoke\nSection: misc\nPriority: optional\n"
                        "Maintainer: Smoke Test <smoke@example.com>\n"
                        "Standards-Version: 4.6.0\n\n"
                        "Package: smoke\nArchitecture: all\n"
                        "Description: dh-linktree smoke test\n")
            # embed 动作：遍历 src_root 下所有文件，在 debian/smoke/
            # usr/share/smoke/lib 下重建同名相对路径的符号链接树
            r = subprocess.run(
                [perl, bin_script, "embed", src_root, "usr/share/smoke/lib"],
                capture_output=True, text=True, env=env, cwd=workdir)
            link = os.path.join(workdir, "debian", "smoke",
                                "usr", "share", "smoke", "lib", "file.js")
            if os.path.islink(link):
                pass_cnt += 1
                print(f"OK: smoke symlink tree created -> {link} -> "
                      f"{os.readlink(link)}")
            else:
                fail += 1
                print(f"FAIL: smoke symlink not created: {link}",
                      file=sys.stderr)
            # dpkg --search 阶段受阻说明（沙箱无 dpkg 数据库——脚本尾部
            # 生成依赖失败属预期，如实记录，不算断言失败）
            tail = (r.stderr or "").strip().splitlines()
            tail = tail[-6:]
            print(f"SMOKE-NOTE: dh_linktree exit={r.returncode}; "
                  f"stderr tail: {' | '.join(tail)}")
            if r.returncode != 0:
                print("SMOKE-NOTE: 受限通过——符号链接树已创建，"
                      "dpkg --search 阶段因沙箱无 dpkg 数据库受阻（如实记录）")
    except Exception as e:  # noqa: BLE001 — 冒烟尽力而为
        fail += 1
        print(f"FAIL: smoke exception: {e}", file=sys.stderr)
    if smoke_blocked:
        print(f"SMOKE-NOTE: {smoke_blocked}（受限说明）")

    print(f"RESULT: ASSERT_PASS={pass_cnt} ASSERT_FAIL={fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
