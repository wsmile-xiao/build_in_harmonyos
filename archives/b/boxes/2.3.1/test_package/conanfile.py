#!/usr/bin/env python3
"""Conan test_package — boxes 2.3.1 (ASCII box drawing filter, executable).

test.sh 真实调用被测二进制（echo 文本画框 / -d 设计 / -r 移除），自身输出
HMBS_TEST_PACKAGE_RESULT 机器证据标记，经 self.run 透传进 conan/preflight
日志供 hmbs 采集。

HMBS_UPSTREAM_TEST_RESULT：上游 black-box + sunny-day 套件在 recipe build()
内真机执行（结果写入包内 res/upstream_test_result.json）。预检复用时 conan
缓存可能跳过 build()，故本阶段读取该文件并裸 print 复发标记。
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class BoxesTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _terminfo_dir(self):
        """Locate the terminfo dir contributed by the ncurses run dep."""
        dep = self.dependencies.get("ncurses")
        if not dep or not dep.package_folder:
            return None
        cands = list(getattr(dep.cpp_info, "resdirs", None) or [])
        cands.append("share")
        cands.append("lib")
        for cand in cands:
            p = os.path.join(dep.package_folder, cand.lstrip("/"), "terminfo")
            if os.path.isdir(p):
                return p
        for base, _dirs, _files in os.walk(dep.package_folder):
            if os.path.basename(base) == "terminfo":
                return base
        return None

    def test(self):
        package_folder = self.dependencies["boxes"].package_folder
        bin_path = os.path.join(package_folder, "bin", "boxes")
        assert os.path.isfile(bin_path), f"boxes binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            # boxes draws via ncurses setupterm; a TERM with a valid TERMINFO
            # is required or the drawing path aborts ("terminals database is
            # inaccessible"). Set these directly in os.environ so the test.sh
            # subprocess (which inherits the current env) gets them; using
            # self.run(env="conanrun") would rebuild/override os.environ.
            os.environ["TERM"] = "xterm"
            # The boxes package bundles the ncurses terminfo under its own
            # share/terminfo; point TERMINFO there so the packaged binary can
            # draw (a consumer has no external TERMINFO dependency).
            terminfo = os.path.join(package_folder, "share", "terminfo")
            if os.path.isdir(terminfo):
                os.environ["TERMINFO"] = terminfo
                os.environ["TERMINFO_DIRS"] = terminfo
            # boxes needs a config file; point BOXES at the packaged one.
            cfg = os.path.join(package_folder, "share", "boxes", "boxes-config")
            if os.path.isfile(cfg):
                os.environ["BOXES"] = cfg
            # The test.sh consumer tests use only grep -F, not sed \b, so
            # no GNU sed PATH override is needed here.
            self.run(f'"{shell}" "{test_script}" "{bin_path}"', cwd=cwd)
            # HMBS_TEST_PACKAGE_RESULT 由 test.sh 在用例结束后自行输出。
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"boxes is not an ELF binary: {magic!r}"
            self.output.info(f"boxes binary exists and has ELF magic: {bin_path}")

        # Re-emit the upstream test result recorded by build() on the real
        # device; the marker must appear in every preflight log.
        result_file = os.path.join(package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_file):
            raise ConanException(
                f"upstream_test_result.json missing in package: {result_file} — "
                "build() must have failed to persist the upstream test result")
        with open(result_file, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(upstream, ensure_ascii=False)}", flush=True)