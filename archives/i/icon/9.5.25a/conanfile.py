#!/usr/bin/env python3
"""Conan recipe — icon 9.5.25a (custom makefile)"""
import os
import json
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.layout import basic_layout


class IconConan(ConanFile):
    name = "icon"
    version = "9.5.25a"
    description = "Icon Programming Language — high-level general-purpose language with string and list processing"
    license = "Public Domain"
    homepage = "https://www.cs.arizona.edu/icon"
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

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf/profile, not shell env vars
        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        try:
            raw = self.conf.get("tools.build:compiler_executables")
            if raw:
                if isinstance(raw, str):
                    raw = json.loads(raw)
                if isinstance(raw, dict) and "c" in raw:
                    cc = raw["c"]
        except (json.JSONDecodeError, TypeError, KeyError):
            pass  # Fall back to PATH lookup

        # Step 1: Configure for linux platform (NoGraphics)
        self.run("make Configure name=linux", cwd=self.source_folder)

        # Override CC in generated Makedefs with full compiler path
        replace_in_file(self, os.path.join(self.source_folder, "Makedefs"),
                        "CC = clang", f"CC = {cc}")

        # Step 2: Build Icont (compiler + interpreter)
        self.run("make Icont", cwd=self.source_folder)

        # Step 3: ELF sign binaries — HarmonyOS requires signed ELF to execute.
        # Ilib needs to run icont, so signing must happen between Icont and Ilib.
        if self.settings.os == "OHOS":
            self._sign_elf(os.path.join(self.source_folder, "bin", "icont"))
            self._sign_elf(os.path.join(self.source_folder, "bin", "iconx"))

        # Step 4: Build Ilib and Ibin
        self.run("make Ilib", cwd=self.source_folder)
        self.run("make Ibin", cwd=self.source_folder)

        # Step 5: Install to temp directory (make Install fails if dest exists)
        install_dir = os.path.join(self.source_folder, "icon-install")
        if os.path.exists(install_dir):
            shutil.rmtree(install_dir)
        self.run(f'make Install dest="{install_dir}"', cwd=self.source_folder)

    def _sign_elf(self, elf_path):
        """Sign an ELF binary for HarmonyOS execution."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"

        try:
            # Remove old signature section (non-zero exit is normal on first signing)
            r = subprocess.run([objcopy, "--remove-section", ".codesign", elf_path],
                                capture_output=True, text=True, timeout=10)
            if r.returncode != 0:
                detail = r.stderr.strip() if r.stderr else f"exit code {r.returncode}"
                self.output.info(f"  objcopy note: {detail}")

            # Sign with self-sign
            tmp = elf_path + ".signed.tmp"
            r = subprocess.run([sign_tool, "sign", "-inFile", elf_path,
                                "-outFile", tmp, "-selfSign", "1"],
                               capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                if os.path.exists(tmp):
                    os.unlink(tmp)
                raise RuntimeError(
                    f"ELF signing failed for {elf_path}: {r.stderr or r.stdout}"
                )

            if os.path.exists(tmp):
                os.replace(tmp, elf_path)
                os.chmod(elf_path, 0o755)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"ELF signing timed out for {elf_path}")
        except (FileNotFoundError, PermissionError) as e:
            raise RuntimeError(f"ELF signing tool error for {elf_path}: {e}")

    def package(self):
        install_dir = os.path.join(self.source_folder, "icon-install")
        copy(self, "*", install_dir, os.path.join(self.package_folder))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
