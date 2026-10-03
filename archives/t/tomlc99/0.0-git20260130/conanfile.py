#!/usr/bin/env python3
"""Conan recipe for tomlc99 0.0-git20260130 — TOML v1.0.0 parser in C99.

Upstream (https://github.com/cktan/tomlc99) is a single-file library
(toml.c + toml.h) built by a plain Makefile that produces:
  - libtoml.a / libtoml.so.1.0  (LIB_VERSION = 1.0)
  - CLI tools toml_cat / toml_json / toml_sample, linked against the
    static archive by make's built-in link rules.

The master branch is the only line of development (no release tags);
per repo convention the snapshot version is 0.0-gitYYYYMMDD — the
pinned master.tar.gz content is dated 2026-01-30 (same convention as
asmjit 0.0-git20231115.1da9e4d).

W0 dependency check: tomlc99 is pure C99 with zero dependencies —
toml.c only includes libc headers (stdio/stdlib/string/ctype/assert/
inttypes); no `requires()` entries and no system libs beyond libc.

Patch 0001 adds -Wl,-soname,libtoml.so.$(LIB_VERSION) to the shared
library link line: upstream links libtoml.so.1.0 with no SONAME field,
which fails the CI L5a quality gate (linkable shared libs must carry a
relative DT_SONAME). tomlc99 is NOT a system-name library, so R26
forced-static does not apply; the default dynamic library is managed
by Conan's dependency chain.

Upstream test surface (real runs, mirrored in test_package):
  - unittest/t1.c  — 20 assertions over toml_utf8_to_ucs/toml_ucs_to_utf8
  - stdex/*.toml   — 62 spec examples: toml_cat output vs *.res
  - test1/ (Go toml-test harness) and test2/ (toml-spec-tests + jq)
    need external toolchains/network and are waived — see
    test_package/MANIFEST.yml for the per-suite rationale.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class Tomlc99Conan(ConanFile):
    name = "tomlc99"
    version = "0.0-git20260130"
    description = "TOML v1.0.0 compliant parser written in C99 (single toml.c + toml.h)"
    license = "MIT"
    homepage = "https://github.com/cktan/tomlc99"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # tomlc99 is a pure C99 library with no runtime dependencies
        # (W0 confirmed: only libc headers are included by toml.c).
        pass

    def validate(self):
        # R32: settings.os must be checked with "in", never "==".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tomlc99 is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler path comes from Conan conf (the ohos-aarch64 profile
        # sets tools.build:compiler_executables), never from bare shell env.
        # conan 2.29.1 registers this conf as a DICT — reading the ":c" subkey
        # as a scalar raises ConanInvalidConfiguration, so read the dict and
        # pick the C compiler (same fix as bzip2 1.0.8 / abc recipes).
        # Note: the upstream Makefile hardcodes `ar -rcs` (not $(AR)), so AR
        # is resolved from PATH (/data/service/hnp/bin/ar on CI workers).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # R9: -j1. CFLAGS stay upstream-owned
        # (-std=c99 -Wall -Wextra -fpic -O2 -DNDEBUG) — do not override.
        # `make all` builds libtoml.a, libtoml.so.1.0 and the three tools.
        # Run in the source folder: the Makefile lives there, not in the
        # conan build dir (same as bzip2 1.0.8 Makefile recipe).
        self.run(f"make CC={cc} -j1 all", cwd=self.source_folder)

    def package(self):
        # Header
        copy(self, "toml.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        # Libraries
        if self.options.shared:
            # libtoml.so.1.0 carries DT_SONAME=libtoml.so.1.0 (patch 0001)
            copy(self, "libtoml.so.1.0", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "lib"))
            # Dev symlink libtoml.so -> libtoml.so.1.0 so -ltoml resolves at
            # link time (R5: rm -f && ln -s). Runtime lookup goes through the
            # SONAME file itself, so only link-time needs the symlink.
            libdir = os.path.join(self.package_folder, "lib")
            link = os.path.join(libdir, "libtoml.so")
            if os.path.lexists(link):
                os.remove(link)
            os.symlink("libtoml.so.1.0", link)
        else:
            copy(self, "libtoml.a", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "lib"))

        # CLI tools — statically linked against libtoml.a by the upstream
        # Makefile ($(EXEC): $(LIB)), so they run without the shared lib.
        # toml_sample is a demo requiring ./sample.toml in cwd; not shipped.
        for tool in ("toml_cat", "toml_json"):
            copy(self, tool, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "bin"))

        # Upstream stdex regression assets for the conan test_package stage:
        # 62 *.toml spec examples + expected *.res outputs, driven by the
        # packaged bin/toml_cat (mirrors upstream stdex/RUN.sh exactly).
        copy(self, "*.toml", src=os.path.join(self.source_folder, "stdex"),
             dst=os.path.join(self.package_folder, "test", "stdex"))
        copy(self, "*.res", src=os.path.join(self.source_folder, "stdex"),
             dst=os.path.join(self.package_folder, "test", "stdex"))

    def package_info(self):
        self.cpp_info.libs = ["toml"]
        # toml_cat / toml_json CLI tools ship in bin/
        # (R38: declared in the software-level commands.json)
        self.cpp_info.bindirs = ["bin"]
