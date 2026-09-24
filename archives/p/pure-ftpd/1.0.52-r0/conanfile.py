#!/usr/bin/env python3
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save, load
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout
import os

class PureftpdConan(ConanFile):
    name = "pure-ftpd"
    version = "1.0.52-r0"
    description = "Free, secure, production-quality and standard-conformant FTP server"
    license = "ISC"
    homepage = "https://www.pureftpd.org/"
    url = ""
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-tls")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            content = load(self, configure_path)
            old = '{\n  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n  test -d "$tmp"\n}  ||\n{\n  tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")\n} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5'
            new = '{\n  tmp=./conf$$-$RANDOM\n  (umask 027 && mkdir "$tmp")\n} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5'
            if old in content:
                content = content.replace(old, new)
                save(self, configure_path, content)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["pureftpd"]
