#!/usr/bin/env python3
"""Conan test_package for soundtouch 2.0.0.

L1 test: compile test.cpp against the installed libSoundTouch headers +
library (real link, real WSOLA DSP run) and execute it.
"""
import os

from conan import ConanFile
from conan.tools.gnu import AutotoolsToolchain


class SoundtouchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "AutotoolsToolchain"
    # failsafe: VirtualRunEnv for shared lib rpath when running

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # compile with the conan toolchain flags (cross CC/CXX via
        # tools.build:compiler_executables conf in the profile)
        self.run(
            "$CXX $CXXFLAGS -I%s/include -c test.cpp -o test.o" %
            self.dependencies["soundtouch"].package_folder,
            env="conanbuild",
        )
        self.run(
            "$CXX $CXXFLAGS test.o -L%s/lib -lSoundTouch -lm -o test_soundtouch" %
            self.dependencies["soundtouch"].package_folder,
            env="conanbuild",
        )

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; wrap
        # binary execution with bash (adplug/adplay precedent)
        bash = os.environ.get("CONFIG_SHELL") or next(
            (p for p in (
                "/data/service/hnp/bin/bash",
                "/bin/bash",
                "/usr/bin/bash",
            ) if os.path.exists(p)),
            "bash",
        )
        pkg = self.dependencies["soundtouch"].package_folder
        pkg_lib = os.path.join(pkg, "lib")
        # both the test binary and libSoundTouch.so need libc++_shared.so
        # from the SDK llvm triplet dir at load time (conanrun env does not
        # carry build-machine loader paths)
        import glob as _glob
        ld_paths = [pkg_lib]
        _base = ("/data/service/hnp/ohos-sdk.org/"
                 "ohos-sdk_26.0.0.18/ohos/native/llvm/lib")
        if not os.path.isdir(_base):
            _cands = sorted(_glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
            _base = _cands[0] if _cands else ""
        if _base:
            for _sub in ("aarch64-linux-ohos",
                         "aarch64-linux-ohos/c++"):
                _d = os.path.join(_base, _sub)
                if os.path.isdir(_d):
                    ld_paths.append(_d)
        self.run(
            'LD_LIBRARY_PATH=%s:$LD_LIBRARY_PATH %s -c "./test_soundtouch"'
            % (":".join(ld_paths), bash),
            env="conanrun",
        )
