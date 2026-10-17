#!/usr/bin/env python3
"""Conan recipe for ddate 0.2.2 — Discordian date converter (C).

ddate prints Gregorian dates in Discordian (Erisian) calendar format.
Upstream is a single-file C program (ddate.c) with a trivial 8-line
CMakeLists (add_executable + gzip manpage + install). CMake 4.x on the
OHOS worker repeatedly fails at project() with "System is unknown to
cmake: Platform/HarmonyOS" + "The C compiler identification is unknown"
(3 preflight rounds: Linux-mapping, then E557 host-runtime probe, both
still red at cmake.configure()). This recipe therefore builds the same
artifact without CMake: compile ddate.c directly with the configured
OHOS clang and gzip the manpage with the Python stdlib. No dependencies,
no upstream test suite (see test_package/MANIFEST.yml audit).

Knowledge applied: bambootracker precedent (pure executable: no
cpp_info.libs, test_package runs installed binary).
"""
import gzip
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class DdateConan(ConanFile):
    name = "ddate"
    version = "0.2.2"
    description = "Perpetual date converter from Gregorian to Discordian (Erisian) calendar"
    license = "public-domain"
    homepage = "https://github.com/bo0ts/ddate"
    url = "https://github.com/bo0ts/ddate"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # R33: compiler comes from Conan conf (authoritative OHOS profile
        # value), never from a bare ${CC} shell variable.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if not cc:
            return shutil.which("clang") or "clang"
        if os.path.isfile(cc):
            return cc
        return shutil.which(os.path.basename(cc)) or cc

    def build(self):
        cc = self._get_cc()
        src = os.path.join(self.source_folder, "ddate.c")
        if not os.path.isfile(src):
            raise ConanException(f"ddate.c not found in source tree: {src}")
        os.makedirs(self.build_folder, exist_ok=True)
        out = os.path.join(self.build_folder, "ddate")
        # Same artifact as upstream add_executable(ddate ddate.c).
        # Plain native compile: no --target/--sysroot overrides, no CMake
        # platform detection involved. Result is a native OHOS binary.
        cmd = [cc, src, "-O2", "-o", out]
        self.output.info("ddate direct compile: " + " ".join(cmd))
        try:
            subprocess.run(
                cmd, check=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, timeout=300,
            )
        except subprocess.CalledProcessError as err:
            raise ConanException(
                f"ddate direct compile failed: {err.output or err}"
            )
        except (OSError, subprocess.SubprocessError) as err:
            raise ConanException(f"ddate direct compile failed: {err}")

    def package(self):
        copy(self, "ddate", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # Upstream: gzip -c -9 ddate.1 > ddate.1.gz, install to
        # share/man/man1. Done with the stdlib: no shell gzip dependency,
        # no /tmp usage (readonly_tmp safe).
        man_src = os.path.join(self.source_folder, "ddate.1")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        if os.path.isfile(man_src):
            with open(man_src, "rb") as fin:
                with gzip.open(os.path.join(man_dir, "ddate.1.gz"),
                               "wb", compresslevel=9) as fout:
                    shutil.copyfileobj(fin, fout)
        else:
            self.output.warning(f"manpage not found, skipping: {man_src}")

    def package_info(self):
        # Pure executable package: no libraries to link against.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
