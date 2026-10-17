#!/usr/bin/env python3
"""Conan recipe for libcleri 1.0.2.

libcleri is an Eclipse-CDT-makefile project: the tarball root has src/,
inc/, test/ and a Release/ subdir containing the generated makefile
(includes ../makefile.init, ../makefile.targets).  There is no configure
script.  Build from Release/ with `make all`; the makefile links
-lpcre2-8, so pcre2 is a required runtime dependency (the produced
libcleri.so has a NEEDED entry for libpcre2-8.so; OHOS provides no system
libpcre2-8.so, it comes from the Conan pcre2 package — hence run=True,
mirroring archives/a/address-standardizer/3.7.0).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class LibcleriConan(ConanFile):
    name = "libcleri"
    version = "1.0.2"
    description = "libcleri 1.0.2 - C parser library (CYI / cleri grammar engine)"
    license = "MIT"
    homepage = "https://github.com/cesbit/libcleri"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        # libcleri.so links libpcre2-8.so dynamically; OHOS has no system
        # libpcre2-8.so, it ships in the Conan pcre2 package.  run=True forces
        # Conan to keep pcre2's binary installed so test_package can resolve
        # libpcre2-8.so's libdir for LD_LIBRARY_PATH (same pattern as
        # archives/a/address-standardizer/3.7.0).  10.45.1.1 is used because
        # its published binary carries complete cpp_info (components
        # pcre2-8/16/32 + include dirs), unlike 10.45 whose published binary
        # CMakeDeps shows empty libs/includes.
        self.requires("pcre2/10.45.1.1", run=True)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # plain makefile project; build in the source tree (Release/ subdir)
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        pcre2 = self.dependencies["pcre2"].cpp_info
        pcre2_inc = pcre2.includedirs[0]
        pcre2_libdir = pcre2.libdirs[0]
        cc = self.settings.get_safe("compiler")
        # The Eclipse makefile uses `CC ?= gcc`; drive it with clang and the
        # pcre2 include/lib dirs from the Conan dependency.
        self.run(
            "make all CC=clang "
            f"CFLAGS=\"-DNDEBUG -I../inc -I{pcre2_inc} -O3 -Winline -Wall "
            "-fmessage-length=0 -fPIC -MMD -MP\" "
            f"LDFLAGS=\"-L{pcre2_libdir}\"",
            cwd="Release",
        )

    def package(self):
        fn = "libcleri.so"
        libdir = os.path.join(self.package_folder, "lib")
        copy(self, fn, src="Release", dst=libdir)
        # 上游 makefile.targets 的 install 目标生成版本化名称：
        #   libcleri.so.1.0.2 / libcleri.so.1 -> libcleri.so
        # 且 .so 的 SONAME 为 libcleri.so.1（-Wl,-soname,libcleri.so.1）。
        # 消费者二进制按 NEEDED=libcleri.so.1 解析，必须提供同 SONAME 文件，
        # 否则运行期 "Error loading shared library libcleri.so.1"。
        os.symlink(fn, os.path.join(libdir, "libcleri.so.1"))
        os.symlink(fn, os.path.join(libdir, "libcleri.so.1.0.2"))
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "inc/cleri"),
            dst=os.path.join(self.package_folder, "include/cleri"),
        )

    def package_info(self):
        self.cpp_info.libs = ["cleri"]
        # libcleri.so has a NEEDED entry for libpcre2-8.so; consumers must
        # link it too.  pcre2/10.45.1.1 exports components pcre2-8/16/32;
        # referencing the aggregate pcre2::pcre2 keeps the CMakeDeps data
        # (include + libs) complete for consumers (component-only reference
        # produced empty CMakeDeps data in the test_package context).
        self.cpp_info.requires = ["pcre2::pcre2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libcleri")
        self.cpp_info.set_property("cmake_target_name", "libcleri::libcleri")