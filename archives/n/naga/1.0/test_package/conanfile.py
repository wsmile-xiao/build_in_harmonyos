#!/usr/bin/env python3
"""Conan test_package — naga 1.0.

naga is an interactive ncurses game: the binary blocks on getch() and
cannot run in a non-interactive CI environment. Following the nudoku
precedent, the recipe exposes the curses-free game logic as libnaga.a;
this test compiles test_naga.c against the installed headers + libnaga.a
and runs 12 real assertions (initial state, movement, screen wrap-around,
food, collision, keypress handling). The packaged binary itself is
verified as an existing aarch64 ELF executable (magic + e_machine).
"""

import os
import struct

from conan import ConanFile


class NagaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["naga"].package_folder
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        bin_path = os.path.join(pkg, "bin", "naga")

        # Binary check: must exist and be an aarch64 ELF executable.
        # (Byte-level check, no os.access(X_OK): HMDFS reports fixed 660.)
        assert os.path.isfile(bin_path), f"naga binary missing: {bin_path}"
        with open(bin_path, "rb") as f:
            header = f.read(20)
        assert header[:4] == b"\x7fELF", "naga binary is not an ELF file"
        (machine,) = struct.unpack("<H", header[18:20])
        assert machine == 183, f"naga binary is not aarch64 (e_machine={machine})"
        self.output.info("naga binary OK: aarch64 ELF executable")

        # R33: compiler from the Conan conf dict, never from shell env vars.
        # Resilience: if the conf absolute path is inaccessible on the worker
        # (preflight 2026-09-08: "/data/service/hnp/bin/clang" -> 127),
        # fall back to bare "clang" resolved via conanbuild PATH.
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        raw_cc = ce.get("c") or "clang"
        if os.path.sep in raw_cc:
            if os.path.isfile(raw_cc) and os.access(raw_cc, os.X_OK):
                cc = raw_cc
            else:
                self.output.warning(
                    f"conf compiler '{raw_cc}' inaccessible, "
                    "falling back to 'clang' via conanbuild PATH"
                )
                cc = "clang"
        else:
            cc = raw_cc

        # OHOS: /system/bin/sh (mksh) cannot execute ELF test binaries, so
        # each phase is launched through CONFIG_SHELL bash (zlib precedent).
        # Compile runs with conanbuild and run runs with conanrun
        # (ncurses/6.5 precedent: two self.run calls, one per scope).
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_naga.sh")
        src_c = os.path.join(self.source_folder, "test_naga.c")
        test_bin = os.path.join(self.build_folder, "test_naga")
        self.run(f"{bash} {script} compile {cc} {inc} {lib} {src_c} {test_bin}",
                 env="conanbuild")
        self.run(f"{bash} {script} run {test_bin}",
                 env="conanrun")
        # ── 上游官方测试证据（no_tests）──
        # 上游确无可执行测试套件（审计见 MANIFEST.yml 的 upstream_test_audit）。
        # build() 的标记在 conan create 命中缓存时不会执行（本轮 incomplete
        # 根因：日志显示 "Already installed!"，build() 被跳过），而
        # test_package 的 test() 每次预检都会执行，故在此用 print 直达
        # stdout 再次输出同一 no_tests 标记，保证缓存命中时仍有证据。
        # 状态/数字与 MANIFEST 审计结论一致，不伪造执行数。
        print(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none",'
            '"command":"none (upstream ships no test suite)",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,'
            '"reason":"Makefile has no check/test target; '
            'src/tests/run_tests.c absent from the source tree"}',
            flush=True,
        )
