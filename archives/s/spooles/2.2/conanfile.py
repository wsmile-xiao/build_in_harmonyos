#!/usr/bin/env python3
"""Conan recipe — spooles 2.2 (plain Makefile, static library).

SPOOLES (SParse Object Oriented Linear Equations Solver) is a C library
for solving sparse real and complex linear systems of equations, released
into the public domain by Boeing Phantom Works (netlib).

Build system: hand-written recursive makefiles, no configure script.
The archive expands with no top-level directory (Make.inc and the
top-level "makefile" sit at the source root), so source() uses
strip_root=False. The library target is `make -f makefile global -j1`
(sequential sub-makes, never parallel). Output is a single static
archive spooles.a, installed as lib/libspooles.a; all module headers are
installed preserving the in-tree layout (flat guarded wrappers like
"IV.h" plus per-module "IV/IV.h") so consumer includes must use the
flat wrappers (#include "IV.h") with a single -I<package>/include.

Upstream ships no test harness (no check/test/ctest target, only
per-module driver programs needing external input files), so build()
emits a no_tests HMBS_UPSTREAM_TEST_RESULT marker after verifying that.
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class SpoolesConan(ConanFile):
    name = "spooles"
    version = "2.2"
    description = "SParse Object Oriented Linear Equations Solver: C library for solving sparse real and complex linear systems of equations"
    license = "LicenseRef-SPOOLES-Public-Domain"
    homepage = "https://www.netlib.org/linalg/spooles/spooles.2.2.html"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "spooles 2.2 upstream only builds a static archive "
                "('make -f makefile global'); shared is not supported"
            )
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "spooles supports Linux/OHOS only, got %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # The 2.2 archive expands into the current directory (no top-level
        # folder); strip_root must stay False.
        get(self, **self.conan_data["sources"], strip_root=False)

    def build(self):
        self._patch_make_inc()
        self._fix_tree_make_global_lib()
        self._assert_no_upstream_test_target()
        # R9: the global archive build drives sequential sub-makes,
        # never parallel.
        self.run("make -f makefile global -j1", cwd=self.source_folder)
        archive = os.path.join(self.source_folder, "spooles.a")
        if not os.path.isfile(archive):
            raise RuntimeError("spooles.a was not produced by 'make global'")
        self._emit_no_tests_marker()

    def _compiler_tools(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # The profile hardcodes the CI worker layout (/data/service/hnp/bin);
        # on machines where that absolute path does not exist, fall back to
        # resolving the same tool from PATH (the profile prepends the real
        # toolchain bin/ to PATH). Keeps CI semantics when the path exists.
        if not os.path.isfile(cc):
            cc = shutil.which("clang") or cc
        toolchain_bin = os.path.dirname(cc) if os.path.dirname(cc) else None
        ar = compilers.get("ar") or (
            os.path.join(toolchain_bin, "llvm-ar") if toolchain_bin else "llvm-ar"
        )
        ranlib = compilers.get("ranlib") or (
            os.path.join(toolchain_bin, "llvm-ranlib") if toolchain_bin else "llvm-ranlib"
        )
        for tool in (ar, ranlib):
            if not os.path.isfile(tool):
                resolved = shutil.which(os.path.basename(tool))
                if resolved:
                    if tool == ar:
                        ar = resolved
                    else:
                        ranlib = resolved
        return cc, ar, ranlib

    def _patch_make_inc(self):
        """Point Make.inc at the Conan toolchain (R33: from conf, not env)."""
        path = os.path.join(self.source_folder, "Make.inc")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        cc, ar, ranlib = self._compiler_tools()
        self.output.info("spooles toolchain: CC=%s AR=%s RANLIB=%s"
                         % (cc, ar, ranlib))
        # Upstream defaults: CC=/usr/lang-4.0/bin/cc, CFLAGS=$(OPTLEVEL),
        # RANLIB=echo (no-op). -fPIC: the static archive may link into
        # shared consumers on OHOS. -Wno-error=int-conversion: 1999-era
        # code passes NULL for int params (e.g. IVinit(nfront, NULL) in
        # ETree/src/transform.c); NULL==0 semantically, modern clang
        # promotes -Wint-conversion to an error, so downgrade it.
        replacements = (
            (r"(?m)^\s*CC\s*=.*$", "  CC = %s" % cc),
            (r"(?m)^\s*CFLAGS\s*=.*$",
             "  CFLAGS = -O2 -fPIC -Wno-error=int-conversion"),
            (r"(?m)^\s*AR\s*=.*$", "  AR = %s" % ar),
            (r"(?m)^\s*RANLIB\s*=.*$", "  RANLIB = %s" % ranlib),
        )
        for pattern, new_line in replacements:
            new_text, count = re.subn(pattern, new_line, text, count=1)
            if count != 1:
                raise RuntimeError(
                    "Make.inc format changed, cannot apply %r" % new_line)
            text = new_text
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def _fix_tree_make_global_lib(self):
        """Tree/src/makeGlobalLib references drawTree.c, the 2.2 tarball
        ships draw.c. Without this fix 'make global' fails in Tree/src."""
        path = os.path.join(self.source_folder, "Tree", "src",
                             "makeGlobalLib")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        if "drawTree.c" not in text:
            raise RuntimeError(
                "Tree/src/makeGlobalLib no longer references drawTree.c, "
                "re-check the upstream source layout")
        if not os.path.isfile(
                os.path.join(self.source_folder, "Tree", "src", "draw.c")):
            raise RuntimeError("Tree/src/draw.c missing from upstream source")
        text = text.replace("drawTree.c", "draw.c")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def _assert_no_upstream_test_target(self):
        """Evidence for the no_tests audit: the top-level makefile offers
        only drivers/lib/global/clean targets, no check/test harness."""
        path = os.path.join(self.source_folder, "makefile")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            targets = re.findall(r"(?m)^([A-Za-z][\w.-]*)\s*:",
                                 f.read())
        for banned in ("check", "test", "tests"):
            if banned in targets:
                raise RuntimeError(
                    "upstream makefile gained a '%s' target, "
                    "re-audit upstream tests" % banned)

    def _emit_no_tests_marker(self):
        upstream = {
            "status": "no_tests",
            "framework": "make-drivers",
            "command": "make -f makefile global -j1 (library build only)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "upstream 2.2 ships no check/test/ctest target; "
                      "per-module drivers need external input files, "
                      "see test_package/MANIFEST.yml audit",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream, ensure_ascii=False))

    def package(self):
        copy(self, "spooles.a", self.source_folder,
             os.path.join(self.package_folder, "lib"),
             keep_path=False)
        os.rename(os.path.join(self.package_folder, "lib", "spooles.a"),
                  os.path.join(self.package_folder, "lib", "libspooles.a"))
        # Keep the in-tree header layout (flat guarded wrappers like IV.h
        # plus per-module IV/IV.h); consumers include the flat wrappers
        # with a single -I<package>/include.
        copy(self, "*.h", self.source_folder,
             os.path.join(self.package_folder, "include"), keep_path=True)

    def package_info(self):
        self.cpp_info.libs = ["spooles"]
        self.cpp_info.set_property("cmake_file_name", "spooles")
        self.cpp_info.set_property("cmake_target_name", "spooles::spooles")
        self.cpp_info.set_property("pkg_config_name", "spooles")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
