#!/usr/bin/env python3
"""Conan recipe for libwandder 2.0.22.

The upstream tag archive (2.0.22-1) ships configure.ac and Makefile.am
only. Bootstrapping autotools inside the HarmonyOS build sandbox is the
same dead end already recorded for wandio/4.2.7, so this recipe compiles
the five sources listed by src/Makefile.am:

  encoder.c decoder.c itemhandler.c
  libwandder_etsili.c libwandder_etsili_ber.c

configure.ac requires uthash.h, libm (ceil) and libpthread. The ETSI
sources call OpenSSL EVP, so openssl is a real link dependency even
though the autoconf probe does not put -lcrypto into ADD_LIBS.
Upstream defines no TESTS / check_PROGRAMS target.
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

_LIB_SOURCES = [
    "src/encoder.c",
    "src/decoder.c",
    "src/itemhandler.c",
    "src/libwandder_etsili.c",
    "src/libwandder_etsili_ber.c",
]


class LibwandderConan(ConanFile):
    name = "libwandder"
    version = "2.0.22"
    description = "C library for DER and BER encoding and decoding"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/LibtraceTeam/libwandder"
    url = "https://github.com/LibtraceTeam/libwandder"
    topics = ("der", "ber", "asn1", "etsi", "libtrace")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libwandder_etsili.h includes <uthash.h>.
        self.requires("uthash/2.3.0", transitive_headers=True)
        # libwandder_etsili.c calls EVP_Decrypt*.
        self.requires("openssl/3.5.7")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libwandder is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            filename="libwandder-2.0.22-1.tar.gz",
            **self.conan_data["sources"],
            strip_root=True,
        )

    def _ensure_source(self):
        marker = os.path.join(self.source_folder, "src", "decoder.c")
        if os.path.isfile(marker):
            return
        os.makedirs(self.source_folder, exist_ok=True)
        get(
            self,
            filename="libwandder-2.0.22-1.tar.gz",
            **self.conan_data["sources"],
            destination=self.source_folder,
            strip_root=True,
        )
        if not os.path.isfile(marker):
            raise ConanException("libwandder source is missing src/decoder.c")

    def _tool_works(self, tool):
        if os.path.isabs(tool) and not os.path.isfile(tool):
            return False
        if not os.path.isabs(tool) and shutil.which(tool) is None:
            return False
        try:
            self.run(f'"{tool}" --version', env="conanbuild")
            return True
        except Exception:
            return False

    def _unique(self, items):
        seen = set()
        ordered = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered

    def _compiler_candidates(self):
        execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cands = []
        if execs.get("c"):
            cands.append(execs.get("c"))
        cc_env = os.environ.get("CC")
        if cc_env:
            cands.append(cc_env)
        cands.append("/storage/Users/currentUser/usr/local/bin/clang")
        cands.append("/storage/Users/currentUser/usr/local/bin/cc")
        for bare in ("clang", "clang-15", "cc", "gcc"):
            cands.append(bare)
            found = shutil.which(bare)
            if found:
                cands.append(found)
        try:
            for pat in glob.glob("/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang"):
                cands.append(pat)
        except Exception:
            pass
        return self._unique(cands)

    def _resolve_compiler(self):
        for cand in self._compiler_candidates():
            if self._tool_works(cand):
                self.output.info(f"libwandder: selected C compiler '{cand}'")
                return cand
        execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        fallback = execs.get("c") or "clang"
        self.output.warning(f"libwandder: no probed compiler worked, using '{fallback}'")
        return fallback

    def _archiver_candidates(self):
        execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cands = []
        if execs.get("ar"):
            cands.append(execs.get("ar"))
        ar_env = os.environ.get("AR")
        if ar_env:
            cands.append(ar_env)
        cands.append("/storage/Users/currentUser/usr/local/bin/llvm-ar")
        for bare in ("llvm-ar", "ar"):
            cands.append(bare)
            found = shutil.which(bare)
            if found:
                cands.append(found)
        try:
            for pat in glob.glob("/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/llvm-ar"):
                cands.append(pat)
        except Exception:
            pass
        return self._unique(cands)

    def _resolve_archiver(self):
        for cand in self._archiver_candidates():
            if self._tool_works(cand):
                self.output.info(f"libwandder: selected archiver '{cand}'")
                return cand
        execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        fallback = execs.get("ar") or shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        self.output.warning(f"libwandder: no probed archiver worked, using '{fallback}'")
        return fallback

    def _dep_include(self, name):
        return os.path.join(self.dependencies[name].package_folder, "include")

    def _dep_libdir(self, name):
        return os.path.join(self.dependencies[name].package_folder, "lib")

    def build(self):
        self._ensure_source()
        apply_conandata_patches(self)

        src_root = self.source_folder
        obj_dir = os.path.join(self.build_folder, "obj")
        os.makedirs(obj_dir, exist_ok=True)

        cc = self._resolve_compiler()
        includes = " ".join(
            f'-I"{path}"'
            for path in (
                src_root,
                os.path.join(src_root, "src"),
                self._dep_include("uthash"),
                self._dep_include("openssl"),
            )
        )
        cflags = "-O2 -fPIC -pthread -Wall"
        objs = []
        for rel in _LIB_SOURCES:
            obj = os.path.join(obj_dir, os.path.basename(rel) + ".o")
            src = os.path.join(src_root, rel)
            self.run(
                f'"{cc}" {cflags} {includes} -c "{src}" -o "{obj}"',
                env="conanbuild",
            )
            objs.append(f'"{obj}"')
        obj_list = " ".join(objs)
        if self.options.shared:
            crypto_lib = self._dep_libdir("openssl")
            out = os.path.join(self.build_folder, "libwandder.so")
            # version-info 6:6:4 -> SONAME libwandder.so.2
            self.run(
                f'"{cc}" -shared -fPIC -Wl,-soname,libwandder.so.2 {obj_list} '
                f'-L"{crypto_lib}" -lcrypto -lpthread -lm -o "{out}"',
                env="conanbuild",
            )
        else:
            ar = self._resolve_archiver()
            out = os.path.join(self.build_folder, "libwandder.a")
            self.run(f'"{ar}" rcs "{out}" {obj_list}', env="conanbuild")

    def package(self):
        if self.options.shared:
            copy(
                self,
                "libwandder.so",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "lib"),
            )
        else:
            copy(
                self,
                "libwandder.a",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "lib"),
            )
        inc = os.path.join(self.source_folder, "src")
        dst_inc = os.path.join(self.package_folder, "include")
        for name in ("libwandder.h", "libwandder_etsili.h"):
            copy(self, name, src=inc, dst=dst_inc)
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["wandder"]
        self.cpp_info.system_libs = ["pthread", "m"]
