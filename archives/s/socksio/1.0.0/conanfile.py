#!/usr/bin/env python3
"""Conan recipe candidate for the pure Python socksio 1.0.0 library."""

import hashlib
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, unzip
from conan.tools.layout import basic_layout


class SocksioConan(ConanFile):
    name = "socksio"
    version = "1.0.0"
    description = "Sans-I/O SOCKS4, SOCKS4A, and SOCKS5 protocol library"
    license = "MIT"
    homepage = "https://github.com/sethmlarson/socksio"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # Pure Python has no C/C++ linkage type or shared/static option.
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        archive = os.environ.get("SOCKSIO_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as source_file:
                digest = hashlib.sha256(source_file.read()).hexdigest()
            if digest != self.conan_data["sources"]["sha256"]:
                raise ConanException("socksio source archive SHA-256 mismatch")
            unzip(self, archive, strip_root=True, extract_filter="data")
        else:
            get(self, **self.conan_data["sources"], strip_root=True,
                extract_filter="data")

    def build(self):
        # Check every distributed module with the target Python standard library.
        # The unmodified upstream pytest suite is run separately on H1 and
        # recorded as R51 evidence; this step does not claim to run that suite.
        self.run("python3 -m compileall -q socksio",
                 cwd=self.source_folder)

    def package(self):
        source = os.path.join(self.source_folder, "socksio")
        target = os.path.join(self.package_folder, "lib", "python", "socksio")
        copied = copy(self, "*.py", src=source, dst=target, keep_path=False)
        if not copied:
            raise ConanException("socksio Python sources were not packaged")
        copy(self, "py.typed", src=source, dst=target, keep_path=False)
        licenses = copy(self, "LICENSE*", src=self.source_folder,
                        dst=os.path.join(self.package_folder, "licenses"),
                        keep_path=False)
        if not licenses:
            raise ConanException("socksio source license was not packaged")

    def package_id(self):
        # The distributed files are pure Python and have no native ABI.
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
