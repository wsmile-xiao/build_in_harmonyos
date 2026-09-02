#!/usr/bin/env python3
"""Conan recipe for cmock 2.7.0, the CMock C runtime and Unity integration."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class CMockConan(ConanFile):
    name = "cmock"
    version = "2.7.0"
    description = "C mocking framework runtime with automatic mock generation support"
    license = "MIT"
    homepage = "https://www.throwtheswitch.org/cmock"
    url = "https://github.com/ThrowTheSwitch/CMock"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cmock 2.7.0 supports Linux and OHOS only, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        unity_dir = os.path.join(self.source_folder, "vendor", "unity")
        get(
            self,
            **self.conan_data["unity"][self.version],
            destination=unity_dir,
            strip_root=True,
        )

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "static"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_archive_tools()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._normalize_static_archive(
            os.path.join(self.build_folder, "src", "libcmock.a"),
            os.path.join(self.build_folder, "src", "libcmock.a.p", "cmock.c.o"),
        )
        self._normalize_static_archive(
            os.path.join(self.build_folder, "vendor", "unity", "libunity.a"),
            os.path.join(
                self.build_folder,
                "vendor",
                "unity",
                "libunity.a.p",
                "src_unity.c.o",
            ),
        )

    def package(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        include_dir = os.path.join(self.package_folder, "include")
        unity_include_dir = os.path.join(include_dir, "unity")
        license_dir = os.path.join(self.package_folder, "licenses")

        copy(
            self,
            "libcmock.a",
            src=os.path.join(self.build_folder, "src"),
            dst=lib_dir,
            keep_path=False,
        )
        copy(
            self,
            "libunity.a",
            src=os.path.join(self.build_folder, "vendor", "unity"),
            dst=lib_dir,
            keep_path=False,
        )
        copy(
            self,
            "cmock.h",
            src=os.path.join(self.source_folder, "src"),
            dst=include_dir,
            keep_path=False,
        )
        copy(
            self,
            "cmock_internals.h",
            src=os.path.join(self.source_folder, "src"),
            dst=include_dir,
            keep_path=False,
        )
        copy(
            self,
            "unity.h",
            src=os.path.join(self.source_folder, "vendor", "unity", "src"),
            dst=unity_include_dir,
            keep_path=False,
        )
        copy(
            self,
            "unity_internals.h",
            src=os.path.join(self.source_folder, "vendor", "unity", "src"),
            dst=unity_include_dir,
            keep_path=False,
        )
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=license_dir,
            keep_path=False,
        )
        os.makedirs(license_dir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "vendor", "unity", "LICENSE.txt"),
            os.path.join(license_dir, "Unity-LICENSE.txt"),
        )

    def package_info(self):
        self.cpp_info.libs = ["cmock", "unity"]
        self.cpp_info.includedirs = ["include", "include/unity"]
        self.cpp_info.set_property("cmake_file_name", "cmock")
        self.cpp_info.set_property("cmake_target_name", "cmock::cmock")
        self.cpp_info.set_property("pkg_config_name", "cmock")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    def _normalize_static_archive(self, archive, object_file):
        """Convert Meson's LLVM thin archive into a portable static archive."""
        if not os.path.isfile(archive) or not os.path.isfile(object_file):
            return

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler_executables.get("c", "")
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        sdk_bindir = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"
        ar = next(
            (
                candidate
                for candidate in (
                    os.path.join(bindir, "llvm-ar"),
                    os.path.join(sdk_bindir, "llvm-ar"),
                    shutil.which("llvm-ar"),
                )
                if candidate and os.path.isfile(candidate)
            ),
            None,
        )
        if not ar:
            return

        normalized = f"{archive}.normal"
        self.run(f'"{ar}" rcD "{normalized}" "{object_file}"')
        os.replace(normalized, archive)

    def _inject_archive_tools(self):
        """Make Meson use the LLVM archiver available in the OHOS SDK."""
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler_executables.get("c", "")
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        sdk_bindir = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"
        ar = next(
            (
                candidate
                for candidate in (
                    os.path.join(bindir, "llvm-ar"),
                    os.path.join(sdk_bindir, "llvm-ar"),
                    shutil.which("llvm-ar"),
                )
                if candidate and os.path.isfile(candidate)
            ),
            None,
        )
        ranlib = next(
            (
                candidate
                for candidate in (
                    os.path.join(bindir, "llvm-ranlib"),
                    os.path.join(sdk_bindir, "llvm-ranlib"),
                    shutil.which("llvm-ranlib"),
                )
                if candidate and os.path.isfile(candidate)
            ),
            None,
        )
        if not ar:
            return

        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "[binaries]" not in content or "\nar =" in content:
            return

        insert = f"[binaries]\nar = '{ar}'\n"
        if ranlib:
            insert += f"ranlib = '{ranlib}'\n"
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", insert, 1))
