#!/usr/bin/env python3
"""Conan recipe for ConvertLIT 1.8.

ConvertLIT is a small C command-line utility that expands Microsoft Reader
LIT files or rewrites them to DRM1.  The 2004 source archive uses two plain
Makefiles and expects a bundled libtommath-0.30 tree.  This recipe links the
published libtommath/1.3.0 package instead and keeps all dependency material
inside a build-folder-private prefix.
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class ConvertlitConan(ConanFile):
    name = "convertlit"
    version = "1.8"
    description = "Convert Microsoft Reader LIT eBooks into an open format"
    license = "GPL-2.0-or-later"
    homepage = "http://www.convertlit.com/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libtommath/1.3.0")

    def validate(self):
        if self.settings.os not in ("Linux", "Macos", "OHOS"):
            raise ConanInvalidConfiguration(
                f"convertlit requires a POSIX host, got {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"convertlit/1.8 is validated for OHOS armv8, got {self.settings.arch}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # The zip has README, clit18/, and lib/ at its root; there is no
        # enclosing directory to strip.
        get(self, **self.conan_data["sources"][self.version], strip_root=False)

    def generate(self):
        # R49: stage dependency headers and the static archive in a private
        # prefix.  This prevents accidental linkage with a worker's /usr/local.
        dep = self.dependencies["libtommath"]
        prefix = os.path.join(self.build_folder, "prefix")
        copy(
            self,
            "*.h",
            src=os.path.join(dep.package_folder, "include"),
            dst=os.path.join(prefix, "include"),
        )
        copy(
            self,
            "*.a",
            src=os.path.join(dep.package_folder, "lib"),
            dst=os.path.join(prefix, "lib"),
        )
        VirtualBuildEnv(self).generate()

    def _normalize_line_endings(self):
        # The official 2004 zip stores most sources as CRLF.  Normalize before
        # applying a portable unified diff; source semantics are unchanged.
        for root, _, files in os.walk(self.source_folder):
            for filename in files:
                if not filename.endswith((".c", ".h", ".mak")) and filename != "Makefile":
                    continue
                path = os.path.join(root, filename)
                with open(path, "rb") as source_file:
                    data = source_file.read()
                normalized = data.replace(b"\r\n", b"\n")
                if normalized != data:
                    with open(path, "wb") as source_file:
                        source_file.write(normalized)

    def _compiler_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c", "clang")
        cc_dir = os.path.dirname(cc) if os.path.isabs(cc) else ""

        def tool(name, llvm_name, fallback):
            configured = executables.get(name)
            if configured:
                return configured
            candidate = os.path.join(cc_dir, llvm_name) if cc_dir else ""
            if candidate and os.path.isfile(candidate):
                return candidate
            return shutil.which(llvm_name) or shutil.which(fallback) or fallback

        return cc, tool("ar", "llvm-ar", "ar")

    def build(self):
        self._normalize_line_endings()
        apply_conandata_patches(self)

        cc, ar = self._compiler_tools()
        prefix = os.path.join(self.build_folder, "prefix")
        include_flag = f"-I{os.path.join(prefix, 'include')}"
        tommath_archive = os.path.join(prefix, "lib", "libtommath.a")

        self.run(
            "make -C lib clean all -j2 CC={} AR={}".format(
                shlex.quote(cc), shlex.quote(ar)
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run(
            "make -C clit18 clean all -j2 CC={} CPPFLAGS={} LDLIBS={}".format(
                shlex.quote(cc),
                shlex.quote(include_flag),
                shlex.quote(tommath_archive),
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "clit",
            src=os.path.join(self.source_folder, "clit18"),
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "COPYING",
            src=os.path.join(self.source_folder, "clit18"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
