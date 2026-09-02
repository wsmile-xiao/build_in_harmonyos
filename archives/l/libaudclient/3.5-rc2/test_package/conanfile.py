#!/usr/bin/env python3
"""Conan test_package for libaudclient (L1 consumer test).

Why pkg-config and not CMakeDeps: the published glib/2.88.0 OHOS binary
ships empty component INTERFACE include dirs in its CMake metadata
(known E216 class issue), and libaudclient's headers pull glib.h and
dbus/dbus-glib.h, so the pkg-config flow (which carries the full
transitive Cflags) is the reliable consumer path — same as the
dbus-glib/0.114 test_package.

The consumer executes real runtime work (R34: no print-only stubs):
it dlopens the packaged libaudclient.so.2 by its upstream soname and
dlsyms the complete 71-symbol EXPORT surface. A D-Bus session bus does
not exist on OHOS (no dbus-daemon, no running Audacious), and every
audctrl entry point sends D-Bus messages immediately, so loading plus
the full export surface is the maximal executable scope (see
MANIFEST.yml).
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import mkdir
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LibaudclientTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        env = Environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self, scope="build").save_script("test-pkg-config-path")

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or shutil.which("clang") \
            or shutil.which("cc") or "cc"
        mkdir(self, self.build_folder)
        self.run(f'{cc} -Wall -g -O2 '
                 f'"{os.path.join(self.source_folder, "test_audclient.c")}" '
                 '-o test_audclient '
                 '$(pkg-config --cflags --libs audclient)',
                 cwd=self.build_folder, env="conanbuild")

    def test(self):
        bin_path = os.path.join(self.build_folder, "test_audclient")
        self.run(f'"{bin_path}"', cwd=self.build_folder, env="conanrun")
        self.output.info("libaudclient test_package: link + dlopen + "
                         "full 71-symbol export surface verified")
        print('HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
              '"command":' + json.dumps(bin_path) + ','
              '"discovered":1,"passedCount":1}')
        # Upstream suite audit conclusion (see test_package/MANIFEST.yml):
        # libaudclient 3.5-rc2 ships no automated tests — the audacious
        # buildsys (buildsys.mk.in, not automake) defines no check target
        # at all, no Makefile declares TESTS/check_PROGRAMS/check-local,
        # and the tree has no tests/ directory. The audit grep already ran
        # against the real source tree during conan create (build() in the
        # recipe, visible in the create log). Marker produced at
        # test_package stage per the aribb24/osmctools/sipcalc/xidle
        # precedent for upstream_test_in_build: false.
        audit_cmd = ("grep -rnE '(^|[^A-Za-z_])TESTS|check_PROGRAMS|"
                     "check-local' Makefile src/*/Makefile buildsys.mk.in "
                     "configure.ac")
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests",
            "framework": "none",
            "command": audit_cmd,
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "upstream libaudclient 3.5-rc2 release tarball contains no "
                "automated tests: the audacious buildsys.mk.in has no check "
                "target; no Makefile declares TESTS/check_PROGRAMS/"
                "check-local; configure.ac has no test macros; no tests/ "
                "directory exists. Consumer-side verification in this "
                "test_package covers link-time ABI (9 API addresses through "
                "real headers), dlopen by upstream soname and the complete "
                "71-symbol EXPORT surface (82 assertions)"
            ),
        }))
