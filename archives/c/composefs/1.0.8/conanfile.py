#!/usr/bin/env python3
"""Conan recipe — composefs 1.0.8 (Meson).

composefs: file system images for containers, backed by fs-verity and EROFS.
HarmonyOS PC adaptation notes:
  - libcrypto (openssl) is a hard build dependency (fs-verity digest code).
  - fuse3 is optional upstream but not published on ohpcd -> -Dfuse=disabled.
  - Patches 0001..0003 adapt to OHOS HMFS semantics (see conandata.yml).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class ComposefsConan(ConanFile):
    name = "composefs"
    version = "1.0.8"
    description = "composefs: file system images backed by fs-verity and EROFS"
    license = "GPL-2.0-or-later OR Apache-2.0"
    homepage = "https://github.com/containers/composefs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    generators = "PkgConfigDeps"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libcrypto is required by composefs (fs-verity digest computation);
        # openssl/4.0.1 is published on ohpcd (verified via conan download).
        self.requires("openssl/4.0.1")

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders here
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names that are not
        # on PATH; pin the real tools by absolute path and drop broken env
        # values (same fix as glib-networking/glib2 recipes).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}")
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # Optional upstream features not available on OHOS: fuse3 is not
        # published on ohpcd; man pages need go-md2man. Disable both.
        tc.project_options["fuse"] = "disabled"
        tc.project_options["man"] = "disabled"
        # R26: default static linkage (avoids runtime DT_NEEDED on
        # libcomposefs.so.1 which is not on the consumer's loader path).
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # composefs's meson.build does dependency('libcrypto'), but openssl's
        # PkgConfigDeps only emits openssl-crypto.pc / openssl-ssl.pc /
        # openssl.pc. Emit a libcrypto.pc shim pointing at the openssl package
        # so meson resolves libcrypto through pkg-config.
        if self.dependencies.get("openssl"):
            openssl_pkg = self.dependencies["openssl"].package_folder
            pc_dir = os.path.join(self.build_folder, "libcrypto-pc")
            os.makedirs(pc_dir, exist_ok=True)
            pc_text = (
                "prefix=" + openssl_pkg + "\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "\n"
                "Name: libcrypto\n"
                "Description: OpenSSL crypto library (conan shim)\n"
                "Version: 4.0.1\n"
                "Libs: -L${libdir} -lcrypto -ldl -lpthread\n"
                "Cflags: -I${includedir}\n"
            )
            with open(os.path.join(pc_dir, "libcrypto.pc"), "w",
                      encoding="utf-8") as fh:
                fh.write(pc_text)
            tc.pkg_config_path = os.pathsep.join([pc_dir, tc.pkg_config_path])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["composefs"]
        # composefs builds both_libraries() unconditionally; the consumer
        # links the shared libcomposefs.so.1, so put the package lib dir on
        # the consumer's loader path (conanrun env applied by test()/run).
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                      os.path.join(self.package_folder, "lib"))
