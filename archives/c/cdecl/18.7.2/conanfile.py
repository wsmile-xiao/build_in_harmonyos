#!/usr/bin/env python3
"""Conan recipe — cdecl 18.7.2 (Autotools)"""
import glob as _glob
import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CdeclConan(ConanFile):
    name = "cdecl"
    version = "18.7.2"
    description = "Composing and deciphering C (or C++) declarations or casts"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/paul-j-lucas/cdecl"
    url = "https://github.com/paul-j-lucas/cdecl"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 发布 tarball 自带维护者机器上生成的过期 src/config.h（ENABLE_TERM_SIZE=1、
        # HAVE_CURSES_H=1、WITH_READLINE=1）。src/pjl_config.h 用 quoted include
        # `#include "config.h"`，编译器优先命中源码树这份旧头文件，遮蔽 configure
        # 按 --disable-term-size/--without-readline 在构建目录生成的新 config.h，
        # 导致 cdecl_term.c 仍编译 curses.h（真机无 curses 而报错）。删除它，
        # 让 `#include "config.h"` 回落到构建目录里 configure 生成的产物。
        _stale_cfg = os.path.join(self.source_folder, "src", "config.h")
        if os.path.isfile(_stale_cfg):
            os.remove(_stale_cfg)
            self.output.info("[ok] Removed stale pre-generated src/config.h from release tarball")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # HarmonyOS: config.guess 无法识别 OHOS，强制指定 build triplet
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # 禁用可选依赖：readline（交互编辑）与 term-size（需要 curses）
        tc.configure_args.append("--without-readline")
        tc.configure_args.append("--disable-term-size")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: conan 建树后父目录对 getcwd() 不可达，configure 内 `pwd` 失败报
        # "working directory cannot be determined"；预置 PWD 让 shell 的 pwd 内建走
        # 逻辑路径（同 aribb24/adms/nspr 已过门禁先例），补丁 0001 已让 configure
        # 在 pwd 失败时回退 $PWD。
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder
        # E002: 真机 /tmp 为只读 erofs，bash heredoc/mktemp 及 run_test.sh 需要可写
        # TMPDIR；固定到 build_folder 下可写目录（hmbs 注入的 TMPDIR 优先复用）。
        tmpdir = os.environ.get("TMPDIR") or os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        # HMFS 平台诊断 (shell_getcwd): 工作目录链对 HNP bash 不可达时，fork
        # 子 shell 偶发 "Out of memory"，configure 内 automake 的 filesystem
        # timestamp resolution 探测（子 shell + 命令替换运行 ls -t）因此失败并
        # 硬报 "ls -t produces unexpected output"。预置缓存变量让 configure 走
        # "(cached)" 分支跳过整个探测（2 = 上游文档化的默认最坏情况分辨率）；
        # 补丁 0004 同时把探测失败降级为警告作为兜底。
        os.environ["am_cv_sleep_fractional_seconds"] = "yes"
        os.environ["am_cv_filesystem_timestamp_resolution"] = "2"
        # 真机 install 工具拒绝多源批量拷贝（install-man 批量拷 man 页退出码 64）：
        # 预置逐文件拷贝的 install wrapper 到 PATH 最前，configure 的
        # AC_PROG_INSTALL 若选中它，后续 make install 全程走兼容路径（package()
        # 还会把 Makefile 的 INSTALL* 变量强制改指向 wrapper，双保险）。
        wrapper_dir = self._write_install_wrapper()
        os.environ["PATH"] = wrapper_dir + os.pathsep + os.environ.get("PATH", "")
        autotools = Autotools(self)
        autotools.configure()
        # VPATH 构建适配: 真机无 flex/bison，configure 在发布树路径下（srcdir 无
        # .git）不检查 flex/bison，LEX/YACC/LEX_OUTPUT_ROOT 全部留空；而 automake
        # 的 .l.c/.y.c 后缀规则在 build 树缺少目标时仍会触发 ylwrap 重建
        # BUILT_SOURCES（lexer.c/parser.c/parser.h），空程序名直接报
        # `ylwrap: line 173: : command not found` (Error 127)。发布包自带这些生成
        # 文件，make 前同步进 build 树 src/（mtime 为当前时间，必然新于
        # lexer.l/parser.y），make 判定目标已最新即跳过生成规则。
        self._sync_generated_sources()
        autotools.make(args=["-j1"])
        # VPATH 构建适配: make check 前把源码树 test/data 同步进 build 树 test 目录
        self._sync_test_data()
        # L1: 运行上游官方测试套件 (make check) 并输出 HMBS 标记
        self._run_upstream_tests(autotools)

    def _sync_generated_sources(self):
        """VPATH 构建适配: 上游发布包自带 flex/bison 生成的 src/lexer.c、
        src/parser.c、src/parser.h（configure.ac 明确注释"trees from a released
        tarball shouldn't require flex & bison"，发布树路径下不设置 LEX/YACC）。
        真机无 flex/bison，automake 的 .l.c/.y.c 后缀规则一旦触发 ylwrap 就会因
        空程序名报 `ylwrap: line 173: : command not found` (Error 127)。这里把
        发布包自带的生成文件复制进 build 树各 src/ 目录（shutil.copy 使 mtime 为
        当前时间，必然新于 lexer.l/parser.y），make 判定目标已最新后完全跳过
        生成规则，编译经 VPATH 使用发布包自带的生成文件。"""
        gen_files = ("lexer.c", "parser.c", "parser.h")
        src_dir = os.path.join(self.source_folder, "src")
        missing = [f for f in gen_files if not os.path.isfile(os.path.join(src_dir, f))]
        if missing:
            self.output.warning(
                f"shipped generated sources not found in {src_dir}: {missing}"
            )
            return
        for mk in _glob.glob(
            os.path.join(self.build_folder, "**", "src", "Makefile"), recursive=True
        ):
            dst_dir = os.path.dirname(mk)
            for f in gen_files:
                shutil.copy(os.path.join(src_dir, f), os.path.join(dst_dir, f))
            self.output.info(
                f"[ok] synced generated lexer.c/parser.c/parser.h -> {dst_dir}"
            )

    def _sync_test_data(self):
        """VPATH (out-of-source) 构建适配: automake 的 make check 在 build 树
        test/ 目录下运行，而上游 test/data 属 EXTRA_DIST，只存在于源码树、
        不会复制进 build 树。test/ 下 .test 脚本以相对 CWD 的路径引用 data/
        配置文件（--config=data/...、--file=data/...、include "data/..."、
        $PWD/data/xdg），缺失时 cdecl fopen 失败返回 EX_NOINPUT(66) 或输出
        与 expected/ 不匹配导致 FAIL。这里把源码树 test/data 递归复制进 build
        树各 test 目录（幂等），保持测试语义与上游一致。"""
        src_data = os.path.join(self.source_folder, "test", "data")
        if not os.path.isdir(src_data):
            self.output.warning(f"skip test-data sync: {src_data} not found")
            return
        synced = 0
        for mk in _glob.glob(
            os.path.join(self.build_folder, "**", "test", "Makefile"), recursive=True
        ):
            dst_data = os.path.join(os.path.dirname(mk), "data")
            if os.path.isdir(dst_data):
                continue
            shutil.copytree(src_data, dst_data)
            self.output.info(f"[ok] synced test/data -> {dst_data}")
            synced += 1
        if synced == 0:
            self.output.warning(
                "no build-tree test/Makefile found; test/data not synced"
            )

    def _run_upstream_tests(self, autotools):
        """运行 `make check`（automake TESTS：test/ 90 个 .test + src/ 4 个
        check_PROGRAMS），解析各子目录 test-suite.log 的真实计数并输出
        HMBS_UPSTREAM_TEST_RESULT 标记；存在失败或未执行则让构建失败。"""
        rc = 0
        try:
            autotools.make(target="check", args=["-j1"])
        except Exception as exc:  # noqa: BLE001 - 需要拿到真实失败计数后再 raise
            rc = 1
            self.output.warning(f"make check returned failure (will verify counts): {exc}")
        total = passed = failed = skipped = 0
        logs = _glob.glob(os.path.join(self.build_folder, "**", "test-suite.log"), recursive=True)
        for log in logs:
            try:
                with open(log, "r", encoding="utf-8", errors="ignore") as _f:
                    text = _f.read()
            except OSError:
                continue
            # automake 汇总行形如 `# TOTAL: 94` / `# PASS: 94`，逐个累加
            for key in ("TOTAL", "PASS", "FAIL", "SKIP"):
                m = re.search(rf"^# {key}:\s+(\d+)", text, re.M)
                if m:
                    n = int(m.group(1))
                    if key == "TOTAL":
                        total += n
                    elif key == "PASS":
                        passed += n
                    elif key == "FAIL":
                        failed += n
                    else:
                        skipped += n
        executed = total - skipped
        self.output.info(
            f"upstream make check: total={total} executed={executed} "
            f"passed={passed} failed={failed} skipped={skipped}"
        )
        if total == 0 or executed == 0:
            raise RuntimeError("make check produced no executed test cases")
        status = "passed" if rc == 0 and failed == 0 and executed == passed else "failed"
        upstream = {
            "status": status,
            "framework": "automake",
            "command": "make check -j1",
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if status != "passed":
            for log in logs:
                self.output.error(f"=== {log} ===")
            raise RuntimeError(
                f"upstream tests failed: total={total} passed={passed} failed={failed} skipped={skipped}"
            )

    def _sync_install_extra(self):
        """VPATH 构建适配: share/bash-completions/completions 与
        share/zsh/site-functions 的 install-data-local 规则以裸文件名 `_cdecl`
        引用 EXTRA_DIST 补全脚本（非 automake 标准 install 规则，无 $(srcdir)
        回退），out-of-source 构建时 build 树没有该文件，`make install` 报
        `cp: bad '_cdecl': No such file or directory`。把源码树的 _cdecl 复制进
        build 树对应目录（幂等），与 _sync_test_data 同模式。"""
        for rel in (
            "share/bash-completions/completions",
            "share/zsh/site-functions",
        ):
            src = os.path.join(self.source_folder, rel, "_cdecl")
            if not os.path.isfile(src):
                self.output.warning(f"skip _cdecl sync: {src} not found")
                continue
            for mk in _glob.glob(
                os.path.join(self.build_folder, "**", rel, "Makefile"),
                recursive=True,
            ):
                dst = os.path.join(os.path.dirname(mk), "_cdecl")
                if os.path.isfile(dst):
                    continue
                shutil.copy(src, dst)
                self.output.info(
                    f"[ok] synced {rel}/_cdecl -> {os.path.dirname(mk)}"
                )

    def _write_install_wrapper(self):
        """真机预装 install 工具拒绝多源批量拷贝：automake 的 install-man 规则
        `$(INSTALL_DATA) $$files '$(DESTDIR)$(man1dir)'` 一次把同目录多个 man 页
        拷入目标目录，真机 staged install 对该形式报 usage error（退出码 64，
        单源形式正常，此前 bin/completions 等单文件安装均通过）。生成一个
        BSD/GNU install 兼容的逐文件拷贝 wrapper，供 configure/make install 使用。
        幂等：重复调用只覆盖写入同一路径。"""
        wrapper_dir = os.path.join(self.build_folder, "hmbs-install")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "install")
        script = (
            "#!/bin/sh\n"
            "# HMBS real-device install wrapper: per-file copy, multi-source safe\n"
            'mode=""\n'
            'destdir=""\n'
            "make_parents=0\n"
            "want_dir=0\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            '    case "$1" in\n'
            "        -d) want_dir=1; shift ;;\n"
            "        -D) make_parents=1; shift ;;\n"
            "        -c|-p|-v|-s|-P|-C) shift ;;\n"
            '        -m) mode="$2"; shift 2 ;;\n'
            "        -o|-g|-B|-S) shift 2 ;;\n"
            '        -t) destdir="$2"; shift 2 ;;\n'
            "        --) shift; break ;;\n"
            "        -*) shift ;;\n"
            "        *) break ;;\n"
            "    esac\n"
            "done\n"
            'if [ "$want_dir" -eq 1 ]; then\n'
            '    for d in "$@"; do\n'
            '        if [ "$make_parents" -eq 1 ]; then mkdir -p "$d" || exit 1;'
            " else mkdir \"$d\" || exit 1; fi\n"
            "    done\n"
            "    exit 0\n"
            "fi\n"
            'if [ "$#" -lt 2 ]; then\n'
            '    echo "install: missing operand" >&2\n'
            "    exit 64\n"
            "fi\n"
            "n=0\n"
            'for _x in "$@"; do n=$((n+1)); done\n'
            'dest=""\n'
            'for _x in "$@"; do dest="$_x"; done\n'
            "apply_mode() {\n"
            '    [ -n "$mode" ] || return 0\n'
            '    chmod "$mode" "$1" 2>/dev/null || true\n'
            "}\n"
            'if [ -n "$destdir" ]; then\n'
            '    for s in "$@"; do\n'
            '        cp -f "$s" "$destdir/" || exit 1\n'
            '        apply_mode "$destdir/$(basename "$s")"\n'
            "    done\n"
            "    exit 0\n"
            "fi\n"
            'if [ "$n" -eq 2 ]; then\n'
            '    src="$1"\n'
            '    if [ -d "$dest" ]; then\n'
            '        cp -f "$src" "$dest/" || exit 1\n'
            '        apply_mode "$dest/$(basename "$src")"\n'
            "    else\n"
            '        cp -f "$src" "$dest" || exit 1\n'
            '        apply_mode "$dest"\n'
            "    fi\n"
            "    exit 0\n"
            "fi\n"
            'if [ ! -d "$dest" ]; then\n'
            '    mkdir -p "$dest" || exit 1\n'
            "fi\n"
            "i=0\n"
            'for arg in "$@"; do\n'
            "    i=$((i+1))\n"
            '    if [ "$i" -lt "$n" ]; then\n'
            '        cp -f "$arg" "$dest/" || exit 1\n'
            '        apply_mode "$dest/$(basename "$arg")"\n'
            "    fi\n"
            "done\n"
            "exit 0\n"
        )
        with open(wrapper, "w", encoding="utf-8", newline="\n") as _f:
            _f.write(script)
        try:
            os.chmod(wrapper, 0o755)
        except OSError:
            self.output.warning("chmod install wrapper failed; ignored")
        self.output.info(f"[ok] wrote install wrapper: {wrapper}")
        return wrapper_dir

    def _patch_makefile_install(self):
        """把 configure 记录进各 Makefile 的 INSTALL/INSTALL_PROGRAM/
        INSTALL_SCRIPT/INSTALL_DATA 变量改指向逐文件拷贝的 install wrapper
        （真机 staged install 多源批量拷贝退出码 64，见 _write_install_wrapper）。
        automake 的 INSTALL_PROGRAM/SCRIPT/DATA 均以 ${INSTALL} 为基底，替换
        INSTALL 一行即可覆盖全部安装路径；此处对四个变量统一替换更稳。"""
        wrapper_dir = self._write_install_wrapper()
        wrapper = os.path.join(wrapper_dir, "install")
        lines_re = re.compile(
            r"^(INSTALL(?:_PROGRAM|_SCRIPT|_DATA)?\s*=\s*).*$", re.M
        )
        replaced = 0
        for mk in _glob.glob(
            os.path.join(self.build_folder, "**", "Makefile"), recursive=True
        ):
            with open(mk, "r", encoding="utf-8", errors="ignore") as _f:
                text = _f.read()

            def _sub(m, _w=wrapper):
                if m.group(1).startswith("INSTALL_DATA"):
                    return m.group(1) + _w + " -m 644"
                return m.group(1) + _w

            new = lines_re.sub(_sub, text)
            if new == text:
                continue
            with open(mk, "w", encoding="utf-8", newline="\n") as _f:
                _f.write(new)
            replaced += 1
            self.output.info(f"[ok] patched INSTALL* -> {wrapper} in {mk}")
        if replaced == 0:
            self.output.warning(
                "no Makefile INSTALL lines patched; make install may still "
                "use the staged install"
            )

    def package(self):
        autotools = Autotools(self)
        # VPATH 构建适配: install-data-local 裸引用 EXTRA_DIST 的 _cdecl
        self._sync_install_extra()
        # 真机 install 工具多源批量拷贝退出码 64：强制 make install 使用
        # 逐文件拷贝的 wrapper（见 _patch_makefile_install）
        self._patch_makefile_install()
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
