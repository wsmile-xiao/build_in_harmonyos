#!/usr/bin/env python3
"""Conan recipe for bam 0.5.1 — Lua-based build system for C/C++ projects.

bam uses a custom Makefile + make_unix.sh build system (not autotools/cmake).
It bundles Lua 5.3.3 source in src/lua/ directory — no system Lua dependency.

On HarmonyOS (OHOS), intermediate tools (txt2c) require ELF signing before
execution, and the system linker at /data/service/hnp/bin/ld is used instead
of the OHOS SDK lld (which is missing libxml2.so.16).
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import unzip, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BamConan(ConanFile):
    name = "bam"
    version = "0.5.1"
    description = "Lua-based build system for C/C++ projects"
    license = "BSD-3-Clause"
    homepage = "https://github.com/matricks/bam"
    url = "https://github.com/matricks/bam"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # bam has no external dependencies (bundles Lua 5.3.3)

    def layout(self):
        basic_layout(self)

    def source(self):
        import hashlib

        sources = self.conan_data["sources"]
        urls = sources["url"]
        if isinstance(urls, str):
            urls = [urls]
        sha256 = sources["sha256"]
        filename = sources.get("filename", "source.tar.gz")

        archive_path = os.path.join(self.source_folder, filename)

        # Use curl — CI workers may lack Python ssl module for HTTPS
        for url in urls:
            try:
                self.run(f'curl -L -sS --fail -o "{archive_path}" "{url}"',
                         cwd=self.source_folder)
                if os.path.exists(archive_path) and os.path.getsize(archive_path) > 0:
                    break
            except Exception:
                continue
        else:
            raise RuntimeError(f"Failed to download from any URL: {urls}")

        # Verify sha256
        h = hashlib.sha256()
        with open(archive_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        if h.hexdigest() != sha256:
            raise RuntimeError(f"SHA256 mismatch: expected {sha256}, got {h.hexdigest()}")

        unzip(self, archive_path, self.source_folder, strip_root=True)

    def _is_ohos(self):
        return self.settings.os == "OHOS"

    def _get_cc(self):
        # R33: Get compiler from Conan conf, not undefined shell variables
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("c") or "clang"

    def _sign_elf(self, path, src):
        """Sign ELF binary on OHOS for execution on HarmonyOS."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if Path(sign_tool).exists():
            self.run(f"{objcopy} --remove-section .codesign {path} || true", cwd=src)  # .codesign 段可能不存在
            self.run(f"{sign_tool} sign -inFile {path} "
                     f"-outFile {path}.signed -selfSign 1", cwd=src)
            shutil.move(f"{path}.signed", path)
        os.chmod(path, 0o755)

    def build(self):
        apply_conandata_patches(self)

        is_ohos = self._is_ohos()
        cc = self._get_cc()

        src = self.source_folder

        # Step 1: Build txt2c tool
        self.run(f"{cc} -Wall -pedantic -fPIC -O2 -c {src}/src/tools/txt2c.c -o {src}/txt2c.o",
                 cwd=src)
        ld_flag = "-fuse-ld=/data/service/hnp/bin/ld" if is_ohos else ""
        self.run(f"{cc} -Wall -pedantic {ld_flag} {src}/txt2c.o -o {src}/src/tools/txt2c",
                 cwd=src)

        # Step 2: Sign txt2c on OHOS
        if is_ohos:
            self._sign_elf(f"{src}/src/tools/txt2c", src)

        # Step 3: Generate internal_base.h using txt2c
        self.run(f"{src}/src/tools/txt2c {src}/src/base.lua {src}/src/tools.lua "
                 f"{src}/src/driver_gcc.lua {src}/src/driver_clang.lua "
                 f"{src}/src/driver_cl.lua {src}/src/driver_solstudio.lua "
                 f"{src}/src/driver_xlc.lua > {src}/src/internal_base.h",
                 cwd=src)

        # Step 4: Compile bam binary with bundled Lua 5.3.3
        self.run(f"{cc} -Wall -pedantic -fPIC -O2 {ld_flag} "
                 f"{src}/src/*.c {src}/src/lua/*.c "
                 f"-o {src}/bam -I {src}/src/lua -lm -lpthread -ldl -rdynamic",
                 cwd=src)

        # Step 5: Sign bam binary on OHOS
        if is_ohos:
            self._sign_elf(f"{src}/bam", src)

    def package(self):
        copy(self, "bam", self.source_folder, os.path.join(self.package_folder, "bin"))
        os.chmod(os.path.join(self.package_folder, "bin", "bam"), 0o755)

    def package_info(self):
        self.cpp_info.libs = []  # bam is a build tool, not a library
        self.cpp_info.builddirs = ["bin"]
        self.cpp_info.bindirs = ["bin"]
