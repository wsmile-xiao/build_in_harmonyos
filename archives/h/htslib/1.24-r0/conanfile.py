#!/usr/bin/env python3
"""Conan recipe — HTSlib 1.24-r0 for OpenHarmony.

Build system: Autotools (configure + make)
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class HtslibConan(ConanFile):
    name = "htslib"
    version = "1.24-r0"
    description = "C library and command-line tools for SAM, BAM, CRAM, VCF, and BCF files"
    license = "MIT"
    homepage = "https://www.htslib.org/"
    url = "https://github.com/samtools/htslib"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("xz/5.6.2")
        self.requires("libdeflate/1.25")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
        else:
            tc.configure_args.append("--disable-versioned-symbols")
        tc.configure_args.extend([
            "--disable-bz2",
            "--disable-libcurl",
            "--disable-plugins",
            "--disable-ref-cache",
            "--with-libdeflate",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_for_ohos()
        self._prepend_uname_shim()

        autotools = Autotools(self)
        autotools.configure()
        self._patch_makefile_for_ohos()
        autotools.make(args=["-j1"])
        autotools.make(target="test/hts_endian", args=["-j1"])
        autotools.make(target="test/test_kstring", args=["-j1"])
        autotools.make(target="test/test_str2int", args=["-j1"])
        test_libdirs = [dep.cpp_info.libdirs[0] for dep in self.dependencies.values() if dep.cpp_info.libdirs]
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(test_libdirs + [os.environ.get("LD_LIBRARY_PATH", "")])
        self.run("./test/hts_endian")
        self.run("./test/test_kstring")
        self.run("./test/test_str2int")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["hts"]
        self.cpp_info.set_property("pkg_config_name", "htslib")
        self.cpp_info.set_property("cmake_file_name", "htslib")
        self.cpp_info.set_property("cmake_target_name", "htslib::htslib")
        self.cpp_info.system_libs = ["m", "pthread"]

    def _patch_configure_for_ohos(self):
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            return
        replace_in_file(self, configure, "umask 077", "umask 022")
        with open(configure, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        content = content.replace("${TMPDIR-/tmp}", "${TMPDIR:-${HOME}/tmp}")
        content = content.replace("${TMPDIR:-/tmp}", "${TMPDIR:-${HOME}/tmp}")
        with open(configure, "w", encoding="utf-8") as f:
            f.write(content)

    def _prepend_uname_shim(self):
        shim_dir = os.path.join(self.build_folder, "_ohos_uname")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "uname")
        with open(shim, "w", encoding="utf-8") as f:
            f.write(
                '#!/bin/sh\n'
                'case "${1:-}" in\n'
                '  -s|"") echo Linux ;;\n'
                '  -r) echo 6.6 ;;\n'
                '  -m|-p) echo aarch64 ;;\n'
                '  *) exec /system/bin/uname "$@" 2>/dev/null || exec uname "$@" ;;\n'
                'esac\n'
            )
        os.chmod(shim, 0o755)
        os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")

    def _patch_makefile_for_ohos(self):
        makefile = os.path.join(self.build_folder, "Makefile")
        if not os.path.isfile(makefile):
            return
        with open(makefile, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        content = content.replace(
            "all: lib-static lib-shared $(BUILT_PROGRAMS) plugins \\",
            "all: lib-static $(BUILT_PROGRAMS) \\",
        )
        content = content.replace(
            "install: libhts.a $(BUILT_PROGRAMS) $(BUILT_PLUGINS) $(REF_CACHE_PROGRAMS) installdirs install-$(SHLIB_FLAVOUR) install-pkgconfig",
            "install: libhts.a $(BUILT_PROGRAMS) $(REF_CACHE_PROGRAMS) installdirs install-pkgconfig",
        )
        with open(makefile, "w", encoding="utf-8") as f:
            f.write(content)

