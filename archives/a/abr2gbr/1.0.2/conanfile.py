#!/usr/bin/env python3
"""Conan recipe for abr2gbr 1.0.2 — Photoshop ABR brush to GIMP GBR converter.

abr2gbr is a small single-file C utility by Marco Lamberto that reads an
Adobe Photoshop brush file (.abr) and converts each sampled brush into a
GIMP brush file (.gbr). It depends only on glib (1.x era, but builds fine
against modern glib with a pkg-config-based Makefile).

Key adaptation points for OHOS:
- Original Makefile calls `glib-config` (GLib 1.x), which does not exist on
  modern systems. We patch the Makefile to use pkg-config instead.
- The patch also adds cross-compile friendly defaults (CC/CFLAGS/LDFLAGS
  override via environment), and installs to a Conan-style prefix.
- No autotools in the upstream orig tarball; the Debian packaging adds a
  configure.ac, but we do not need it for a single .c file.
"""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Abr2gbrConan(ConanFile):
    name = "abr2gbr"
    version = "1.0.2"
    description = "Convert Adobe Photoshop .abr brush files to GIMP .gbr brush files"
    license = "GPL-2.0-only"
    homepage = "https://www.sunnyspot.org/gimp/tools.html"
    url = "https://salsa.debian.org/debian/abr2gbr.git"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # abr2gbr uses glib data types (gchar, gint32, g_print, etc.)
        self.requires("glib/2.84.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # R33: Get compiler from Conan conf, not undefined shell variables
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("c") or "clang"

    def _sdk_llvm_libdir(self):
        """LLVM lib dir of the compiler toolchain (contains libxml2.so.16).

        The OHOS clang driver spawns `lld` for linking, and lld's RUNPATH
        ($ORIGIN/../lib) points into the SDK llvm/lib. On CI workers the
        ambient LD_LIBRARY_PATH (e.g. ~/usr/local/lib) can shadow that dir
        with an incompatible libxml2.so.16, making lld fail with
        "Error loading shared library libxml2.so.16 ... symbol not found".
        Prepend the SDK llvm/lib so the correct libxml2 is found first.
        """
        cc = self._get_cc()
        cc_real = os.path.realpath(cc)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        return llvm_lib if os.path.isdir(llvm_lib) else ""

    def _glib_cflags(self):
        """GLib include flags, from Conan dep cpp_info (build-time resolve)."""
        try:
            dep = self.dependencies["glib"]
            incdirs = list(dep.cpp_info.includedirs)
            for comp in dep.cpp_info.components.values():
                for d in comp.includedirs:
                    if d not in incdirs:
                        incdirs.append(d)
            if incdirs:
                return " ".join(f"-I{d}" for d in incdirs)
        except KeyError:
            # glib dep missing from graph (shouldn't happen — declared in requires)
            self.output.warning("glib not in dependency graph; glib include flags empty")
        return ""

    def _glib_libs(self):
        """GLib link flags, from Conan dep cpp_info (build-time resolve).

        glib is built static against musl libc's gettext symbols. The OHOS
        SDK libc.so lacks gettext, but the system musl loader
        (ld-musl-aarch64.so.1) exports it — so we must link that .so by
        name using -l: (same approach as the glib recipe).
        """
        parts = []
        try:
            dep = self.dependencies["glib"]
            libs = list(dep.cpp_info.libs)
            libdirs = list(dep.cpp_info.libdirs)
            for comp in dep.cpp_info.components.values():
                for l in comp.libs:
                    if l not in libs:
                        libs.append(l)
                for d in comp.libdirs:
                    if d not in libdirs:
                        libdirs.append(d)
            if libdirs:
                parts.append(" ".join(f"-L{d}" for d in libdirs))
            if libs:
                parts.append(" ".join(f"-l{l}" for l in libs))
            # glib's declared system libs (m, pthread, rt, dl, z)
            syslibs = list(dep.cpp_info.system_libs)
            for comp in dep.cpp_info.components.values():
                for s in comp.system_libs:
                    if s not in syslibs:
                        syslibs.append(s)
            if syslibs:
                parts.append(" ".join(f"-l{s}" for s in syslibs))
        except KeyError:
            # glib dep missing from graph — fall back to bare -lglib-2.0
            self.output.warning("glib not in dependency graph; using -lglib-2.0 fallback")
            parts.append("-lglib-2.0")
        # gettext/intl symbols live in system musl libc on OHOS
        if str(self.settings.os) == "OHOS":
            parts.append("-L/lib -l:ld-musl-aarch64.so.1")
        return " ".join(parts).strip()

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        cc = self._get_cc()
        glib_cflags = self._glib_cflags()
        glib_libs = self._glib_libs()

        # The patched Makefile reads CC, CFLAGS, LDFLAGS, GLIB_LIBS from env.
        # Optimization level follows build_type so Debug builds get -g -O0
        # instead of a hardcoded -O2 (per AI review).
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-g -O0"
        # Prepend the SDK llvm/lib to LD_LIBRARY_PATH so the lld linker
        # loads the SDK's libxml2.so.16 instead of a shadowed one from the
        # ambient environment (see _sdk_llvm_libdir).
        sdk_ld = self._sdk_llvm_libdir()
        ld_env = f'LD_LIBRARY_PATH="{sdk_ld}:$LD_LIBRARY_PATH" ' if sdk_ld else ""
        env_prefix = (
            f"CC={cc} "
            f'CFLAGS="{glib_cflags} {opt}" '
            f'LDFLAGS="" '
            f'GLIB_LIBS="{glib_libs}"'
        )

        self.run(f"cd {src} && {ld_env}{env_prefix} make abr2gbr")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        bindir = os.path.join(pkg, "bin")
        os.makedirs(bindir, exist_ok=True)

        # The patched Makefile builds the binary at ./abr2gbr (symlink to .obj/abr2gbr)
        bin_path = os.path.join(src, "abr2gbr")
        if os.path.isfile(bin_path):
            dest = os.path.join(bindir, "abr2gbr")
            os.rename(bin_path, dest)
            os.chmod(dest, 0o755)
        else:
            # Fallback: look in .obj/
            obj_bin = os.path.join(src, ".obj", "abr2gbr")
            if os.path.isfile(obj_bin):
                dest = os.path.join(bindir, "abr2gbr")
                os.rename(obj_bin, dest)
                os.chmod(dest, 0o755)

        # jbr2gbr is an alias of the same binary (upstream Makefile creates the
        # symlink; restored per review so the JBR→GBR entry point stays usable).
        jbr_link = os.path.join(bindir, "jbr2gbr")
        if os.path.isfile(dest) and not os.path.exists(jbr_link):
            os.symlink("abr2gbr", jbr_link)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
