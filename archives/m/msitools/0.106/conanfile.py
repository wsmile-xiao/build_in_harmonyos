#!/usr/bin/env python3
"""Conan recipe — msitools 0.106 (Meson build).

Requires: glib, libgsf, libxml2
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class MsitoolsConan(ConanFile):
    name = "msitools"
    version = "0.106"
    description = "A set of programs to inspect and build Windows Installer (.MSI) files"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/msitools"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"msitools only supports Linux and OHOS, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("libgsf/1.14.58")
        self.requires("libxml2/2.15.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        mb_path = os.path.join(self.source_folder, "meson.build")
        lmb_path = os.path.join(self.source_folder, "libmsi", "meson.build")
        if os.path.exists(mb_path):
            with open(mb_path) as f:
                content = f.read()
            # (1) Remove 'vala' from project() languages (valac not available)
            content = content.replace("'c', 'vala',", "'c',")
            # (2) Conan generates libgsf-1.pc (matches upstream pkg-config name)
            # (3) Official tarball makes libgcab unconditional, but it's not in
            #     conan cache. Restore the introspection guard around libgcab.
            old_gcab = "libgcab = dependency('libgcab-1.0', version: '>= 0.1.10')"
            new_gcab = (
                "if get_option('introspection')\n"
                "  libgcab = dependency('libgcab-1.0', version: '>= 0.1.10')\n"
                "endif"
            )
            content = content.replace(old_gcab, new_gcab)
            with open(mb_path, "w") as f:
                f.write(content)
        # (4) Official tarball uses shared_library; switch to static_library (R26)
        if os.path.exists(lmb_path):
            with open(lmb_path) as f:
                lcontent = f.read()
            # shared_library → static_library and drop version arg (not supported)
            lcontent = lcontent.replace(
                "libmsi = shared_library('msi-1.0',",
                "libmsi = static_library('msi-1.0',"
            )
            lcontent = lcontent.replace("  version: '0.0.0',\n", "")
            with open(lmb_path, "w") as f:
                f.write(lcontent)

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.generate()
        tc = MesonToolchain(self)
        # R26: Static linking for the library to avoid system path pollution
        tc.project_options["default_library"] = "static"
        # Disable introspection (requires valac + libgcab) to skip Vala compilation
        tc.project_options["introspection"] = False
        # Find libintl for static linking (libgsf depends on g_libintl_bindtextdomain)
        import glob
        for intl_path in [
            os.path.join(os.path.dirname(p), "lib")
            for p in glob.glob("/data/service/hnp/gettext.org/*/lib/libintl.*")
        ]:
            intl_dir = os.path.dirname(intl_path)
            if os.path.isdir(intl_dir):
                tc.c_link_args.append(f"-L{intl_dir}")
                tc.c_link_args.append("-lintl")
                break
        # lld enables --no-allow-shlib-undefined by default, which fails
        # when libgsf.so has transitive deps on libintl not in the link line
        tc.c_link_args.append("-Wl,--allow-shlib-undefined")
        tc.generate()
        # Set up build environment: LD_LIBRARY_PATH for Meson sanity check
        # (Meson runs compiled test binaries that need to find shared libs like
        # libintl.so.8 from glib). Use dynamic lookup, no hardcoded paths.
        env = Environment()
        try:
            glib_dep = self.dependencies["glib"]
            glib_lib = os.path.join(glib_dep.package_folder, "lib")
            if os.path.isdir(glib_lib):
                env.append("LD_LIBRARY_PATH", glib_lib)
        except (KeyError, AttributeError):
            pass
        # Override AR with dynamically located llvm-ar (not hardcoded path)
        ar_path = shutil.which("llvm-ar")
        if ar_path:
            env.define("AR", ar_path)
        # lld enables --no-allow-shlib-undefined by default; override it.
        # Also add libintl path for libgsf's transitive dependency.
        ldflags = ["-Wl,--allow-shlib-undefined"]
        import glob as _glob
        for intl_path in _glob.glob("/data/service/hnp/gettext.org/*/lib/libintl.*"):
            intl_dir = os.path.dirname(intl_path)
            ldflags.append(f"-L{intl_dir}")
            ldflags.append("-lintl")
            break
        env.define("LDFLAGS", " ".join(ldflags))

        # Create glib-mkenums wrapper with correct perl shebang.
        # The system glib-mkenums has #!/usr/bin/perl but /usr/bin/perl
        # doesn't exist on OHOS (perl is in /data/service/hnp/bin/).
        perl_bin = shutil.which("perl")
        if perl_bin:
            wrapper_dir = os.path.join(self.build_folder, "bin_wrappers")
            os.makedirs(wrapper_dir, exist_ok=True)
            for tool in ("glib-mkenums", "glib-genmarshal"):
                src = shutil.which(tool)
                if src:
                    wrapper = os.path.join(wrapper_dir, tool)
                    with open(wrapper, "w") as f:
                        f.write("#!/bin/sh\n")
                        f.write(f'exec {perl_bin} "{src}" "$@"\n')
                    os.chmod(wrapper, 0o755)
            env.prepend("PATH", wrapper_dir)

        env.vars(self).save_script("msitools_env")
        # gnome.mkenums() needs glib_mkenums and glib_genmarshal from pc file.
        # Conan's generated .pc lacks these variables, so we create a wrapper.
        pc_dir = os.path.join(self.build_folder, "conan")
        glib_pc = os.path.join(pc_dir, "glib-2.0.pc")
        if os.path.exists(glib_pc) and perl_bin:
            wrapper_dir = os.path.join(self.build_folder, "bin_wrappers")
            mkenums_wrapper = os.path.join(wrapper_dir, "glib-mkenums")
            genmarshal_wrapper = os.path.join(wrapper_dir, "glib-genmarshal")
            with open(glib_pc) as f:
                content = f.read()
            extra_vars = (
                "\n"
                f"glib_genmarshal={genmarshal_wrapper}\n"
                f"glib_mkenums={mkenums_wrapper}\n"
            )
            if extra_vars.strip() not in content:
                with open(glib_pc, "a") as f:
                    f.write(extra_vars)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["msi-1.0"]
