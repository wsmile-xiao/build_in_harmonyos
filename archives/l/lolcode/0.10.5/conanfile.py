#!/usr/bin/env python3
"""Conan recipe for lolcode 0.10.5 — LOLCODE interpreter (terminal tool).

The original source ships only a trivial Makefile (gcc *.c -o lolcode).
We inject a configure script + standards-compliant Makefile in source()
and build with direct make commands.

R26: Static linking for terminal tools.
"""
import os
import textwrap

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.build import can_run


class LolcodeConan(ConanFile):
    name = "lolcode"
    version = "0.10.5"
    description = "An efficient LOLCODE interpreter written in C"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/justinmeza/lolcode"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No dependencies (R27: would use  if any)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The original source has no configure script and a trivial Makefile.
        # Inject a configure script and a proper Makefile.
        configure_script = textwrap.dedent("""\
            #!/bin/sh
            # Simple configure script for lolcode (R1: minimal parameters)
            prefix="/usr/local"
            while [ $# -gt 0 ]; do
                case "$1" in
                    --prefix=*)
                        prefix="${1#--prefix=}"
                        ;;
                    *)
                        ;;
                esac
                shift
            done
            cat > config.mk << EOF
            PREFIX = $prefix
            EOF
            echo "Configuration complete."
            echo "  prefix=$prefix"
            exit 0
        """)
        save(self, "configure", configure_script)
        os.chmod(os.path.join(self.source_folder, "configure"), 0o755)

        makefile_content = textwrap.dedent("""\
            CC ?= gcc
            CFLAGS ?= -O2
            LDFLAGS ?=
            PREFIX ?= /usr/local
            DESTDIR ?=
            TMPDIR ?= /tmp

            -include config.mk

            BIN = lolcode

            all: $(BIN)

            $(BIN): lolcode.c
            \t$(CC) $(CFLAGS) -o $(BIN) lolcode.c $(LDFLAGS)

            install: all
            \tinstall -d $(DESTDIR)$(PREFIX)/bin
            \tinstall -m 755 $(BIN) $(DESTDIR)$(PREFIX)/bin/

            check: all
            \t@echo "Running basic tests..."
            \t@printf 'HAI 1.2\\nVISIBLE "HAI WORLD!"\\nKTHXBYE\\n' > $(TMPDIR)/test_lolcode.lol
            \t./$(BIN) -f $(TMPDIR)/test_lolcode.lol
            \t@echo "Tests complete."
            \t@rm -f $(TMPDIR)/test_lolcode.lol

            clean:
            \trm -f $(BIN)

            .PHONY: all install check clean
        """)
        save(self, "Makefile", makefile_content)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)
        # Get the C compiler from the profile conf
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang") if comp else "clang"
        src = self.source_folder
        # R26: Terminal tools must be statically linked
        self.run("./configure --prefix=/", env="conanbuild", cwd=src)
        self.run(f"make -j1 CC='{cc}' LDFLAGS='-static'", env="conanbuild", cwd=src)

    def package(self):
        src = self.source_folder
        self.run(f"make install DESTDIR={self.package_folder}", env="conanbuild", cwd=src)

    def package_info(self):
        # Terminal tool: binary in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["lolcode"]
