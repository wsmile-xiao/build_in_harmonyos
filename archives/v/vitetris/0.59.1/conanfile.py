#!/usr/bin/env python3
"""Conan recipe for vitetris 0.59.1 — Makefile build system.

vitetris is a terminal-based Tetris game by Victor Geraldsson.
Build: ./configure --prefix=... && make && make install
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class VitetrisConan(ConanFile):
    name = "vitetris"
    version = "0.59.1"
    package_type = "application"
    description = "Terminal-based Tetris game by Victor Geraldsson"
    license = "BSD-2-Clause"
    homepage = "https://victornils.net/tetris/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # vitetris builds in-source (Makefile in source dir)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _config_shell(self):
        # R5: OHOS has no /bin/sh, use CONFIG_SHELL from profile [buildenv]
        # Fallback chain: CONFIG_SHELL env → PATH lookup → hard-coded OHOS path
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            shutil.which("bash"),
            "/data/service/hnp/bin/bash",
        ):
            if candidate and os.path.exists(candidate):
                return candidate
        # Last resort: return the OHOS default; build() will fail with a clear
        # shell-not-found error rather than a silent wrong-shell invocation.
        return "/data/service/hnp/bin/bash"

    def _is_ohos(self):
        return self.settings.os == "OHOS"

    def _sign_elf(self, path):
        """Sign ELF binary on OHOS so the kernel allows execution (E077/E082).

        Without signing, OHOS rejects execution with 'Operation not permitted'
        (exit 126). Mirrors the pattern used by bam/0.5.1 and zstd/1.5.7.
        """
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if Path(sign_tool).exists():
            self.run(f'{objcopy} --remove-section .codesign "{path}" || true')
            self.run(f'{sign_tool} sign -inFile "{path}" '
                     f'-outFile "{path}.signed" -selfSign 1')
            shutil.move(f"{path}.signed", path)
        os.chmod(path, 0o755)

    def build(self):
        apply_conandata_patches(self)

        config_shell = self._config_shell()

        # vitetris uses a custom configure script (not autotools).
        # --prefix writes the path into config.mk; make install uses it directly.
        # Using package_folder as prefix so `make install` lands in the right layout.
        prefix = self.package_folder
        self.run(
            f'"{config_shell}" ./configure --prefix="{prefix}"',
            cwd=self.source_folder,
        )

        # R9: Always use -j1, never -j$(nproc)
        # R33: CC/CFLAGS come from config.mk (written by configure)
        # SHELL={config_shell} so Makefile-internal ./src-conf.sh runs on OHOS
        self.run(f'make SHELL="{config_shell}" -j1', cwd=self.source_folder)

    def package(self):
        config_shell = self._config_shell()
        # make install uses prefix from config.mk (set in build()).
        # No DESTDIR needed since prefix already points to package_folder.
        self.run(f'make install SHELL="{config_shell}"', cwd=self.source_folder)
        # E077: OHOS requires signed ELF binaries; sign tetris so test_package
        # can execute it. CI PR pipeline does not run ci/artifacts/sign.sh.
        if self._is_ohos():
            tetris_bin = os.path.join(self.package_folder, "bin", "tetris")
            if os.path.isfile(tetris_bin):
                self._sign_elf(tetris_bin)

    def package_info(self):
        # vitetris is a command-line application, not a library
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
