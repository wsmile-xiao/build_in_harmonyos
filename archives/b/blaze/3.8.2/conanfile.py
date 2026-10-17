import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BlazeConan(ConanFile):
    name = "blaze"
    version = "3.8.2"
    description = "High-performance C++ math library for dense and sparse arithmetic"
    license = "BSD-3-Clause"
    homepage = "https://bitbucket.org/blaze-lib/blaze"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _source_root(self):
        archive_root = os.path.join(self.source_folder, f"blaze-{self.version}")
        return archive_root if os.path.isdir(archive_root) else self.source_folder

    def build(self):
        # This is an upstream Blazetest program, not a recipe-owned substitute.
        compiler = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("cpp", "c++")
        source_root = self._source_root()
        test_include_root = os.path.join(source_root, "blazetest")
        test_source = os.path.join(
            source_root,
            "blazetest",
            "src",
            "mathtest",
            "vectors",
            "dynamicvector",
            "ClassTest.cpp",
        )
        executable = os.path.join(self.build_folder, "blaze-dynamicvector-test")
        self.run(
            f"{shlex.quote(compiler)} -std=c++14 -O0 "
            f"-I{shlex.quote(source_root)} "
            f"-I{shlex.quote(test_include_root)} "
            f"{shlex.quote(test_source)} -o {shlex.quote(executable)}",
            env="conanbuild",
        )
        if can_run(self):
            self.run(shlex.quote(executable), env="conanbuild")
            self.output.info("blaze upstream DynamicVector ClassTest passed")
        else:
            self.output.info(
                "Skipping blaze upstream DynamicVector ClassTest: "
                "the target binary cannot run on this build machine"
            )

    def package(self):
        source_root = self._source_root()
        copy(
            self,
            "*",
            src=os.path.join(source_root, "blaze"),
            dst=os.path.join(self.package_folder, "include", "blaze"),
        )
        copy(
            self,
            "LICENSE",
            src=source_root,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Blaze")
        self.cpp_info.set_property("cmake_target_name", "Blaze::Blaze")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
