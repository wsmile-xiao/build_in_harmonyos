#!/usr/bin/env python3
"""Conan recipe for fastconstmap 0.9.0, a Python C extension."""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FastconstmapConan(ConanFile):
    name = "fastconstmap"
    version = "0.9.0"
    description = "Fast, immutable, compact map from strings to uint64"
    license = "Apache-2.0"
    homepage = "https://github.com/lemire/fastconstmap"
    url = "https://github.com/lemire/fastconstmap"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("python/3.12.9")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _first_file(pattern, description):
        matches = sorted(glob.glob(pattern))
        if not matches:
            raise ConanException(f"unable to locate {description}: {pattern}")
        return matches[0]

    def _python_paths(self):
        py_pkg = self.dependencies["python"].package_folder
        py_inc = os.path.dirname(
            self._first_file(
                os.path.join(py_pkg, "include", "python*", "Python.h"),
                "Python.h",
            )
        )
        py_lib = os.path.join(py_pkg, "lib")
        py_lib_file = self._first_file(
            os.path.join(py_lib, "libpython*.so"), "libpython shared library"
        )
        py_lib_name = os.path.basename(py_lib_file).split(".so", 1)[0]
        py_site = self._first_file(
            os.path.join(py_lib, "python*", "site-packages"),
            "Python site-packages directory",
        )
        return py_pkg, py_inc, py_lib, py_lib_name, py_site

    def _compiler(self):
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = configured.get("c") or shutil.which("clang") or shutil.which("cc")
        if not compiler:
            raise ConanException(
                "C compiler not found; set tools.build:compiler_executables.c "
                "in the Conan profile"
            )
        return compiler

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isdir(os.path.join(self.source_folder, "src")):
            raise ConanException("fastconstmap source directory is missing")

        _, py_inc, py_lib, py_lib_name, _ = self._python_paths()
        compiler = self._compiler()
        output = os.path.join(self.source_folder, "fastconstmap", "_fastconstmap.so")
        command = " ".join(
            [
                shlex.quote(compiler),
                "-shared",
                "-fPIC",
                "-O3",
                "-std=c11",
                f"-I{shlex.quote(py_inc)}",
                "-Isrc",
                "src/constmap.c",
                "src/fastconstmap_module.c",
                f"-L{shlex.quote(py_lib)}",
                f"-l{py_lib_name.removeprefix('lib')}",
                "-lm",
                "-o",
                shlex.quote(output),
            ]
        )
        # Build the two sources directly. This preserves the upstream setup.py
        # flags while avoiding an undeclared setuptools/Python build tool.
        self.run(command, cwd=self.source_folder)

    def package(self):
        py_pkg, _, _, _, py_site = self._python_paths()
        site_rel = os.path.relpath(py_site, py_pkg)
        site = os.path.join(self.package_folder, site_rel)
        pkg = os.path.join(site, "fastconstmap")
        os.makedirs(pkg, exist_ok=True)
        src = os.path.join(self.source_folder, "fastconstmap")
        if not os.path.isdir(src):
            raise ConanException("built fastconstmap Python package is missing")
        for entry in os.listdir(src):
            path = os.path.join(src, entry)
            if os.path.isfile(path) and not entry.endswith(".pyc"):
                dst = os.path.join(pkg, entry)
                shutil.copy2(path, dst)
                if entry.endswith(".so"):
                    os.chmod(dst, 0o755)

        sign_tool = shutil.which("binary-sign-tool")
        if not sign_tool:
            raise ConanException(
                "binary-sign-tool not found in the Conan build environment PATH"
            )
        for module in glob.glob(os.path.join(pkg, "*.so")):
            signed = module + ".signed"
            self.run(
                " ".join(
                    [
                        shlex.quote(sign_tool),
                        "sign",
                        "-inFile",
                        shlex.quote(module),
                        "-outFile",
                        shlex.quote(signed),
                        "-selfSign",
                        "1",
                    ]
                )
            )
            os.replace(signed, module)
            os.chmod(module, 0o755)

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        tests = os.path.join(self.source_folder, "tests")
        if os.path.isdir(tests):
            shutil.copytree(tests, os.path.join(self.package_folder, "share", "fastconstmap", "tests"))

    def package_info(self):
        self.cpp_info.libs = []
        sites = glob.glob(os.path.join(self.package_folder, "lib", "python*", "site-packages"))
        if sites:
            self.runenv_info.append_path("PYTHONPATH", sites[0])
