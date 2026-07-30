#!/usr/bin/env python3
"""Conan recipe — SLEPc 3.25.1 (PETSc-style Python configure)."""
import os
import re
import shutil
import sys
from pathlib import Path

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# PETSc records the interpreter it was configured with as an absolute path in
# petscvariables (PYTHON = /..., PYTHON_EXE = "..."). When the Conan binary
# is downloaded to a different machine that path may not exist. The SLEPc
# recipe replaces it with the current interpreter so configure/make can run.
_PYTHON_LINE_PATTERN = re.compile(
    r'^(?P<key>PYTHON(?:_EXE)?)\s*=\s*(?P<value>"?[^"\n]+"?)',
    re.MULTILINE,
)


def _relocate_python_refs(text: str, interpreter: str) -> str:
    """Replace PETSc's recorded PYTHON/PYTHON_EXE with the current interpreter."""
    quoted = f'"{interpreter}"'

    def _sub(match: "re.Match[str]") -> str:
        key = match.group("key")
        value = match.group("value")
        was_quoted = value.startswith('"')
        return f"{key} = {quoted if was_quoted else interpreter}"

    return _PYTHON_LINE_PATTERN.sub(_sub, text)


class SlepcConan(ConanFile):
    name = "slepc"
    version = "3.25.1"
    description = "Scalable Library for Eigenvalue Problem Computations"
    license = "BSD-2-Clause"
    homepage = "https://slepc.upv.es/"
    url = "https://gitlab.com/slepc/slepc"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("petsc/3.25.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _prepare_petsc(self):
        """Copy and relocate PETSc metadata without modifying Conan's cache."""
        source = Path(self.dependencies["petsc"].package_folder)
        destination = Path(self.build_folder) / "petsc"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)

        variables = destination / "lib" / "petsc" / "conf" / "petscvariables"
        content = variables.read_text(encoding="utf-8")
        match = re.search(r"^PREFIXDIR\s*=\s*(.+)$", content, re.MULTILINE)
        old_prefix = match.group(1).strip() if match else str(source)
        new_prefix = str(destination)

        text_suffixes = {"", ".h", ".pc", ".mk", ".py", ".txt"}
        for path in destination.rglob("*"):
            if not path.is_file() or path.suffix not in text_suffixes:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            relocated = text.replace(old_prefix, new_prefix)
            relocated = _relocate_python_refs(relocated, sys.executable)
            if relocated != text:
                path.write_text(relocated, encoding="utf-8")
        return destination

    def build(self):
        apply_conandata_patches(self)
        petsc_dir = self._prepare_petsc()
        slepc_dir = self.source_folder
        env = f"SLEPC_DIR={slepc_dir} PETSC_DIR={petsc_dir}"
        configure_args = [
            f"--prefix={self.package_folder}",
            "--with-slepc4py=0",
        ]
        self.run(
            f"{env} ./configure {' '.join(configure_args)}",
            cwd=self.source_folder,
        )
        self.run(
            f"{env} make -j1",
            cwd=self.source_folder,
        )

    def package(self):
        petsc_dir = Path(self.build_folder) / "petsc"
        env = f"SLEPC_DIR={self.source_folder} PETSC_DIR={petsc_dir}"
        self.run(f"{env} make install", cwd=self.source_folder)
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["slepc"]
        self.cpp_info.requires = ["petsc::petsc"]
        petsc_root = self.dependencies["petsc"].package_folder
        self.cpp_info.includedirs = [
            "include",
            os.path.join(petsc_root, "include"),
            os.path.join(petsc_root, "include", "petsc"),
        ]
