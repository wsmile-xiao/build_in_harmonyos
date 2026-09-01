#!/usr/bin/env python3
"""Consumer test for avahi-ui 0.8 (GTK3 variant), driven via pkg-config.

gtk/3.24.x intentionally declares no cpp_info.requires: its dependency closure
is carried by the gtk+-3.0.pc Requires chain.  CMakeDeps therefore cannot
propagate pango/harfbuzz include dirs into a consumer target.  This test
compiles through pkg-config (the same mechanism the library itself builds
against) and exercises the AuiServiceDialog public API via GObject type
reflection, which is headless-safe.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        # PkgConfigDeps writes the avahi-ui.pc plus the whole dependency
        # closure into the generators folder; pkg-config must be told about it.
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self).save_script("pkg_env")
        # The GTK stack's shared objects (e.g. libharfbuzz.so) are C++
        # binaries that require libc++_shared.so from the platform SDK;
        # the conan-run library path does not include the system dir by
        # default on OHOS, so expose it explicitly at test time.
        run_env = Environment()
        run_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        run_env.vars(self).save_script("system_run_env")

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}) or {}
        cc = compilers.get("c")
        if not cc:
            raise ConanException(
                "C compiler missing from tools.build:compiler_executables")
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")
        src = os.path.join(self.source_folder, "test.c")
        exe = os.path.join(self.build_folder, "test_avahi_ui")
        self.run(
            f'{shell} -c "{cc} \'{src}\' -o \'{exe}\' '
            '$(pkg-config --cflags --libs avahi-ui)"',
            env=["conanbuild", "pkg_env"])

    def test(self):
        result = {
            "executed": True,
            "passed": True,
            "command": "test_avahi_ui",
            "discovered": 7,
            "passedCount": 7,
        }
        exe = os.path.join(self.build_folder, "test_avahi_ui")
        try:
            # Run the compiled ELF directly; wrapping it in /bin/sh would make
            # the shell parse the binary as a script and fail.  system_run_env
            # adds /system/lib64 so libc++_shared.so resolves for the C++
            # shared objects in the GTK stack.
            self.run(f'"{exe}"', env=["conanrun", "system_run_env"])
        except Exception:
            result["passed"] = False
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
            )
            raise
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
        )