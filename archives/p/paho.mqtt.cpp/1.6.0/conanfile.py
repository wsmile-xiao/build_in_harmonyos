#!/usr/bin/env python3
"""Conan recipe for paho.mqtt.cpp 1.6.0 using CMake."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save


class PahoMqttCppConan(ConanFile):
    name = "paho.mqtt.cpp"
    version = "1.6.0"
    description = "Eclipse Paho C++ client library for MQTT protocol"
    license = "EPL-2.0 AND EDL-1.0"
    homepage = "https://github.com/eclipse/paho.mqtt.cpp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "paho.mqtt.c/1.3.14",
            transitive_headers=True,
            transitive_libs=True,
        )

    def build_requirements(self):
        self.test_requires("catch2/2.13.10-r0")

    def configure(self):
        self.options["paho.mqtt.c"].shared = self.options.shared

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # The repository's header-only Catch2 package does not ship the
        # upstream CTest integration module used by include(Catch).  Keep the
        # Catch2 test binary as one CTest case; OHOS excludes only the
        # explicitly tagged broker-dependent cases because no MQTT broker is
        # available in the device validation environment.
        catch_module_dir = os.path.join(self.build_folder, "cmake-modules")
        os.makedirs(catch_module_dir, exist_ok=True)
        broker_filter = ' "~[broker]"' if str(self.settings.os) == "OHOS" else ""
        with open(os.path.join(catch_module_dir, "Catch.cmake"), "w", encoding="utf-8") as module:
            module.write(
                "# Minimal Catch.cmake for upstream CTest integration\n"
                "function(catch_discover_tests TARGET)\n"
                f"    add_test(NAME ${{TARGET}} COMMAND ${{TARGET}}{broker_filter})\n"
                "endfunction()\n"
            )
        tc.variables["CMAKE_MODULE_PATH"] = catch_module_dir
        tc.variables["PAHO_BUILD_STATIC"] = True
        tc.variables["PAHO_BUILD_SHARED"] = self.options.shared
        # The repository paho.mqtt.c/1.3.14 package exports the non-SSL
        # targets only; keep this recipe's supported variant explicit.
        tc.variables["PAHO_WITH_SSL"] = False
        tc.variables["PAHO_BUILD_SAMPLES"] = False
        tc.variables["PAHO_BUILD_EXAMPLES"] = False
        tc.variables["PAHO_BUILD_TESTS"] = True
        tc.variables["PAHO_BUILD_DOCUMENTATION"] = False
        tc.variables["PAHO_WITH_MQTT_C"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # HMDFS does not permit GNU make's jobserver FIFO.  Keep the OHOS
        # build serial so CMake does not append the default -j20 invocation.
        if str(self.settings.os) == "OHOS":
            self.conf.define("tools.build:jobs", 1)
        cmake.build()
        if can_run(self):
            self.run("ctest --output-on-failure", cwd=self.build_folder)
        else:
            self.output.warning("Skipping upstream Catch2 tests because the target cannot run on this host.")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        save(
            self,
            os.path.join(
                self.package_folder,
                "lib",
                "cmake",
                "PahoMqttCpp",
                "paho-mqtt-c-include-fix.cmake",
            ),
            r"""# The repository paho.mqtt.c package currently omits its include
# directory from CMakeDeps metadata although the headers are packaged under
# include/. Recover that path from the CMakeDeps package-folder variable.
if(TARGET paho.mqtt.c::paho.mqtt.c)
    # CMakeDeps exposes the package folder in the dependency data file,
    # even when the dependency recipe omitted cpp_info.includedirs.  The
    # generated target can still have an empty generator expression in its
    # include property, so use the packaged header as the source of truth.
    set(_paho_mqtt_c_prefix "")
    if(DEFINED paho.mqtt.c_PACKAGE_FOLDER_RELEASE)
        set(_paho_mqtt_c_prefix "${paho.mqtt.c_PACKAGE_FOLDER_RELEASE}")
    elseif(DEFINED paho.mqtt.c_PACKAGE_FOLDER_DEBUG)
        set(_paho_mqtt_c_prefix "${paho.mqtt.c_PACKAGE_FOLDER_DEBUG}")
    endif()
    if(EXISTS "${_paho_mqtt_c_prefix}/include/MQTTAsync.h")
        set_property(TARGET paho.mqtt.c::paho.mqtt.c APPEND PROPERTY
            INTERFACE_INCLUDE_DIRECTORIES "${_paho_mqtt_c_prefix}/include")
    endif()
endif()
""",
        )
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "edl-v10", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        library = "paho-mqttpp3" if self.options.shared else "paho-mqttpp3-static"
        self.cpp_info.libs = [library]
        # Keep the dependency visible from the package-level CMake target as
        # well as from the component target below.  Conan's test-package
        # consumer resolves the component target, but its transitive graph is
        # rooted at the package-level requirement; without both declarations
        # the generated paho.mqtt.c target can lose its libraries in consumers.
        self.cpp_info.requires = ["paho.mqtt.c::paho.mqtt.c"]
        self.cpp_info.set_property("cmake_file_name", "PahoMqttCpp")
        self.cpp_info.set_property(
            "cmake_build_modules",
            [os.path.join("lib", "cmake", "PahoMqttCpp", "paho-mqtt-c-include-fix.cmake")],
        )
        component = self.cpp_info.components["paho-mqttpp3"]
        component.set_property("cmake_file_name", "PahoMqttCpp")
        component.set_property("cmake_target_name", "PahoMqttCpp::paho-mqttpp3")
        component.libs = [library]
        component.includedirs = ["include"]
        component.requires = ["paho.mqtt.c::paho.mqtt.c"]
        if self.settings.os in ("Linux", "OHOS"):
            component.system_libs = ["pthread"]
