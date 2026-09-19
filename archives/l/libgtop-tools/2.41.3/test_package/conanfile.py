#!/usr/bin/env python3
"""L1 test for libgtop-tools: verify the two daemon binaries were built and run."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class LibgtopToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        if can_run(self):
            # OHOS 实测：self.run 输出流继承会导致编译失败静默（无 error 行），
            # 输出绑定日志文件。
            self.run(
                "clang test.c -o test_libgtop_tools > compile.log 2>&1 || (cat compile.log; exit 1)",
                env="conanbuild",
            )

    def test(self):
        if can_run(self):
            pkg = self.dependencies["libgtop-tools"]
            bindir = pkg.cpp_info.bindirs[0]
            daemon_bin = os.path.join(bindir, "libgtop_daemon2")
            server_bin = os.path.join(bindir, "libgtop_server2")
            # Existence + executability checks (test.c)
            self.run(
                f"./test_libgtop_tools {daemon_bin} {server_bin}",
                env="conanrun",
            )
            # Real execution: libgtop_daemon2 --help parses GOption args and
            # exits 0 before daemonizing (setreuid happens only later in
            # main()); this exercises dynamic glib linking + the statically
            # linked in-tree libgtop-2.0.
            self.run(f"{daemon_bin} --help", env="conanrun")
            # libgtop_server2 is an upstream setuid-root helper: it calls
            # setreuid() unconditionally, which OHOS seccomp blocks for
            # non-root users (Signal 31/SIGSYS). Execute it and record the
            # outcome without failing the test — on a suid-capable install
            # it would proceed to serve the libgtop protocol on stdin/stdout.
            self.run(f"{server_bin} < /dev/null", env="conanrun", ignore_errors=True)
            self.output.info("OK: libgtop-tools smoke test completed")
