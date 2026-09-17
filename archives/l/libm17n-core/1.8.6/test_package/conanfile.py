#!/usr/bin/env python3
"""Consumer-side test for libm17n-core (m17n-lib 1.8.6).

The probe is compiled the way a real consumer builds it:
  * compiler taken from the Conan profile (tools.build:compiler_executables),
  * include/lib search paths taken from the aggregated cpp_info of the
    tested package and its dependencies,
  * every library declared by the package is linked in (-lm17n-core,
    -lm17n, -lm17n-flt), so a missing or unlinkable library fails the test,
  * the binary is executed with the dependency libdirs on LD_LIBRARY_PATH so
    that the DT_NEEDED entries (libxml2) and the package's own .so resolve.

On a cross build only compile+link is verified; on the OHOS CI worker
(build == host) the probe is executed on the target.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class Libm17nCoreTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    # VirtualRunEnv/VirtualBuildEnv are listed explicitly because an explicit
    # generators list *replaces* the default one; without VirtualRunEnv there
    # is no conanrun environment for test().
    generators = "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _compiler(self):
        """C compiler for the probe: the Conan profile value first (R33)."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") if isinstance(compilers, dict) else None
        if cc:
            return cc
        # Fallback only for profiles that do not pin the executables.
        for candidate in (os.environ.get("CC"), "clang", "cc", "gcc"):
            if candidate and (shutil.which(candidate)
                              or os.path.isfile(candidate)):
                return candidate
        return "cc"

    def _dep_dirs(self):
        incs = []
        libs = []
        for _ref, dep in self.dependencies.items():
            incs.extend(dep.cpp_info.includedirs)
            libs.extend(dep.cpp_info.libdirs)
        return list(dict.fromkeys(incs)), list(dict.fromkeys(libs))

    def build(self):
        incs, libdirs = self._dep_dirs()
        dep = self.dependencies[self.tested_reference_str.split("/")[0]]
        cflags = " ".join("-I" + p for p in incs)
        link = " ".join(
            ["-L" + p for p in libdirs]
            + ["-l" + lib for lib in dep.cpp_info.libs]
            + ["-Wl,-rpath," + p for p in libdirs]
        )
        # -std=gnu99: musl only declares POSIX interfaces with the GNU dialect.
        self.run(f"{self._compiler()} -std=gnu99 -Wall test.c -o test_probe "
                 f"{cflags} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross build: compile and link verified only "
                             "(the probe runs on the OHOS target)")
            return
        _incs, libdirs = self._dep_dirs()
        ldpath = os.pathsep.join(libdirs)
        self.run(
            f'export LD_LIBRARY_PATH="{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; '
            "./test_probe",
            env="conanrun",
        )
