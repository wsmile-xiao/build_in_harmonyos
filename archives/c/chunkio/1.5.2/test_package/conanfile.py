#!/usr/bin/env python3
"""Conan L1 test_package for chunkio 1.5.2 (consumer view).

Compiles test_chunkio.c against the *installed* package only (find_package +
chunkio::chunkio) and runs it, so the test really consumes what a downstream
consumer gets: the public headers under include/chunkio (plus the bundled
monkey mk_list.h that <chunkio/chunkio.h> pulls in) and
libchunkio-static.a + libcio-crc32.a.

17 checks: two version fingerprints (installed header + linked library),
the memfs backend round trip, and the fs backend — the latter is the path
that exercises the OHOS fallocate()/posix_fallocate() -> ftruncate() fallback
from patch 0004 against a real directory.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class ChunkioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d: run the consumer binary itself (cmake.test() would be a stub),
        # under the conanrun environment so the packaged archives are used.
        exe = os.path.join(self.build_folder, "bin", "test_chunkio")
        if not os.path.isfile(exe):
            raise ConanException("consumer binary missing: %s" % exe)
        self.run('"%s"' % exe, env="conanrun")
        self.output.success("chunkio 1.5.2 test_package: consumer checks passed")
