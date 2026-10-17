import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibqrtrConan(ConanFile):
    name = "libqrtr"
    version = "1.4.0"
    description = "GLib-based library for the Qualcomm QRTR bus"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.freedesktop.org/mobile-broadband/libqrtr-glib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("glib/2.88.0", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        # glib/2.88.0 exports gio-2.0 but lacks the Unix-header module needed
        # by upstream's dependency('gio-unix-2.0') check.
        glib = self.dependencies["glib"]
        gio_unix_pc = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        with open(gio_unix_pc, "w", encoding="utf-8") as pc:
            pc.write(
                f"prefix={glib.package_folder}\n"
                "includedir=${prefix}/include\n\n"
                "Name: gio-unix-2.0\n"
                "Description: Unix-specific headers for GIO\n"
                "Version: 2.88.0\n"
                "Requires: gio-2.0\n"
                "Cflags: -I${includedir}/gio-unix-2.0\n"
            )
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "static"
        tc.project_options["introspection"] = False
        tc.project_options["gtk_doc"] = False

        # Meson derives the archiver name ``llvm-ar`` from clang, but CI's
        # short PATH may not contain that executable. Resolve it from Conan's
        # toolchain configuration or the OHOS SDK and write the absolute path
        # into Meson's machine file.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or ""
        compiler_dir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        candidates = [executables.get("ar")]
        candidates.extend(
            os.path.join(directory, "llvm-ar")
            for directory in (
                compiler_dir,
                "/data/service/hnp/ohos-sdk/native/llvm/bin",
                "/data/service/hnp/bin",
            )
            if directory
        )
        candidates.extend((shutil.which("llvm-ar"), shutil.which("ar")))
        ar = next((path for path in candidates if path and os.path.isfile(path)), None)
        if not ar:
            raise ConanInvalidConfiguration(
                "Could not locate OHOS archiver (llvm-ar/ar) for Meson"
            )
        tc.ar = ar
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        meson.test()

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.libs = ["qrtr-glib"]
        self.cpp_info.includedirs = ["include", "include/libqrtr-glib"]
        self.cpp_info.set_property("pkg_config_name", "qrtr-glib")
        self.cpp_info.requires = ["glib::gio-2.0", "glib::gobject-2.0"]

