#!/usr/bin/env python3
"""Conan test_package -- jnoise 0.6.0 consumer-side verification (R34).

jnoise is an application; the test *executes the packaged binary*, it does
not merely check that files exist.  Six falsifiable assertions run in
test_jnoise.cpp:
  A1 packaged bin/jnoise is an ELF with e_machine == EM_AARCH64 (read with
     open()/read(), because stat() on OHOS paths gives false negatives)
  A2 its dynamic string table declares a NEEDED entry for libjack
  A3 that very SONAME loads via dlopen() in the Conan run environment and
     exports jack_client_open (positive control for the runtime layer)
  A4 `jnoise 0`   -> exit 1 plus "Level is too high, max = -10dB"
  A5 `jnoise abc` -> exit 1 plus "Level is too high" (atof() of a
     non-numeric argument yields 0.0 dB, above the -10 dB ceiling)
  A6 `jnoise -10` -> exit 1 plus "Can't connect to JACK" and NOT "Level is
     too high" (the -10 dB boundary value is accepted, so the process really
     reaches the JACK client path; A6 presupposes that no JACK server is
     running -- the case on this device and on CI workers, see notes.md)
Each assertion prints its own [PASS]/[FAIL] line; the summary line starts
with RESULT: so it can never be miscounted as a seventh assertion, and the
program exits non-zero unless all six pass.
"""
import os

from conan import ConanFile


class JnoiseTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # R33: compiler from the Conan profile conf, never a bare shell ${CXX}.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or "clang++"
        env_prefix = ""
        try:
            real = os.path.realpath(cxx)
            llvm_lib = os.path.join(os.path.dirname(os.path.dirname(real)), "lib")
            if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
                env_prefix = 'export LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}"; '.format(llvm_lib)
        except OSError:
            pass
        self.run(env_prefix + '"{}" -O1 -std=c++11 -o test_jnoise test_jnoise.cpp -ldl'.format(cxx))

    def test(self):
        pkg = self.dependencies["jnoise"].package_folder
        jnoise_bin = os.path.join(pkg, "bin", "jnoise")
        self.run('./test_jnoise "{}"'.format(jnoise_bin), env="conanrun")
