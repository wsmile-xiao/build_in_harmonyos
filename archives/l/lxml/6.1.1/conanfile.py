#!/usr/bin/env python3
"""Conan recipe for lxml 6.1.1 — Python C extension (setuptools build).

lxml is a Pythonic XML processing library combining libxml2 and libxslt
with the ElementTree API.  The C extensions are built via setup.py build_ext.
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LxmlConan(ConanFile):
    name = "lxml"
    version = "6.1.1"
    description = "Pythonic XML processing library combining libxml2/libxslt"
    license = "BSD-3-Clause"
    homepage = "https://lxml.de"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libxml2/2.15.3")
        self.requires("libxslt/1.1.45")
        self.requires("python/3.12.9")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)

        # Get Conan-managed Python paths
        py = self.dependencies["python"]
        py_pkg = py.package_folder
        py_bin = os.path.join(py_pkg, "bin", "python3.12")
        py_lib = os.path.join(py_pkg, "lib")
        py_inc = os.path.join(py_pkg, "include", "python3.12")

        # Collect all dependency paths (including transitive like openssl)
        lib_dirs = [py_lib]
        include_dirs = [py_inc]
        pkgconfig_dirs = []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf:
                lib_dirs.append(os.path.join(pf, "lib"))
                include_dirs.append(os.path.join(pf, "include"))
                pkgconfig_dirs.append(os.path.join(pf, "lib", "pkgconfig"))
                if os.path.isdir(os.path.join(pf, "include", "libxml2")):
                    include_dirs.append(os.path.join(pf, "include", "libxml2"))

        ld_path = os.pathsep.join(lib_dirs)
        inc_path = os.pathsep.join(include_dirs)
        pkg_path = os.pathsep.join(pkgconfig_dirs)

        # Compiler paths from Conan profile (R33)
        cc = "/data/service/hnp/bin/clang"
        cxx = "/data/service/hnp/bin/clang++"
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        if compilers.get("c"):
            cc = compilers["c"]
        if compilers.get("cpp"):
            cxx = compilers["cpp"]

        # Build using Conan-managed Python 3.12.9 (has correct sysconfig for OHOS).
        # setuptools/cython borrowed from system pip-global via PYTHONPATH.
        pip_global = "/storage/Users/currentUser/.opendesk/interpreters/pip-global"
        self.run(
            f'export PYTHONHOME="{py_pkg}" && '
            f'export PYTHONPATH="{pip_global}" && '
            f'export CC="{cc}" && '
            f'export CXX="{cxx}" && '
            f'export LD_LIBRARY_PATH="{ld_path}" && '
            f'export LIBRARY_PATH="{ld_path}" && '
            f'export C_INCLUDE_PATH="{inc_path}" && '
            f'export PKG_CONFIG_PATH="{pkg_path}" && '
            f'export LDFLAGS="-fuse-ld=bfd -L{py_lib} -lpython3.12" && '
            f'"{py_bin}" setup.py build_ext --inplace && '
            'find src/lxml -name "*.so" | while read f; do '
            'chmod 755 "$f" && '
            '/data/service/hnp/bin/binary-sign-tool sign -inFile "$f" -outFile "$f.signed" -selfSign 1 2>/dev/null && '
            'mv -f "$f.signed" "$f" && chmod 755 "$f" || true; '
            'done',
            cwd=self.source_folder
        )

    def package(self):
        src_lxml = os.path.join(self.source_folder, "src", "lxml")
        lxml_dst = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "lxml")
        copy(self, "*.so", src=src_lxml, dst=lxml_dst)
        copy(self, "*.py", src=src_lxml, dst=lxml_dst)
        copy(self, "*.h", src=src_lxml,
             dst=os.path.join(self.package_folder, "include", "lxml"))
        # Re-sign .so files AFTER copy (conan copy() invalidates ELF signature)
        self.output.info("Re-signing .so files in package folder...")
        self.run(
            f'find "{lxml_dst}" -name "*.so" | while read f; do '
            'chmod 755 "$f" && '
            '/data/service/hnp/bin/llvm-objcopy --remove-section .codesign "$f" 2>/dev/null; '
            '/data/service/hnp/bin/binary-sign-tool sign -inFile "$f" -outFile "$f.signed" -selfSign 1 && '
            'mv -f "$f.signed" "$f" && chmod 755 "$f"; '
            'done'
        )

    def package_info(self):
        self.cpp_info.libs = ["etree", "objectify", "builder", "sax",
                              "diff", "_difflib", "_elementpath"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
