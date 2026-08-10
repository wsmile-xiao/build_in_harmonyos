from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import Environment
import os


class LibgcabConan(ConanFile):
    name = "libgcab"
    version = "1.6"
    description = "Library to create and read Microsoft Cabinet (.cab) files"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/msitools"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("zlib/1.3.1")

    def layout(self):
        self.folders.build = "build"
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Generate .pc files for dependencies (meson needs pkg-config)
        pkg = PkgConfigDeps(self)
        pkg.generate()

        # Create wrapper .pc files for glib sub-libraries (gio-2.0, gobject-2.0, etc.)
        # glib package bundles all libs in glib-2.0.pc, but meson looks for gio-2.0
        gen_folder = self.generators_folder
        with open(os.path.join(gen_folder, "gio-2.0.pc"), "w") as f:
            f.write("Name: gio-2.0\nDescription: GObject I/O (part of glib)\nVersion: 2.84.0\nRequires: glib-2.0\n")

        # Add glib_mkenums variable to generated glib-2.0.pc (meson gnome module needs it)
        glib_dep = self.dependencies.get("glib")
        if glib_dep:
            glib_mkenums = os.path.join(glib_dep.package_folder, "bin", "glib-mkenums")
            pc_path = os.path.join(gen_folder, "glib-2.0.pc")
            if os.path.exists(pc_path) and os.path.exists(glib_mkenums):
                with open(pc_path, "r") as f:
                    content = f.read()
                if "glib_mkenums" not in content:
                    with open(pc_path, "a") as f:
                        f.write("glib_mkenums={}\n".format(glib_mkenums))

        # Set ar/nm/strip paths and PKG_CONFIG_PATH for meson
        env = Environment()
        env.define_path("AR", "/data/service/hnp/bin/llvm-ar")
        env.define_path("NM", "/data/service/hnp/bin/llvm-nm")
        env.define_path("STRIP", "/data/service/hnp/bin/llvm-strip")
        # Add OHOS SDK llvm lib to LD_LIBRARY_PATH (lld needs libxml2.so.16)
        env.define_path("LD_LIBRARY_PATH", "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib")
        # Set PKG_CONFIG_PATH to include generated .pc files and dependency .pc files
        pkg_config_paths = [self.generators_folder]
        for dep in self.dependencies.values():
            pkg_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkg_dir):
                pkg_config_paths.append(pkg_dir)
        env.define("PKG_CONFIG_PATH", ":".join(pkg_config_paths))
        envvars = env.vars(self)
        envvars.save_script("conanbuildenv")

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["introspection"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["docs"] = "false"
        tc.project_options["nls"] = "false"
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
        self.cpp_info.libs = ["gcab-1.0"]
        self.cpp_info.includedirs = ["include/libgcab-1.0"]
        self.cpp_info.set_property("pkg_config_name", "libgcab-1.0")
