import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibnovaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Keep the source directory pristine: every generated file
        # (toolchain, deps, env scripts, build outputs) goes to
        # build/<build_type>/ instead of next to the recipe files.
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The build machine *is* the OHOS target machine (native build),
        # so the compiled test always runs - no can_run() guard needed.
        # (can_run() would return False here because conan detects the
        # build host OS as Linux while the host profile says OHOS.)
        exe = os.path.join(self.build_folder, "test_package")
        self.run(f'"{exe}"', env="conanrun")

        # OHOS-specific package check (independent of the consumer test
        # above, counted separately in MANIFEST.yml): ELF/SONAME/NEEDED/
        # glibc/RPATH/absolute-path/codesign checks on the final package
        # plus a signed real-astronomy run on this device.
        if self.settings.os == "OHOS":
            pkg = self.dependencies["libnova"].package_folder
            ohos_exe = os.path.join(self.build_folder, "ohos_check")
            script = os.path.join(self.source_folder, "test_ohos.sh")
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
                or "/data/service/hnp/bin/bash"
            self.run(
                f'"{bash}" "{script}" "{pkg}" "{ohos_exe}" '
                f'"{self._tool("readelf")}" "{self._tool("llvm-objcopy")}" '
                f'"{self._tool("binary-sign-tool")}"',
                env="conanrun",
            )

    def _tool(self, name):
        # Prefer the build toolchain copy (tools.build:compiler_executables
        # points into the OHOS SDK toolchain dir); fall back to PATH, then
        # the hnp tool dir (same resolution order as the boost/1.91.0
        # consumer recipe; no hardcoded build-machine paths).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(
            compilers.get("c") or compilers.get("cpp") or "")
        for cand in (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            shutil.which(name) or "",
            os.path.join("/data/service/hnp/bin", name),
        ):
            if cand and os.path.isfile(cand):
                return cand
        return name
