import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class PlayerctlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    # VirtualBuildEnv / VirtualRunEnv: CC on PATH + runtime lib dirs (LD_LIBRARY_PATH).
    # We compile the consumer directly from the resolved cpp_info of playerctl and its
    # transitive deps (glib) instead of pkg-config: on this OHOS worker the
    # PkgConfigDeps-generated PKG_CONFIG_PATH is not reliably injected into the test
    # build environment, so `pkg-config --cflags --libs playerctl` cannot find
    # playerctl.pc. Reading cpp_info is deterministic and self-contained.
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = os.environ.get("CC") or "clang"

        inc_dirs, lib_dirs, libs = [], [], []
        for dep in self.dependencies.values():
            ci = dep.cpp_info
            inc_dirs.extend(ci.includedirs)
            lib_dirs.extend(ci.libdirs)
            libs.extend(ci.libs)
            for comp in ci.components.values():
                inc_dirs.extend(comp.includedirs)
                lib_dirs.extend(comp.libdirs)
                libs.extend(comp.libs)

        # de-duplicate while preserving order (dependent libs must precede their deps)
        def _uniq(seq):
            seen, out = set(), []
            for x in seq:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out

        inc_dirs = _uniq(inc_dirs)
        lib_dirs = _uniq(lib_dirs)
        libs = _uniq(libs)

        inc = " ".join("-I%s" % p for p in inc_dirs)
        lib = " ".join("-L%s" % p for p in lib_dirs)
        lnk = " ".join("-l%s" % l for l in libs)
        cmd = "{cc} test.c -o test_playerctl {inc} {lib} {lnk}".format(
            cc=cc, inc=inc, lib=lib, lnk=lnk)
        self.run(cmd, shell=True, env="conanbuild")

    def test(self):
        self.run("./test_playerctl", env="conanrun")
