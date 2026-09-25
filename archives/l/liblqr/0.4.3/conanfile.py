import os
from conan import ConanFile
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, copy
from conan.tools.layout import basic_layout


class LiblqrConan(ConanFile):
    name = "liblqr"
    version = "0.4.3"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def requirements(self):
        self.requires("glib/2.88.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()
        PkgConfigDeps(self).generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Run the upstream test target for real (SKILL.md L-gate). liblqr
        # ships no test programs, so this is expected to be a no-op pass —
        # the point is to prove it, not to assume it.
        autotools.make(args=["check"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.includedirs = ["include/lqr-1"]
        self.cpp_info.libs = ["lqr-1"]
        self.cpp_info.set_property("pkg_config_name", "lqr-1")
