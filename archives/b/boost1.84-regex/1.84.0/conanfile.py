import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BoostRegexConan(ConanFile):
    name = "boost1.84-regex"
    version = "1.84.0"
    description = "Boost.Regex 1.84.0 built without Boost.Build"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/libs/regex/"
    url = "https://www.boost.org/"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "boost1.84-regex currently supports OHOS armv8 only"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")
        source_files = [
            "static_mutex.cpp",
            "posix_api.cpp",
            "regex_debug.cpp",
            "regex.cpp",
            "wide_posix_api.cpp",
        ]
        source_dir = os.path.join(self.source_folder, "libs", "regex", "src")
        object_dir = os.path.join(self.build_folder, "objects")
        os.makedirs(object_dir, exist_ok=True)
        flags = [
            "-std=c++17",
            "-O0" if self.settings.build_type == "Debug" else "-O2",
            "-fPIC" if self.options.fPIC else "",
            f'-I"{self.source_folder}"',
            f'-I"{os.path.join(self.source_folder, "libs", "regex", "include")}"',
            "-DBOOST_REGEX_SOURCE",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ]
        flags = " ".join(flag for flag in flags if flag)
        objects = []
        for source_file in source_files:
            source = os.path.join(source_dir, source_file)
            obj = os.path.join(object_dir, source_file.replace(".cpp", ".o"))
            self.run(f'{cxx} {flags} -c "{source}" -o "{obj}"')
            objects.append(f'"{obj}"')
        library = os.path.join(self.build_folder, "libboost_regex.a")
        self.run(f'{ar} rcs "{library}" {" ".join(objects)}')

    def package(self):
        # Root boost/ headers (public API)
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "boost"),
            dst=os.path.join(self.package_folder, "include", "boost"),
        )
        # libs/regex/include/ headers (internal config.hpp etc.)
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "libs", "regex", "include", "boost"),
            dst=os.path.join(self.package_folder, "include", "boost"),
        )
        copy(self, "libboost_regex.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE_1_0.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["boost_regex"]
        self.cpp_info.system_libs = ["pthread", "dl", "m"]
        self.cpp_info.set_property("cmake_file_name", "boost1.84-regex")
        self.cpp_info.set_property(
            "cmake_target_name", "boost1.84-regex::boost1.84-regex"
        )
