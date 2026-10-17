#!/usr/bin/env python3
"""Conan recipe - jbjg 2.1 (JBIG-KIT static library)."""
import os
import hashlib
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration


class JbjgConan(ConanFile):
    name = "jbjg"
    version = "2.1"
    description = "JBIG-KIT lossless image compression library (ITU-T T.82)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.cl.cam.ac.uk/~mgk25/jbigkit/"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"])
        local_archive = os.environ.get("JBJG_SOURCE_ARCHIVE", "").strip()
        if local_archive:
            path = Path(local_archive).expanduser().resolve()
            expected = os.environ.get("JBJG_SOURCE_ARCHIVE_SHA256", "").strip().lower()
            if not path.is_file() or not expected:
                raise ConanInvalidConfiguration(
                    "JBJG_SOURCE_ARCHIVE and JBJG_SOURCE_ARCHIVE_SHA256 are required together"
                )
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                raise ConanInvalidConfiguration(
                    "JBJG_SOURCE_ARCHIVE SHA-256 does not match the declared task input"
                )
            source.pop("sha256", None)
            source["url"] = path.as_uri()
            source["filename"] = path.name
        get(self, **source, strip_root=True)

    def _resolve_tool(self, name, configured=""):
        candidates = [configured, shutil.which(name)]
        if os.name != "nt":
            candidates.append(os.path.join("/data/service/hnp/bin", name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def build(self):
        # JBIG-KIT uses a hand-written Makefile. The patch exposes AR/RANLIB
        # variables and a check target so the upstream codec tests run here.
        compiler_exes = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = self._resolve_tool("clang", compiler_exes.get("c", ""))
        ar = self._resolve_tool("llvm-ar")
        ranlib = self._resolve_tool("llvm-ranlib")
        if not cc or not ar or not ranlib:
            raise ConanInvalidConfiguration(
                "jbjg requires clang, llvm-ar, and llvm-ranlib from the configured toolchain"
            )
        libjbig = os.path.join(self.source_folder, "libjbig")
        makefile = os.path.join(libjbig, "Makefile")
        with open(makefile, encoding="utf-8") as f:
            make_text = f.read()
        make_text = make_text.replace("ar rc", "{} rc".format(ar))
        make_text = make_text.replace("-ranlib ", "-{} ".format(ranlib))
        if "\ncheck: test\n" not in make_text:
            make_text += "\ncheck: test\n"
        with open(makefile, "w", encoding="utf-8", newline="\n") as f:
            f.write(make_text)
        cflags = "-O2 -W -Wno-unused-result"
        if bool(self.options.fPIC):
            cflags += " -fPIC"
        command = "make -C {} CC={} AR={} RANLIB={} CFLAGS={} all check".format(
            shlex.quote(libjbig),
            shlex.quote(cc),
            shlex.quote(ar),
            shlex.quote(ranlib),
            shlex.quote(cflags),
        )
        self.run(command)

    def package(self):
        libjbig = os.path.join(self.source_folder, "libjbig")
        copy(self, "libjbig.a", src=libjbig, dst=os.path.join(self.package_folder, "lib"))
        for h in ("jbig.h", "jbig_ar.h"):
            copy(self, h, src=libjbig, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["jbig"]
        self.cpp_info.includedirs = ["include"]
        # libtiff 走 find_package(JBIG)
        self.cpp_info.set_property("cmake_file_name", "JBIG")
        self.cpp_info.set_property("cmake_target_name", "JBIG::JBIG")
