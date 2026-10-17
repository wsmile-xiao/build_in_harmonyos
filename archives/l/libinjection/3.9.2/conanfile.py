#!/usr/bin/env python3
"""Conan recipe for libinjection 3.9.2 (raw Makefile build, no configure).

libinjection is a C library for SQL/XSS injection detection. The upstream
build is a plain Makefile (SUBDIRS=src) producing libinjection.a/.so plus a
`make check` regression suite driven by shell test-drivers. No autotools
configure script exists, so the recipe drives make directly.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibinjectionConan(ConanFile):
    name = "libinjection"
    version = "3.9.2"
    description = "libinjection — SQL injection and XSS detection library (C)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/client9/libinjection"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Upstream Makefile builds both static and shared; we only install the
        # static lib (R26 keeps system-name style C libs static by default).
        # basic_layout copies sources into <build>/src; run make there.
        #
        # R02 CI L1 fix — controlled interpreter resolution: the remote CI
        # build env has `python3` but no `python` executable, so the upstream
        # generation scripts' original `#!/usr/bin/env python` shebang failed
        # with `env: exec python: No such file or directory` (exit 127). The
        # portability patches now rewrite those shebangs to python3; as an
        # additional self-contained guard, we create a build-local bin dir with
        # `python -> python3` and prepend it to PATH for the make invocation.
        # The dir lives under the Conan build folder and is discarded with the
        # build — it never depends on the executor's interactive PATH.
        py3 = shutil.which("python3") or "python3"
        pybin = os.path.join(self.build_folder, ".ohos-python-bin")
        self.run(
            f"mkdir -p '{pybin}' && ln -sf '{py3}' '{pybin}/python' && "
            f"PATH={pybin}:$PATH make CC=clang 'AR=llvm-ar r' -j1",
            cwd=self.source_folder)

    def package(self):
        # Upstream `make install` (only defined in src/Makefile) respects
        # PREFIX; headers + libinjection.a land in {PREFIX}/include and
        # {PREFIX}/lib. The top-level Makefile has no install target, so run
        # the src subdirectory make directly.
        self.run(f"make CC=clang 'AR=llvm-ar r' install PREFIX={self.package_folder}",
                 cwd=os.path.join(self.source_folder, "src"))

    def package_info(self):
        # LIBNAME=injection -> libinjection.a / -linjection
        self.cpp_info.libs = ["injection"]
