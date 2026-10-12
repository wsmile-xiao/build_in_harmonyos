#!/usr/bin/env python3
"""Conan recipe for libnice 0.1.21 on HarmonyOS PC aarch64."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.meson import Meson, MesonToolchain


class LibNiceConan(ConanFile):
    name = "libnice"
    version = "0.1.21"
    description = "GLib-based ICE library with STUN client and server tools"
    license = "LGPL-2.1-or-later"
    homepage = "https://nice.freedesktop.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    generators = "PkgConfigDeps"
    exports_sources = "test_package/test_ohos_stun_loopback.sh"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Historical HarmonyOS device builds require shared GLib; static GLib
        # carries G_INTL_STATIC_COMPILATION and breaks libnice's link contract.
        self.requires(
            "glib/2.84.0.1.1",
            options={"shared": True},
        )
        self.requires("openssl/1.1.1w")

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("libnice/0.1.21 is supported on OHOS only")
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("libnice/0.1.21 supports OHOS aarch64 only")

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _inject_meson_binaries(self):
        # MesonToolchain on OHOS may emit the versioned name llvm-ar-15, while
        # the device SDK provides llvm-ar in the selected compiler's bindir.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c") or ""
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if bindir:
            if not ar:
                ar = next(
                    (
                        os.path.join(bindir, name)
                        for name in ("llvm-ar", "ar")
                        if os.path.isfile(os.path.join(bindir, name))
                    ),
                    None,
                )
            if not ranlib:
                ranlib = next(
                    (
                        os.path.join(bindir, name)
                        for name in ("llvm-ranlib", "ranlib")
                        if os.path.isfile(os.path.join(bindir, name))
                    ),
                    None,
                )

        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")

        for name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, name)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as stream:
                content = stream.read()
            if "[binaries]\n" not in content:
                continue
            binaries = []
            if ar and "\nar =" not in content:
                binaries.append("ar = '{}'".format(ar))
            if ranlib and "\nranlib =" not in content:
                binaries.append("ranlib = '{}'".format(ranlib))
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                binaries.append("pkg-config = '{}'".format(pkg_config))
            if binaries:
                content = content.replace(
                    "[binaries]\n",
                    "[binaries]\n{}\n".format("\n".join(binaries)),
                    1,
                )
                with open(path, "w", encoding="utf-8") as stream:
                    stream.write(content)

    def _restore_glib_mkenums_variable(self):
        # PkgConfigDeps omits GLib's upstream glib_mkenums variable, which
        # Meson's gnome.mkenums() requires to locate the packaged tool.
        path = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(path):
            return
        with open(path, encoding="utf-8") as stream:
            content = stream.read()
        if any(line.startswith("glib_mkenums=") for line in content.splitlines()):
            return
        bindir_line = next(
            (line for line in content.splitlines() if line.startswith("bindir=")),
            None,
        )
        if bindir_line:
            content = content.replace(
                bindir_line,
                bindir_line + "\nglib_mkenums=${bindir}/glib-mkenums",
                1,
            )
            with open(path, "w", encoding="utf-8") as stream:
                stream.write(content)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["crypto-library"] = "openssl"
        tc.project_options["gstreamer"] = "disabled"
        tc.project_options["gupnp"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["gtk_doc"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "enabled"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_binaries()
        self._restore_glib_mkenums_variable()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

        # Run the complete upstream Meson suite when binaries can run natively.
        # In particular, the native HarmonyOS aarch64 CI executes every test
        # registered by upstream; cross builds cannot execute those binaries.
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() because target binaries are not runnable"
            )
        elif str(self.settings.os) == "OHOS" and os.uname().sysname in (
            "OHOS",
            "HarmonyOS",
        ):
            self.run(
                'meson test -v -C "{}" --timeout-multiplier=16 --no-rebuild'.format(
                    self.build_folder
                )
            )
            shell = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash"
            )
            script = os.path.join(
                self.export_sources_folder,
                "test_package",
                "test_ohos_stun_loopback.sh",
            )
            self.run(
                shlex.join(
                    [
                        shell,
                        script,
                        "stun/tools/stund",
                        "stun/tools/stunbdc",
                    ]
                ),
                cwd=self.build_folder,
            )
        else:
            meson.test()

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.libs = ["nice"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "glib::gthread-2.0",
            "openssl::openssl",
        ]
        self.cpp_info.set_property("cmake_file_name", "libnice")
        self.cpp_info.set_property("cmake_target_name", "libnice::libnice")
        self.cpp_info.set_property("pkg_config_name", "nice")
