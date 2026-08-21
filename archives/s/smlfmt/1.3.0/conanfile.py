#!/usr/bin/env python3
"""Conan recipe for smlfmt 1.3.0 on HarmonyOS.

Build system: handwritten GNU Makefile. Build entry point is
`make -j1 smlfmt` which invokes `mlton -output smlfmt src/smlfmt.mlb`.
The recipe sets MAKE=/data/service/hnp/bin/make and injects mlton bin
directory via PATH, plus GMP include/library paths for the C codegen.
"""
import os
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SmlfmtConan(ConanFile):
    name = "smlfmt"
    version = "1.3.0"
    description = "Source formatter for Standard ML"
    license = "MIT"
    homepage = "https://github.com/shwestrick/smlfmt"
    url = "https://github.com/shwestrick/smlfmt"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0")

    def build_requirements(self):
        self.tool_requires("mlton/20241230")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        gmp = self.dependencies["gmp"].package_folder
        mlton = self.dependencies.build["mlton"].package_folder
        self._mlton_bin = os.path.join(mlton, "bin")
        self._gmp_inc = os.path.join(gmp, "include")
        self._gmp_lib = os.path.join(gmp, "lib")

    def _env_prefix(self):
        tmpdir = os.environ.get("TMPDIR", self.build_folder)
        compile_args = " ".join([
            "-codegen c",
            "-cc /data/service/hnp/bin/clang",
            f"-cpp-opt -I{self._gmp_inc}",
            f"-link-opt -L{self._gmp_lib}",
            "-link-opt -lgmp",
        ])
        return (
            f'PATH="{self._mlton_bin}${{PATH:+:${{PATH}}}}" '
            f'MAKE="/data/service/hnp/bin/make" '
            f'TMPDIR="{tmpdir}" '
            f'MLTON_COMPILE_ARGS="{compile_args}" '
            f'MLTON_FILESYS_TMPPREFIX="{tmpdir}/smlfmt-filesys-" '
        )

    def build(self):
        env_prefix = self._env_prefix()
        self.run(
            f'{env_prefix}make -j1 smlfmt',
            cwd=self.source_folder, env="conanbuild",
        )
        self.output.info("UPSTREAM_BUILD_MARKER: make smlfmt PASS")
        self.run(
            f'{env_prefix}make -j1 test',
            cwd=self.source_folder, env="conanbuild",
        )
        self.output.info("UPSTREAM_TEST_MARKER: make test PASS")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "smlfmt", self.source_folder, bindir)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        self._sign_tree(bindir)

    def _sign_tree(self, root):
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanException("HarmonyOS ELF signing tools are unavailable")
        for current, _, files in os.walk(root):
            for name in files:
                path = os.path.join(current, name)
                try:
                    with open(path, "rb") as handle:
                        if handle.read(4) != b"\x7fELF":
                            continue
                except OSError:
                    continue
                clean = path + ".codesign-clean"
                signed = path + ".codesign-signed"
                orig_mode = stat.S_IMODE(os.stat(path).st_mode)
                subprocess.run([objcopy, "--remove-section", ".codesign", path, clean], check=True)
                subprocess.run([signer, "sign", "-inFile", clean, "-outFile", signed,
                                "-selfSign", "1"], check=True)
                os.chmod(signed, orig_mode)
                os.replace(signed, path)
                if os.path.exists(clean):
                    os.remove(clean)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("PATH", bindir)
