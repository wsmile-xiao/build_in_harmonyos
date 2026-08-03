#!/usr/bin/env python3
import os

from conan import ConanFile


class OpensslTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["openssl"]
        cpp = dep.cpp_info
        inc_flags = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in cpp.libdirs)
        link_flags = " ".join(f"-l{lib}" for lib in cpp.libs)
        sys_flags = " ".join(f"-l{lib}" for lib in cpp.system_libs)
        cc = os.environ.get("CC", "clang")
        self.run(
            f"{cc} test_openssl.c -o test_openssl "
            f"{inc_flags} {lib_flags} {link_flags} {sys_flags}"
        )

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "")
        if not bash or not os.path.exists(bash):
            bash = ""
            for candidate in [
                "/data/service/hnp/bin/bash",
                "/storage/Users/currentUser/usr/local/bin/bash",
                "/usr/bin/bash",
                "/bin/bash",
            ]:
                if os.path.exists(candidate):
                    bash = candidate
                    break
        if bash:
            self.run(f"{bash} -c './test_openssl'", env="conanrun")
        else:
            self.run("./test_openssl", env="conanrun")
