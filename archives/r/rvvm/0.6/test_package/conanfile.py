import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class RvvmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["rvvm"].cpp_info
        # R34/L1e: verify the packaged artifacts really exist so the test cannot
        # silently fall back to any system librvvm.
        for p in dep.includedirs:
            if not os.path.isdir(p):
                raise ConanException(f"rvvm package include dir missing: {p}")
        libdir = dep.libdirs[0]
        if not os.path.isdir(libdir):
            raise ConanException(f"rvvm package lib dir missing: {libdir}")
        inc = " ".join("-I" + p for p in dep.includedirs)
        # R33: compiler from Conan conf, matching the recipe itself.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # Static-link the packaged librvvm_static.a; pthread/m are its runtime deps.
        self.run(
            f"{cc} test.c -o test_probe {inc} -L{libdir} "
            "-lrvvm_static -lpthread -lm"
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile + link verified only")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
