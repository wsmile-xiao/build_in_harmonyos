"""Independent consumer for the installed DVB-CSA library."""

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibdvbcsaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if str(self.settings.os) == "OHOS":
            executable = Path(self.build_folder) / self.cpp.build.bindirs[0] / "test_libdvbcsa"
            signer = shutil.which("binary-sign-tool")
            readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
            objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
            if not signer or not readelf or not objcopy:
                raise ConanInvalidConfiguration("ELF signer, readelf, and objcopy are required on OHOS")
            pending = executable.with_name(executable.name + ".signing")
            signed = executable.with_name(executable.name + ".signed")
            if pending.exists() or signed.exists():
                raise ConanInvalidConfiguration("stale signing sibling")
            try:
                shutil.copy2(executable, pending)
                before = subprocess.run([readelf, "-S", str(pending)], check=True,
                                        capture_output=True, text=True, timeout=20)
                if ".codesign" in before.stdout:
                    subprocess.run([objcopy, "--remove-section=.codesign", str(pending)],
                                   check=True, capture_output=True, text=True, timeout=20)
                subprocess.run([signer, "sign", "-inFile", str(pending),
                                "-outFile", str(signed), "-selfSign", "1"],
                               check=True, capture_output=True, text=True, timeout=40)
                sections = subprocess.run([readelf, "-S", str(signed)], check=True,
                                          capture_output=True, text=True, timeout=20)
                if ".codesign" not in sections.stdout:
                    raise ConanException("signed consumer has no .codesign section")
                os.chmod(signed, executable.stat().st_mode | 0o755)
                os.replace(signed, executable)
            finally:
                for temporary in (pending, signed):
                    if temporary.exists():
                        temporary.unlink()

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_libdvbcsa"),
                     env="conanrun")
            self.output.info("CONSUMER_1_OF_1_PASS")
