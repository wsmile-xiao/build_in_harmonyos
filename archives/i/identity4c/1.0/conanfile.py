#!/usr/bin/env python3
"""Conan recipe for identity4c 1.0 — UFP Identity C library.

Provides SSL/TLS identity verification using OpenSSL and XML-based identity
documents parsed via libxml2. Bundles strmap and picohttpparser as source.

Build system: manual Makefile (autotools not available on CI runners).
License: GPL-2.0+ with OpenSSL exception.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class Identity4cConan(ConanFile):
    name = "identity4c"
    version = "1.0"
    description = "UFP Identity C library — SSL/TLS identity verification"
    license = "GPL-2.0+"
    homepage = "https://github.com/ufpidentity/identity4c"
    url = "https://github.com/ufpidentity/identity4c"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("libxml2/2.15.3")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: platform check uses in ("Linux", "OHOS"), never == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"identity4c requires Linux or OHOS, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        """R33: Get C compiler from profile conf, not bare shell variables.
        Falls back to 'clang' which is the standard OHOS cross-compiler."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("c", "clang")

    def generate(self):
        # Determine dependency paths from conan
        openssl = self.dependencies["openssl"]
        libxml2 = self.dependencies["libxml2"]
        openssl_inc = os.path.join(openssl.package_folder, "include")
        libxml2_inc = os.path.join(libxml2.package_folder, "include", "libxml2")
        openssl_lib = os.path.join(openssl.package_folder, "lib")
        libxml2_lib = os.path.join(libxml2.package_folder, "lib")
        src = self.source_folder
        build = self.build_folder

        cc = self._get_cc()
        cflags = "-fPIC -O2 -g0"
        inc_flags = f"-I{src} -I{openssl_inc} -I{libxml2_inc}"
        sources = " ".join([
            "identity.c", "identity-openssl-bridge.c", "identity-resolver.c",
            "identity-xml-parser.c", "picohttpparser.c", "strmap.c"
        ])
        objs = " ".join([
            "identity.o", "identity-openssl-bridge.o", "identity-resolver.o",
            "identity-xml-parser.o", "picohttpparser.o", "strmap.o"
        ])
        libs = f"-L{openssl_lib} -L{libxml2_lib} -lssl -lcrypto -lxml2"

        # Write a small Makefile for reproducibility
        makefile = f"""CC={cc}
CFLAGS={cflags} {inc_flags}
AR=ar
ARFLAGS=rcs
LIBS={libs}

all: libufpidentity.a

libufpidentity.a: {objs}
\t$(AR) $(ARFLAGS) $@ $^

{objs}: %.o: %.c
\t$(CC) $(CFLAGS) -c $< -o $@

install: libufpidentity.a
\tmkdir -p $(DESTDIR)/lib $(DESTDIR)/include
\tcp libufpidentity.a $(DESTDIR)/lib/
\tcp identity.h strmap.h $(DESTDIR)/include/

clean:
\trm -f *.o libufpidentity.a

.PHONY: all install clean
"""
        with open(os.path.join(src, "Makefile"), "w") as f:
            f.write(makefile)

    def build(self):
        # Use the manually generated Makefile (avoids autotools dependency)
        cc = self._get_cc()
        openssl = self.dependencies["openssl"]
        libxml2 = self.dependencies["libxml2"]
        openssl_inc = os.path.join(openssl.package_folder, "include")
        libxml2_inc = os.path.join(libxml2.package_folder, "include", "libxml2")
        openssl_lib = os.path.join(openssl.package_folder, "lib")
        libxml2_lib = os.path.join(libxml2.package_folder, "lib")

        src = self.source_folder
        cflags = f"-fPIC -O2 -g0 -I{src} -I{openssl_inc} -I{libxml2_inc}"
        for c in ["identity.c", "identity-openssl-bridge.c", "identity-resolver.c",
                   "identity-xml-parser.c", "picohttpparser.c", "strmap.c"]:
            o = c.replace(".c", ".o")
            self.run(f"{cc} {cflags} -c {c} -o {o}", cwd=src)
        self.run(f"ar rcs libufpidentity.a identity.o identity-openssl-bridge.o "
                 f"identity-resolver.o identity-xml-parser.o picohttpparser.o strmap.o",
                 cwd=src)

    def package(self):
        src = self.source_folder
        copy(self, "libufpidentity.a", src=src,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "identity.h", src=src,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "strmap.h", src=src,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["ufpidentity"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["openssl::openssl", "libxml2::libxml2"]
