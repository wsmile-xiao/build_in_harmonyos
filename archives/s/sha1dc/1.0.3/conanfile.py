#!/usr/bin/env python3
"""Conan recipe for sha1dc 1.0.3."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Sha1dcConan(ConanFile):
    name = "sha1dc"
    version = "1.0.3"
    description = "SHA-1 collision detection library and sha1dcsum tools"
    license = "MIT"
    homepage = "https://github.com/cr-marcstevens/sha1collisiondetection"
    url = ""
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sha1dc 1.0.3 supports Linux/OHOS in this recipe, got {self.settings.os}"
            )

    def source(self):
        source = dict(self.conan_data["sources"])
        source["filename"] = "sha1dc-1.0.3.tar.gz"
        get(self, **source, strip_root=True, verify=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = self._resolve_tool(compilers.get("c"), "clang")
        ar = self._resolve_tool(compilers.get("ar"), "llvm-ar", sibling_from=cc)
        ranlib = self._resolve_tool(
            compilers.get("ranlib"), "llvm-ranlib", sibling_from=cc
        )

        cflags = self._build_type_cflags()
        if self.options.get_safe("fPIC"):
            cflags.append("-fPIC")
        if self.settings.os == "OHOS":
            cflags.append("-Wno-error=unused-command-line-argument")

        make_args = [
            "-j1",
            f"CC={shlex.quote(cc)}",
            f"LD={shlex.quote(cc)}",
            f"AR={shlex.quote(ar)}",
            f"RANLIB={shlex.quote(ranlib)}",
            "LIBTOOL=__conan_no_libtool__",
            f"TARGETCFLAGS={shlex.quote(' '.join(cflags))}",
        ]
        self.run(f"make {' '.join(make_args)}", cwd=self.source_folder)
        self.run(f"make {' '.join(make_args)} check", cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "sha1.h", src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "include", "sha1dc"), keep_path=False)
        copy(self, "libsha1detectcoll.a", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "sha1dcsum*", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        for name in ("sha1dcsum", "sha1dcsum_partialcoll"):
            path = os.path.join(self.package_folder, "bin", name)
            if os.path.exists(path):
                self._sign_ohos_binary(path)
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["sha1detectcoll"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "sha1dc")
        self.cpp_info.set_property("cmake_target_name", "sha1dc::sha1dc")
        self.cpp_info.set_property("pkg_config_name", "sha1dc")

    def _build_type_cflags(self):
        build_type = str(self.settings.build_type)
        if build_type == "Debug":
            return ["-O0", "-g"]
        if build_type == "RelWithDebInfo":
            return ["-O2", "-g", "-DNDEBUG"]
        if build_type == "MinSizeRel":
            return ["-Os", "-DNDEBUG"]
        return ["-O2", "-DNDEBUG"]

    def _resolve_tool(self, configured, fallback, sibling_from=None):
        if configured and os.path.exists(configured):
            return configured
        found = shutil.which(fallback)
        if found:
            return found
        if sibling_from:
            bindir = os.path.dirname(sibling_from) if os.path.isabs(sibling_from) else ""
            candidate = os.path.join(bindir, fallback) if bindir else ""
            if candidate and os.path.exists(candidate):
                return candidate
        if configured:
            bindir = os.path.dirname(configured) if os.path.isabs(configured) else ""
            candidate = os.path.join(bindir, fallback) if bindir else ""
            if candidate and os.path.exists(candidate):
                return candidate
        home_candidate = os.path.join(os.path.expanduser("~"), "usr", "local", "bin", fallback)
        if os.path.exists(home_candidate):
            return home_candidate
        return fallback

    def _sign_ohos_binary(self, path):
        if self.settings.os != "OHOS":
            return
        objcopy = self._resolve_tool(None, "llvm-objcopy")
        signer = self._resolve_tool(None, "binary-sign-tool")
        if not (os.path.exists(objcopy) and os.path.exists(signer)):
            return
        signed = path + ".signed"
        self.run(f"{shlex.quote(objcopy)} --remove-section .codesign {shlex.quote(path)}", quiet=True)
        self.run(
            f"{shlex.quote(signer)} sign -inFile {shlex.quote(path)} "
            f"-outFile {shlex.quote(signed)} -selfSign 1",
            quiet=True,
        )
        os.replace(signed, path)
