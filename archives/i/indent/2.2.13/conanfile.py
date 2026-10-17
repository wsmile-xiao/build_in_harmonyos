#!/usr/bin/env python3
"""Conan recipe for GNU indent 2.2.3 on OHOS aarch64.

indent is the GNU C code formatting/beautifier CLI tool. It builds a single
executable (no library), so this is an application package (commands.json
declared at software level).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IndentConan(ConanFile):
    name = "indent"
    version = "2.2.13"
    description = "GNU indent - C code formatting and beautifier tool"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/indent/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # AutotoolsToolchain does not inject OHOS build/host triplets; the
        # upstream config/config.sub does not know the ohos kernel-os.
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
        ])
        # musl (OHOS libc) has no libintl; NLS is optional for a formatter.
        # Upstream indent.h already guards _(X) with ENABLE_NLS, but
        # src/indent.c calls bindtextdomain/textdomain unguarded - patched.
        tc.configure_args.append("--disable-nls")
        tc.generate()

    def _sign_binary(self, path):
        # acme 0.97 precedent: OHOS device refuses unsigned ELFs; strip the
        # placeholder .codesign section first (E077), then self-sign.
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if self.settings.os != "OHOS" or not os.path.exists(sign_tool):
            return
        tmp_signed = path + ".signed"
        self.run(f"{objcopy} --remove-section .codesign {path} 2>/dev/null || true")
        # E077/§12.14: conan build env injects the SDK LD_LIBRARY_PATH which
        # breaks the signer (exit 127); strip it for this call.
        self.run(
            f"env -u LD_LIBRARY_PATH {sign_tool} sign -inFile {path} -outFile {tmp_signed} -selfSign 1",
            quiet=True,
        )
        os.replace(tmp_signed, path)
        os.chmod(path, 0o755)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1", "MAKEINFO=true"])
        # Upstream regression/Makefile is a static file shipped in the tarball
        # and not listed in AC_CONFIG_FILES, so an out-of-tree build never gets
        # it generated into the build dir (the patched SUBDIRS no longer
        # recurse there either). Copy regression/ as-is, sign the freshly
        # built indent, and drive the official TEST (INDENT=../src/indent).
        # keep_path=True: TEST reads input/<case>.c relative to its own dir,
        # so the input/ tree must survive the copy intact.
        copy(self, "*", os.path.join(self.source_folder, "regression"),
             os.path.join(self.build_folder, "regression"), keep_path=True)
        self._sign_binary(os.path.join(self.build_folder, "src", "indent"))
        self.run("sh ./TEST", cwd=os.path.join(self.build_folder, "regression"))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
