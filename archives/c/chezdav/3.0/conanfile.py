#!/usr/bin/env python3
"""Conan recipe for chezdav 3.0 on HarmonyOS PC/aarch64.

The official phodav 3.0 source contains libphodav, spice-webdavd, and chezdav.
This application build omits the unrelated Spice daemon, retains only chezdav,
and statically links the bundled libphodav implementation into it. Optional
Avahi discovery is disabled; the core local/public WebDAV server remains
enabled and is exercised by both the upstream suite and test_package.
"""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class ChezdavConan(ConanFile):
    name = "chezdav"
    version = "3.0"
    description = "A small command-line WebDAV server from GNOME phodav"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/phodav"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib2/2.88.0")
        self.requires("libsoup3/3.6.5-r2")
        self.requires("libxml2/2.15.3.1")
        # libsoup3's published shared build requires the PIC zlib revision.
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = "build/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS workers may export llvm-* tool names that are not on PATH.
        # Resolve the actually runnable archive tools, matching the proven
        # glib2/libsoup3/gssdp Meson recipes in this repository.
        for variable in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(variable, None)
        tools = {
            name: shutil.which(name)
            for name in ("ar", "as", "strip", "nm", "ranlib")
        }
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                "Required build tools not in PATH: {}".format(", ".join(missing))
            )

        PkgConfigDeps(self).generate()

        toolchain = MesonToolchain(self)
        toolchain.ar = tools["ar"]
        toolchain.as_ = tools["as"]
        # Stripping invalidates HarmonyOS's embedded code signature.
        toolchain.strip = None
        toolchain.binaries["nm"] = tools["nm"]
        toolchain.binaries["ranlib"] = tools["ranlib"]
        # libphodav is private to the executable, so link it statically and do
        # not publish a second public library package under the chezdav name.
        toolchain.project_options["default_library"] = "static"
        toolchain.project_options["avahi"] = "disabled"
        toolchain.project_options["gtk_doc"] = "disabled"
        toolchain.project_options["systemdsystemunitdir"] = ""
        toolchain.project_options["udevrulesdir"] = ""

        # The published glib2 package is static while libsoup3 already embeds
        # its GLib/GObject copy. Keep the real GLib pkg-config Cflags (notably
        # gio-unix-2.0), but clear its Libs fields so the chezdav executable
        # resolves g_* symbols from libsoup3 instead of linking a second
        # GObject domain. This is the same single-copy fix used by gssdp/1.6.6.
        glib2 = self.dependencies.get("glib2")
        extra_pc = []
        if glib2 and glib2.package_folder:
            glib_root = glib2.package_folder
            original_pc_dir = os.path.join(glib_root, "lib", "pkgconfig")
            fixed_pc_dir = os.path.join(self.build_folder, "glib2-pc-fix")
            if os.path.isdir(original_pc_dir):
                os.makedirs(fixed_pc_dir, exist_ok=True)
                for filename in os.listdir(original_pc_dir):
                    if not filename.endswith(".pc"):
                        continue
                    source = os.path.join(original_pc_dir, filename)
                    destination = os.path.join(fixed_pc_dir, filename)
                    with open(source, encoding="utf-8") as handle:
                        content = handle.read()
                    content = re.sub(
                        r"^prefix=.*$", "prefix={}".format(glib_root),
                        content, count=1, flags=re.MULTILINE,
                    )
                    if filename in (
                        "glib-2.0.pc",
                        "gobject-2.0.pc",
                        "gio-2.0.pc",
                        "gio-unix-2.0.pc",
                        "gmodule-2.0.pc",
                        "gmodule-no-export-2.0.pc",
                        "gmodule-export-2.0.pc",
                        "gthread-2.0.pc",
                    ):
                        content = re.sub(
                            r"^Libs:.*$", "Libs: ", content, flags=re.MULTILINE
                        )
                        content = re.sub(
                            r"^Libs\.private:.*$", "Libs.private: ",
                            content, flags=re.MULTILINE,
                        )
                    with open(destination, "w", encoding="utf-8") as handle:
                        handle.write(content)
                extra_pc.append(fixed_pc_dir)

        if extra_pc:
            toolchain.pkg_config_path = os.pathsep.join(
                [toolchain.pkg_config_path] + extra_pc
            )
        toolchain.generate()

        generated_glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(generated_glib_pc):
            with open(generated_glib_pc, encoding="utf-8") as handle:
                content = handle.read()
            content = re.sub(
                r"^Libs:.*$", "Libs: ", content, flags=re.MULTILINE
            )
            content = re.sub(
                r"^Libs\.private:.*$", "Libs.private: ",
                content, flags=re.MULTILINE,
            )
            with open(generated_glib_pc, "w", encoding="utf-8") as handle:
                handle.write(content)

        # libsoup3-r2's generated module flattens its static GLib dependency
        # into Libs even though libsoup itself is shared and exports those
        # symbols. Linking that line verbatim would put another GLib/GObject
        # copy in chezdav. Keep only libsoup's own shared object; Requires still
        # supplies its non-GLib runtime dependencies.
        generated_soup_pc = os.path.join(
            self.generators_folder, "libsoup-3.0.pc"
        )
        if os.path.isfile(generated_soup_pc):
            with open(generated_soup_pc, encoding="utf-8") as handle:
                content = handle.read()
            content = re.sub(
                r"^Libs:.*$",
                'Libs: -L"${libdir}" -lsoup-3.0',
                content,
                flags=re.MULTILINE,
            )
            with open(generated_soup_pc, "w", encoding="utf-8") as handle:
                handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if cross_building(self):
            self.output.info(
                "cross-building: upstream HarmonyOS runtime tests are deferred"
            )
            return

        # The upstream Meson test expands to 18 localhost WebDAV cases.
        if hasattr(os, "uname") and os.uname().sysname in ("OHOS", "HarmonyOS"):
            self.run(
                'meson test -v -C "{}" --no-rebuild '
                "--timeout-multiplier=16".format(self.build_folder)
            )
        else:
            meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()

        # Meson strips build-tree RPATH metadata while installing, which can
        # both remove the dependency lookup path and invalidate the HarmonyOS
        # code signature. Preserve the original linked executable instead.
        built_chezdav = os.path.join(self.build_folder, "bin", "chezdav")
        packaged_chezdav = os.path.join(self.package_folder, "bin", "chezdav")
        if os.path.isfile(built_chezdav):
            shutil.copy2(built_chezdav, packaged_chezdav)

        # The adaptation patch omits the separate Spice daemon. Keep this
        # defensive cleanup so a future upstream build-layout change cannot
        # accidentally publish it from either possible install location.
        for directory in ("bin", "sbin"):
            unwanted_binary = os.path.join(
                self.package_folder, directory, "spice-webdavd"
            )
            if os.path.exists(unwanted_binary):
                os.remove(unwanted_binary)
        for directory in (
            "include", "lib", "lib64", "sbin", "share", "etc"
        ):
            rmdir(self, os.path.join(self.package_folder, directory))

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        binary_dir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", binary_dir)
        self.runenv_info.prepend_path("PATH", binary_dir)
