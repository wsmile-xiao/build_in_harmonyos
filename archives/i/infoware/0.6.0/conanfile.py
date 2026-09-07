import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, download, export_conandata_patches, get


class InfowareConan(ConanFile):
    name = "infoware"
    version = "0.6.0"
    description = "C++ system information library (CPU, memory, OS, kernel, PCI devices)"
    license = "CC0-1.0"
    homepage = "https://github.com/ThePhD/infoware"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS must be accepted alongside Linux
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"infoware supports Windows, macOS and Linux-like hosts "
                f"(incl. OHOS), got {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True,
            filename="infoware-0.6.0.tar.gz")
        # pci.ids snapshot for the build-time pci_generator; upstream defaults
        # to git-cloning it, which build workers cannot do (see conandata.yml).
        # download() (not get()) because get() always tries to decompress and
        # the zip decoder would choke on this plain data file.
        pci_ids = self.conan_data["sources"][1]
        download(self, pci_ids["url"], sha256=pci_ids["sha256"],
                 filename="pci.ids")

    def generate(self):
        toolchain = CMakeToolchain(self)
        # CMake has no OHOS platform module (same approach as merged
        # abcmidi/cbmconvert recipes): present a generic Linux/aarch64 host.
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # Upstream requires the pci.ids database at configure time and would
        # otherwise try to git clone it.
        toolchain.cache_variables["INFOWARE_PCI_IDS_PATH"] = os.path.join(
            self.source_folder, "pci.ids")
        # Build the upstream examples and register them with CTest so the
        # official suite runs inside the recipe build (cmake.test() below).
        toolchain.cache_variables["INFOWARE_EXAMPLES"] = True
        toolchain.cache_variables["INFOWARE_TESTS"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Pure static library package (R38: no commands.json for libraries)
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = []
        self.cpp_info.libs = ["infoware"]
