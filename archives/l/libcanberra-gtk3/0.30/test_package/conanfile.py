#!/usr/bin/env python3
"""Installed-package API tests for libcanberra-gtk3 0.30.

libcanberra-gtk3 ships no automated test suite upstream.  The consumer
here links the published libcanberra-gtk3/0.30 and verifies:

  * every public symbol in canberra-gtk.h is relocated against
    libcanberra-gtk3.so at load time (strong-typed function pointers);
  * when GTK3 can initialise on the target (gtk_init_check succeeds),
    the GTK context factory and the widget proplist helper run against
    the broadway backend; on headless targets where no display can be
    opened the GTK runtime part is skipped and the symbol relocation
    check remains the gate.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class LibcanberraGtk3TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps", "VirtualRunEnv"
    exports_sources = "CMakeLists.txt", "*.c"

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
            raise ConanException("libcanberra-gtk3 target consumers are not runnable")
        executable = os.path.join(self.cpp.build.bindirs[0], "libcanberra_gtk3_api_surface")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(executable)
        self._set_ld_library_path()
        self.run(f'"{executable}"', env="conanrun")

    def _set_ld_library_path(self):
        lib_dirs = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep.package_folder
        ]
        if str(self.settings.os) == "OHOS":
            lib_dirs.append("/system/lib64")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs)
        os.environ.setdefault("HOME", os.path.expanduser("~"))

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                temporary,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed consumer has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
