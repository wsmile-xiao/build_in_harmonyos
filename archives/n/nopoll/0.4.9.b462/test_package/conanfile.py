#!/usr/bin/env python3
"""Conan test_package — nopoll 0.4.9.b462

Consumer-side verification: compiles test.c against the packaged
libnopoll + headers, runs it on the target (conanrun env).
The test creates a listener + client loopback in one process and
asserts a websocket echo roundtrip.
"""
from conan import ConanFile
from conan.tools.build import can_run


class NopollTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["nopoll"]
        inc = dep.cpp_info.includedirs[0]
        # upstream headers live under include/nopoll/ and cross-include each
        # other with <nopoll_xxx.h> (same-dir refs, same as upstream pkg-config
        # Cflags -I${includedir}/nopoll)
        incdir = inc if inc.endswith("/nopoll") else inc + "/nopoll"
        libdir = dep.cpp_info.libdirs[0]
        # openssl is a transitive dependency of libnopoll (static lib needs
        # its symbols at final link); take lib path from the openssl dep
        ssl = self.dependencies["openssl"]
        ssllib = ssl.cpp_info.aggregated_components().libdirs[0]
        cc = "clang"
        self.run(
            f"{cc} test.c -o test -I{inc} -I{incdir} -L{libdir} -L{ssllib} "
            f"-lnopoll -lssl -lcrypto -lpthread -ldl",
            env="conanbuild",
        )

    def test(self):
        if can_run(self):
            self.run("./test", env="conanrun")
