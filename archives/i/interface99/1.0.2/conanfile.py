#!/usr/bin/env python3
"""Conan recipe for interface99 1.0.2 — full-featured interfaces for C99.

interface99 is a single-header, header-only C99 metaprogramming library
built on top of Metalang99 (its macro engine, also header-only).  The
upstream repository vendors Metalang99 through a git submodule and its
top-level CMake pulls it via FetchContent at configure time; a conan
package that ships only interface99.h would be unusable for consumers
(`#include <metalang99.h>` sits at the top of interface99.h), and
Metalang99 has no package in the registry yet.

This recipe therefore ships both header sets inside one package:

- sources: both official tag tarballs (interface99 v1.0.2, Metalang99
  v1.13.5 — the exact version upstream's FetchContent pins), each
  checksum-verified;
- layout: `include/interface99.h` + `include/metalang99.h` +
  `include/metalang99/…` so a plain `-I<pkg>/include` resolves both
  headers for consumers;
- upstream's own test suite (8 programs under tests/, which upstream
  builds as a separate CMake project with AddressSanitizer) is compiled
  and executed in build() without the sanitizer — OHOS musl ships no
  ASan runtime (platform gap, attributed in the PR description), the
  test logic itself is unchanged.

No CMake is run for the package itself: an INTERFACE library has nothing
to compile, and the headers are installed directly (cotila precedent).
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get


class Interface99Conan(ConanFile):
    name = "interface99"
    version = "1.0.2"
    description = ("interface99: full-featured interfaces (vtables) for C99, "
                   "implemented with the Metalang99 macro engine")
    license = "MIT"  # both interface99 and Metalang99 are MIT
    homepage = "https://github.com/Hirrolot/interface99"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def validate(self):
        # C99 is enforced at compile time by consumers/build recipes
        # (-std=c99); the OHOS profile carries no compiler.cstd, so a
        # check_min_cstd() here would reject every valid configuration.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"interface99 is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["interface99"], strip_root=True)
        # Metalang99 lands in a subfolder of its own: interface99.h does
        # `#include <metalang99.h>`, and the flat metalang99 tarball root
        # holds that header plus the `metalang99/` implementation headers.
        get(self, **self.conan_data["sources"]["metalang99"],
            destination=os.path.join(self.source_folder, "metalang99-src"),
            strip_root=True)

    def build(self):
        # No patches declared; upstream sources are used as-is.
        self._run_upstream_tests()

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        if compilers:
            if isinstance(compilers, str):
                import json
                try:
                    compilers = json.loads(compilers)
                except ValueError:
                    compilers = {}
            if compilers.get("c"):
                return compilers["c"]
        return "clang"

    def _run_upstream_tests(self):
        """Compile and run upstream's tests/ suite, unmodified.

        Upstream builds these as a separate CMake project with
        -fsanitize=address hard-wired for GCC/Clang; OHOS musl has no ASan
        runtime, so the sanitizer flag is dropped here (platform gap) while
        the test sources and C99 standard stay exactly as upstream's.
        """
        cc = self._cc()
        src = self.source_folder
        ml99 = os.path.join(src, "metalang99-src", "include")
        tests = os.path.join(src, "tests")
        workdir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(workdir, exist_ok=True)

        # Shield from ambient LD_LIBRARY_PATH: some CI workers carry
        # /usr/local/lib in it, whose incompatible libxml2.so.16 breaks
        # the SDK's lld (which links libxml2 for itself) on every link.
        shield = Environment()
        shield.define("LD_LIBRARY_PATH", "")
        with shield.vars(self).apply():
            self._compile_and_run_upstream_tests(cc, src, ml99, tests, workdir)

    def _compile_and_run_upstream_tests(self, cc, src, ml99, tests, workdir):
        # (name, extra sources relative to tests/)
        cases = [
            ("basic_tests", ["basic_tests.c", "common.c"]),
            ("vcalls", ["vcalls.c"]),
            ("decl_impl", ["decl_impl.c", "common.c"]),
            ("metalang99_compliant", ["metalang99_compliant.c"]),
            ("superinterfaces", ["superinterfaces.c", "common.c"]),
            ("default_impl", ["default_impl.c"]),
            ("version", ["version.c"]),
            ("extern_impl", ["extern_impl/test.c", "extern_impl/impl.c",
                             "common.c"]),
        ]
        includes = f"-I{shlex.quote(src)} -I{shlex.quote(ml99)}"
        extern_include = f"-I{shlex.quote(os.path.join(tests, 'extern_impl'))}"
        failures = []
        for name, sources in cases:
            exe = os.path.join(workdir, name)
            files = " ".join(shlex.quote(os.path.join(tests, s))
                             for s in sources)
            extra = "" if name != "extern_impl" else f" {extern_include}"
            compile_cmd = (f"{shlex.quote(cc)} -std=c99 {includes}{extra} "
                           f"{files} -o {shlex.quote(exe)}")
            self.run(compile_cmd, cwd=workdir)
            try:
                self.run(shlex.quote(exe), cwd=workdir)
                self.output.info(f"[upstream-test] {name}: PASS")
            except ConanException:
                failures.append(name)
                self.output.info(f"[upstream-test] {name}: FAIL")
        if failures:
            raise ConanException(
                f"upstream test suite failed: {', '.join(failures)}")
        self.output.info(
            "[upstream-test] 8/8 programs compiled and passed (ASan stripped, "
            "OHOS musl has no ASan runtime — attributed as platform gap)")

    def package(self):
        copy(self, "interface99.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)
        # Metalang99's headers live under its include/ directory
        # (metalang99.h + metalang99/): interface99.h does
        # `#include <metalang99.h>`, whose own includes are
        # `<metalang99/…>` — both resolve against package include/.
        copy(self, "metalang99.h",
             src=os.path.join(self.source_folder, "metalang99-src", "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)
        copy(self, "metalang99/*.h",
             src=os.path.join(self.source_folder, "metalang99-src", "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE", src=self.source_folder, dst=licenses,
             keep_path=False)
        os.replace(os.path.join(licenses, "LICENSE"),
                   os.path.join(licenses, "interface99-LICENSE"))
        copy(self, "LICENSE",
             src=os.path.join(self.source_folder, "metalang99-src"),
             dst=licenses, keep_path=False)
        os.replace(os.path.join(licenses, "LICENSE"),
                   os.path.join(licenses, "metalang99-LICENSE"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_target_name",
                                   "interface99::interface99")
        self.cpp_info.set_property("cmake_file_name", "interface99")
        self.cpp_info.set_property("pkg_config_name", "interface99")
