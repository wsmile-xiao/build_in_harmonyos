"""Conan consumer of shfm: drive the packaged script on a pty, then build and run an OHOS
aarch64 program from the directory that shfm printed on exit (the `cd "$(shfm)"` contract)."""
import os
import platform
import shlex
import shutil
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ShfmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "consumer.c", "drive_shfm.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-static"
        tc.generate()

    def _selected_file(self):
        return os.path.join(self.build_folder, "shfm-selected-dir.txt")

    def build(self):
        shfm = os.path.join(self.dependencies["shfm"].package_folder, "bin", "shfm")
        workdir = os.path.join(self.build_folder, "shfm-workdir")
        consumer_dir = os.path.join(workdir, "ohos_consumer")
        shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(os.path.join(workdir, "alpha"))
        os.makedirs(consumer_dir)
        shutil.copy(os.path.join(self.source_folder, "consumer.c"), consumer_dir)
        for path in (os.path.join(consumer_dir, "notes.txt"), os.path.join(workdir, "zeta.txt")):
            with open(path, "w") as handle:
                handle.write("picked with shfm\n")

        # shfm needs a controlling terminal: drive it on a pty, collect its cd-on-exit stdout.
        driver = os.path.join(self.source_folder, "drive_shfm.py")
        self.run("{} {} {} {} {}".format(
            shlex.quote(sys.executable), shlex.quote(driver), shlex.quote(shfm),
            shlex.quote(workdir), shlex.quote(self._selected_file())))

        with open(self._selected_file()) as handle:
            selected = handle.read().strip()
        cmake = CMake(self)
        cmake.configure(variables={"SHFM_SELECTED_DIR": selected})
        cmake.build()

    def test(self):
        with open(self._selected_file()) as handle:
            selected = handle.read().strip()
        consumer = os.path.join(self.build_folder, self.cpp.build.bindirs[0], "shfm_ohos_consumer")
        # Native aarch64 runners execute the static binary directly; an x86 build host
        # needs qemu-aarch64.  The program runs inside the directory shfm printed.
        native = platform.machine().lower() in ("aarch64", "arm64")
        launcher = "" if native else "qemu-aarch64 "
        self.run("{}{} {}".format(launcher, shlex.quote(consumer), shlex.quote(selected)),
                 cwd=selected)
