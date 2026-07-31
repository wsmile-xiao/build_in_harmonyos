#!/usr/bin/env python3
"""Conan recipe — bison 3.8.2 (GNU parser generator, autotools).

Fix for OHOS: config.status creates temp dirs with umask 077 (perms 700),
but the OHOS filesystem doesn't allow writing files into such directories.
We patch config.status after configure to use umask 000 and add chmod.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BisonConan(ConanFile):
    name = "bison"
    version = "3.8.2"
    description = "GNU parser generator, converts grammar rules to LALR/GLR parsers"
    license = "GPL-3.0"
    homepage = "https://www.gnu.org/software/bison/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

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
        tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "bison-build")
        os.makedirs(tmpdir, exist_ok=True)
        hnp_bin = "/data/service/hnp/bin"
        current_path = os.environ.get("PATH", "")
        if hnp_bin not in current_path:
            os.environ["PATH"] = hnp_bin + ":" + current_path

        # Step 1: Run configure --no-create (creates config.status but doesn't run it)
        self.run(
            f'cd "{self.source_folder}" && '
            f'umask 022 && '
            f'TMPDIR="{tmpdir}" '
            f'CONFIG_SHELL=/data/service/hnp/bin/bash '
            f'SHELL=/data/service/hnp/bin/bash '
            f'AWK=/data/service/hnp/bin/awk '
            f'PATH="/data/service/hnp/bin:$PATH" '
            f'./configure --prefix= --disable-nls --no-create',
            env="conanrun"
        )

        # Step 2: Patch config.status to fix temp dir permissions
        cs = os.path.join(self.source_folder, "config.status")
        if os.path.exists(cs):
            with open(cs, "r") as f:
                content = f.read()
            # Replace umask 077 with umask 000 so temp dirs are world-writable.
            # Use re.sub + explicit success check: str.replace() would silently
            # return the original string if upstream config.status changes its
            # whitespace/variable naming, and the build would later fail with
            # a cryptic "Permission denied" instead of a clear patch failure.
            new_content, n = re.subn(r"umask\s+077", "umask 000", content, count=1)
            if n == 0:
                raise RuntimeError(
                    "config.status patch failed: 'umask 077' pattern not found "
                    "(upstream bison may have changed config.status format)"
                )
            content = new_content
            # Also add chmod after temp dir creation for extra safety.
            new_content, n = re.subn(
                r"(^|(?<=\n))(\s*ac_tmp=\$tmp)",
                r"\2\n  chmod 755 \"$ac_tmp\" 2>/dev/null",
                content,
                count=1,
            )
            if n == 0:
                raise RuntimeError(
                    "config.status patch failed: 'ac_tmp=$tmp' pattern not found "
                    "(upstream bison may have changed config.status format)"
                )
            content = new_content
            with open(cs, "w") as f:
                f.write(content)

        # Step 3: Run config.status manually (now patched)
        self.run(
            f'cd "{self.source_folder}" && '
            f'TMPDIR="{tmpdir}" '
            f'AWK=/data/service/hnp/bin/awk '
            f'PATH="/data/service/hnp/bin:$PATH" '
            f'./config.status',
            env="conanrun"
        )

        # Step 4: Run make
        self.run(
            f'cd "{self.source_folder}" && '
            f'TMPDIR="{tmpdir}" '
            f'AWK=/data/service/hnp/bin/awk '
            f'PATH="/data/service/hnp/bin:$PATH" '
            f'make -j1 MAKEINFO=true',
            env="conanrun"
        )

    def package(self):
        self.run(
            f'cd "{self.source_folder}" && '
            f'PATH="/data/service/hnp/bin:$PATH" '
            f'make install DESTDIR="{self.package_folder}" MAKEINFO=true',
            env="conanrun"
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
