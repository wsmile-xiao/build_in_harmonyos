import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout


class Openrct2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # application package: no consumer linkage; binary execution test only.
        pass

    def test(self):
        # headless server form verification: openrct2-cli --version prints version.
        #
        # env combines conanbuild (toolchain llvm lib dir, where libc++_shared.so
        # lives — conanrun alone yields "Error relocating ... 127", #9606 family)
        # + conanrun (dependency lib dirs incl. transitive deps like expat for
        # fontconfig/2.18.1.1 — note: fontconfig/2.18.1 has an ABSOLUTE-path
        # DT_NEEDED to the expat build machine and is broken on other hosts;
        # this recipe pins 2.18.1.1 which links by soname, CI #44768).
        bin_dir = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "bin")
        cli = os.path.join(bin_dir, "openrct2-cli")
        self.run(f'"{cli}" --version', env=["conanbuild", "conanrun"])
