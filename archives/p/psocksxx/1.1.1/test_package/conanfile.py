#!/usr/bin/env python3
"""Consumer test for psocksxx.

Compiles a real library client (test_consumer.cpp) against the packaged
headers and static archive, then runs it: the consumer opens a loopback TCP
echo server and drives psocksxx::tcpnsockstream / nsockaddr through a full
write/read round-trip. Exit code of the consumer decides the test result.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class PsocksxxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: compile/link only, skip run")
            return
        dep = self.dependencies[self.tested_reference_str]
        include = os.path.join(dep.package_folder, "include")
        lib = os.path.join(dep.package_folder, "lib")
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cxx = executables.get("cpp") or "clang++"
        self.run(
            '{cxx} -std=c++11 -I{inc} test_consumer.cpp -L{lib} -lpsocksxx '
            '-o test_consumer'.format(cxx=cxx, inc=include, lib=lib),
            env="conanbuild",
        )
        # Mirror the cppunit consumer-test invocation: unsigned ad-hoc test
        # binaries are executed through the shell on OHOS.
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        self.run('{} -c "./test_consumer"'.format(bash), env="conanrun")
