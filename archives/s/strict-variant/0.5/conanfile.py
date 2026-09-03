#!/usr/bin/env python3
"""Conan recipe for strict-variant 0.5 (header-only C++11 variant)."""
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class StrictVariantConan(ConanFile):
    name = "strict-variant"
    version = "0.5"
    package_type = "header-library"

    description = (
        "Header-only C++11 variant with strict, non-surprising conversions "
        "and a never-empty value."
    )
    homepage = "https://github.com/cbeck88/strict-variant"
    license = "BSL-1.0"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("variant", "sum-type", "header-only", "cpp11", "embedded")

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # Header-only package: settings do not change the packaged headers.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # The official test/run_tests.sh requires b2 or bjam. Neither is
        # available on the OHOS device, so execute the same six default test
        # targets directly with the flags from test/Jamroot.jam. The optional
        # Boost Spirit target is handled separately and remains conditional.
        self._run_upstream_tests()

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return (
            executables.get("cpp")
            or shutil.which("clang++")
            or shutil.which("c++")
            or "c++"
        )

    def _run(self, command, cwd):
        rendered = " ".join(shlex.quote(str(part)) for part in command)
        self.output.info(f"$ {rendered}")
        result = subprocess.run(
            command,
            cwd=cwd,
            env=dict(os.environ),
            capture_output=True,
            text=True,
        )
        output = (result.stdout or "") + (result.stderr or "")
        if output.strip():
            self.output.info(output.rstrip())
        if result.returncode != 0:
            raise ConanException(
                f"Command failed (exit {result.returncode}): {rendered}\n{output}"
            )

    def _compile_and_run(self, compiler, source, output, flags, include_dirs, cwd):
        command = [compiler, *flags]
        command.extend(f"-I{include_dir}" for include_dir in include_dirs)
        command.extend([source, "-o", output])
        self._run(command, cwd=cwd)
        if can_run(self):
            self._run([output], cwd=cwd)
        else:
            self.output.warning(
                f"Compiled upstream target {os.path.basename(output)} but did not "
                "execute it because can_run(self) is false."
            )

    def _run_upstream_tests(self):
        source_root = self.source_folder
        test_root = os.path.join(source_root, "test")
        include_root = os.path.join(source_root, "include")
        build_root = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(build_root, exist_ok=True)

        compiler = self._compiler()
        flags = [
            "-std=c++11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-DSTRICT_VARIANT_DEBUG",
        ]
        if str(self.settings.compiler) == "clang":
            # clang 15 diagnoses two issues in the unchanged upstream tests:
            # recursive_wrapper's deprecated implicit copy assignment and the
            # tutorial's intentionally incomplete formatter branch. Demote
            # only these diagnostics while retaining -Werror for all others.
            flags.extend(
                [
                    "-Wno-error=deprecated-copy-with-user-provided-copy",
                    "-Wno-error=return-type",
                ]
            )

        core_includes = [include_root, os.path.join(test_root, "include")]
        for name in ("variant", "compare", "hash", "alloc"):
            self._compile_and_run(
                compiler,
                os.path.join(test_root, f"{name}.cpp"),
                os.path.join(build_root, name),
                flags,
                core_includes,
                build_root,
            )

        example_flags = [*flags, "-fno-exceptions", "-fno-rtti"]
        for name in ("tutorial_basic", "tutorial_advanced"):
            self._compile_and_run(
                compiler,
                os.path.join(test_root, f"{name}.cpp"),
                os.path.join(build_root, name),
                example_flags,
                [include_root],
                build_root,
            )

        boost_root = os.environ.get("BOOST_ROOT") or "/usr/include"
        boost_header = os.path.join(boost_root, "boost", "version.hpp")
        if os.path.isfile(boost_header):
            self._compile_and_run(
                compiler,
                os.path.join(test_root, "spirit.cpp"),
                os.path.join(build_root, "spirit"),
                flags,
                [include_root, os.path.join(test_root, "include"), boost_root],
                build_root,
            )
        else:
            self.output.warning(
                "Skipping optional upstream spirit test: Boost headers are not "
                f"available at {boost_header}; this matches test/Jamroot.jam."
            )

    def package(self):
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "include", "strict_variant"),
            dst=os.path.join(self.package_folder, "include", "strict_variant"),
            keep_path=True,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "strict_variant")
        self.cpp_info.set_property("cmake_target_name", "strict_variant::strict_variant")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
