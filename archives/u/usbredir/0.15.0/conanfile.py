#!/usr/bin/env python3
"""Conan recipe for usbredir 0.15.0, the SPICE/QEMU USB redirection libraries."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class UsbredirConan(ConanFile):
    name = "usbredir"
    version = "0.15.0"
    description = "USB redirection protocol parser and host libraries"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.spice-space.org"
    url = "https://gitlab.freedesktop.org/spice/usbredir"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_upstream_tests": [True, False],
    }
    default_options = {"shared": True, "fPIC": True, "with_upstream_tests": False}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libusb/1.0.27")
        if self.options.with_upstream_tests:
            # The two upstream Meson tests link against glib-2.0 only.
            self.requires("glib/2.84.0")

    def package_id(self):
        self.info.options.rm_safe("with_upstream_tests")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["git_werror"] = "disabled"
        tc.project_options["tools"] = "disabled"
        tc.project_options["tests"] = "enabled" if self.options.with_upstream_tests else "disabled"
        tc.project_options["fuzzing"] = "disabled"
        tc.generate()

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        if not ar:
            cc = compiler_executables.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                ar_candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(ar_candidate):
                    ar = ar_candidate
                ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(ranlib_candidate):
                    ranlib = ranlib_candidate
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                insert = f"[binaries]\nar = '{ar}'\n"
                if ranlib:
                    insert += f"ranlib = '{ranlib}'\n"
                content = content.replace("[binaries]\n", insert, 1)
                with open(native_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._copy_shared_library_aliases(self.build_folder)
        if self.options.with_upstream_tests and can_run(self):
            meson.test()
        elif self.options.with_upstream_tests:
            self.output.info("cross-building: skip upstream Meson runtime execution")

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        if self.options.shared:
            self._copy_shared_library_aliases(self.package_folder)
            self._sign_shared_libraries()

    def _copy_shared_library_aliases(self, directory):
        if str(self.settings.os) != "OHOS":
            return
        aliases = []
        for root in (
            os.path.join(directory, "usbredirparser"),
            os.path.join(directory, "usbredirhost"),
            os.path.join(directory, "lib"),
        ):
            if not os.path.isdir(root):
                continue
            for filename in os.listdir(root):
                if ".so." not in filename:
                    continue
                path = os.path.join(root, filename)
                if not os.path.isfile(path):
                    continue
                stem, version = filename.split(".so.", 1)
                major = version.split(".", 1)[0]
                if not major.isdigit():
                    continue
                for alias in (f"{stem}.so.{major}", f"{stem}.so"):
                    alias_path = os.path.join(root, alias)
                    if not os.path.exists(alias_path):
                        shutil.copyfile(path, alias_path)
                        aliases.append(alias)
        if aliases:
            self.output.info(f"created OHOS shared library aliases: {', '.join(aliases)}")

    def _sign_shared_libraries(self):
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return

        libdir = os.path.join(self.package_folder, "lib")
        for root, _, files in os.walk(libdir):
            for filename in files:
                if ".so" not in filename:
                    continue
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    continue
                subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
                signed = path + ".signed"
                subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
                    check=True,
                )
                os.replace(signed, path)
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["usbredirhost", "usbredirparser"]
        self.cpp_info.set_property("cmake_file_name", "usbredir")
        self.cpp_info.set_property("cmake_target_name", "usbredir::usbredir")
        self.cpp_info.set_property("pkg_config_name", "libusbredirhost")
        self.cpp_info.components["parser"].libs = ["usbredirparser"]
        self.cpp_info.components["parser"].set_property(
            "pkg_config_name", "libusbredirparser"
        )
        self.cpp_info.components["host"].libs = ["usbredirhost"]
        self.cpp_info.components["host"].requires = ["parser"]
        self.cpp_info.components["host"].set_property(
            "pkg_config_name", "libusbredirhost"
        )
