#!/usr/bin/env python3
"""Conan recipe — ophcrack 3.8.0 (autotools, binary tool).

ophcrack is a Windows password cracker based on rainbow tables. On HarmonyOS
PC it is adapted as:

  * GUI frontend (Qt5Charts) is compiled out via `./configure --disable-gui`;
    the CLI core (crack/find/lookup) is fully functional.
  * Dependencies: openssl (crypto) and expat (XML table reports) from cnb.
  * OHOS uname reports HarmonyOS, so config.guess cannot guess the build
    type: --build/--host are passed explicitly.
  * OHOS musl libc lacks pthread_cancel/pthread_setcancelstate/type; the
    scheduler uses them only for stop, patched to no-ops (patch 0001).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OphcrackConan(ConanFile):
    name = "ophcrack"
    version = "3.8.0"
    description = "ophcrack - Windows password cracker based on rainbow tables"
    license = "GPL-2.0-with-OpenSSL-exception"
    homepage = "https://ophcrack.sourceforge.io/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("expat/2.8.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cxx", "clang++")
        openssl_dir = self.dependencies["openssl"].package_folder
        expat_dir = self.dependencies["expat"].package_folder
        # E001: PATH has no `cc`, only clang — export CC/CXX for configure.
        # OHOS uname reports HarmonyOS: pass explicit --build/--host.
        self.run(
            f'cd "{self.source_folder}" && CC={cc} CXX={cxx} ./configure '
            f"--disable-gui "
            f"--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu "
            f"--with-libssl={openssl_dir} --with-libexpat={expat_dir} "
            f"> /dev/null"
        )
        self.run(f'cd "{self.source_folder}" && make -j1')

    def package(self):
        copy(self, "ophcrack", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "bin"))
        # R7: Self-sign ELF binary on OHOS for local execution
        if self.settings.os == "OHOS":
            ophcrack_path = os.path.join(self.package_folder, "bin", "ophcrack")
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool) and os.path.isfile(ophcrack_path):
                signed_path = f"{ophcrack_path}.signed"
                self.run(
                    f'{sign_tool} sign -inFile "{ophcrack_path}"'
                    f' -outFile "{signed_path}"'
                    f' -selfSign 1 -signAlg SHA256withECDSA',
                    quiet=True
                )
                if os.path.isfile(signed_path):
                    os.replace(signed_path, ophcrack_path)
                    os.chmod(ophcrack_path, 0o755)

    def package_info(self):
        # ophcrack is a command-line tool, not a library
        self.cpp_info.bindirs = ["bin"]
