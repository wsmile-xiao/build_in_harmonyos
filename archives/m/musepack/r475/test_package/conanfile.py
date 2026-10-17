#!/usr/bin/env python3
"""Consumer test for the packaged musepack — end-to-end encode/decode
round-trip exercising both the command-line tools and the library:

  1. gen_wav generates a short stereo WAV (canonical 44-byte header)
  2. packaged mpcenc encodes it to an SV8 .mpc
  3. packaged mpcdec decodes it back to PCM (must exist and be non-empty)
  4. check_mpc links libmpcdec and validates the SV8 streaminfo via
     mpc_demux_get_info plus real frame decoding

test_type="explicit": executed by `conan test` (CI). `conan create`
builds this package without executing it, which keeps noexec sandbox
environments (knowledge E052/E077) able to pass local W3 verification.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class MusepackTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt", "gen_wav.c", "check_mpc.c"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run musepack tools in this environment")
            return

        pkg = self.dependencies["musepack"]
        bindir = os.path.join(pkg.package_folder, "bin")
        mpcenc = os.path.join(bindir, "mpcenc")
        mpcdec = os.path.join(bindir, "mpcdec")
        gen_wav = os.path.join(self.cpp.build.bindirs[0], "gen_wav")
        check_mpc = os.path.join(self.cpp.build.bindirs[0], "check_mpc")

        workdir = os.path.join(self.build_folder, "roundtrip")
        os.makedirs(workdir, exist_ok=True)
        wav_in = os.path.join(workdir, "in.wav")
        mpc_out = os.path.join(workdir, "out.mpc")
        wav_out = os.path.join(workdir, "decoded.wav")

        # 1) short stereo WAV
        self.run(f'"{gen_wav}" "{wav_in}"', env="conanrun")
        # 2) encode to MPC SV8 with the packaged encoder tool
        self.run(f'"{mpcenc}" --overwrite "{wav_in}" "{mpc_out}"', env="conanrun")
        # 3) decode back to PCM with the packaged decoder tool
        self.run(f'"{mpcdec}" "{mpc_out}" "{wav_out}"', env="conanrun")
        # 4) both artifacts must exist and be non-empty
        for path in (mpc_out, wav_out):
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise ConanException(f"round-trip artifact missing/empty: {path}")
        print(f"round-trip OK: {os.path.getsize(mpc_out)} bytes .mpc -> "
              f"{os.path.getsize(wav_out)} bytes wav")
        # 5) library-level SV8 streaminfo + frame decode check
        self.run(f'"{check_mpc}" "{mpc_out}"', env="conanrun")
