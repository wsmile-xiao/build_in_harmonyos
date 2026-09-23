#!/usr/bin/env python3
"""dh-vim-addon consumer test (R34) — really executes the packaged artifact.

R1 文件存在断言: bin/dh_vim-addon + lib/perl5/Debian/Debhelper/Sequence/vim_addon.pm
R2 perl -c 语法检查: 两个文件（PERL5LIB 含本包 + 依赖包 debhelper/dpkg 的 perl 库根）
R3 功能冒烟（真实运行）: 最小 debian 骨架 + 两个 addon 目录，真实运行
   `dh_vim-addon -p<package>`——断言脚本退出码 0，且在
   usr/share/vim/vimfiles/pack/dist-bundle/{start,opt}/ 下创建了符号链接树
R4 鸿蒙特有测试（OpenHarmony 平台特性）: 目标机架构、OHOS hnp perl 运行时、
   目标架构解释器、OHOS 权限语义下的可执行位、packpath 链接可重定位、
   上游固定 shebang 在 OHOS 的调用契约
"""
import os
import shutil
import subprocess
import sys
import tempfile


def find_perl():
    for cand in ("/data/service/hnp/bin/perl", shutil.which("perl")):
        if cand and os.path.isfile(cand):
            return cand
    return "perl"


def collect_perl_dirs(*roots):
    """收集 perl 库根目录（PERL5LIB 候选）。

    只加包根与常见 perl 库根（lib/perl5、lib、share/perl5、share/perl），
    不 walk 全树——否则会误抓同名模块（实测 dpkg 包的 Dselect/Method/Config.pm
    会遮蔽 perl 核心 Config 模块，导致 Errno.pm 编译失败）。
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


def pick_writable_root():
    for cand in ("/data/storage/el2/base/cache",
                 tempfile.gettempdir(),
                 os.environ.get("TMPDIR"),
                 os.path.join(os.path.expanduser("~"), "tmp"),
                 "/var/tmp"):
        if cand and os.path.isdir(cand) and os.access(cand, os.W_OK):
            return cand
    return None


def write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    dep_dirs = sys.argv[2:]
    fail = 0
    passed = 0

    bin_script = os.path.join(pkg, "bin", "dh_vim-addon")
    seq_pm = os.path.join(pkg, "lib", "perl5", "Debian", "Debhelper",
                          "Sequence", "vim_addon.pm")

    # ── R1: 文件存在断言 ──────────────────────────────────────────
    for f in (bin_script, seq_pm):
        if os.path.isfile(f):
            passed += 1
            print("OK: file present: %s" % f)
        else:
            fail += 1
            print("FAIL: missing file: %s" % f, file=sys.stderr)

    perl = find_perl()
    env = dict(os.environ)
    env["PERL5LIB"] = os.pathsep.join(collect_perl_dirs(pkg, *dep_dirs))

    # ── R2: perl -c 语法检查 ──────────────────────────────────────
    for f in (bin_script, seq_pm):
        if not os.path.isfile(f):
            continue
        r = subprocess.run([perl, "-c", f], capture_output=True, text=True,
                           env=env)
        if r.returncode == 0:
            passed += 1
            print("OK: perl -c %s" % f)
        else:
            fail += 1
            print("FAIL: perl -c %s: %s" % (f, r.stderr), file=sys.stderr)

    # ── R3: 功能冒烟——真实运行 dh_vim-addon 创建符号链接树 ─────────
    # symlink_targets 供 R4/H5 复用（冒烟临时树在 finally 中删除，
    # 链接目标必须当场记录）
    symlink_targets = []
    writable = pick_writable_root()
    if writable is None or not os.path.isfile(bin_script):
        print("SMOKE-NOTE: 无可写目录或脚本缺失，功能冒烟跳过")
    else:
        work = tempfile.mkdtemp(prefix="dhvim-smoke-", dir=writable)
        try:
            os.makedirs(os.path.join(work, "debian"))
            write(os.path.join(work, "debian", "control"),
                  "Source: smoke\n"
                  "Section: misc\n"
                  "Priority: optional\n"
                  "Maintainer: Smoke Test <smoke@example.com>\n"
                  "Build-Depends: debhelper-compat (= 13)\n"
                  "Standards-Version: 4.6.0\n"
                  "\n"
                  "Package: smoke\n"
                  "Architecture: all\n"
                  "Description: dh-vim-addon smoke test\n")
            write(os.path.join(work, "debian", "changelog"),
                  "smoke (1.0) unstable; urgency=medium\n\n"
                  "  * smoke\n\n"
                  " -- Smoke <smoke@example.com>  Mon, 01 Jan 2024 "
                  "00:00:00 +0000\n")
            # 自动 addon（start/）+ 可选 addon（opt/）——均不含 doc/，
            # 避免依赖 vim-common 的 helpztags（该包未发布）
            auto_dir = os.path.join(work, "debian", "smoke", "usr", "share",
                                    "smoke", "plugin")
            os.makedirs(auto_dir)
            write(os.path.join(auto_dir, "x.vim"), "let g:loaded_smoke=1\n")
            opt_dir = os.path.join(work, "debian", "smoke", "usr", "share",
                                   "optsmoke")
            os.makedirs(opt_dir)
            write(os.path.join(opt_dir, "o.vim"), "let g:loaded_optsmoke=1\n")
            write(os.path.join(work, "debian", "smoke.vim-addon"),
                  "usr/share/smoke\n")
            write(os.path.join(work, "debian", "smoke.vim-opt-addon"),
                  "usr/share/optsmoke\n")

            r = subprocess.run([perl, bin_script, "-psmoke"],
                               capture_output=True, text=True, env=env,
                               cwd=work)
            base = os.path.join(work, "debian", "smoke", "usr", "share",
                                "vim", "vimfiles", "pack", "dist-bundle")
            if r.returncode == 0:
                passed += 1
                print("OK: dh_vim-addon -psmoke exit 0")
            else:
                fail += 1
                print("FAIL: dh_vim-addon exit=%s stderr=%s"
                      % (r.returncode, (r.stderr or "")[-600:]),
                      file=sys.stderr)
            for sub, name in (("start", "smoke"), ("opt", "optsmoke")):
                link = os.path.join(base, sub, name)
                if os.path.islink(link):
                    passed += 1
                    target = os.readlink(link)
                    symlink_targets.append((sub, name, target))
                    print("OK: symlink tree %s/%s -> %s" % (sub, name, target))
                else:
                    fail += 1
                    print("FAIL: expected symlink missing: %s" % link,
                          file=sys.stderr)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    # ── R4: 鸿蒙特有测试（OpenHarmony 平台特性）────────────────────
    # 上游是 Debian 侧工具：固定 shebang `#!/usr/bin/perl`，依赖 Debian 系统
    # perl 路径、dpkg 数据库与 0755 安装权限。OpenHarmony PC 上这些前提都不
    # 成立（解释器由 hnp 运行时提供、包路径为 /storage/Users 长绝对路径、
    # 权限由平台收敛）。以下断言针对这些平台差异，7 条。
    print("-- R4: OpenHarmony-specific checks --")

    # H1: 消费链运行在 OpenHarmony（sysname=HarmonyOS）aarch64 目标机上
    #（用 os.uname() 而非 `uname` 子进程——CI worker 的 PATH 不含 uname，
    #  实测 subprocess 调用 uname 会 FileNotFoundError）
    uts = os.uname()
    if uts.sysname == "HarmonyOS" and uts.machine == "aarch64":
        passed += 1
        print("OK: H1 OpenHarmony target %s/%s (%s)"
              % (uts.sysname, uts.machine, uts.release))
    else:
        fail += 1
        print("FAIL: H1 expected HarmonyOS/aarch64, got %s/%s"
              % (uts.sysname, uts.machine), file=sys.stderr)

    # H2: 平台 perl 由 OHOS 自带 hnp 运行时提供（OHOS 无系统 perl 发行包）
    hnp_perl = "/data/service/hnp/bin/perl"
    if os.path.exists(hnp_perl):
        passed += 1
        print("OK: H2 OHOS hnp perl runtime: %s -> %s"
              % (hnp_perl, os.path.realpath(hnp_perl)))
    else:
        fail += 1
        print("FAIL: H2 missing OHOS hnp perl runtime %s" % hnp_perl,
              file=sys.stderr)

    # H3: 解释器为目标架构构建（aarch64-linux），确保跑的是 OHOS 目标运行时
    r = subprocess.run([perl, "-V:archname"], capture_output=True, text=True)
    archname = r.stdout.strip()
    if "aarch64" in archname:
        passed += 1
        print("OK: H3 perl %s" % archname)
    else:
        fail += 1
        print("FAIL: H3 unexpected perl archname %r" % archname,
              file=sys.stderr)

    # H4: OHOS 文件系统权限语义下安装产物保留属主可执行位
    #（实测 mode=0770，非 Debian 常见 0755；CLI 调用与 CI L2 门禁均依赖此项）
    if os.path.isfile(bin_script) and os.access(bin_script, os.X_OK):
        passed += 1
        print("OK: H4 bin/dh_vim-addon executable on OHOS "
              "(mode=0o%o)" % (os.stat(bin_script).st_mode & 0o777))
    else:
        fail += 1
        print("FAIL: H4 bin/dh_vim-addon missing or not executable",
              file=sys.stderr)

    # H5: 制品可重定位——packpath 符号链接必须是相对目标
    #（OHOS 上 Conan 包位于 /storage/Users/<user>/.conan2/... 长绝对路径，
    #  绝对链接在制品迁移/重定位后失效；上游生成的是相对链接，2 条断言）
    if len(symlink_targets) == 2:
        for sub, name, target in symlink_targets:
            if not target.startswith("/"):
                passed += 1
                print("OK: H5 relocatable relative symlink %s/%s -> %s"
                      % (sub, name, target))
            else:
                fail += 1
                print("FAIL: H5 symlink %s/%s target=%r is not relative"
                      % (sub, name, target), file=sys.stderr)
    else:
        fail += 2
        print("FAIL: H5 packpath tree unavailable (smoke phase not run)",
              file=sys.stderr)

    # H6: 上游固定 shebang 未经改写（本适配 0 补丁），但 OHOS 上不存在
    # `/usr/bin/perl`，故调用方必须经平台解释器执行（本测试即该路径）。
    # 断言 shebang 保持上游原样；`/usr/bin/perl` 的存在性只作证据记录。
    shebang = None
    if os.path.isfile(bin_script):
        with open(bin_script, "rb") as fh:
            shebang = fh.readline().decode("utf-8", "replace").strip()
    print("NOTE: H6 shebang=%r  /usr/bin/perl exists=%s"
          % (shebang, os.path.exists("/usr/bin/perl")))
    if shebang == "#!/usr/bin/perl":
        passed += 1
        print("OK: H6 upstream shebang preserved (invoke via platform perl)")
    else:
        fail += 1
        print("FAIL: H6 unexpected shebang %r" % shebang, file=sys.stderr)

    print("RESULT: ASSERT_PASS=%d ASSERT_FAIL=%d" % (passed, fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
