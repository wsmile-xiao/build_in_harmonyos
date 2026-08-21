import os
import subprocess
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class NymphrpcTestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["nymphrpc"].cpp_info
        incdir = dep.includedirs[0] if dep.includedirs else "include/nymph"
        libdir = dep.libdirs[0] if dep.libdirs else "lib"
        libs = " ".join("-l" + l for l in dep.libs) if dep.libs else "-lnymphrpc"

        poco_inc = []
        poco_lib = []
        for _r, d in self.dependencies.items():
            if str(_r.ref).startswith("poco"):
                base = getattr(d, "package_folder", None) or ""
                for p in d.cpp_info.includedirs:
                    if not os.path.isabs(p) and base:
                        p = os.path.join(base, p)
                    if os.path.isdir(p):
                        poco_inc.append(p)
                for p in d.cpp_info.libdirs:
                    if os.path.isdir(p):
                        poco_lib.append(p)

        inc_flags = "-I " + incdir
        for d in poco_inc:
            inc_flags += " -I " + d

        lib_flags = ""
        for d in poco_lib:
            lib_flags += " -L " + d
        lib_flags += " -L " + libdir

        cppstd = self.settings.get_safe("compiler.cppstd")
        std_flag = "-std=c++%s" % str(cppstd).replace("gnu", "") if cppstd else "-std=c++17"

        cc = os.environ.get("CXX", "clang++")
        poco_libs = "-lPocoNet -lPocoUtil -lPocoFoundation -lPocoJSON -pthread"

        cmd = "%s %s test.cpp -o test_probe %s %s %s %s" % (
            cc, std_flag, inc_flags, lib_flags, libs, poco_libs
        )
        self.run(cmd)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only compile+link verified")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        libdirs = []
        for _r, d in self.dependencies.items():
            libdirs += d.cpp_info.libdirs
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        cmd = "%s -c 'export LD_LIBRARY_PATH=\"%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\"; ./test_probe'" % (
            bash, ldpath
        )
        self.run(cmd, env="conanrun")
