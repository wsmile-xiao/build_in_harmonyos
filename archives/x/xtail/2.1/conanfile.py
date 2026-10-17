"""xtail 2.1: follow files and newly created directory entries."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XtailConan(ConanFile):
    name = "xtail"
    version = "2.1"
    description = "Follow multiple files and directories as they change"
    license = "Unlicense"
    homepage = "https://salsa.debian.org/debian/xtail"
    url = "https://salsa.debian.org/debian/xtail"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Old Makefile.in only adds -I$(srcdir); config.h is generated in
        # Conan's separate build directory.
        tc.extra_cflags.append(f"-I{self.build_folder}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The release archive has configure.in newer than configure. Never
        # regenerate released scripts (autoconf is not a build requirement).
        for filename in ("configure", "config.h.in"):
            path = os.path.join(self.source_folder, filename)
            os.utime(path, None)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        copy(self, "xtail", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "xtail.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
