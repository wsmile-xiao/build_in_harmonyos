#!/usr/bin/env python3
"""Conan recipe for zix 0.8.1.

Zix is a lightweight C library providing portability helpers, data structures,
threading primitives, and filesystem utilities used by the LV2 audio ecosystem.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class ZixConan(ConanFile):
    name = "zix"
    version = "0.8.1"
    description = "Lightweight C library of portability wrappers and data structures"
    license = "ISC"
    homepage = "https://drobilla.net/software/zix"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"zix is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["benchmarks"] = "disabled"
        tc.project_options["checks"] = "enabled"
        tc.project_options["docs"] = "disabled"
        tc.project_options["html"] = "disabled"
        tc.project_options["lint"] = "false"
        tc.project_options["singlehtml"] = "disabled"
        tc.project_options["tests"] = "enabled"
        tc.project_options["tests_cpp"] = "auto"
        tc.project_options["threads"] = "enabled"
        tc.generate()
        self._inject_meson_archiver()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._ensure_shared_library_aliases(self.build_folder)

        if cross_building(self):
            self.output.info(
                "cross-building: skip upstream meson tests because target binaries "
                "are not runnable on the build host"
            )
            return

        self.output.info("Running zix upstream test suite with meson test")
        test_env = Environment()
        test_env.prepend_path("LD_LIBRARY_PATH", self.build_folder)
        with test_env.vars(self).apply():
            self.run(
                'meson test -C "{}" --print-errorlogs'.format(self.build_folder),
                env="conanbuild",
            )

    def package(self):
        Meson(self).install()
        self._ensure_shared_library_aliases(os.path.join(self.package_folder, "lib"))
        self._fix_pkg_config_prefix()

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses", "LICENSES"),
            keep_path=True,
        )

    def package_info(self):
        self.cpp_info.libs = ["zix-0"]
        self.cpp_info.includedirs = ["include/zix-0"]
        self.cpp_info.set_property("cmake_file_name", "zix")
        self.cpp_info.set_property("cmake_target_name", "zix::zix")
        self.cpp_info.set_property("pkg_config_name", "zix-0")
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]

    def _ensure_shared_library_aliases(self, folder):
        if not self.options.shared:
            return

        versioned = os.path.join(folder, "libzix-0.so.0.8.1")
        if not os.path.isfile(versioned):
            return

        # OHOS build/install trees can miss Meson's SONAME aliases.
        for alias, target in (
            ("libzix-0.so.0", "libzix-0.so.0.8.1"),
            ("libzix-0.so", "libzix-0.so.0"),
        ):
            alias_path = os.path.join(folder, alias)
            if os.path.lexists(alias_path):
                continue
            try:
                os.symlink(target, alias_path)
            except (OSError, NotImplementedError):
                shutil.copy2(versioned, alias_path)

    def _fix_pkg_config_prefix(self):
        pc_path = os.path.join(self.package_folder, "lib", "pkgconfig", "zix-0.pc")
        if not os.path.isfile(pc_path):
            return

        with open(pc_path, "r", encoding="utf-8") as handle:
            content = handle.read()

        package_prefix = self.package_folder.replace("\\", "/")
        patched = content.replace("prefix=/\n", f"prefix={package_prefix}\n")
        patched = patched.replace("prefix=/\r\n", f"prefix={package_prefix}\n")
        if patched != content:
            with open(pc_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(patched)
            self.output.info("Patched zix-0.pc prefix to the Conan package folder")

    def _inject_meson_archiver(self):
        compiler_exes = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_exes.get("ar")
        ranlib = compiler_exes.get("ranlib")

        if not ar:
            cc = compiler_exes.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            ar, ranlib = self._find_archiver_from_compiler_dir(bindir)

        if not ar and str(self.settings.os) == "OHOS":
            ar, ranlib = self._find_ohos_archiver()

        if not ar:
            return

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if os.path.isfile(path):
                self._patch_meson_machine_file(path, ar, ranlib)

    @staticmethod
    def _find_archiver_from_compiler_dir(bindir):
        if not bindir:
            return None, None

        ar = os.path.join(bindir, "llvm-ar")
        if not os.path.isfile(ar):
            return None, None

        ranlib = os.path.join(bindir, "llvm-ranlib")
        return ar, ranlib if os.path.isfile(ranlib) else None

    @staticmethod
    def _find_ohos_archiver():
        ar = "/data/service/hnp/bin/llvm-ar"
        ranlib = "/data/service/hnp/bin/llvm-ranlib"
        if os.path.isfile(ar):
            return ar, ranlib if os.path.isfile(ranlib) else None
        return None, None

    @staticmethod
    def _patch_meson_machine_file(path, ar, ranlib):
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()

        if "[binaries]" not in content or "\nar =" in content:
            return

        insertion = "[binaries]\nar = '{}'\n".format(ar.replace("\\", "/"))
        if ranlib:
            insertion += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))

        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", insertion, 1))
