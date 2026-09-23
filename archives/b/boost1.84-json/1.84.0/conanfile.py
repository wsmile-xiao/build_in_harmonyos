import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class BoostJsonConan(ConanFile):
    name = "boost1.84-json"
    version = "1.84.0"
    description = "Boost.JSON 1.84.0 built without Boost.Build"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/libs/json/"
    url = "https://www.boost.org/"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "boost1.84-json currently supports OHOS armv8 only"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _build_flags(self):
        flags = [
            "-std=c++17",
            "-O0" if self.settings.build_type == "Debug" else "-O2",
            "-fPIC" if self.options.fPIC else "",
            f'-I"{self.source_folder}"',
            "-DBOOST_JSON_SOURCE",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_JSON_NO_LIB=1",
        ]
        return " ".join(flag for flag in flags if flag)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        # Apply conandata patches before compiling upstream tests. The
        # cmake_install_test patch is required so the upstream 50/50 cpp
        # inventory is fully compilable.
        apply_conandata_patches(self)

        # ── 1. Build the static library ──
        flags = self._build_flags()
        obj_dir = os.path.join(self.build_folder, "objects")
        os.makedirs(obj_dir, exist_ok=True)
        src_obj = os.path.join(obj_dir, "src.o")
        source = os.path.join(self.source_folder, "libs", "json", "src", "src.cpp")
        self.run(f'{cxx} {flags} -c "{source}" -o "{src_obj}"')
        library = os.path.join(self.build_folder, "libboost_json.a")
        self.run(f'{ar} rcs "{library}" "{src_obj}"')

        # ── 2. Validate every upstream test cpp compiles ──
        # Upstream Boost.JSON 1.84.0 ships 50 .cpp files under
        # libs/json/test/. The OHOS validation must compile all of them
        # (including the 4 that the upstream CMakeLists.txt treats as
        # standalone targets: limits, no_exceptions, intrusive_macros,
        # cmake_install_test). Test sources are compiled in-place as
        # .o files under build/objects/test/; no linking is performed
        # here, that remains the test_package's responsibility.
        test_dir = os.path.join(self.source_folder, "libs", "json", "test")
        test_obj_dir = os.path.join(self.build_folder, "objects", "test")
        os.makedirs(test_obj_dir, exist_ok=True)
        # ryu/ tests use a sibling gtest.hpp that includes test_suite.hpp
        # from the test root, so add -I for the test directory itself.
        test_flags = f"{flags} -I\"{test_dir}\""
        cpp_files = sorted(
            os.path.join(root, name)
            for root, _dirs, files in os.walk(test_dir)
            for name in files
            if name.endswith(".cpp")
        )
        if len(cpp_files) != 50:
            raise ConanInvalidConfiguration(
                f"Expected 50 upstream json test cpp files, found {len(cpp_files)}"
            )
        for cpp in cpp_files:
            rel = os.path.relpath(cpp, test_dir)
            obj = os.path.join(test_obj_dir, rel.replace(os.sep, "__") + ".o")
            self.run(f'{cxx} {test_flags} -c "{cpp}" -o "{obj}"')

    def package(self):
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "boost"),
            dst=os.path.join(self.package_folder, "include", "boost"),
        )
        copy(self, "libboost_json.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE_1_0.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["boost_json"]
        self.cpp_info.system_libs = ["pthread", "dl", "m"]
        self.cpp_info.set_property("cmake_file_name", "boost1.84-json")
        self.cpp_info.set_property(
            "cmake_target_name", "boost1.84-json::boost1.84-json"
        )
