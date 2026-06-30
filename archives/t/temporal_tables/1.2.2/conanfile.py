#!/usr/bin/env python3
"""Conan recipe for temporal_tables 1.2.2 — PostgreSQL Extension (PGXS/Makefile).

Temporal Tables PostgreSQL Extension built using direct C compilation
(bypassing PGXS due to pg_config --pkgincludedir incompatibility).
This recipe enforces R26: static linking (BUILD_SHARED_LIBS=OFF).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class TemporaltablesConan(ConanFile):
    name = "temporal_tables"
    version = "1.2.2"
    description = "Temporal Tables PostgreSQL Extension"
    license = "BSD-2-Clause"
    homepage = "https://github.com/arkhipov/temporal_tables"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,  # R26: static linking
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Use AutotoolsToolchain to generate env vars (CC, CFLAGS, etc.)
        tc = AutotoolsToolchain(self)
        # R26: BUILD_SHARED_LIBS=OFF — static linking for terminal tools
        tc.extra_cflags.append("-fPIC")
        tc.generate()

    def _get_pg_include_dirs(self):
        """Get PostgreSQL include directories from pg_config."""
        pg_config = shutil.which("pg_config")
        if not pg_config:
            return []
        dirs = []
        try:
            result = subprocess.run([pg_config, "--includedir-server"],
                                    capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                dirs.append(result.stdout.strip())
        except Exception:
            pass
        try:
            result = subprocess.run([pg_config, "--includedir"],
                                    capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                dirs.append(result.stdout.strip())
        except Exception:
            pass
        return dirs

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        pg_includes = self._get_pg_include_dirs()
        inc_flags = " ".join(f"-I{d}" for d in pg_includes)

        # Direct compilation without PGXS (avoids pg_config --pkgincludedir issue)
        # R26: BUILD_SHARED_LIBS=OFF — build static library
        self.run(
            f"cd {src_dir} && "
            f"$CC $CFLAGS -fPIC {inc_flags} -D_GNU_SOURCE "
            f"-c temporal_tables.c -o temporal_tables.o && "
            f"$CC $CFLAGS -fPIC {inc_flags} -D_GNU_SOURCE "
            f"-c versioning.c -o versioning.o && "
            f"llvm-ar rcs libtemporal_tables.a temporal_tables.o versioning.o"
        )

    def package(self):
        src_dir = self.source_folder
        # Copy the built static library (R26: static linking)
        copy(self, "*.a", src=src_dir, dst=os.path.join(self.package_folder, "lib"))
        # Copy header files for consumers
        copy(self, "*.h", src=src_dir, dst=os.path.join(self.package_folder, "include"))
        # Also copy extension SQL and control files
        copy(self, "*.control", src=src_dir, dst=os.path.join(self.package_folder, "share/extension"))
        copy(self, "*.sql", src=src_dir, dst=os.path.join(self.package_folder, "share/extension"))

    def package_info(self):
        self.cpp_info.libs = ["temporal_tables"]
