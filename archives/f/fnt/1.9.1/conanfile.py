#!/usr/bin/env python3
"""Conan recipe for fnt — a font manager shell script (no compilation needed)."""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class FntConan(ConanFile):
    name = "fnt"
    version = "1.9.1"
    description = "Apt for fonts, the missing font manager for macOS/linux"
    license = "MIT"
    homepage = "https://github.com/alexmyczko/fnt"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches declared in conandata.yml (0001-fnt.patch)
        # The patch handles both shebang fix and HarmonyOS platform detection.
        # No inline string-replacement code — patches are the single source.
        apply_conandata_patches(self)
        # P3 fail-fast: if the patched fnt source is missing, the adaptation
        # silently produced nothing — abort instead of shipping an empty pkg.
        fnt_path = os.path.join(self.source_folder, "fnt")
        if not os.path.exists(fnt_path):
            raise FileNotFoundError(
                f"fnt source not found at {fnt_path} after applying patches — "
                "expected from 0001-fnt.patch"
            )

    def package(self):
        import shutil, subprocess, sys
        dst_bin = os.path.join(self.package_folder, "bin")
        os.makedirs(dst_bin, exist_ok=True)
        src_fnt = os.path.join(self.source_folder, "fnt")
        dst_fnt = os.path.join(dst_bin, "fnt")
        shutil.copyfile(src_fnt, dst_fnt)
        # Fix permissions. HMDFS may reject os.chmod with PermissionError;
        # fall back to the chmod binary, but DO inspect its return code and
        # surface failures — silent 2>/dev/null + unchecked os.system ships
        # a non-executable fnt that fails downstream with "Permission denied".
        try:
            os.chmod(dst_fnt, 0o755)
        except (PermissionError, OSError) as e:
            self.output.warn(f"os.chmod failed ({e}); trying chmod binary")
            r = subprocess.run(["chmod", "755", dst_fnt], capture_output=True)
            if r.returncode != 0:
                msg = (
                    f"chmod binary failed rc={r.returncode}: "
                    f"{r.stderr.decode(errors='replace').strip()}"
                )
                self.output.warn(msg)
                # CHMOD also failed: surface the failure instead of shipping a
                # non-executable fnt that fails downstream with "Permission
                # denied" — the exact silent-failure mode the comment above
                # warns against. Raise so Conan marks the build failed and no
                # incomplete package is produced.
                raise ConanException(msg)
        copy(self, "fnt.1", src=self.source_folder, dst=os.path.join(self.package_folder, "man", "man1"))
        copy(self, "completions/_fnt", src=self.source_folder, dst=os.path.join(self.package_folder, "zsh", "site-functions"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []