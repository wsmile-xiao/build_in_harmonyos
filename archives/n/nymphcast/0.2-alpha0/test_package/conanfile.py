#!/usr/bin/env python3
"""test_package for nymphcast - compile a real probe that runs the packaged
nymphcast_server executable and validates its version banner."""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class NymphcastTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Probe uses libc only (popen/fgets); no external include/lib flags.
        # -static-libstdc++: statically link the C++ runtime so the probe does
        # not depend on libc++_shared.so being resolvable at run time (the
        # conanrun env only adds Conan package lib dirs, not the OHOS SDK or
        # system lib64 paths; on a clean W3/CI shell the probe would otherwise
        # fail with "Error loading shared library libc++_shared.so").
        cc = os.environ.get("CXX", "clang++")
        self.run(cc + " -std=c++17 -static-libstdc++ test.cpp -o test_probe")

    def _runtime_lib_dirs(self):
        # The dynamic dependencies pulled in by nymphcast_server (Poco,
        # freeimage, ...) are themselves linked against libc++_shared.so,
        # which is not shipped inside any Conan package. On the device it
        # lives in /system/lib64; on the CI/W3 worker shell the conanrun
        # env only prepends Conan package lib dirs, so resolve the runtime
        # from the OHOS toolchain (clang --print-file-name) and extend the
        # loader path explicitly.
        import subprocess
        dirs = []
        try:
            clang = os.environ.get("CC", "/data/service/hnp/bin/clang")
            if not os.path.isfile(clang):
                clang = "/data/service/hnp/bin/clang"
            out = subprocess.check_output(
                [clang, "--print-file-name=libc++_shared.so"], text=True).strip()
            d = os.path.dirname(os.path.abspath(out))
            if os.path.isfile(os.path.join(d, "libc++_shared.so")):
                dirs.append(d)
        except Exception:
            pass
        if os.path.isfile("/system/lib64/libc++_shared.so"):
            dirs.append("/system/lib64")
        return dirs

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only compile+link verified")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        extra = ":".join(self._runtime_lib_dirs())
        # conanrun.sh preserves the parent LD_LIBRARY_PATH, so exporting the
        # runtime dir here propagates through to the popen() child.
        self.run(bash + " -c 'LD_LIBRARY_PATH=\"" + extra
                 + ":${LD_LIBRARY_PATH:-}\" ./test_probe'", env="conanrun")
