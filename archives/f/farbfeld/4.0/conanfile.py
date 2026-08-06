#!/usr/bin/env python3
"""Conan recipe for farbfeld 4 — suckless lossless image format tools."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class FarbfeldConan(ConanFile):
    name = "farbfeld"
    version = "4.0"
    description = "Lossless image format with 16-bit RGBA pixel data and simple conversion tools"
    license = "ISC"
    homepage = "https://tools.suckless.org/farbfeld/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.58")
        self.requires("libjpeg/10")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"farbfeld supports Linux/OHOS, got {self.settings.os}"
            )

    def source(self):
        source = dict(self.conan_data["sources"])
        source["filename"] = "farbfeld-4.tar.gz"
        get(self, **source, strip_root=True, verify=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate(scope="build")

    def build(self):
        apply_conandata_patches(self)
        cc = self._resolve_compiler()
        cflags = " ".join(self._cflags())
        cppflags = " ".join(self._cppflags())
        ldflags = " ".join(self._ldflags())

        self.run(
            "make -j1 "
            "CC={} CPPFLAGS={} CFLAGS={} LDFLAGS={} "
            "PNG-LDLIBS=-lpng JPG-LDLIBS=-ljpeg".format(
                shlex.quote(cc),
                shlex.quote(cppflags),
                shlex.quote(cflags),
                shlex.quote(ldflags),
            ),
            cwd=self.source_folder,
        )

        # Sign OHOS ELF binaries
        for binary in ["png2ff", "ff2png", "jpg2ff", "ff2jpg", "ff2pam", "ff2ppm"]:
            path = os.path.join(self.source_folder, binary)
            if os.path.isfile(path):
                self._sign_ohos_binary(path)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        man1_dir = os.path.join(self.package_folder, "share", "man", "man1")
        man5_dir = os.path.join(self.package_folder, "share", "man", "man5")

        for binary in ["png2ff", "ff2png", "jpg2ff", "ff2jpg", "ff2pam", "ff2ppm", "2ff"]:
            src = os.path.join(self.source_folder, binary)
            if os.path.isfile(src):
                copy(self, binary, src=self.source_folder, dst=bin_dir, keep_path=False)
                installed = os.path.join(bin_dir, binary)
                os.chmod(installed, 0o755)
                if binary != "2ff":
                    self._sign_ohos_binary(installed)

        copy(self, "*.1", src=self.source_folder, dst=man1_dir, keep_path=False)
        copy(self, "farbfeld.5", src=self.source_folder, dst=man5_dir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

    def _cflags(self):
        if str(self.settings.build_type) == "Debug":
            opt = ["-O0", "-g"]
        else:
            opt = ["-Os"]
        return ["-std=c99", "-pedantic", "-Wall", "-Wextra", "-fPIC"] + opt

    def _cppflags(self):
        flags = ["-D_DEFAULT_SOURCE"]
        for dep_name in ["libpng", "libjpeg"]:
            dep = self.dependencies[dep_name]
            inc_dir = os.path.join(dep.package_folder, "include")
            if os.path.isdir(inc_dir):
                flags.append(f"-I{inc_dir}")
        return flags

    def _ldflags(self):
        flags = []
        for dep_name in ["libpng", "libjpeg"]:
            dep = self.dependencies[dep_name]
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                flags.append(f"-L{lib_dir}")
        return flags

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
