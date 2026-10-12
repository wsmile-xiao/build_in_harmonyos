import hashlib
import os
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get, replace_in_file, unzip


class MptpConan(ConanFile):
    name = "mptp"
    version = "0.2.5"
    license = "AGPL-3.0-or-later"
    description = "Multi-rate Poisson tree processes for species delimitation"
    homepage = "https://github.com/Pas-Kapli/mptp"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Supported targets: Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        archive = os.environ.get("MPTP_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != self.conan_data["sources"]["sha256"]:
                raise ConanException("MPTP_SOURCE_ARCHIVE SHA-256 mismatch")
            unzip(self, archive, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        if os.path.realpath(self.export_sources_folder) != os.path.realpath(self.source_folder):
            copy(self, "CMakeLists.txt", self.export_sources_folder, self.source_folder)
        # Upstream labels every non-PPC CPU x86_64. Preserve algorithms and
        # report the actual native ARM platform rather than an x86 binary.
        header = os.path.join(self.source_folder, "src", "mptp.h")
        replace_in_file(self, header, "#ifdef __PPC__", '#if defined(__aarch64__)\n#define PROG_CPU "aarch64"\n#elif defined(__PPC__)')
        replace_in_file(self, header, "#ifdef __linux__", '#if defined(__OHOS__)\n#define PROG_OS "ohos"\n#include <sys/resource.h>\n#include <sys/sysinfo.h>\n#elif defined(__linux__)')

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
