from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, unzip
from conan.tools.layout import basic_layout
import os
import shlex


class SectarConan(ConanFile):
    name = "sectar"
    version = "1.02"
    description = "AES file encryption command-line utility"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/star/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        archive = os.path.join(self.source_folder, "sectar-1.02.tar.gz")
        download(self, source["url"], archive, sha256=source["sha256"])
        unzip(self, archive, destination=self.source_folder, strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compiler = self.conf.get("tools.build:compiler_executables", default={}).get("c")
        if not compiler:
            raise RuntimeError("tools.build:compiler_executables.c is required for cross-compilation")
        src = os.path.join(self.source_folder, "sectar")
        sources = ("main.c", "crypt.c", "rijndael-api-fst.c", "rijndael-alg-fst.c",
                   "getopt.c", "getopt1.c")
        inputs = " ".join(shlex.quote(os.path.join(src, name)) for name in sources)
        output = os.path.join(self.build_folder, "sectar")
        self.run(f"{shlex.quote(compiler)} -std=gnu89 -Wno-implicit-function-declaration "
                 f"-DVERSION=\\\"1.02\\\" -static -I{shlex.quote(src)} "
                 f"{inputs} -o {shlex.quote(output)}")

    def package(self):
        copy(self, "sectar", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
