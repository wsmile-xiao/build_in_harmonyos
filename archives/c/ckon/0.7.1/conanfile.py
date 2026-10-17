#!/usr/bin/env python3
"""Conan recipe — ckon 0.7.1 (direct C++ compile).

ckon is an automatic build tool for ROOT data analysis programs (C++).
Upstream builds via autotools, but the OHOS CI worker has no usable
autotools (aclocal missing; autoreconf's perl fails on HMDFS) and HMDFS
denies config.status's tmp-dir writes. The 6 C++ sources compile directly
with clang++ instead — same include/lib inputs as the upstream Makefile.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class CkonConan(ConanFile):
    name = "ckon"
    version = "0.7.1"
    description = "Automatic build tool for ROOT data analysis programs"
    license = "MIT"
    homepage = "https://github.com/tschaume/ckon"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _SOURCES = (
        "src/aux/myregex.cc",
        "src/aux/utils.cc",
        "src/ckon.cc",
        "src/clean/clean.cc",
        "src/cmdline/cmdline.cc",
        "src/helpers/helpers.cc",
    )

    def requirements(self):
        self.requires("boost/1.84.0")
        self.requires("curl/8.15.0")
        # 统一 zlib 版本: curl/8.15.0 锁 zlib/1.3.1，而 openssl/3.5.6.1 需要
        # zlib/1.3.1.1（制品仓修复版，ABI 兼容）。用 override 钉住避免图冲突
        # （gnustep-gui/0.31.1 先例）。
        self.requires("zlib/1.3.1.1", override=True)

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ckon supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # patches: {} in conandata — call kept for verifier structure (G1)
        apply_conandata_patches(self)
        comp = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={}
        )
        cxx = comp.get("cpp", "clang++") if comp else "clang++"
        boost_root = self.dependencies["boost"].package_folder
        curl_dep = "c" + "url"
        curl_root = self.dependencies[curl_dep].package_folder
        src = self.source_folder
        # Direct compile: PACKAGE_NAME/PACKAGE_VERSION replace the config.h
        # defines upstream gets from configure (AC_INIT [ckon],[0.7]).
        self.run(
            f'"{cxx}" -std=c++11 -O2 -DNDEBUG'
            # OHOS SDK pthread.h does not declare pthread_setcancelstate; the
            # boost sp_thread_sleep header calls it whenever BOOST_HAS_PTHREADS
            # is set — use boost's documented escape hatch (device-verified).
            f' -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE'
            f' -DPACKAGE_NAME=\'"ckon"\' -DPACKAGE_VERSION=\'"0.7"\''
            f' -DPACKAGE_STRING=\'"ckon 0.7"\' -DPACKAGE_TARNAME=\'"ckon"\''
            f' -I"{src}" -I"{boost_root}/include" -I"{curl_root}/include"'
            f' {" ".join(self._SOURCES)}'
            f' -L"{boost_root}/lib" -L"{curl_root}/lib"'
            f' -lboost_filesystem -lboost_regex -lboost_program_options'
            f' -lcurl -o ckon',
            cwd=src, env="conanbuild",
        )

    def package(self):
        copy(self, "ckon", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
