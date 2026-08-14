#!/usr/bin/env python3
"""Conan recipe — Gauche 0.9.15 (Scheme interpreter).

Gauche is a Scheme interpreter with R7RS compatibility, UTF-8 support,
and multithreading. It builds via autotools and produces the `gosh`
executable and `libgauche` shared library.

Key OHOS adaptations:
  - config.guess/config.sub patched for OHOS platform detection
  - Boehm GC patched to disable pthread_cancel (musl libc gap)
  - extension directory skipped because OHOS dynamic module loading fails
  - pthread_compat.c stub for missing pthread_cancel/setcancelstate

File location: archives/g/gauche/0.9.15.1/conanfile.py
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GaucheConan(ConanFile):
    name = "gauche"
    version = "0.9.15.1"
    description = "Gauche is a Scheme implementation designed as a scripting language"
    license = "BSD-3-Clause"
    homepage = "https://practical-scheme.net/gauche/"
    url = "https://github.com/shirok/Gauche"

    # Gauche produces both an executable (gosh) and a library (libgauche).
    # We classify it as an application since the primary deliverable is the
    # interpreter binary.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # No external Conan dependencies — Gauche bundles its own Boehm GC.

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        get(
            self,
            url=source["url"],
            sha256=source["sha256"],
            strip_root=True,
        )
        required_entries = ("configure", "gc", "libsrc")
        if not all(os.path.exists(os.path.join(self.source_folder, entry))
                   for entry in required_entries):
            raise ConanException(
                "Extracted release root does not contain configure, gc/, and libsrc/"
            )

    def generate(self):
        tc = AutotoolsToolchain(self)

        # Gauche 非系统同名库（R26 仅限系统同名库），默认动态构建：
        # 其 Boehm GC 需要生成 libgc_pic.a（PIC 归档）供 libgauche 链接，
        # --disable-shared 会使 libgc_pic.a 为空导致 GC_* 符号未定义。
        # 依赖链由 Conan 管理，gosh 可执行文件自带 RPATH。
        # OHOS libc does not provide pthread cancellation. Boehm GC already
        # supports disabling that optional feature with this capability macro.
        tc.extra_cflags.append("-DGC_NO_PTHREAD_CANCEL")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # 0046 changes configure.ac inputs, so regenerate the generated
        # configure scripts instead of editing them in place (R6).
        self.run("autoconf", cwd=self.source_folder)
        self.run("autoconf", cwd=os.path.join(self.source_folder, "gc"))

        autotools = Autotools(self)
        autotools.configure()

        # The core interpreter does not require the OHOS-incompatible ext/ or
        # documentation trees.  Invoke upstream subdirectory targets directly
        # instead of altering generated Makefile.in/configure files (R6).
        make_args = "-j16 --jobserver-style=pipe"
        for subdir in ("gc", "lib"):
            self.run(f'make -C "{os.path.join(self.build_folder, subdir)}" all {make_args}')

        # HMDFS can make `pwd` fail in make's child shell.  The upstream
        # POSTBUILD hook accepts TARGETLIB as a Make variable, so supply the
        # known build directory without changing the generated Makefile.
        src_build = os.path.join(self.build_folder, "src")
        postbuild = (
            f'TARGETLIB="{src_build}" DESTDIR= '
            "$(MAKEVERSLINK) $(LIBGAUCHE).$(SOEXT)"
        )
        self.run(
            f'make -C "{src_build}" all {make_args} '
            f"POSTBUILD='{postbuild}'"
        )

    def package(self):
        # The upstream install target invokes the newly built gosh.  That
        # executable cannot be loaded from the HMDFS build path, so package the
        # completed core artifacts with Conan's file API instead.
        src_build = os.path.join(self.build_folder, "src")
        lib_build = os.path.join(self.build_folder, "lib")
        include_dir = os.path.join(
            self.package_folder, "lib", "gauche-0.98", "0.9.15", "include"
        )

        copy(self, "gosh", src=src_build, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libgauche-0.98.so*", src=src_build,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "gauche.h", src=os.path.join(self.source_folder, "src"),
             dst=include_dir, keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "src", "gauche"),
             dst=os.path.join(include_dir, "gauche"), keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "gc", "include"),
             dst=include_dir)
        copy(self, "config.h", src=os.path.join(src_build, "gauche"),
             dst=os.path.join(include_dir, "gauche"), keep_path=False)
        copy(self, "config_threads.h", src=os.path.join(src_build, "gauche"),
             dst=os.path.join(include_dir, "gauche"), keep_path=False)
        copy(self, "configP.h", src=os.path.join(src_build, "gauche", "priv"),
             dst=os.path.join(include_dir, "gauche", "priv"), keep_path=False)

        scheme_dir = os.path.join(
            self.package_folder, "share", "gauche-0.98", "0.9.15", "lib"
        )
        copy(self, "*.scm", src=os.path.join(self.source_folder, "lib"), dst=scheme_dir)
        copy(self, "*.sld", src=os.path.join(self.source_folder, "lib"), dst=scheme_dir)
        copy(self, "*.scm", src=lib_build, dst=scheme_dir)
        copy(self, "*.sld", src=lib_build, dst=scheme_dir)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Gauche installs headers under lib/gauche-<abi>/<ver>/include/
        # (autotools GAUCHE_HEADER_INSTALL_DIR), not under a top-level include/.
        # Conan cpp_info.includedirs is relative to the package folder.
        gauche_inc = os.path.join("lib", "gauche-0.98", "0.9.15", "include")
        self.cpp_info.includedirs = [gauche_inc]
        self.cpp_info.libs = ["gauche-0.98"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        # Gauche resolves its Scheme standard library through this path at
        # runtime.  Conan's run environment must point at the packaged tree.
        gauche_lib = os.path.join(
            self.package_folder, "share", "gauche-0.98", "0.9.15", "lib"
        )
        self.runenv_info.define_path("GAUCHE_LOAD_PATH", gauche_lib)
