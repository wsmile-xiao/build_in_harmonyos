import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    copy,
    get,
)
from conan.tools.layout import basic_layout


class BoostFilesystemConan(ConanFile):
    name = "boost1.84-filesystem"
    version = "1.84.0"
    description = "Boost.Filesystem 1.84.0 built without Boost.Build"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/libs/filesystem/"
    url = "https://www.boost.org/"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "boost1.84-filesystem currently supports OHOS armv8 only"
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
            "codecvt_error_category.cpp",
            "directory.cpp",
            "exception.cpp",
            "operations.cpp",
            "path.cpp",
            "path_traits.cpp",
            "portability.cpp",
            "unique_path.cpp",
            "utf8_codecvt_facet.cpp",
        ]
        source_dir = os.path.join(self.source_folder, "libs", "filesystem", "src")
        object_dir = os.path.join(self.build_folder, "objects")
        os.makedirs(object_dir, exist_ok=True)
        flags = [
            "-std=c++17",
            "-O0" if self.settings.build_type == "Debug" else "-O2",
            "-fPIC" if self.options.fPIC else "",
            f'-I"{self.source_folder}"',
        ]
        # Auto-discover all Boost sub-module include directories.
        # Boost 1.84.0 splits headers across many libs/*/include paths.
        import glob as _glob
        for inc_dir in sorted(_glob.glob(os.path.join(self.source_folder, "libs", "*", "include"))):
            flags.append(f'-I"{inc_dir}"')
        flags += [
            "-DBOOST_FILESYSTEM_SOURCE",
            "-DBOOST_SYSTEM_NO_DEPRECATED",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
            # OHOS libc++ (Clang 15) does not provide std::atomic_ref (C++20);
            # force the boost::atomic::atomic_ref fallback path.
            "-DBOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF",
        ]
        flags = " ".join(flag for flag in flags if flag)
        objects = []
        for source_file in source_files:
            source = os.path.join(source_dir, source_file)
            obj = os.path.join(object_dir, source_file.replace(".cpp", ".o"))
            self.run(f'{cxx} {flags} -c "{source}" -o "{obj}"')
            objects.append(f'"{obj}"')
        library = os.path.join(self.build_folder, "libboost_filesystem.a")
        self.run(f'{ar} rcs "{library}" {" ".join(objects)}')

    def package(self):
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "boost"),
            dst=os.path.join(self.package_folder, "include", "boost"),
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "libs", "filesystem", "include", "boost"),
            dst=os.path.join(self.package_folder, "include", "boost"),
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "libs", "config", "include", "boost"),
            dst=os.path.join(self.package_folder, "include", "boost"),
        )
        # Auto-copy all Boost sub-module headers for downstream consumers.
        import glob as _glob
        for inc_dir in _glob.glob(os.path.join(self.source_folder, "libs", "*", "include", "boost")):
            copy(self, "*", src=inc_dir, dst=os.path.join(self.package_folder, "include", "boost"))
        copy(self, "libboost_filesystem.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE_1_0.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["boost_filesystem"]
        self.cpp_info.system_libs = ["pthread", "dl", "m"]
        self.cpp_info.set_property("cmake_file_name", "boost1.84-filesystem")
        self.cpp_info.set_property(
            "cmake_target_name", "boost1.84-filesystem::boost1.84-filesystem"
        )
