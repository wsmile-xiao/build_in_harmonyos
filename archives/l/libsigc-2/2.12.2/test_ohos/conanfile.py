#!/usr/bin/env python3
# HarmonyOS-specific test runner — libsigc-2/2.12.2
#
# Runs test_ohos.sh against the FINAL Conan package on OpenHarmony PC.
# Independent of test_package (library API): this validates OHOS delivery
# — ELF64 Little-Endian AArch64, musl loader, versioned SONAME, NEEDED
# closure, .codesign sections, absence of host paths and RPATH, and a
# real signal/slot run on the target.
#
# The consumer binary is compiled here (not reused from test_package) so
# the check applies to the exact package under test; it links against
# the packaged library through CMakeDeps exactly like a downstream
# project would.
import os
import tempfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class TestOHOSShared(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        tested = getattr(self, "tested_reference", None)
        if tested is None:
            # conan test <path> <ref> injects the reference; when it is not
            # available during graph computation (older conan 2.x), the
            # recipe's declared fallback below is used.
            tested = "libsigc-2/2.12.2"
        self.requires(tested)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()  # conanrun env for the consumer launch

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if str(self.settings.os) != "OHOS":
            raise ConanException("test_ohos must run on the OHOS profile")
        tested = getattr(self, "tested_reference", None) or "libsigc-2/2.12.2"
        pkg = self.dependencies[tested.split("#")[0]]
        pkg_root = Path(pkg.package_folder).resolve(strict=True)
        readelf = os.environ.get("OHOS_READELF", "readelf")
        script = str(Path(self.recipe_folder, "test_ohos.sh"))
        consumer = str(Path(self.build_folder, self.cpp.build.bindirs[0], "test_ohos_sigc").resolve(strict=True))
        variant = "shared" if pkg.options.shared else "static"
        # The conanrun environment (VirtualRunEnv) already exports
        # LD_LIBRARY_PATH pointing at the packaged shared library, so the
        # script just runs the consumer inside that environment.
        self.run(
            f'"bash" "{script}" "{pkg_root}" "{consumer}" "{readelf}" "{variant}"',
            env="conanrun",
        )
