#!/usr/bin/env python3
"""Conan recipe — libsecret 0.20.5 (Meson).

GObject-based secret storage client library (freedesktop.org Secrets API).
Builds the C library + libegg; introspection/vapi/tpm2 disabled (no tss2/gjs in CI).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class LibsecretConan(ConanFile):
    name = "libsecret"
    version = "0.20.5"
    description = "GObject based library for accessing the Secret Service API"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libsecret"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "gcrypt": [True, False]}
    default_options = {"shared": True, "fPIC": True, "gcrypt": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.3")
        # glib-2.0.pc Requires: proxy-libintl + libpcre2-8; meson resolves the
        # .pc chain via pkg-config, so both must be direct dependencies too.
        self.requires("proxy-libintl/0.5")
        self.requires("pcre2/10.47")
        # gobject-2.0.pc Requires: libffi
        self.requires("libffi/3.5.2")
        # gio-2.0.pc Requires: zlib
        self.requires("zlib/1.3.2")
        # libgcrypt.pc Requires.private: gpg-error; gcrypt.h includes
        # gpg-error.h unconditionally, so expose libgpg-error directly.
        self.requires("libgpg-error/1.55")
        if self.options.gcrypt:
            self.requires("libgcrypt/1.12.2")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Ensure AR points to a discoverable path for meson
        ar_path = shutil.which("llvm-ar") or shutil.which("ar")
        if ar_path:
            os.environ["AR"] = ar_path
        # Expose glib/libgcrypt via pkg-config so meson finds glib-2.0 etc.
        PkgConfigDeps(self).generate()
        # glib package ships its own full set of .pc (incl. gio-unix-2.0);
        # copy the .pc files into the generators folder so meson resolves
        # every glib component, rewriting their "prefix=/" to the real
        # package folder (upstream ships them with a root prefix).
        import re as _re
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            src_pc = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(src_pc):
                real_prefix = dep.package_folder.replace(os.sep, "/")
                for pc_name in os.listdir(src_pc):
                    if not pc_name.endswith(".pc"):
                        continue
                    with open(os.path.join(src_pc, pc_name), encoding="utf-8") as handle:
                        content = handle.read()
                    rewritten = _re.sub(
                        r"^prefix=.*$", "prefix={}".format(real_prefix),
                        content, flags=_re.MULTILINE,
                    )
                    with open(
                        os.path.join(self.generators_folder, pc_name),
                        "w", encoding="utf-8", newline="\n",
                    ) as handle:
                        handle.write(rewritten)
        # libgcrypt.pc only lists gpg-error under Requires.private, so
        # pkg-config does not propagate its Cflags — gcrypt.h includes
        # gpg-error.h unconditionally. Append the gpg-error include dir.
        gp_err_dep = self.dependencies.get("libgpg-error")
        libgcrypt_pc = os.path.join(self.generators_folder, "libgcrypt.pc")
        if gp_err_dep and gp_err_dep.package_folder and os.path.isfile(libgcrypt_pc):
            gp_err_inc = os.path.join(gp_err_dep.package_folder, "include")
            with open(libgcrypt_pc, encoding="utf-8") as handle:
                content = handle.read()
            if "-I{}".format(gp_err_inc) not in content:
                rewritten = _re.sub(
                    r"^(Cflags:.*)$",
                    r"\1 -I{}".format(gp_err_inc),
                    content,
                    count=1,
                    flags=_re.MULTILINE,
                )
                with open(libgcrypt_pc, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(rewritten)
        # proxy-libintl ships only libintl.a/libintl.h (no .pc), but
        # glib-2.0.pc has "Requires: proxy-libintl" — synthesize it.
        intl_dep = self.dependencies.get("proxy-libintl")
        if intl_dep and intl_dep.package_folder:
            intl_prefix = intl_dep.package_folder.replace(os.sep, "/")
            with open(
                os.path.join(self.generators_folder, "proxy-libintl.pc"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                handle.write(
                    "prefix={}\n".format(intl_prefix)
                    + "libdir=${prefix}/lib\n"
                    + "includedir=${prefix}/include\n\n"
                    + "Name: proxy-libintl\n"
                    + "Description: Minimal gettext-compatible proxy library\n"
                    + "Version: 0.5\n"
                    + "Libs: -L${libdir} -lintl\n"
                    + "Cflags: -I${includedir}\n"
                )
        # PkgConfigDeps-generated glib*.pc files carry broken tool variables
        # ("//bin/gdbus-codegen", "//bin/glib-mkenums"); repoint each at the
        # real script inside the resolved glib package.
        glib_dep = self.dependencies.get("glib")
        if glib_dep and glib_dep.package_folder:
            tool_scripts = {
                "gdbus_codegen": "gdbus-codegen",
                "glib_mkenums": "glib-mkenums",
                "glib_genmarshal": "glib-genmarshal",
                "gdbus": "gdbus",
            }
            import re as _re
            for pc_file in os.listdir(self.generators_folder):
                if not pc_file.endswith(".pc"):
                    continue
                pc_path = os.path.join(self.generators_folder, pc_file)
                with open(pc_path, encoding="utf-8") as handle:
                    content = handle.read()
                rewritten = content
                for var, script in tool_scripts.items():
                    real = os.path.join(glib_dep.package_folder, "bin", script)
                    if os.path.isfile(real):
                        rewritten = _re.sub(
                            r"^{}=.*$".format(var),
                            "{}={}".format(var, real),
                            rewritten,
                            flags=_re.MULTILINE,
                        )
                if rewritten != content:
                    with open(pc_path, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(rewritten)
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        # R49: keep everything inside the Conan build folder (private prefix)
        tc.project_options["introspection"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["gcrypt"] = "true" if self.options.gcrypt else "false"
        tc.project_options["tpm2"] = "false"
        tc.project_options["bash_completion"] = "disabled"
        tc.project_options["manpage"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.generate()

    def build(self):
        # Ensure meson build tool is available (not pre-installed on all CI workers)
        if not shutil.which("meson"):
            self.run(f"{sys.executable} -m pip install --user meson")
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        # libegg is an internal static lib linked into libsecret-1 and is
        # not installed by meson; consumers only need secret-1.
        self.cpp_info.libs = ["secret-1"]
        self.cpp_info.includedirs = ["include/libsecret-1"]
        if self.options.shared and str(self.settings.os) in ("Linux", "OHOS"):
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
            )
        # Propagate dependency targets so consumers get glib include/link paths
        # (cpp_info.requires uses the recipe name, not cmake_file_name)
        self.cpp_info.requires = [
            "glib::glib", "glib::gobject", "glib::gio", "glib::gmodule",
            "glib::gthread", "proxy-libintl::proxy-libintl",
            # direct deps required to be referenced (pkg-config chain carriers)
            "pcre2::pcre2", "libffi::libffi", "zlib::zlib", "libgpg-error::libgpg-error",
        ]
        if self.options.gcrypt:
            self.cpp_info.requires.append("libgcrypt::libgcrypt")
