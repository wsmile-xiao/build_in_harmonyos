#!/usr/bin/env python3
"""Conan recipe for libcello 2.1.0 — upstream GNU make Makefile build system.

Cello is a higher-level-programming-in-C library (objects, GC, exceptions,
containers). It ships a hand-written GNU make Makefile (no CMake/autotools).

Zero patches: the upstream source builds and links cleanly on OHOS arm64.
The Makefile's Linux branch is used (OHOS defines __unix__, so the upstream
platform detection selects the Linux branch). OHOS musl libc provides
execinfo.h with real backtrace/backtrace_symbols symbols in libc.so, so the
backtrace feature is kept enabled (CELLO_NSTRACE is NOT forced).

Build note: the upstream Makefile uses immediate assignments
(`CFLAGS =`, `LIBS =`, `LFLAGS =`) that ignore environment variables, but
`CC ?= gcc` and `AR ?= ar` DO respect the environment. The C/C++ compiler is
read directly from the Conan conf key `tools.build:compiler_executables`
(the authoritative source — the OHOS profile sets it to the SDK clang), NOT
from os.environ["CC"] / shutil.which("clang"), which resolve to the wrong
clang in CI sandboxes. CFLAGS/LIBS use `=` so they are passed on the make
command line (command-line overrides win over `=` assignments).

Shared/static: the upstream Makefile's `all` target builds BOTH libCello.a
and libCello.so, and both build cleanly on OHOS. This recipe supports both:
  shared=False (default) -> libCello.a
  shared=True             -> libCello.so
build() selects only the relevant make target so no unused artifact is built.
The upstream libCello.so is unversioned (no DT_SONAME, no versioned symlink);
this is preserved as-is (adding -soname would exceed upstream behavior, i.e.
a build patch). Consumers find it via -lCello + Conan RPATH.

Dependencies: -lpthread -lm (OHOS musl libc merges these into libc.so, so they
are no-ops on OHOS but declared for correctness/parity with upstream Linux).

OHOS lld runtime: the SDK's lld (invoked by clang at the final link step of
both libCello.a/so and ./tests/test) is itself dynamically linked against
libxml2.so.16, which lives in the LLVM distribution's host lib dir (the
sibling `lib/` of the real clang path). That dir is not on the default
LD_LIBRARY_PATH, so the link fails with "Error loading shared library
libxml2.so.16". The host lib dir is derived dynamically from the active
compiler's real path (realpath(cc) -> .../llvm/bin/clang -> .../llvm/lib),
and LD_LIBRARY_PATH is injected via Conan's native Environment so it
propagates to every subprocess (make -> clang -> lld). A pre-build lld probe
verifies lld can actually load libxml2.so.16 with the computed path, failing
loudly before `make` if the derivation is wrong. No hardcoded SDK version or
machine path. Proven pattern: minised/1.16.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import get, copy


class CelloConan(ConanFile):
    name = "libcello"
    version = "2.1.0"
    description = "Higher level programming in C (objects, GC, exceptions, containers)"
    license = "BSD-2-Clause"
    homepage = "https://libcello.org/"
    url = ""
    topics = ("cello", "oop", "gc", "c")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        # fPIC is only meaningful for position-independent code (shared libs
        # and relocatable static). On Windows it is irrelevant.
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        # When building a shared lib, -fPIC is mandatory and implicit; the
        # standalone fPIC option is redundant (repo convention: lzo/lame).
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        # No patches to export; kept for spec-compliance / future use.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── Compiler & OHOS SDK runtime (proven minised/1.16 pattern) ──────
    def _get_cc(self):
        # Read the C compiler directly from the Conan conf key
        # tools.build:compiler_executables — the authoritative source the OHOS
        # profile sets to the SDK clang. Never fall back to
        # os.environ["CC"] / shutil.which("clang") as the primary source:
        # in the CI sandbox those resolve to a system clang whose sibling
        # lib/ has no libxml2.so.16, silently breaking lld at link time.
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        return compilers.get("c") or "clang"

    def _get_cxx(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        return compilers.get("cpp") or compilers.get("c") or "clang++"

    def _get_ar(self):
        # Derive llvm-ar from the active compiler's real bin dir (sibling
        # toolchain tool). Falls back to "llvm-ar" (PATH-resolved) so a
        # non-OHOS or oddly laid-out SDK still works.
        cc = self._get_cc()
        try:
            real_cc = os.path.realpath(cc)
        except OSError:
            return "llvm-ar"
        cand = os.path.join(os.path.dirname(real_cc), "llvm-ar")
        return cand if os.path.isfile(cand) else "llvm-ar"

    def _sdk_llvm_libdir(self):
        # Derive the OHOS LLVM host lib dir (where lld's libxml2.so.16 lives)
        # from the active compiler's real path: realpath(cc) ->
        # .../llvm/bin/clang -> .../llvm/lib. Only return if libxml2.so.16 is
        # actually present, so a misconfigured path fails loudly at probe time
        # instead of silently injecting an empty LD_LIBRARY_PATH.
        if str(self.settings.os) != "OHOS":
            return ""
        cc = self._get_cc()
        try:
            real_cc = os.path.realpath(cc)
        except OSError:
            return ""
        llvm_lib = os.path.join(
            os.path.dirname(os.path.dirname(real_cc)), "lib"
        )
        if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            return llvm_lib
        return ""

    def _probe_lld(self, sdk_lib):
        # Self-check: ensure lld (the linker clang invokes at the final link
        # step) can actually load its libxml2.so.16 dependency with the
        # computed LD_LIBRARY_PATH. Failing here — before `make` — gives a
        # clear error instead of a cryptic link-time "Error loading shared
        # library libxml2.so.16" that only surfaces at `make check`.
        cc = self._get_cc()
        try:
            real_cc = os.path.realpath(cc)
        except OSError as e:
            raise ConanException(
                f"OHOS lld probe: cannot resolve compiler path {cc}: {e}"
            )
        bin_dir = os.path.dirname(real_cc)
        lld = None
        for cand in ("lld", "ld.lld"):
            p = os.path.join(bin_dir, cand)
            if os.path.isfile(p):
                lld = p
                break
        if not lld:
            raise ConanException(
                f"OHOS lld probe: lld not found in {bin_dir} "
                "(SDK layout unexpected)"
            )
        probe_env = dict(os.environ)
        existing = probe_env.get("LD_LIBRARY_PATH", "")
        probe_env["LD_LIBRARY_PATH"] = (
            sdk_lib + (os.pathsep + existing if existing else "")
        )
        try:
            res = subprocess.run(
                [lld, "-flavor", "gnu", "--version"],
                capture_output=True, text=True, env=probe_env,
            )
        except (OSError, subprocess.SubprocessError) as e:
            raise ConanException(
                f"OHOS lld probe: failed to run {lld}: {e}"
            )
        if res.returncode != 0:
            raise ConanException(
                f"OHOS lld probe: `{lld} -flavor gnu --version` exited "
                f"rc={res.returncode} — libxml2.so.16 not loadable from "
                f"{sdk_lib}; stderr:\n{res.stderr.strip()}"
            )
        first = res.stdout.splitlines()[0].strip() if res.stdout.strip() else "ok"
        self.output.info(f"OHOS lld probe OK: {lld} -> {first}")

    def build(self):
        cc = self._get_cc()
        ar = self._get_ar()

        # CFLAGS: match the upstream Linux branch, adjusted for OHOS.
        # Upstream Linux: -I ./include -std=gnu99 -Wall -Wno-unused -g -ggdb
        cflags = ["-I./include", "-std=gnu99", "-Wall", "-Wno-unused"]
        if self.options.get_safe("fPIC") or self.options.shared:
            cflags.append("-fPIC")
        if self.settings.build_type == "Release":
            cflags += ["-O2", "-DNDEBUG"]
        else:
            cflags += ["-g"]
        # OHOS musl libc merges libm + pthread into libc.so (verified:
        # floor/pthread_create are T symbols in libc.so; libm.so/libpthread.so
        # absent). -lm/-lpthread still resolve via the 8-byte redirect stubs,
        # so they are harmless and match upstream exactly.
        libs = "-lpthread -lm"

        make_vars = (
            f'CC="{cc}" AR="{ar}" '
            f'CFLAGS="{" ".join(cflags)}" '
            f'LIBS="{libs}" '
            f'LFLAGS=""'
        )

        # OHOS lld runtime: build the Conan-native Environment once and scope
        # BOTH the library build and `make check` under it. lld is a
        # subprocess of clang at the final link step of both libCello.a/so
        # and ./tests/test, so LD_LIBRARY_PATH must survive the whole make
        # invocation — a raw os.environ tweak does not reliably propagate to
        # Conan's generated run/build scripts; Environment().prepend_path +
        # env.vars(self).apply() does.
        env = Environment()
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path: {sdk_lib}"
            )
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
            self._probe_lld(sdk_lib)

        target = "libCello.so" if self.options.shared else "libCello.a"
        nproc = os.cpu_count() or 1
        with env.vars(self).apply():
            # Build only the artifact matching the shared option (the
            # Makefile's `all` builds both; selecting one target avoids a
            # wasted build and makes the produced artifact unambiguous).
            self.run(f'make -j{nproc} {target} {make_vars}')

            # ── Upstream official tests (make check) ───────────────────
            # The upstream Makefile's `check` target compiles tests/*.c,
            # links ./tests/test against libCello.a (it always uses the
            # static lib, regardless of the shared option) with the same
            # CC/CFLAGS/LIBS, then RUNS ./tests/test — the real upstream
            # test suite (21 suites, 133 tests, 1639 assertions via
            # ptest.h). This must run during the conan create build phase on
            # OHOS (not just in a prior manual run): L1 requires upstream-
            # test execution evidence in the conan create log. The same
            # Environment scope covers check because it links ./tests/test
            # via clang -> lld. No || true / ignore_errors / skip: a test
            # failure must fail conan create (hard rule: upstream has
            # official tests -> they must really build+run on OHOS AArch64).
            self.run(f'make -j{nproc} check {make_vars}')

    def package(self):
        # Header lives at source_folder/include/Cello.h — copy from the
        # include/ subdir with keep_path=False so it lands at dst/Cello.h
        # (not a doubled include/include/Cello.h).
        copy(self, "Cello.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)
        if self.options.shared:
            copy(self, "libCello.so", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        else:
            copy(self, "libCello.a", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["Cello"]
        self.cpp_info.includedirs = ["include"]
        # Upstream Makefile links -lpthread -lm on Linux/OHOS. OHOS musl merges
        # these into libc.so, so they are no-ops on OHOS but declared for
        # correctness/parity with the upstream link line.
        self.cpp_info.system_libs = ["pthread", "m"]
