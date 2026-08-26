#!/usr/bin/env python3
"""Conan recipe — libzbar 0.23.93 (Autotools: configure + make).

ZBar bar code reader — library + command-line tools (zbarimg, zbarcam).
Adapted for HarmonyOS PC (arm64) with ImageMagick support enabled.

R26: libzbar is not a system-name library; default dynamic linking.
R32: settings.os must check in ("Linux", "OHOS").
R38: Produces executables (zbarimg, zbarcam) — commands.json declared.

The GitHub tarball lacks autotools-generated files (configure, config.guess,
etc.); build() runs `autoreconf -fi` to regenerate them, then applies
HarmonyOS-specific fixes inline (generated files cannot be conandata patches).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, save, load
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class LibzbarConan(ConanFile):
    name = "libzbar"
    version = "0.23.93"
    description = "ZBar bar code reader — library and command-line tools"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/mchehab/zbar"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def build_requirements(self):
        # GitHub tag archive has no generated configure; autoreconf -fi
        # needs automake (aclocal/automake), libtool (libtoolize),
        # gettext (autopoint/AM_GNU_GETTEXT macros).
        # autoconf and m4 are provided by the SDK (/data/service/hnp/bin).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")
        self.tool_requires("gettext/0.22.5.1")

    def requirements(self):
        self.requires("dbus/1.14.10")
        self.requires("imagemagick/7.1.2.29")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libzbar is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)

    def generate(self):
        # ── Pkg-config shims ──────────────────────────────────────
        # dbus Conan package has no dbus-1.pc; ImageMagick .pc files
        # have prefix="/" (broken). Generate correct shims.
        pc_dir = os.path.join(self.build_folder, "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)

        # dbus-1.pc shim
        dbus = self.dependencies["dbus"]
        with open(os.path.join(pc_dir, "dbus-1.pc"), "w") as f:
            f.write(f"prefix={dbus.package_folder}\n")
            f.write("exec_prefix=${prefix}\n")
            f.write("libdir=${prefix}/lib\n")
            f.write("includedir=${prefix}/include\n")
            f.write("Name: dbus-1\n")
            f.write("Description: D-BUS message bus\n")
            f.write("Version: 1.14.10\n")
            f.write("Libs: -L${libdir} -ldbus-1\n")
            f.write("Cflags: -I${includedir}/dbus-1.0\n")

        # MagickWand.pc shim (fix broken prefix="/")
        im = self.dependencies["imagemagick"]
        with open(os.path.join(pc_dir, "MagickWand.pc"), "w") as f:
            f.write(f"prefix={im.package_folder}\n")
            f.write("exec_prefix=${prefix}\n")
            f.write("libdir=${prefix}/lib\n")
            f.write("includedir=${prefix}/include/ImageMagick-7\n")
            f.write("Name: MagickWand\n")
            f.write("Description: MagickWand - C API for ImageMagick\n")
            f.write("Version: 7.1.2\n")
            f.write("Requires: MagickCore-7.Q16HDRI\n")
            f.write("Cflags: -I${includedir}"
                    " -DMAGICKCORE_HDRI_ENABLE=1"
                    " -DMAGICKCORE_QUANTUM_DEPTH=16"
                    " -DMAGICKCORE_CHANNEL_MASK_DEPTH=32\n")
            f.write("Libs: -L${libdir} -lMagickWand-7.Q16HDRI\n")

        # MagickCore-7.Q16HDRI.pc shim
        with open(os.path.join(pc_dir, "MagickCore-7.Q16HDRI.pc"), "w") as f:
            f.write(f"prefix={im.package_folder}\n")
            f.write("exec_prefix=${prefix}\n")
            f.write("libdir=${prefix}/lib\n")
            f.write("includedir=${prefix}/include/ImageMagick-7\n")
            f.write("Name: MagickCore-7.Q16HDRI\n")
            f.write("Description: MagickCore - C API for ImageMagick\n")
            f.write("Version: 7.1.2\n")
            f.write("Cflags: -I${includedir}"
                    " -DMAGICKCORE_HDRI_ENABLE=1"
                    " -DMAGICKCORE_QUANTUM_DEPTH=16"
                    " -DMAGICKCORE_CHANNEL_MASK_DEPTH=32\n")
            f.write("Libs: -L${libdir} -lMagickCore-7.Q16HDRI\n")

        # ── Environment for autotools tool_requires ───────────────
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", pc_dir)

        # gettext: fix autopoint hardcoded prefix (same as avahi recipe)
        gettext_pkg = self.dependencies.build["gettext"].package_folder
        gettext_datadir = os.path.join(gettext_pkg, "share", "gettext")
        if os.path.isdir(gettext_datadir):
            env.define("gettext_datadir", gettext_datadir)
        gettext_aclocal = os.path.join(gettext_pkg, "share", "aclocal")
        if os.path.isdir(gettext_aclocal):
            env.prepend_path("ACLOCAL_PATH", gettext_aclocal)

        # libtool: fix libtoolize hardcoded prefix via _lt_pkgdatadir
        libtool_pkg = self.dependencies.build["libtool"].package_folder
        lt_share = os.path.join(libtool_pkg, "share", "libtool")
        if os.path.isdir(os.path.join(lt_share, "build-aux")):
            env.define("_lt_pkgdatadir", lt_share)
        lt_aclocal = os.path.join(libtool_pkg, "share", "aclocal")
        if os.path.isdir(lt_aclocal):
            env.prepend_path("ACLOCAL_PATH", lt_aclocal)

        env.vars(self).save_script("libzbar_env")

        # ── AutotoolsToolchain ─────────────────────────────────────
        tc = AutotoolsToolchain(self)
        # Disable bindings not available on OHOS (not cropping core functionality)
        tc.configure_args.append("--with-gtk=no")
        tc.configure_args.append("--with-qt=no")
        tc.configure_args.append("--with-java=no")
        tc.configure_args.append("--with-python=no")
        # ImageMagick is explicitly enabled (zbarimg tool requires it)
        tc.generate()

    def _fix_config_guess(self, src):
        """Fix config.guess for HarmonyOS platform recognition (E007)."""
        path = os.path.join(src, "config", "config.guess")
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace(
            "Linux|GNU|GNU/*)",
            "Linux|GNU|GNU/*|HarmonyOS)"
        )
        # Add aarch64:HarmonyOS pattern (after aarch64:Linux)
        content = content.replace(
            "    aarch64:Linux:*:*)\n\tset_cc_for_build",
            "    aarch64:HarmonyOS:*:*)\n\tGUESS=$UNAME_MACHINE-unknown-linux-musl\n\t;;\n    aarch64:Linux:*:*)\n\tset_cc_for_build"
        )
        save(self, path, content)

    def _fix_config_sub(self, src):
        """Fix config.sub to accept HarmonyOS as an OS (E007)."""
        path = os.path.join(src, "config", "config.sub")
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace(
            " | linux-gnu*",
            " | linux-gnu* | harmonyos*"
        )
        save(self, path, content)

    def _fix_configure_umask(self, src):
        """Remove umask 077 from configure for HMDFS compatibility.

        On HarmonyOS HMDFS, mktemp -d with umask 077 creates directories
        that cannot be written to, causing 'Permission denied' errors.
        Also add chmod 755 after temp dir creation as a safety net.
        """
        path = os.path.join(src, "configure")
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        content = content.replace("umask 077", "")
        # Add chmod after temp dir creation
        content = content.replace(
            'ac_tmp=$tmp',
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null'
        )
        save(self, path, content)

    def _fix_config_status(self, src):
        """Fix config.status: remove umask 077 for temp dir (HMDFS)."""
        path = os.path.join(src, "config.status")
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        content = content.replace(
            "ac_tmp=$tmp",
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null'
        )
        save(self, path, content)

    def _fix_imagemagick_la_files(self):
        """Fix ImageMagick .la files with broken prefix='//' paths.

        The ImageMagick Conan package was built with prefix='/', so .la
        files contain hardcoded '//lib/...' paths. Fix libdir and
        dependency_libs to use the actual package folder.
        """
        im = self.dependencies["imagemagick"]
        im_lib = os.path.join(im.package_folder, "lib")
        for la_name in os.listdir(im_lib) if os.path.isdir(im_lib) else []:
            if not la_name.endswith(".la"):
                continue
            la_path = os.path.join(im_lib, la_name)
            if not os.path.exists(la_path):
                continue
            content = load(self, la_path)
            # Fix libdir from //lib to actual path
            content = content.replace("libdir='//lib'", f"libdir='{im_lib}'")
            # Fix dependency_libs paths from //lib/ to actual path
            content = content.replace("//lib/", f"{im_lib}/")
            save(self, la_path, content)

    def build(self):
        # GitHub tarball lacks autotools-generated files; regenerate
        self.run("autoreconf -fi", cwd=self.source_folder)

        # Fix generated files for HarmonyOS (applied after autoreconf)
        self._fix_config_guess(self.source_folder)
        self._fix_config_sub(self.source_folder)
        self._fix_configure_umask(self.source_folder)
        self._fix_imagemagick_la_files()

        autotools = Autotools(self)
        autotools.configure()

        # Fix config.status (generated by configure, not a source patch)
        # The umask fix in _fix_configure_umask prevents the HMDFS issue,
        # but config.status is generated by configure so apply fix too.
        self._fix_config_status(self.source_folder)

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["zbar"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
