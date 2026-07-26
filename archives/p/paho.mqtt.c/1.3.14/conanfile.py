from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches, rmdir
import os


class PahoMqttCConan(ConanFile):
    name = "paho.mqtt.c"
    version = "1.3.14"
    description = "Eclipse Paho C client library for MQTT protocol"
    license = "EPL-2.0"
    homepage = "https://github.com/eclipse/paho.mqtt.c"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_ssl": [True, False],
    }
    default_options = {
        "shared": False,
        "with_ssl": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["PAHO_WITH_SSL"] = self.options.with_ssl
        tc.variables["PAHO_BUILD_STATIC"] = True
        tc.variables["PAHO_BUILD_SHARED"] = self.options.shared
        tc.variables["PAHO_BUILD_DOCUMENTATION"] = False
        tc.variables["PAHO_BUILD_SAMPLES"] = False
        tc.variables["PAHO_BUILD_TESTS"] = False
        tc.variables["PAHO_ENABLE_TESTING"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["paho-mqtt3a", "paho-mqtt3c"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
