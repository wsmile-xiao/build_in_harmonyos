#!/usr/bin/env python3
"""Conan test_package — bus 3.1.11.

Verifies a third-party consumer can compile, link and run against the
installed libbus (public header bus.h + -lbus), and that the installed
`bus` CLI executes on the platform.

Runtime note: all libbus IPC entry points (bus_create/bus_open/bus_write...)
require System V IPC (semget/shmget), which the OHOS app sandbox blocks with
SIGSYS. The library API path exercised here (bus_open on a non-existent bus
file) returns -1 before any semaphore syscall, so it runs on the sandbox while
still calling a real public API. Full IPC round-trip tests are enumerated in
the ledger and their SIGSYS platform block is documented separately.
"""
from conan import ConanFile
from conan.tools.layout import basic_layout
import os


class BusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        dep = self.dependencies["bus"]
        inc = " ".join(f"-I{p}" for p in dep.cpp_info.includedirs)
        lib = " ".join(f"-L{p}" for p in dep.cpp_info.libdirs)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        self.run(f"{cc} -Wall {inc} test.c {lib} -lbus -o test_bus", cwd=self.source_folder)
        self.run(f"{cc} -Wall {inc} test_ohos.c {lib} -lbus -o test_ohos", cwd=self.source_folder)

    def test(self):
        # conanrun env is empty for this package (VirtualRunEnv injects no
        # libdirs/PATH), so use absolute paths for binary and lib resolution.
        dep = self.dependencies["bus"]
        ld = ":".join(dep.cpp_info.libdirs)
        bus_bin = os.path.join(dep.cpp_info.bindirs[0], "bus")
        # Use absolute path: conan test() cwd is not guaranteed to be source_folder
        self.run(f'LD_LIBRARY_PATH="{ld}:$LD_LIBRARY_PATH" "{self.source_folder}/test_bus"', env="conanrun")
        # HarmonyOS-specific test (real API + SysV IPC platform probe)
        self.run(f'LD_LIBRARY_PATH="{ld}:$LD_LIBRARY_PATH" "{self.source_folder}/test_ohos"', env="conanrun")
        # bus CLI with no subcommand exits 2 (documented: "2 = the command is
        # not recognised") — proves the binary executes on OHOS.
        self.run(f'LD_LIBRARY_PATH="{ld}:$LD_LIBRARY_PATH" "{bus_bin}" >/dev/null 2>&1; test $? -eq 2', env="conanrun")
