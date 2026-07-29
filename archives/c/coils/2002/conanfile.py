import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class CoilsConan(ConanFile):
    name = "coils"
    version = "2002"
    description = "Coiled-coil secondary structure prediction program"
    license = "GPL-2.0-or-later"
    homepage = "https://packages.debian.org/source/stable/coils"
    url = "https://salsa.debian.org/med-team/coils"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c") or "cc"

    def _binary_path(self):
        return os.path.join(self.build_folder, "ncoils")

    def build(self):
        source = self.source_folder
        binary = self._binary_path()
        self.run(
            f'"{self._compiler()}" -O2 -I"{source}" -o "{binary}" '
            f'"{os.path.join(source, "ncoils.c")}" '
            f'"{os.path.join(source, "read_matrix.c")}" -lm'
        )

        if can_run(self):
            output = os.path.join(self.build_folder, "1srya-coils.fasta")
            self.run(
                f'COILSDIR="{source}" "{binary}" -f < '
                f'"{os.path.join(source, "1srya.fa")}" > "{output}"'
            )
            self.run(f'grep -q "^>1srya " "{output}"')
            self.run(f'grep -q "xxxxxxxx" "{output}"')

    def package(self):
        copy(self, "ncoils", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(
            self,
            "*.mat",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "res", "coils"),
        )
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.define("COILSDIR", os.path.join(self.package_folder, "res", "coils"))
