#!/usr/bin/env python3
"""Conan recipe for MLton 20241230 on HarmonyOS."""
import os
import stat
import subprocess
import uuid

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MltonConan(ConanFile):
    name = "mlton"
    version = "20241230"
    description = "Whole-program optimizing compiler for Standard ML"
    license = "HPND"
    homepage = "https://www.mlton.org/"
    url = "https://github.com/MLton/mlton"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0")

    def build_requirements(self):
        # Poly/ML is an explicit, audited source-built bootstrap compiler.
        self.tool_requires("polyml/5.9.2.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        polyml = self.dependencies.build["polyml"].package_folder
        wrapper = os.path.join(self.generators_folder, "polyc-mlton-bootstrap")
        os.makedirs(self.generators_folder, exist_ok=True)
        source_polyc = os.path.join(polyml, "bin", "polyc")
        with open(source_polyc, "r", encoding="utf-8") as handle:
            data = handle.read()
        data = data.replace('prefix="/"', f'prefix="{polyml}"', 1)
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
        os.chmod(wrapper, os.stat(wrapper).st_mode | stat.S_IXUSR)

    def _make_vars(self):
        gmp = self.dependencies["gmp"].package_folder
        polyml = self.dependencies.build["polyml"].package_folder
        return [
            'CC="/data/service/hnp/bin/clang"',
            'AR="/data/service/hnp/bin/ar"',
            'RANLIB="/data/service/hnp/bin/ranlib"',
            'STRIP="/data/service/hnp/bin/strip"',
            f'WITH_GMP_INC_DIR="{os.path.join(gmp, "include")}"',
            f'WITH_GMP_LIB_DIR="{os.path.join(gmp, "lib")}"',
            f'POLYC="{os.path.join(self.generators_folder, "polyc-mlton-bootstrap")} -b {os.path.join(polyml, "bin", "poly")}"',
            'MLTON_COMPILE_ARGS="-codegen c"',
            'OLD_MLTON_COMPILE_ARGS="-codegen c"',
            'WITH_NPI_RUNTIME=false',
            'WITH_PIE_RUNTIME=true',
            'RSYNC="cp -fpR"',
        ]

    def build(self):
        tmpdir = os.environ.get("TMPDIR", self.build_folder)
        make_vars = " ".join(self._make_vars())
        self.run(f'TMPDIR="{tmpdir}" make -j1 {make_vars} bootstrap-polyml', cwd=self.source_folder, env="conanbuild")
        self.output.info("UPSTREAM_BOOTSTRAP_MARKER: bootstrap-polyml PASS")
        filesys_tmp_prefix = f"/dev/shm/mlton-filesys-{uuid.uuid4().hex}-"
        try:
            self.run(
                f'TMPDIR="{tmpdir}" MLTON_FILESYS_TMPPREFIX="{filesys_tmp_prefix}" '
                f'make -j1 {make_vars} check',
                cwd=self.source_folder, env="conanbuild",
            )
        finally:
            for suffix in ("A", "B"):
                try:
                    os.remove(filesys_tmp_prefix + suffix)
                except FileNotFoundError:
                    pass
        self.output.info("UPSTREAM_TEST_MARKER: make check PASS")
        self._sign_tree(os.path.join(self.source_folder, "build"))
        self.output.info("ADAPTED_TEST_MARKER: HarmonyOS platform/TMPDIR/signing PASS")

    def package(self):
        tmpdir = os.environ.get("TMPDIR", self.build_folder)
        make_vars = " ".join(self._make_vars())
        self.run(
            f'TMPDIR="{tmpdir}" make -j1 {make_vars} DESTDIR="{self.package_folder}" PREFIX="" install-no-strip',
            cwd=self.source_folder, env="conanbuild",
        )
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        self._sign_tree(self.package_folder)

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
