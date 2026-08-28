import os
import re

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ElfutilsConan(ConanFile):
    name = "elfutils"
    version = "0.191"
    package_type = "library"
    description = "elfutils - libelf for ELF parsing (OHOS)"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceware.org/elfutils/"
    url = "https://sourceware.org/elfutils/"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os != "OHOS":
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration("elfutils recipe targets OHOS")
        if self.settings.arch != "armv8":
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration("elfutils recipe targets OHOS armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # The shipped configure requires argp_parse (GNU argp), which is not
        # available on OHOS; make the check non-fatal because we only build
        # libelf (the elfutils tools are not consumed).
        configure = os.path.join(src, "configure")
        with open(configure, encoding="utf-8") as handle:
            content = handle.read()
        content = re.sub(
            r'no\) \{.*?5; \} ;;',
            'no) argp_LDADD= ;;',
            content,
            flags=re.DOTALL,
        )
        # hmdfs temp dirs created with umask 077 are unwritable on OHOS.
        content = content.replace("(umask 077 && mktemp -d", "(umask 000 && mktemp -d")
        content = content.replace("(umask 077 && mkdir", "(umask 000 && mkdir")
        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(content)

        autotools = Autotools(self)
        autotools.configure(args=[
            "--build=aarch64-linux-gnu",
            "--host=aarch64-linux-ohos",
            "--disable-nls",
            "--disable-debuginfod",
            "--disable-libdebuginfod",
            "--disable-backends",
        ])
        # Build only libelf; the elfutils tools need argp which OHOS lacks.
        self.run("make -C libelf -j1 libelf.a", cwd=src)

    def package(self):
        libelf = os.path.join(self.source_folder, "libelf")
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")
        copy(self, "libelf.a", src=libelf, dst=libdir)
        for header in ("gelf.h", "libelf.h"):
            copy(self, header, src=libelf, dst=incdir)
        copy(self, "elf.h", src=os.path.join(libelf, "elf"),
             dst=os.path.join(incdir, "elf"))

    def package_info(self):
        self.cpp_info.libs = ["elf"]
