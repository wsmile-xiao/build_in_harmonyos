from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class Base91Conan(ConanFile):
    name = "base91"
    version = "0.6.0"
    package_type = "application"
    description = "basE91 binary-to-ASCII encoder and decoder"
    license = "BSD-3-Clause"
    homepage = "https://base91.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("encoding", "base91", "ascii")

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"base91 is adapted for Linux/OHOS, got {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"base91/0.6.0 is validated for OHOS armv8, got {self.settings.arch}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return executables.get("c", "cc")

    def build(self):
        self.run(f'make CC="{self._compiler()}"', cwd=self.source_folder)
        self.run(f'make CC="{self._compiler()}" check', cwd=self.source_folder)

    def package(self):
        # 'make install' needs the 'install' utility, which is not on the
        # Conan PATH in OHOS toybox. Copy the artifacts manually instead.
        copy(self, "base91", src=self.source_folder, dst=f"{self.package_folder}/bin")
        copy(self, "base91.1", src=self.source_folder, dst=f"{self.package_folder}/share/man/man1")
        copy(self, "LICENSE", src=self.source_folder, dst=f"{self.package_folder}/licenses")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
