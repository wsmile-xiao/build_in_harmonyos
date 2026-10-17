#!/usr/bin/env python3
"""Conan recipe — webp-pixbuf-loader 0.2.7 (Meson)

A GDK Pixbuf loader module for WebP images.  Built with meson,
depends on libwebp and gdk-pixbuf.

The module exports fill_info() and fill_vtable() as G_MODULE_EXPORT
entry points, loaded at runtime by gdk-pixbuf's query-loaders.
"""
import glob
import os
import shlex

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class WebpPixbufLoaderConan(ConanFile):
    name = "webp-pixbuf-loader"
    version = "0.2.7"
    description = "WebP GDK Pixbuf Loader library"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/aruiz/webp-pixbuf-loader"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libwebp/1.6.0")
        self.requires(
            "gdk-pixbuf/2.44.6",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        try:
            get(self, **sources, strip_root=True)
        except Exception as error:
            if not mirror_url:
                raise
            self.output.warning(
                f"Primary source failed ({error}), trying mirror"
            )
            get(
                self,
                url=mirror_url,
                sha256=sources["sha256"],
                strip_root=True,
            )

    def generate(self):
        PkgConfigDeps(self).generate()
        self._create_webp_subpkg_config()
        tc = MesonToolchain(self)
        tc.project_options.update(
            {
                "wrap_mode": "nodownload",
                "default_library": "shared" if self.options.shared else "static",
                "gdk_pixbuf_moduledir": os.path.join(
                    self.package_folder, "lib", "gdk-pixbuf-2.0", "loaders"
                ),
                "update_cache": False,
            }
        )
        tc.generate()

    def _create_webp_subpkg_config(self):
        """Create libwebpdemux.pc and libwebpmux.pc.

        The libwebp conan package exposes only 'webp' and 'sharpyuv'
        through cpp_info, but meson looks for libwebpdemux and libwebpmux
        as separate pkg-config dependencies.  The cmake build of libwebp
        installs these libraries; we create the missing .pc files pointing
        to them.
        """
        libwebp = self.dependencies["libwebp"]
        libdir = os.path.join(libwebp.package_folder, "lib")
        includedir = os.path.join(libwebp.package_folder, "include")
        webp_version = str(libwebp.ref.version)

        for name, lib in [
            ("libwebpdemux", "webpdemux"),
            ("libwebpmux", "webpmux"),
        ]:
            pc_content = (
                f"prefix={libwebp.package_folder}\n"
                f"exec_prefix=${{prefix}}\n"
                f"libdir=${{exec_prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n"
                f"\n"
                f"Name: {name}\n"
                f"Description: WebP {lib} library\n"
                f"Version: {webp_version}\n"
                f"Libs: -L${{libdir}} -l{lib}\n"
                f"Cflags: -I${{includedir}}\n"
            )
            pc_path = os.path.join(self.generators_folder, f"{name}.pc")
            with open(pc_path, "w", encoding="utf-8") as f:
                f.write(pc_content)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.compile()

    def package(self):
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.install()
        if self.settings.os == "OHOS":
            self._sign_shared_module()

    def _build_environment(self):
        env = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    def _sign_shared_module(self):
        """Sign ELF shared module on HarmonyOS (R7 safe-execution)."""
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip signing")
            return
        libdir = os.path.join(self.package_folder, "lib")
        patterns = [
            os.path.join(libdir, "**", "*.so"),
            os.path.join(libdir, "**", "*.so.*"),
        ]
        candidates = []
        for pattern in patterns:
            candidates.extend(glob.glob(pattern, recursive=True))
        for binary in sorted(set(candidates)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            self.run(
                shlex.join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        binary,
                        "-outFile",
                        binary,
                        "-selfSign",
                        "1",
                    ]
                )
            )

    def package_info(self):
        self.cpp_info.libs = ["pixbufloader-webp"]
        self.cpp_info.requires = [
            "libwebp::libwebp",
            "gdk-pixbuf::gdk-pixbuf",
        ]
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
