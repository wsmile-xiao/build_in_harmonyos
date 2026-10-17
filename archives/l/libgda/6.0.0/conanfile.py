#!/usr/bin/env python3
"""Conan recipe for libgda 6.0.0 — GNU Data Access library.

Build system: Meson + Vala
Dependencies: glib2, libxml2, sqlite3, iso-codes (system)
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class LibgdaConan(ConanFile):
    name = "libgda"
    version = "6.0.0"
    description = "GNU Data Access - database abstraction library"
    license = "LGPL-2.1+"
    homepage = "https://www.gnome.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "json": [True, False],
        "libsoup": [True, False],
        "sqlcipher": [True, False],
    }
    default_options = {
        "shared": True,
        "json": True,
        "libsoup": True,
        "sqlcipher": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib2/2.88.0")
        self.requires("libxml2/2.15.3.1")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.cpp.source.includedirs = ["include"]

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Force GNU ld instead of lld (lld has libxml2.so.16 loading issue on OHOS)
        if self.settings.os in ("Linux", "OHOS"):
            tc.extra_ldflags.append("-fuse-ld=/data/service/hnp/bin/ld")
        # Build options matching the meson_options.txt defaults
        tc.project_options["ui"] = "false"
        tc.project_options["help"] = "false"
        tc.project_options["experimental"] = "false"
        tc.project_options["tools"] = "false"
        tc.project_options["doc"] = "false"
        tc.project_options["examples"] = "false"
        tc.project_options["libsecret"] = "false"
        tc.project_options["graphviz"] = "false"
        tc.project_options["ldap"] = "false"
        tc.project_options["web"] = "false"
        tc.project_options["flatpak"] = "false"
        # Feature options (no trimming - enable what we can)
        tc.project_options["json"] = "true" if self.options.json else "false"
        tc.project_options["libsoup"] = "true" if self.options.libsoup else "false"
        tc.project_options["sqlcipher"] = "true" if self.options.sqlcipher else "false"
        # Library type
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        # Generate .pc files for conan dependencies
        pkg = PkgConfigDeps(self)
        pkg.generate()
        # Create missing .pc files for glib2 sub-libraries (gio, gobject, etc.)
        glib2_pc = Path("glib-2.0.pc")
        if glib2_pc.exists():
            glib2_content = glib2_pc.read_text()
            # Extract prefix and libdir from glib-2.0.pc
            prefix_val = ""
            for line in glib2_content.split("\n"):
                if line.startswith("prefix="):
                    prefix_val = line.split("=", 1)[1]
                elif line.startswith("libdir="):
                    libdir_val = line.split("=", 1)[1]
            if prefix_val:
                for libname in ["gio-2.0", "gobject-2.0", "gmodule-2.0", "gthread-2.0", "gmodule-no-export-2.0"]:
                    pc_file = Path(f"{libname}.pc")
                    if not pc_file.exists():
                        pc_content = f"""prefix={prefix_val}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/glib-2.0

Name: {libname}
Description: {libname} (part of glib2)
Version: 2.88.0
Requires: glib-2.0
Libs: -L"${{libdir}}" -l{libname}
Cflags: -I"${{includedir}}"
"""
                        pc_file.write_text(pc_content)
                        self.output.info(f"Created {libname}.pc")
        # Create a native file with build tools (vala, ar) that meson can't find via PATH on OHOS
        # Add vala and pkg-config to the cross file's [binaries] (for host machine)
        for fname in ["conan_meson_cross.ini", "conan_meson_native.ini"]:
            fpath = Path(fname)
            if fpath.exists():
                content = fpath.read_text()
                if "[binaries]" in content and "vala" not in content:
                    content = content.replace(
                        "[binaries]",
                        "[binaries]\nvala = '/storage/Users/currentUser/usr/local/bin/valac'\npkg-config = '/data/service/hnp/bin/pkg-config'\nglib-mkenums = '/storage/Users/currentUser/usr/local/bin/glib-mkenums'\nglib-genmarshal = '/storage/Users/currentUser/usr/local/bin/glib-genmarshal'\nglib-compile-resources = '/storage/Users/currentUser/usr/local/bin/glib-compile-resources'"
                    )
                    fpath.write_text(content)
                    self.output.info(f"Added vala+pkg-config to {fname}")
                # Fix needs_exe_wrapper - we CAN run binaries on OHOS (hmdfs is fine for ninja)
                if "needs_exe_wrapper" in content:
                    content = content.replace("needs_exe_wrapper = true", "needs_exe_wrapper = false")
                    fpath.write_text(content)
                    self.output.info(f"Set needs_exe_wrapper=false in {fname}")
                # Also append system PKG_CONFIG_PATH for json-glib, libsoup, etc.
                if "pkg_config_path" in content and "usr/local/lib/pkgconfig" not in content:
                    content = content.replace(
                        "pkg_config_path = '",
                        "pkg_config_path = '"  # keep original conan path first
                    )
                    # Append system paths at the end of the value
                    content = content.replace(
                        "pkg_config_path = '",
                        "pkg_config_path = '"
                    )
                    # Find the pkg_config_path line and append system paths
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if line.startswith("pkg_config_path = '") and line.endswith("'"):
                            # Insert system paths before the closing quote
                            lines[i] = line[:-1] + ":/storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/share/pkgconfig'"
                            break
                    content = "\n".join(lines)
                    fpath.write_text(content)
                    self.output.info(f"Appended system pkg-config path to {fname}")
                break
        # Create native file for build machine binaries (vala+pkg-config run on build machine)
        native_file = Path("conan_meson_native.ini")
        if not native_file.exists():
            native_content = """[binaries]
c = '/data/service/hnp/bin/clang'
cpp = '/data/service/hnp/bin/clang++'
vala = '/storage/Users/currentUser/usr/local/bin/valac'
ar = '/data/service/hnp/bin/llvm-ar'
ranlib = '/data/service/hnp/bin/llvm-ranlib'
pkg-config = '/data/service/hnp/bin/pkg-config'
glib-mkenums = '/storage/Users/currentUser/usr/local/bin/glib-mkenums'
glib-genmarshal = '/storage/Users/currentUser/usr/local/bin/glib-genmarshal'
glib-compile-resources = '/storage/Users/currentUser/usr/local/bin/glib-compile-resources'

[built-in options]
c_link_args = ['-fuse-ld=/data/service/hnp/bin/ld']
cpp_link_args = ['-fuse-ld=/data/service/hnp/bin/ld']

[buildenv]
PATH = '/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin'
"""
            native_file.write_text(native_content)
            self.output.info("Created native file with vala+pkg-config")

    def build(self):
        apply_conandata_patches(self)
        # Fix conanbuildenv to prioritize ~/usr/local/bin for Python3 glib tools
        # (system glib-mkenums has broken Perl shebang on OHOS)
        import glob
        for envfile in glob.glob(os.path.join(self.generators_folder, "conanbuildenv-*.sh")):
            with open(envfile) as f:
                content = f.read()
            if "/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin" in content:
                content = content.replace(
                    "/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin",
                    "/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin"
                )
                with open(envfile, 'w') as f:
                    f.write(content)
                self.output.info(f"Fixed PATH order in {os.path.basename(envfile)}")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libgda-6.0")
        self.cpp_info.libs = ["gda-6.0"]
        self.cpp_info.includedirs = ["include/libgda-6.0"]
        # pkg-config dependencies
        self.cpp_info.requires = ["glib2::glib-2.0", "glib2::gobject-2.0", "libxml2::libxml-2.0", "sqlite3::sqlite3"]
