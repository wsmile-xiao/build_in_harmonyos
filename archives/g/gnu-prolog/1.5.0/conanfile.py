import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnuPrologConan(ConanFile):
    name = "gnu-prolog"
    version = "1.5.0"
    package_type = "application"
    description = "GNU Prolog compiler and runtime"
    license = "GPL-2.0-or-later"
    homepage = "https://gprolog.org/"
    url = "https://gprolog.org/"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os != "OHOS":
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration("gnu-prolog recipe targets OHOS")
        if self.settings.arch != "armv8":
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration("gnu-prolog recipe targets OHOS armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        src = os.path.join(self.source_folder, "src")
        stage = os.path.join(self.build_folder, "stage")
        os.makedirs(stage, exist_ok=True)
        autotools = Autotools(self)
        autotools.configure(
            args=[
                f"--with-install-dir={stage}",
                "--without-links-dir",
                "--without-doc-dir",
                "--without-html-dir",
                "--without-examples-dir",
                "--disable-linedit",
                "--disable-sockets",
            ],
            build_dir=src,
        )
        autotools.make(build_dir=src)
        autotools.make(target="check", build_dir=src)
        autotools.install(build_dir=src)

    def package(self):
        copy(self, "*", os.path.join(self.build_folder, "stage"), self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
