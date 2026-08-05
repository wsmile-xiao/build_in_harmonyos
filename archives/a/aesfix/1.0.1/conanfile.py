#!/usr/bin/env python3
"""Conan recipe for aesfix 1.0.1."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AesfixConan(ConanFile):
    name = "aesfix"
    version = "1.0.1"
    description = "Correct unidirectional bit errors in AES-128 key schedules"
    license = "BSD-3-Clause"
    homepage = "http://citp.princeton.edu/memory/"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aesfix 1.0.1 supports Linux/OHOS in this recipe, got {self.settings.os}"
            )

    def source(self):
        source = dict(self.conan_data["sources"])
        source["filename"] = "aesfix-1.0.1.tar.gz"
        get(self, **source, strip_root=True, verify=True)

    def build(self):
        make = self._make_program()
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = self._resolve_tool(compilers.get("cpp") or compilers.get("cxx"), "clang++")
        cxxflags = " ".join(self._cxxflags())
        self.run(
            " ".join(
                [
                    shlex.quote(make),
                    "-j1",
                    f"CXX={shlex.quote(cxx)}",
                    f"CXXFLAGS={shlex.quote(cxxflags)}",
                ]
            ),
            cwd=self.source_folder,
        )

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "aesfix"),
            keep_path=False,
        )
        copy(
            self,
            "sched.*",
            src=os.path.join(self.source_folder, "samples"),
            dst=os.path.join(self.package_folder, "share", "aesfix", "samples"),
            keep_path=False,
        )
        copy(
            self,
            "aesfix",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )

        binary = os.path.join(self.package_folder, "bin", "aesfix")
        if os.path.exists(binary):
            self._sign_ohos_binary(binary)
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

    def _cxxflags(self):
        flags = ["-Wall", "-funroll-loops"]
        build_type = str(self.settings.get_safe("build_type") or "Release")
        if build_type == "Debug":
            flags.extend(["-O0", "-g"])
        elif build_type == "RelWithDebInfo":
            flags.extend(["-O2", "-g", "-DNDEBUG"])
        elif build_type == "MinSizeRel":
            flags.extend(["-Os", "-DNDEBUG"])
        else:
            flags.extend(["-O2", "-DNDEBUG"])
        if self.options.get_safe("fPIC"):
            flags.append("-fPIC")
        if self.settings.os == "OHOS":
            flags.append("-Wno-error=unused-command-line-argument")
        return flags

    def _make_program(self):
        configured = self.conf.get("tools.gnu:make_program", default=None, check_type=str)
        if configured:
            return configured
        return shutil.which("make") or "make"

    def _resolve_tool(self, configured, fallback):
        if configured and os.path.exists(configured):
            return configured
        found = shutil.which(fallback)
        if found:
            return found
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
