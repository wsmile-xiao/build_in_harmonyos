#!/usr/bin/env python3
"""Conan recipe for tinydns 1.05 (from djbdns 1.05) -- C CLI tools built with plain Makefile.

Build: make prog (no configure script). Produces tinydns family tools:
  tinydns-conf, tinydns, tinydns-data, tinydns-get, tinydns-edit.
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, save
from conan.tools.layout import basic_layout


class TinydnsConan(ConanFile):
    name = "tinydns"
    version = "1.05"
    description = "tinydns -- authoritative DNS server from djbdns 1.05"
    license = "Public Domain"
    homepage = "https://cr.yp.to/djbdns.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # djbdns uses conf-cc/conf-ld/conf-home for compiler/linker settings.
        # Override with OHOS cross-compiler from Conan config (R33).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        # Write conf-cc and conf-ld with OHOS compiler to source folder
        # where the Makefile expects them (make prog runs in source_folder)
        conf_cc = f"{cc} -O2 -Wimplicit -Wunused -Wcomment -Wchar-subscripts -Wuninitialized -Wshadow -Wcast-qual -Wcast-align -Wwrite-strings"
        conf_ld = f"{cc}"
        save(self, os.path.join(self.source_folder, "conf-cc"), conf_cc)
        save(self, os.path.join(self.source_folder, "conf-ld"), conf_ld)

        # conf-home is djbdns' compile-time default runtime home. It is only
        # baked into auto_home.c as a *string* used by the -conf programs to
        # emit `<home>/bin/tinydns` paths into generated run scripts -- it is
        # not a build-time filesystem dependency, and we never run make install.
        # R49/PF6: never reference a shared system prefix; derive a
        # package-owned path from the package folder instead.
        save(self, os.path.join(self.source_folder, "conf-home"), os.path.join(self.package_folder, "tinydns"))

        # Build all programs (make prog) -- upstream default it runs install which needs root
        self.run("make prog -j1", cwd=self.source_folder)

    def package(self):
        top = self.source_folder
        bin_dir = os.path.join(self.package_folder, "bin")
        # Package only tinydns family (the tinydns software component)
        for prog in ("tinydns-conf", "tinydns", "tinydns-data", "tinydns-get", "tinydns-edit"):
            copy(self, prog, top, bin_dir)

    def package_info(self):
        # application package: consumers use the tinydns* binaries
        self.cpp_info.bindirs = ["bin"]