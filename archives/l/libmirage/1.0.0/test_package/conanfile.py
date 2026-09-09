#!/usr/bin/env python3
"""Conan test_package for libmirage (L1 consumer test).

Why pkg-config and not CMakeDeps: the published glib/2.88.0 OHOS binary
ships empty component INTERFACE include dirs in its CMake metadata (known
E216 class issue), so CMake consumers cannot resolve glib-object.h; the
pkg-config flow is the canonical consumer path for an autotools-era
library (dbus-glib 0.114 test_package precedent).

Two layers, both executing real functionality (R34: no print-only stubs):
  1. test_mirage — C consumer compiled and linked against libmirage via
     pkg-config, constructing the top-level MirageMirage object and
     querying the library version through the real API;
  2. L1e negative-test dependency: the compiled binary requires the
     package's lib/ + include/ artifacts (static libmirage.a), so moving
     them away makes this test fail (CI L1e sabotage check).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import mkdir
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LibmirageTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

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
        # Same accessor AutotoolsToolchain uses internally: the profile
        # conf value is a dict, conf_info.get without check_type can
        # hand back the raw string / default in test context.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or shutil.which("clang") \
            or shutil.which("cc") or "cc"
        mkdir(self, self.build_folder)
        self.run(f'{cc} -g -O2 "{os.path.join(self.source_folder, "test.c")}" '
                 '-o test_mirage '
                 '$(pkg-config --cflags --libs libmirage)',
                 cwd=self.build_folder, env="conanbuild")

    def test(self):
        # real API consumer binary (static link incl. glib/sndfile chain)
        self.run("./test_mirage", cwd=self.build_folder, env="conanrun")
        self.output.info("libmirage test_package: API consumer verified")
