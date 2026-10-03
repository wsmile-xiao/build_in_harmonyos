#!/usr/bin/env python3
"""Conan recipe for sexpect 2.4.0 (CMake) — "Expect for shells".

sexpect is a single-binary CLI that drives interactive programs over a PTY
without Tcl/Expect: `sexpect spawn` starts one daemon per session which owns
the pty master and a UNIX-domain sockfile; `send/expect/interact/wait/get/...`
are short-lived clients talking to that daemon over the sockfile.

Zero third-party dependencies (libc + pthread only).  The upstream CTest
suite (25 bash-driven cases, 2 more are Linux-guarded upstream) is executed
inside build() per R51.

OHOS adaptations (see patches/ and notes.md):
  * HarmonyOS denies creating pathname AF_UNIX sockets for non-app processes
    (bind(2) -> EPERM on every writable filesystem) and mounts /tmp read-only.
    The source patch makes both the server and the clients fall back to the
    abstract socket namespace, keyed by a deterministic hash of the sockfile
    path, when pathname bind is not permitted.  No platform macro is used.
  * Two upstream tests write temporary files into /tmp (read-only on OHOS):
    they now use ${TMPDIR:-/tmp} (build() points TMPDIR into the build tree).
  * One test spawns `ls -l /`, which the OHOS sandbox denies (EACCES); the
    child then exits non-zero and `sexpect wait` (which propagates the child
    exit status) fails.  That child command now lists the logfile in the test
    cwd instead; the assertions themselves are unchanged.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SexpectConan(ConanFile):
    name = "sexpect"
    version = "2.4.0"
    description = "Expect for shells: drive interactive programs over a PTY from shell scripts"
    license = "GPL-3.0-only"
    homepage = "https://github.com/clarkwang/sexpect"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("expect", "pty", "terminal", "automation", "cli")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sexpect targets Linux/OHOS only, got {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"], build_tool_args=["-j1"])

        # Upstream CTest suite (bash-driven).  HarmonyOS mounts /tmp read-only,
        # so TMPDIR points at a writable directory inside the build tree; the
        # patched tests honour ${TMPDIR:-/tmp}.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        # ctest is invoked explicitly: CMake.test() becomes
        # `cmake --build --target test`, which cannot forward ctest flags
        # such as --output-on-failure (plfit 0.9.6 same rationale).
        self.run("ctest --output-on-failure --parallel 1", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
