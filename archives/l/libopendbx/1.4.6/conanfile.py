#!/usr/bin/env python3
"""Conan recipe for libopendbx 1.4.6 — OpenDBX C database abstraction library.

Upstream project "opendbx" builds libopendbx (C API), libopendbxplus (C++
wrapper) and the sqlite3 backend plugin from one autotools tree. This recipe
builds the full tree with the sqlite3 backend, runs the upstream regression
suite (odbxtest + odbxplustest) against ref/sqlite3.ref, and packages the
C library plus the sqlite3 backend plugin.
"""
import glob as _glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibopendbxConan(ConanFile):
    name = "libopendbx"
    version = "1.4.6"
    description = "OpenDBX: lightweight but extensible database access library (C API)"
    license = "LGPL-2.0-or-later"
    homepage = "https://linuxnetworks.de/doc/index.php/OpenDBX"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libopendbx supports Linux/OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        self.requires("sqlite3/3.49.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # In-source build: the bundled 2002-era autotools Makefiles use
        # relative include paths (-I../../lib) that break under VPATH.
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-backends=sqlite3",
            "--disable-utils",
        ])
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_regression()

    def _run_upstream_regression(self):
        """Run the upstream regression binaries (odbxtest + odbxplustest)
        against the sqlite3 backend and require output identical to
        test/ref/sqlite3.ref (the upstream's own verification method)."""
        root = self.source_folder
        backend = os.path.join(root, "backends", "sqlite3", ".libs", "libsqlite3backend.so")
        testdir = os.path.join(root, "regression-run")
        os.makedirs(testdir, exist_ok=True)
        ref = os.path.join(root, "test", "ref", "sqlite3.ref")
        with open(ref, "r", encoding="utf-8", errors="replace") as f:
            want = [line.rstrip() for line in f.read().splitlines()]
        for app in ("odbxtest", "odbxplustest"):
            app_path = os.path.join(root, "test", app)
            out = os.path.join(testdir, app + ".out")
            err = os.path.join(testdir, app + ".err")
            self.run(
                f"'{app_path}' -b '{backend}' -h . -d odbx.sq3 > '{out}' 2> '{err}'",
                cwd=testdir,
                check=True,
            )
            with open(out, "r", encoding="utf-8", errors="replace") as f:
                got = [line.rstrip() for line in f.read().splitlines()]
            if got != want:
                raise ConanException(
                    f"upstream regression {app}: output differs from test/ref/sqlite3.ref "
                    f"({len(got)} vs {len(want)} lines); see {err}"
                )
            self.output.info(f"upstream regression {app}: PASS (output matches ref/sqlite3.ref)")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Keep only the C-library artifacts: libopendbx, the sqlite3 backend
        # plugin, the C headers (odbx.h, opendbx/api.h) and opendbx.pc. The
        # C++ wrapper library and header belong to the libopendbxplus package.
        lib_dir = os.path.join(self.package_folder, "lib")
        for name in list(os.listdir(lib_dir)):
            if name.startswith("libopendbxplus"):
                _remove_tree(os.path.join(lib_dir, name))
        # Libtool .la wrappers are not needed at runtime.
        for _la in _glob.glob(os.path.join(lib_dir, "**", "*.la"), recursive=True):
            os.remove(_la)
        # opendbxplus.pc and the C++ header belong to the libopendbxplus package.
        pc = os.path.join(lib_dir, "pkgconfig", "opendbxplus.pc")
        if os.path.exists(pc):
            os.remove(pc)
        cpp_header = os.path.join(self.package_folder, "include", "opendbx", "api")
        if os.path.exists(cpp_header):
            os.remove(cpp_header)

    def package_info(self):
        self.cpp_info.libs = ["opendbx"]
        self.cpp_info.includedirs = ["include"]
        # The sqlite3 backend plugin is installed at lib/opendbx/; consumers
        # load it at runtime by path (OpenDBX supports backend paths directly).
        self.cpp_info.libdirs = ["lib", "lib/opendbx"]


def _remove_tree(path):
    if os.path.isdir(path):
        import shutil as _shutil
        _shutil.rmtree(path)
    else:
        os.remove(path)
