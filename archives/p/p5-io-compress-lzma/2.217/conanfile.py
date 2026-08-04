import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class P5IoCompressLzmaConan(ConanFile):
    name = "p5-io-compress-lzma"
    version = "2.217"
    description = "Perl modules for reading and writing LZMA, XZ, and Lzip streams"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/IO-Compress-Lzma"
    url = ""
    topics = ("perl", "cpan", "lzma", "xz", "lzip")

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        self.requires("perl/5.42.2")
        self.requires("p5-io-compress/2.217")
        self.requires("p5-compress-raw-lzma/2.217")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        copy(self, "*.pm", src=os.path.join(self.source_folder, "lib"), dst=perl_lib, keep_path=True)
        copy(self, "README", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "Changes", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "Makefile.PL", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "META.json", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "META.yml", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "*", src=os.path.join(self.source_folder, "t"), dst=os.path.join(self.package_folder, "share", self.name, "t"))
        copy(self, "*", src=os.path.join(self.source_folder, "examples"), dst=os.path.join(self.package_folder, "share", self.name, "examples"))

    def package_info(self):
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PERL5LIB", perl_lib)
        self.buildenv_info.prepend_path("PERL5LIB", perl_lib)
