#!/usr/bin/env python3
"""Conan recipe — MoarVM 2025.11 (Perl Configure.pl + GNU Make)."""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MoarvmConan(ConanFile):
    name = "moarvm"
    version = "2025.11"
    description = "Metamodel On A Runtime virtual machine for Raku and NQP"
    license = "Artistic-2.0"
    homepage = "https://www.moarvm.org/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"MoarVM is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    @staticmethod
    def _w3_safe_url(url):
        """Preserve percent signs in W3-generated local cache filenames."""
        if isinstance(url, list):
            return [MoarvmConan._w3_safe_url(item) for item in url]
        return url.replace("%", "%25") if url.startswith("file://") else url

    def source(self):
        source = dict(self.conan_data["sources"])
        source["url"] = self._w3_safe_url(source["url"])
        get(self, **source, strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        self.run(
            f'perl Configure.pl --os=linux --compiler=clang --cc="{cc}" '
            f'--ld="{cc}" --ar="{ar}" --relocatable '
            f'--prefix="{self.package_folder}"',
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")
        self.run("make test", cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run("make install", cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        self.cpp_info.libs = ["moar"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
