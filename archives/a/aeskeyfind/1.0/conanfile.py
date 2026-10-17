#!/usr/bin/env python3
"""Conan recipe for aeskeyfind 1.0."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AeskeyfindConan(ConanFile):
    name = "aeskeyfind"
    version = "1.0"
    description = "Finds AES-128 and AES-256 keys in memory images"
    license = "BSD-3-Clause"
    homepage = "https://citp.princeton.edu/our-work/memory/code/"
    url = "https://salsa.debian.org/pkg-security-team/aeskeyfind"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aeskeyfind supports Linux/OHOS in this recipe, got {self.settings.os}"
            )

    def source(self):
        source = dict(self.conan_data["sources"])
        source["filename"] = "aeskeyfind-1.0.tar.gz"
        get(self, **source, strip_root=True, verify=True)

    def build(self):
        apply_conandata_patches(self)
        cc = self._resolve_compiler()
        cflags = self._cflags()
        self.run(
            "make -j1 CC={} CFLAGS={}".format(
                shlex.quote(cc),
                shlex.quote(" ".join(cflags)),
            ),
            cwd=self.source_folder,
        )
        built_binary = os.path.join(self.source_folder, "aeskeyfind")
        self._sign_ohos_binary(built_binary)
        if can_run(self):
            self.run("./aeskeyfind -h 2>&1 | grep -q 'Usage: aeskeyfind'",
                     cwd=self.source_folder)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "aeskeyfind", src=self.source_folder, dst=bin_dir, keep_path=False)
        binary = os.path.join(bin_dir, "aeskeyfind")
        if os.path.isfile(binary):
            os.chmod(binary, 0o755)
            self._sign_ohos_binary(binary)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "aeskeyfind"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

    def _cflags(self):
        if str(self.settings.build_type) == "Debug":
            opt = ["-O0", "-g"]
        else:
            opt = ["-O2", "-DNDEBUG"]
        return [
            "-Wall",
            "-std=c99",
            "-D_DEFAULT_SOURCE",
            "-D_FILE_OFFSET_BITS=64",
        ] + opt

    def _resolve_compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = compilers.get("c")
        if configured:
            return configured
        return shutil.which("clang") or shutil.which("cc") or str(self.settings.compiler)

    def _find_tool(self, name):
        env_name = "OHOS_" + name.upper().replace("-", "_")
        configured = os.environ.get(env_name)
        candidates = [
            configured,
            shutil.which(name),
            os.path.join("/data/service/hnp/bin", name),
            os.path.join("/storage/Users/currentUser/usr/local/bin", name),
            os.path.join(os.path.expanduser("~"), "usr", "local", "bin", name),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _sign_ohos_binary(self, path):
        if self.settings.os != "OHOS" or not os.path.isfile(path):
            return
        signer = self._find_tool("binary-sign-tool")
        if not signer:
            self.output.warning("binary-sign-tool not found; skip OHOS ELF signing")
            return
        objcopy = self._find_tool("llvm-objcopy")
        if objcopy:
            self.run(
                f"{shlex.quote(objcopy)} --remove-section .codesign "
                f"{shlex.quote(path)} 2>/dev/null || true",
                quiet=True,
            )
        signed = path + ".signed"
        self.run(
            f"{shlex.quote(signer)} sign -inFile {shlex.quote(path)} "
            f"-outFile {shlex.quote(signed)} -selfSign 1",
            quiet=True,
        )
        if os.path.isfile(signed):
            os.replace(signed, path)
            os.chmod(path, 0o755)
