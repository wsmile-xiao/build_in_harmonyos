from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
from conan.errors import ConanInvalidConfiguration
import os


class AdmsConan(ConanFile):
    name = "adms"
    version = "2.3.7"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/Qucs/ADMS"
    url = "https://github.com/Qucs/ADMS"
    description = "Automatic device model synthesizer for Verilog-AMS"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports = "conandata.yml"

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("adms is adapted for OHOS only")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("adms supports OHOS armv8/aarch64 only")

    def layout(self):
        cmake_layout(self)

    def source(self):
        data = self.conan_data["sources"][self.version]
        get(self, **data, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # ADMS declares cmake_minimum_required(VERSION 2.8), whereas CMake
        # 4.x requires a policy compatibility version of at least 3.5.  This
        # must be a cache variable so CMake reads it before the project file.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={"BUILD_TESTING": "OFF"})
        cmake.build()

        # Exercise the upstream test inputs that do not require external
        # ngspice/Qucs/Xyce checkouts.
        test_dir = os.path.join(self.source_folder, "testcases")
        exe = os.path.join(self.build_folder, "admsXml", "admsXml")
        for stem in ("0000_scale_factor", "0001_operator", "0002_transition"):
            self.run(
                '"{}" -e "{}" "{}"'.format(
                    exe,
                    os.path.join(test_dir, stem + ".xml"),
                    os.path.join(test_dir, stem + ".va"),
                ),
                cwd=test_dir,
            )

    def package(self):
        copy(self, "admsXml", src=os.path.join(self.build_folder, "admsXml"), dst=os.path.join(self.package_folder, "bin"))
        data_dir = os.path.join(self.package_folder, "share", "adms")
        copy(self, "*.xml", src=os.path.join(self.source_folder, "admsXml"), dst=data_dir)
        copy(self, "*.vams", src=os.path.join(self.source_folder, "admsXml"), dst=data_dir)
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.define_path("ADMS_DATA_DIR", os.path.join(self.package_folder, "share", "adms"))
