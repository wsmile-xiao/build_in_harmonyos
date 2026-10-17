#!/usr/bin/env python3
"""Conan test_package for vosk-api 0.3.50.

Consumer-side verification of the packaged libvosk.so:

  1. test_vosk         — links `vosk::vosk` and drives the public C API
                         declared in <vosk_api.h>: the documented graceful
                         failure contract for missing models, plus a real
                         functional round-trip through
                         vosk_text_processor_new / vosk_text_processor_itn
                         (OpenFst Fst::Read + Compose + ShortestPath);
  2. make_identity_fst — OpenFst-only helper that writes the two identity
                         transducers used as ITN fixtures. It is a separate
                         process so that the OpenFst copy statically linked into
                         libvosk.so and the one linked into the fixture
                         generator never coexist in the same address space;
  3. ohos_dlopen_probe — loads libvosk.so through the OHOS dynamic loader
                         (the ctypes consumption path) and resolves the public
                         C API symbols with dlsym();
  4. ohos_specific_test.sh — HarmonyOS-specific checks: AArch64/ELF64 target,
                         NEEDED closure and the runtime dlopen probe above.
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class VoskApiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Test-only dependency: used to write the ITN FST fixtures.
        self.requires("openfst/1.8.4")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        # LD_LIBRARY_PATH for libvosk.so's own runtime dependency (libopenblas).
        VirtualRunEnv(self).generate(scope="run")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Skipping vosk-api consumer tests: target binaries "
                             "cannot run on this host")
            return

        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries directly; run
        # everything through bash and under the Conan run environment so that
        # libvosk.so's shared dependencies resolve.
        bash = os.environ.get("CONFIG_SHELL", "bash")
        bindir = self.cpp.build.bindirs[0]

        vosk_dep = self.dependencies["vosk-api"]
        lib_dir = os.path.join(vosk_dep.package_folder,
                               vosk_dep.cpp_info.libdirs[0])
        libvosk = os.path.join(lib_dir, "libvosk.so")

        tmp_root = os.environ.get("TMPDIR") or os.environ.get("HOME") or "/tmp"
        work = tempfile.mkdtemp(prefix="vosk-api-test-", dir=tmp_root)
        tagger = os.path.join(work, "tagger.fst")
        verbalizer = os.path.join(work, "verbalizer.fst")
        missing_model = os.path.join(work, "no-such-model")

        # 1. build the FST fixtures (OpenFst-only helper binary)
        self.run(f'{bash} -c \'./make_identity_fst "{tagger}"\'',
                 cwd=bindir, env="conanrun")
        self.run(f'{bash} -c \'./make_identity_fst "{verbalizer}"\'',
                 cwd=bindir, env="conanrun")

        # 2. functional consumer test against libvosk.so
        self.run(f'{bash} -c \'./test_vosk "{tagger}" "{verbalizer}" '
                 f'"{missing_model}"\'', cwd=bindir, env="conanrun")

        # 3. HarmonyOS-specific checks (target arch, NEEDED closure, dlopen)
        script = os.path.join(self.recipe_folder, "ohos_specific_test.sh")
        probe = os.path.join(bindir, "ohos_dlopen_probe")
        self.run(f'{bash} "{script}" "{libvosk}" "{probe}" "{work}"',
                 cwd=bindir, env="conanrun")
