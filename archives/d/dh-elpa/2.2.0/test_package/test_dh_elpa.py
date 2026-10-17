#!/usr/bin/env python3
"""dh-elpa consumer test (R34):
  R1 文件存在断言: bin/dh_elpa + bin/dh_elpa_test + Sequence/elpa.pm +
     debhelper 模板 (emacsen-common compat/install/remove) + prerm-elpa +
     lib/dh-elpa install/remove + dh-elpa.el（man 页存在则加条件断言）
  R2 perl -c 语法检查: dh_elpa + elpa.pm（硬断言——PERL5LIB 加入本包
     share/perl5 与依赖包 perl 库根；Module::Metadata 由 perl 核心提供）；
     dh_elpa_test 依赖 File::Find::Rule/Array::Utils/Text::Glob/
     Debian::Control（未发布 ohpcd）——模块齐备才断言，否则 SMOKE-NOTE
  R3 功能冒烟（--no-byte-compile）: 最小 debian 骨架（control/compat=12/
     changelog/elpa）+ 单文件 elisp 包真实运行 dh_elpa——emacs -batch
     安装器把 .el 装入
     debian/smoke/usr/share/emacs/site-lisp/elpa/smoke-0.1/ 并生成
     smoke-pkg.el
  R4 功能冒烟（字节编译默认开启，尽力）: DH_ELPA_TEMPLATEDIR 指向包内模板
     目录后运行 dh_elpa——emacsen-common helper 脚本生成 + substvars
     misc:Depends 写入（构建期不产 .elc：字节编译由 helper 脚本在消费机
     安装时执行）；postinst/prerm autoscript 阶段因沙箱无
     /usr/share/debhelper/autoscripts 受阻，如实 SMOKE-NOTE，不伪造通过率
  emacs 无法在沙箱执行时 R3/R4 如实降级为受限说明，R1/R2 硬断言不受影响
"""
import os
import subprocess
import sys
import tempfile


def collect_perl_dirs(*roots):
    """收集 perl 库根目录（PERL5LIB 候选）。

    只加包根与常见 perl 库根（lib/perl5、share/perl5、lib、share/perl），
    不 walk 全树——否则会误抓同名模块（dpkg 包 Dselect/Method/Config.pm
    遮蔽 perl 核心 Config 模块的实测教训，见 dh-linktree notes）。
    """
    dirs = set()
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for cand in (root,
                     os.path.join(root, "lib", "perl5"),
                     os.path.join(root, "share", "perl5"),
                     os.path.join(root, "lib"),
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
    r1_files = [
        ("bin/dh_elpa", os.path.join(pkg, "bin", "dh_elpa")),
        ("bin/dh_elpa_test", os.path.join(pkg, "bin", "dh_elpa_test")),
        ("Sequence/elpa.pm",
         os.path.join(pkg, "share", "perl5", "Debian", "Debhelper",
                      "Sequence", "elpa.pm")),
        ("debhelper 模板 compat",
         os.path.join(pkg, "share", "debhelper", "dh_elpa",
                      "emacsen-common", "compat")),
        ("debhelper 模板 install",
         os.path.join(pkg, "share", "debhelper", "dh_elpa",
                      "emacsen-common", "install")),
        ("debhelper 模板 remove",
         os.path.join(pkg, "share", "debhelper", "dh_elpa",
                      "emacsen-common", "remove")),
        ("autoscripts/prerm-elpa",
         os.path.join(pkg, "share", "debhelper", "autoscripts",
                      "prerm-elpa")),
        ("lib/dh-elpa/install",
         os.path.join(pkg, "lib", "dh-elpa", "install")),
        ("lib/dh-elpa/remove",
         os.path.join(pkg, "lib", "dh-elpa", "remove")),
        ("dh-elpa.el",
         os.path.join(pkg, "share", "emacs", "site-lisp", "elpa",
                      "dh-elpa.el")),
    ]
    for label, f in r1_files:
        if os.path.isfile(f):
            pass_cnt += 1
            print(f"OK: file present: {label}")
        else:
            fail += 1
            print(f"FAIL: missing file: {label} ({f})", file=sys.stderr)

    # man 页为 pod2man 构建产物——存在则加条件断言，缺失如实记录
    man1 = os.path.join(pkg, "share", "man", "man1", "dh_elpa.1")
    man1t = os.path.join(pkg, "share", "man", "man1", "dh_elpa_test.1")
    if os.path.isfile(man1) and os.path.isfile(man1t):
        pass_cnt += 1
        print("OK: man pages present (dh_elpa.1 + dh_elpa_test.1)")
    else:
        print("SMOKE-NOTE: man pages absent (pod2man unavailable at build "
              "time — 如实记录，不影响功能断言)")

    perl = "/data/service/hnp/bin/perl"
    if not os.path.isfile(perl):
        perl = "perl"
    env = dict(os.environ)
    # 沙箱 PATH 缺 /bin、/system/bin——dh_elpa 内部 doit() 需调用
    # install/cp（toybox 提供）；依赖包 bin/ 提供 dpkg-parsechangelog
    # 与 emacs 命令
    extra_path = ["/system/bin", "/bin"]
    for dep_dir in dep_dirs:
        dep_bin = os.path.join(dep_dir, "bin")
        if os.path.isdir(dep_bin):
            extra_path.append(dep_bin)
    env["PATH"] = os.pathsep.join(
        extra_path + env.get("PATH", "").split(os.pathsep))
    env["PERL5LIB"] = os.pathsep.join(collect_perl_dirs(pkg, *dep_dirs))
    # dh_elpa 经 Dh_Lib 调 dpkg-architecture 解析 DEB_HOST_ARCH——OHOS 上
    # dpkg-architecture 不识别 ohos triple（dpkg 配方实测），预设 arm64
    # （dpkg-architecture 官方支持 env 预设优先）
    env["DEB_HOST_ARCH"] = "arm64"
    # 上游 helper/install 自带抑制（helper/install:8-9）——dh_elpa 直接
    # 运行时同样抑制，避免 emacs 尝试向不可写 HOME 写 eln-cache
    env["EMACS_INHIBIT_AUTOMATIC_NATIVE_COMPILATION"] = "t"
    # emacs 探测（提前到 R2 前——EMACSLOADPATH 需按 emacs 包 lisp 目录补齐）
    import shutil
    emacs = None
    if os.path.isfile("/data/service/hnp/bin/emacs"):
        emacs = "/data/service/hnp/bin/emacs"
    else:
        for dep_dir in dep_dirs:
            p = os.path.join(dep_dir, "bin", "emacs")
            if os.path.isfile(p):
                emacs = p
                break
        if emacs is None:
            emacs = shutil.which("emacs")

    # EMACSLOADPATH：dh-elpa 内部用 `emacs -batch -Q -l package`（加载
    # package.el）——emacs 包 runenv 只导出 `<pkg>/share/emacs/<ver>/lisp`
    # 单目录，而 package.el 位于 lisp/emacs-lisp/，且 -Q 隐含
    # --no-site-lisp → 必须把 lisp 的各子目录一并加入（复现 emacs 默认
    # dump load-path 形态），否则 emacs 报 "Cannot open load file" exit 255
    # （CI build #51320 实测）。
    elpa_dir = os.path.join(pkg, "share", "emacs", "site-lisp", "elpa")
    load_dirs = [elpa_dir]
    lisp_root = None
    for dep_dir in dep_dirs:
        base = os.path.join(dep_dir, "share", "emacs")
        if os.path.isdir(base):
            for ver in sorted(os.listdir(base)):
                cand = os.path.join(base, ver, "lisp")
                if os.path.isdir(cand):
                    lisp_root = cand
                    break
        if lisp_root:
            break
    if lisp_root:
        load_dirs.append(lisp_root)
        for name in sorted(os.listdir(lisp_root)):
            sub = os.path.join(lisp_root, name)
            if os.path.isdir(sub):
                load_dirs.append(sub)
        print(f"SMOKE-NOTE: emacs lisp root={lisp_root}")
    else:
        print("SMOKE-NOTE: emacs lisp 目录未找到（依赖包无 "
              "share/emacs/*/lisp）")
    cur_loadpath = env.get("EMACSLOADPATH", "")
    if cur_loadpath:
        load_dirs.append(cur_loadpath)
    env["EMACSLOADPATH"] = os.pathsep.join(load_dirs)

    # ── R2: perl -c 语法检查 ──────────────────────────────────────
    # dh_elpa 与 elpa.pm 的依赖均在 requires 内（Dh_Lib/Dpkg::Version/
    # Config::Tiny）或 perl 核心（Module::Metadata）——硬断言。
    r2_files = [
        os.path.join(pkg, "bin", "dh_elpa"),
        os.path.join(pkg, "share", "perl5", "Debian", "Debhelper",
                     "Sequence", "elpa.pm"),
    ]
    for f in r2_files:
        if not os.path.isfile(f):
            continue
        r = subprocess.run([perl, "-c", f], capture_output=True, text=True,
                           env=env)
        if r.returncode == 0:
            pass_cnt += 1
            print(f"OK: perl -c {os.path.basename(f)}")
        else:
            fail += 1
            print(f"FAIL: perl -c {os.path.basename(f)}: {r.stderr}",
                  file=sys.stderr)

    # dh_elpa_test 的 use 语句依赖 File::Find::Rule / Array::Utils /
    # Text::Glob / Debian::Control（均未发布 ohpcd）——先探测，齐备才做
    # 语法检查断言；缺失如实 SMOKE-NOTE（受限说明），不伪造
    dh_elpa_test = os.path.join(pkg, "bin", "dh_elpa_test")
    if os.path.isfile(dh_elpa_test):
        missing_mods = []
        for mod in ("File::Find::Rule", "Array::Utils", "Text::Glob",
                    "Debian::Control"):
            r = subprocess.run([perl, "-M" + mod, "-e", "1"],
                               capture_output=True, text=True, env=env)
            if r.returncode != 0:
                missing_mods.append(mod)
        if not missing_mods:
            r = subprocess.run([perl, "-c", dh_elpa_test],
                               capture_output=True, text=True, env=env)
            if r.returncode == 0:
                pass_cnt += 1
                print("OK: perl -c dh_elpa_test")
            else:
                fail += 1
                print(f"FAIL: perl -c dh_elpa_test: {r.stderr}",
                      file=sys.stderr)
        else:
            print("SMOKE-NOTE: dh_elpa_test 语法检查跳过——所需 Perl 模块"
                  "未发布 ohpcd: " + ", ".join(missing_mods) +
                  "（受限说明，如实记录）")

    # emacs 预检——dh_elpa 内部 doit_quietly 会吞掉 emacs 的 stderr，
    # 这里显式复现 `-l package` 加载并打印 stderr（诊断用）
    if emacs is not None:
        probe = subprocess.run(
            [emacs, "-batch", "-Q", "-l", "package", "--eval",
             '(princ "package-loaded")'],
            capture_output=True, text=True, env=env)
        ptail = (probe.stderr or "").strip().splitlines()
        print(f"SMOKE-NOTE: emacs -l package probe exit={probe.returncode}; "
              f"stderr: {' | '.join(ptail[-4:])}")

    # ── R3/R4: 功能冒烟（尽力，受限通过如实记录） ─────────────────
    smoke_blocked = ""
    try:
        writable_root = None
        for cand in ("/data/storage/el2/base/cache",
                     tempfile.gettempdir(), "/tmp", "/var/tmp"):
            if os.path.isdir(cand) and os.access(cand, os.W_OK):
                writable_root = cand
                break
        if writable_root is None:
            smoke_blocked = "无可写绝对路径，冒烟跳过"
        elif emacs is None:
            smoke_blocked = "emacs 不可用（依赖包无 bin/emacs）——dh_elpa "
            "安装器即 emacs -batch，功能冒烟跳过（R1/R2 硬断言不受影响）"
        else:
            smoke_id = f"dhelpa-smoke-{os.getpid()}"
            workdir = os.path.join(writable_root, smoke_id)
            os.makedirs(os.path.join(workdir, "debian"), exist_ok=True)
            with open(os.path.join(workdir, "debian", "control"), "w") as f:
                f.write("Source: smoke\nSection: misc\nPriority: optional\n"
                        "Maintainer: Smoke Test <smoke@example.com>\n"
                        "Standards-Version: 4.6.0\n\n"
                        "Package: smoke\nArchitecture: all\n"
                        "Description: dh-elpa smoke test package\n")
            # debhelper 兼容级别——CI 实测（build #51164）缺此文件 dh_elpa
            # 直接报错 "Please specify the compatibility level in
            # debian/compat"（level 1 requested）exit 25。取 12，与上游
            # dh-elpa 2.2.0 自身的 debhelper-compat (= 12) 一致。
            with open(os.path.join(workdir, "debian", "compat"), "w") as f:
                f.write("12\n")
            with open(os.path.join(workdir, "debian", "changelog"), "w") as f:
                f.write("smoke (0.1) unstable; urgency=medium\n\n"
                        "  * Smoke test.\n\n"
                        " -- Smoke Test <smoke@example.com>  "
                        "Mon, 01 Jan 2024 00:00:00 +0000\n")
            with open(os.path.join(workdir, "debian", "elpa"), "w") as f:
                f.write("smoke.el\n")
            with open(os.path.join(workdir, "smoke.el"), "w") as f:
                f.write(";;; smoke.el --- smoke test package "
                        "-*- lexical-binding: t; -*-\n\n"
                        ";; Version: 0.1\n"
                        ";; Package-Version: 0.1\n"
                        ";; Package-Requires: ((emacs \"24.1\"))\n\n"
                        ";;; Commentary:\n\n"
                        ";;; Code:\n\n"
                        "(defun smoke-hello ()\n"
                        "  \"Return a greeting string.\"\n"
                        "  \"hello\")\n\n"
                        "(provide 'smoke)\n"
                        ";;; smoke.el ends here\n")

            # R3: --no-byte-compile——emacs 安装器装入 .el + 生成 -pkg.el
            dh_elpa = os.path.join(pkg, "bin", "dh_elpa")

            # 诊断复现：dh_elpa 内部用 doit_quietly 吞掉 emacs 的 stderr，
            # 这里按同样参数手动复现，把真实报错抓出来（CI build #52239
            # 只见 "returned exit code 255"，根因未知）
            try:
                print(f"SMOKE-NOTE: emacs --version: "
                      f"{(subprocess.run([emacs, '--version'], capture_output=True, text=True, env=env).stdout or '').strip().splitlines()[:1]}")
                # 上游 dh-elpa 2.2.0 声明 emacs >= 1:30.1，制品仓仅 29.1
                # （R51/依赖核对已记录）——探测关键 API 是否在 29.1 存在，
                # 判定是「测试环境问题」还是「真实版本阻塞」
                api_probe = subprocess.run(
                    [emacs, "-batch", "-Q", "--eval",
                     "(princ (format \"emacs=%s\" emacs-version))"
                     "(dolist (s '(lm-package-requires copy-package-desc "
                     "package--make-autoloads-and-stuff package-desc-from-define "
                     "package--description-file package-generate-autoloads "
                     "loaddefs-generate))"
                     "(princ (format \" %s=%s\" s (if (fboundp s) \"y\" \"N\"))))"],
                    capture_output=True, text=True, env=env)
                print(f"SMOKE-NOTE: api probe rc={api_probe.returncode} "
                      f"out={(api_probe.stdout or '').strip()[:400]}")
                dest_rel = os.path.join("debian", "smoke", "usr", "share",
                                        "emacs", "site-lisp", "elpa")
                os.makedirs(os.path.join(workdir, dest_rel), exist_ok=True)
                rep_cmd = [
                    emacs, "-batch", "-Q", "-l", "package",
                    "--eval", "(add-to-list 'package-directory-list "
                              "\"/usr/share/emacs/site-lisp/elpa\")",
                    "-f", "package-initialize",
                    "-l", "dh-elpa.el",
                    "-f", "dhelpa-batch-install-file",
                    dest_rel, "./smoke.el",
                    os.path.join(workdir, "debian", ".debhelper", "elpa"),
                    "1704067200",
                ]
                rep = subprocess.run(rep_cmd, capture_output=True, text=True,
                                     env=env, cwd=workdir)
                print(f"SMOKE-NOTE: reproduce emacs install exit={rep.returncode}")
                print(f"SMOKE-NOTE: reproduce stderr: "
                      f"{(rep.stderr or '').strip()[-700:]}")
                print(f"SMOKE-NOTE: reproduce stdout: "
                      f"{(rep.stdout or '').strip()[-300:]}")
            except Exception as de:  # noqa: BLE001
                print(f"SMOKE-NOTE: reproduce failed: {de}")

            r3 = subprocess.run(
                [perl, dh_elpa, "--no-byte-compile"],
                capture_output=True, text=True, env=env, cwd=workdir)
            r3_el = os.path.join(workdir, "debian", "smoke", "usr", "share",
                                 "emacs", "site-lisp", "elpa", "smoke-0.1",
                                 "smoke.el")
            r3_pkg = os.path.join(workdir, "debian", "smoke", "usr", "share",
                                  "emacs", "site-lisp", "elpa", "smoke-0.1",
                                  "smoke-pkg.el")
            for label, f in (("R3 .el 装入", r3_el),
                             ("R3 -pkg.el 生成", r3_pkg)):
                if os.path.isfile(f):
                    pass_cnt += 1
                    print(f"OK: {label}: {f}")
                else:
                    fail += 1
                    print(f"FAIL: {label}: {f}", file=sys.stderr)
            tail = (r3.stderr or "").strip().splitlines()
            print(f"SMOKE-NOTE: dh_elpa --no-byte-compile exit="
                  f"{r3.returncode}; stderr tail: {' | '.join(tail[-6:])}")

            # R4: 字节编译模式（默认）——DH_ELPA_TEMPLATEDIR 指向包内模板
            # 目录（补丁 0001 的 env 覆盖）。注意：dh_elpa 构建期不产
            # 生 .elc——字节编译由生成的 emacsen-common helper 脚本在
            # 消费机安装时执行（helper/install: byte-recompile-directory）。
            # 构建期可观测的字节编译模式产物 = helper 脚本 + misc:Depends
            # substvar——断言这两个。
            r4_env = dict(env)
            r4_env["DH_ELPA_TEMPLATEDIR"] = os.path.join(
                pkg, "share", "debhelper", "dh_elpa", "emacsen-common")
            r4 = subprocess.run([perl, dh_elpa], capture_output=True,
                                text=True, env=r4_env, cwd=workdir)
            r4_helper = os.path.join(workdir, "debian", "smoke", "usr",
                                     "lib", "emacsen-common", "packages",
                                     "install", "smoke")
            r4_substvars = os.path.join(workdir, "debian",
                                        "smoke.substvars")
            if os.path.isfile(r4_helper):
                pass_cnt += 1
                print(f"OK: R4 helper 脚本生成: {r4_helper}")
            else:
                fail += 1
                print(f"FAIL: R4 helper 脚本缺失: {r4_helper}",
                      file=sys.stderr)
            substvars_ok = False
            if os.path.isfile(r4_substvars):
                with open(r4_substvars, "r") as f:
                    substvars_ok = "emacsen-common" in f.read()
            if substvars_ok:
                pass_cnt += 1
                print("OK: R4 substvars misc:Depends (emacsen-common)")
            else:
                fail += 1
                print(f"FAIL: R4 substvars 缺失 emacsen-common: "
                      f"{r4_substvars}", file=sys.stderr)
            tail = (r4.stderr or "").strip().splitlines()
            print(f"SMOKE-NOTE: dh_elpa (byte-compile) exit="
                  f"{r4.returncode}; stderr tail: {' | '.join(tail[-6:])}")
            if r4.returncode != 0:
                print("SMOKE-NOTE: 受限通过——helper 脚本与 substvars 已"
                      "生成；postinst/prerm autoscript 阶段因沙箱无 "
                      "/usr/share/debhelper/autoscripts（debhelper 包未携带 "
                      "postinst-emacsen 模板）受阻（如实记录）")
            else:
                print("SMOKE-NOTE: 字节编译模式全流程退出码 0——"
                      "autoscript 阶段在沙箱内可用")
    except Exception as e:  # noqa: BLE001 — 冒烟尽力而为
        fail += 1
        print(f"FAIL: smoke exception: {e}", file=sys.stderr)
    if smoke_blocked:
        print(f"SMOKE-NOTE: {smoke_blocked}（受限说明）")

    print(f"RESULT: ASSERT_PASS={pass_cnt} ASSERT_FAIL={fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
