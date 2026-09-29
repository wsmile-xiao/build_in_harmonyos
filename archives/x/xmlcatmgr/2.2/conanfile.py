import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain


class XmlcatmgrConan(ConanFile):
    name = "xmlcatmgr"
    version = "2.2"
    package_type = "application"
    license = "BSD-3-Clause"
    homepage = "https://xmlcatmgr.sourceforge.net/"
    description = "Manage XML and SGML catalog entries"
    topics = ("xml", "sgml", "catalog", "command-line")
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("xmlcatmgr supports Linux and OHOS")
        if str(self.settings.compiler) not in ("gcc", "clang"):
            raise ConanInvalidConfiguration("xmlcatmgr requires GCC or Clang")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_cflags = ["-fPIE"]
        tc.extra_ldflags = ["-pie", "-Wl,-z,relro,-z,now"]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # The distributed Makefile has no TESTS; `make check` only rebuilds.
        # Actual XML and SGML behavior is exercised by test_package.

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
