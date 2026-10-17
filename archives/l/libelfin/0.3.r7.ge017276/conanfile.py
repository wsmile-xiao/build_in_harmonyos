#!/usr/bin/env python3
"""Conan recipe — libelfin 0.3.r7.ge017276

libelfin provides two C++11 libraries for reading ELF binaries and DWARFv4
debug information: libelf++ (elf/) and libdwarf++ (dwarf/).

Build system: plain recursive Makefile (no ./configure).  The version string
follows upstream `git describe`: 0.3 plus 7 commits, pinned at the commit the
Arch Linux package uses (e0172767b79b76373044118ef0272b49b02a0894).

The recipe builds both libraries, then runs the upstream test suite
(test/test.sh: five dump tools x two golden fixtures = 10 comparisons) inside
build(), so the upstream result is part of the conan-create log.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class LibelfinConan(ConanFile):
    name = "libelfin"
    version = "0.3.r7.ge017276"
    description = "C++11 ELF/DWARF parser (libelf++ and libdwarf++)"
    license = "MIT"
    homepage = "https://github.com/aclements/libelfin"
    url = "https://github.com/aclements/libelfin"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libelfin only supports Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _find_bash():
        """test/test.sh uses bash syntax ([[ ]]); OHOS has no /bin/bash."""
        candidates = [
            os.environ.get("CONFIG_SHELL", ""),
            "/data/service/hnp/bin/bash",
            "/bin/bash",
            "/usr/bin/bash",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        found = shutil.which("bash")
        if found:
            return found
        raise ConanInvalidConfiguration(
            "no bash interpreter found (test/test.sh requires bash)"
        )

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from the Conan configuration, never from the
        # shell environment.  The conf only defines "c" and "cpp" keys.
        comp = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = comp.get("c") or "clang"
        cxx = comp.get("cpp") or "clang++"
        # VER feeds the patched pkg-config rules (upstream used `git describe`,
        # which cannot work in a release tarball without a .git directory).
        make_args = f'CC="{cc}" CXX="{cxx}" VER="{self.version}"'

        # R9: keep the recursive upstream Makefile serial.
        self.run(f"make {make_args} -j1", cwd=self.source_folder)

        # Upstream test suite.  test.sh builds examples/ (which consumes the
        # in-tree .pc files) and diffs dump-sections/segments/lines/syms/tree
        # against the two committed golden fixtures = 10 comparisons.
        # It is executed through an explicit bash: the shebang is #!/bin/bash
        # and OHOS has no /bin/bash, so `make check` cannot work unpatched.
        bash = self._find_bash()
        self.run(
            f'{make_args} "{bash}" ./test.sh',
            cwd=os.path.join(self.source_folder, "test"),
        )

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        include_root = os.path.join(self.package_folder, "include", "libelfin")
        copy(
            self,
            "*.hh",
            src=os.path.join(self.source_folder, "elf"),
            dst=os.path.join(include_root, "elf"),
        )
        copy(
            self,
            "*.hh",
            src=os.path.join(self.source_folder, "dwarf"),
            dst=os.path.join(include_root, "dwarf"),
        )

        libdir = os.path.join(self.package_folder, "lib")
        for subdir in ("elf", "dwarf"):
            copy(self, "*.a", src=os.path.join(self.source_folder, subdir), dst=libdir)
            if self.options.get_safe("shared"):
                copy(
                    self,
                    "*.so*",
                    src=os.path.join(self.source_folder, subdir),
                    dst=libdir,
                )

        # pkg-config metadata, matching the two files upstream generates in
        # its build tree, but relocatable through ${pcfiledir}.
        pc_dir = os.path.join(libdir, "pkgconfig")
        for pc_name, lib_name, subdir, description, requires in (
            ("libelf++", "elf++", "elf", "C++11 ELF library", None),
            ("libdwarf++", "dwarf++", "dwarf", "C++11 DWARF library", "libelf++"),
        ):
            lines = [
                "prefix=${pcfiledir}/../..",
                "libdir=${prefix}/lib",
                f"includedir=${{prefix}}/include/libelfin/{subdir}",
                "",
                f"Name: {pc_name}",
                f"Description: {description}",
                f"Version: {self.version}",
            ]
            if requires:
                lines.append(f"Requires: {requires} = {self.version}")
            lines += [
                f"Libs: -L${{libdir}} -l{lib_name}",
                "Cflags: -I${includedir}",
            ]
            save(self, os.path.join(pc_dir, f"{pc_name}.pc"), "\n".join(lines) + "\n")

    def package_info(self):
        self.cpp_info.libs = ["dwarf++", "elf++"]
        self.cpp_info.includedirs = ["include/libelfin/elf", "include/libelfin/dwarf"]

        self.cpp_info.set_property("cmake_file_name", "libelfin")
        self.cpp_info.set_property("cmake_target_name", "libelfin::libelfin")
