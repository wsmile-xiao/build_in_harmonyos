#!/usr/bin/env python3
"""Conan recipe for iqueue 2.2 — lock-free interthread message queue (C, Makefile)."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class IqueueConan(ConanFile):
    name = "iqueue"
    version = "2.2"
    description = "C implementation of an interthread message queue without locks (lock-free, zero-copy)."
    license = "MIT"
    homepage = "https://github.com/je-so/iqueue"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def configure(self):
        # Upstream ships static archives only (bin/iqueue.a); no .so target.
        if self.options.shared:
            raise ConanInvalidConfiguration("iqueue/2.2: upstream Makefile only builds static archives")

    def build(self):
        apply_conandata_patches(self)
        # iqueue is a plain Makefile project (no configure script).
        # basic_layout() places sources in self.source_folder; run make there.
        # Build only the library target: the upstream `all` target also builds
        # the test binary, which uses glibc's malloc_stats() (missing on OHOS).
        self.run("make -j1 makedir iqueue", cwd=self.source_folder)

    def package(self):
        # Upstream Makefile has no install target: install manually.
        # Archives land at bin/iqueue.a (release) and bin/iqueue_debug.a (debug).
        # Conan 2's copy() has no rename kwarg; use shutil to install the
        # archive under the conventional libiqueue.a name.
        import shutil
        copy(self, "iqueue.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "atomic.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "bin", "iqueue.a"),
                    os.path.join(lib_dir, "libiqueue.a"))

    def package_info(self):
        self.cpp_info.libs = ["iqueue"]