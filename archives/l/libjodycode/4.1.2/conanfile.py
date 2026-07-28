#!/usr/bin/env python3
"""Conan recipe for libjodycode 4.1.2."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibjodycodeConan(ConanFile):
    name = "libjodycode"
    version = "4.1.2"
    description = "General-purpose C utility library used by Jody Bruchon's tools"
    license = "MIT"
    homepage = "https://codeberg.org/jbruchon/libjodycode"
    url = "https://codeberg.org/jbruchon/libjodycode"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_urls = sources.pop("mirror_urls", [])
        mirror_sha256 = sources.pop("mirror_sha256", None)
        try:
            get(self, **sources, strip_root=True)
        except Exception as error:
            if not mirror_urls or not mirror_sha256:
                raise
            self.output.warning(f"Primary source failed ({error}); trying verified mirrors")
            for mirror_url in mirror_urls:
                try:
                    get(self, url=mirror_url, sha256=mirror_sha256, strip_root=True)
                    return
                except Exception as mirror_error:
                    self.output.warning(f"Mirror source failed ({mirror_error}): {mirror_url}")
            raise

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")
        shell = self._make_shell()

        make_vars = self._make_vars(cc, ar, ranlib)
        if shell:
            make_vars += f' SHELL="{shell}"'
        self.run(f'make -C "{self.source_folder}" {make_vars} -j1')
        if self.settings.os == "OHOS" and shell:
            self.run(f'"{shell}" "{os.path.join(self.source_folder, "test.sh")}"')
        else:
            self.run(f'make -C "{self.source_folder}" {make_vars} test')

    def package(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        shell = self._make_shell()
        make_vars = self._make_vars(cc)
        make_vars += f' DESTDIR="{self.package_folder}"'
        if shell:
            make_vars += f' SHELL="{shell}"'
        self.run(
            'make -C "{}" {} install'.format(self.source_folder, make_vars)
        )

        lib_dir = os.path.join(self.package_folder, "lib")
        for filename in os.listdir(lib_dir):
            if filename.endswith((".la", ".dylib")):
                os.remove(os.path.join(lib_dir, filename))
            elif self.options.shared and filename == "libjodycode.a":
                os.remove(os.path.join(lib_dir, filename))
            elif not self.options.shared and filename.startswith("libjodycode.so"):
                os.remove(os.path.join(lib_dir, filename))

        if self.options.shared:
            full_so = os.path.join(lib_dir, f"libjodycode.so.{self.version}")
            if os.path.exists(full_so):
                for filename in (f"libjodycode.so.{self.version.split('.')[0]}", "libjodycode.so"):
                    alias = os.path.join(lib_dir, filename)
                    if not os.path.exists(alias):
                        shutil.copy2(full_so, alias)

    def package_info(self):
        self.cpp_info.libs = ["jodycode"]
        self.cpp_info.set_property("cmake_file_name", "libjodycode")
        self.cpp_info.set_property("cmake_target_name", "libjodycode::libjodycode")

    def _make_shell(self):
        shell = os.environ.get("CONFIG_SHELL")
        if shell and (not os.path.isabs(shell) or os.path.exists(shell)):
            return shell
        if self.settings.os == "OHOS":
            return shutil.which("bash") or "bash"
        return shell

    def _make_vars(self, cc, ar=None, ranlib=None):
        make_vars = f'CC="{cc}" PREFIX=/ VERSION="{self.version}" VERSION_MAJOR="{self.version.split(".")[0]}"'
        if ar:
            make_vars += f' AR="{ar}"'
        if ranlib:
            make_vars += f' RANLIB="{ranlib}"'
        if self.settings.os == "OHOS":
            make_vars += ' LN="cp -f"'
        return make_vars
