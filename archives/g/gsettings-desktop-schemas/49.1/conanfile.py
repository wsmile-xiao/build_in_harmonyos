#!/usr/bin/env python3
"""Conan recipe for gsettings-desktop-schemas 49.1.

A collection of GSettings schemas for the GNOME desktop, including helper
header files with enum definitions. This is a header-only/data package —
no libraries are produced (introspection is disabled).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GsettingsDesktopSchemasConan(ConanFile):
    name = "gsettings-desktop-schemas"
    version = "49.1"
    description = "Shared GSettings schemas for the desktop, including helper headers"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gsettings-desktop-schemas"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Create glib-mkenums wrapper: the original Perl script has
        # shebang #!/usr/bin/perl but OHOS has perl at /data/service/hnp/bin/perl
        orig_path = "/data/service/hnp/bin/glib-mkenums"
        wrapper_path = os.path.join(self.generators_folder, "glib-mkenums")
        with open(orig_path, "r") as f:
            content = f.read()
        content = content.replace("#! /usr/bin/perl", "#!/data/service/hnp/bin/perl", 1)
        with open(wrapper_path, "w") as f:
            f.write(content)
        os.chmod(wrapper_path, 0o755)

        tc = MesonToolchain(self)
        # Disable GObject introspection — not available on OHOS
        tc.project_options["introspection"] = "false"
        # Explicitly set ar/ranlib for OHOS (not auto-detected like Android)
        tc.binaries["ar"] = "/data/service/hnp/bin/llvm-ar"
        tc.binaries["ranlib"] = "/data/service/hnp/bin/llvm-ranlib"
        # Use the wrapper for glib-mkenums
        tc.binaries["glib-mkenums"] = wrapper_path
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
        self.cpp_info.set_property("pkg_config_name", "gsettings-desktop-schemas")
        # Header-only package: expose include directory
        self.cpp_info.includedirs = ["include/gsettings-desktop-schemas"]
        # No libraries to link — schemas are data files consumed at runtime
        self.cpp_info.libs = []
        # Resdirs for schema XML data files
        self.cpp_info.resdirs = ["share/glib-2.0/schemas"]
