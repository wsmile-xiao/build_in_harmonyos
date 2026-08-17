from conan import ConanFile
import os
import shutil
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class JthreadConan(ConanFile):
    name = "jthread"
    version = "1.3.3"
    description = "Portable C++ thread wrapper library"
    license = "MIT"
    homepage = "https://research.edm.uhasselt.be/jori/page/CS/Jthread.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
    }

    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        source_data = dict(self.conan_data["sources"])
        source_url = source_data.get("url", "")
        if isinstance(source_url, str) and source_url.startswith("file://"):
            source_data["url"] = source_url.replace("%", "%25")
        get(self, **source_data, strip_root=True)

    def _find_compiler(self, name):
        candidates = [
            shutil.which(name),
            f"/data/service/hnp/bin/{name}",
            os.path.expanduser(f"~/usr/local/bin/{name}"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise RuntimeError(f"{name} compiler not found")

    def generate(self):
        cc = self._find_compiler("clang")
        cxx = self._find_compiler("clang++")

        self.output.info(f"Using C compiler: {cc}")
        self.output.info(f"Using CXX compiler: {cxx}")

        tc = CMakeToolchain(self)
        tc.variables["CMAKE_C_COMPILER"] = cc
        tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["JTHREAD_COMPILE_STATIC_ONLY"] = (
            "OFF" if self.options.shared else "ON"
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        cc = self._find_compiler("clang")
        cxx = self._find_compiler("clang++")

        cmake = CMake(self)
        cmake.configure(
            variables={
                "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
                "CMAKE_C_COMPILER": cc,
                "CMAKE_CXX_COMPILER": cxx,
            }
        )
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["jthread"]
        self.cpp_info.set_property("cmake_file_name", "jthread")
        self.cpp_info.set_property("cmake_target_name", "jthread::jthread")

        if str(self.settings.os) == "OHOS":
            self.cpp_info.system_libs = ["pthread"]
