#!/usr/bin/env python3
"""Conan test_package for tnftpd 20231001 - daemon binary smoke test.

tnftpd is an inetd-style FTP daemon; it has no --help/--version that prints
to stdout and blocks on the FTP control loop if run with a live socket.  The
consumer test therefore (a) verifies binary presence/executable/ELF and
(b) runs the self-terminating ``-C <user>`` access-check mode (getopt parses
the option, sgetpwnam + checkaccess run, then main exits 0/1 without entering
the FTP loop or depending on /etc state).  All assertions are offline and
deterministic; the test.sh emits the HMBS machine-evidence markers.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class TnftpdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building：工具类无编译验证，跳过执行")
            return
        dep = self.dependencies.get("tnftpd")
        bindir = "bin"
        if dep is not None:
            try:
                rel = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
            except Exception:
                rel = "bin"
            cand = rel if os.path.isabs(rel) else os.path.join(
                dep.package_folder, rel)
            bindir = cand if os.path.isdir(cand) else os.path.join(
                dep.package_folder, "bin")
            self.output.info("tnftpd package_folder=%s bindir=%s" % (
                dep.package_folder, bindir))

        # /tmp 在目标机只读（erofs）；test.sh 内一律用 $TMPDIR 落临时文件。
        # HMBS 已注入 TMPDIR/TMP/TEMP，缺失时回退到 build_folder/tmp。
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or ""
        )
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        os.environ["TEMPDIR"] = tmpdir

        script = os.path.join(self.recipe_folder, "test.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        self.run('"%s" "%s" "%s"' % (shell, script, bindir), env="conanrun")
