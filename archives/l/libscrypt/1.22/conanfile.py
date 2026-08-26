#!/usr/bin/env python3
"""Conan recipe for libscrypt 1.22 — scrypt KDF shared/static library.

Upstream: technion/libscrypt (tag v1.22), BSD-2-Clause.
Upstream uses a plain Makefile (no configure, no autotools).

Cross-compile notes (OHOS aarch64):
  * The upstream Makefile hardcodes the literal `ar` (not `$(AR)`) when
    building libscrypt.a. A minimal patch (patches/0001-Makefile-cross-compile.patch)
    introduces `AR ?= ar` defaults and uses `$(AR)`, so
    the Conan toolchain's archiver is honoured. No other Makefile behaviour
    is changed (no -march=native, no host probe, no strip upstream).
  * CC, AR, RANLIB, CFLAGS, LDFLAGS, PREFIX, DESTDIR are passed explicitly on
    the make command line — never inherited from the host shell, never the
    host gcc.
  * The glibc-specific upstream defaults `-D_FORTIFY_SOURCE=2` (in CFLAGS) and
    `-fstack-protector` / `-Wl,-rpath=.` (in CFLAGS_EXTRA) are dropped by
    overriding CFLAGS/LDFLAGS entirely; -fPIC is retained.
  * Only the library target `libscrypt.so.0` is built (it also produces
    libscrypt.a as a side effect). The demo `reference` binary is NOT built:
    it would require OHOS ELF signing to execute and is not a deliverable.

R33: compiler/AR come from Conan conf + buildenv, never host shell defaults.
R9:  make -j1.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibscryptConan(ConanFile):
    name = "libscrypt"
    version = "1.22"
    description = "Shared/static library implementing the scrypt KDF (a replacement for bcrypt)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/technion/libscrypt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── Toolchain resolution (R33: from Conan conf / buildenv, not host shell) ──
    def _cc(self):
        # Profile config may carry a stale toolchain path (e.g.
        # /data/service/hnp/bin/clang that does not exist on this host).
        # Verify the configured binary actually exists; otherwise fall
        # back to `clang` resolved from the Conan buildenv PATH, which on
        # OHOS is the real clang wrapper that auto-signs the ELF.
        import shutil
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = comp_execs.get("c", "clang")
        if os.path.isabs(cc):
            return cc if os.path.exists(cc) else "clang"
        return cc if shutil.which(cc) else "clang"

    def _ar(self):
        # Archiver from buildenv PATH (llvm-ar / ar); overridable via env.
        return os.environ.get("AR", "ar")

    def _ranlib(self):
        return os.environ.get("RANLIB", "ranlib")

    # ── OHOS SDK linker runtime path (lld/libxml2.so.16) ──────────────
    # The OHOS clang driver spawns `lld` for linking. lld is a dynamically
    # linked ELF whose NEEDED list includes libxml2.so.16, resolved via its
    # RUNPATH ($ORIGIN/../lib → the SDK llvm/lib). On CI workers the ambient
    # LD_LIBRARY_PATH (e.g. ~/usr/local/lib) can shadow that dir with an
    # ABI-mismatched libxml2.so.16, so lld fails to start with
    # "Error loading shared library libxml2.so.16 ... xmlFreeDoc: symbol not
    #  found" and clang-15 aborts with "linker command failed". This is NOT a
    # libscrypt source bug. Prepend the SDK's own llvm/lib so the lld that
    # make/clang invoke loads the SDK's matched libxml2 first.
    def _sdk_llvm_libdir(self):
        """Resolve the active OHOS SDK llvm/lib containing libxml2.so.16.

        Derives the dir from the real clang path (tools.build:compiler_executables
        → resolved by _cc()), never hardcoding a user name, an SDK version,
        or an absolute path. On non-OHOS hosts returns "".
        """
        if str(self.settings.os) != "OHOS":
            return ""
        cc = self._cc()
        cc_real = os.path.realpath(cc)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        # Only trust the dir if it actually carries libxml2.so.16 — guards
        # against stale profile paths or a bare `clang` on PATH whose parent
        # is not the SDK.
        if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            return llvm_lib
        return ""

    def _build_environment(self):
        """Conan Environment that prepends the SDK llvm/lib to LD_LIBRARY_PATH.

        Applied around every self.run() in build() so make → clang → lld all
        inherit it. No new Conan dependency is added (libxml2 is the SDK's own
        runtime, not a libscrypt build input).
        """
        env = Environment()
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path for lld: {sdk_lib}"
            )
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        return env

    def _cflags(self):
        bt = str(self.settings.build_type)
        opt = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }.get(bt, "-O2")
        # -fPIC retained (needed for both the .so and a relocatable .a);
        # upstream -D_FORTIFY_SOURCE=2 / -fstack-protector / -Wl,-rpath=. dropped.
        return f"{opt} -fPIC"

    def _ldflags(self):
        # Keep the useful upstream linker semantics: soname + version script
        # + relro. The version-script path is relative and resolves because
        # make runs in the source folder where libscrypt.version lives.
        return (
            "-Wl,-soname,libscrypt.so.0 "
            "-Wl,--version-script=libscrypt.version "
            "-Wl,-z,relro"
        )

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        base_args = [
            f'CC="{self._cc()}"',
            f'AR="{self._ar()}"',
            f'RANLIB="{self._ranlib()}"',
            f'CFLAGS="{self._cflags()}"',
            f'LDFLAGS="{self._ldflags()}"',
            f'PREFIX="{self.package_folder}"',
            "-j1",
        ]

        # All make/clang/lld invocations run inside the SDK linker-runtime
        # environment so lld finds the SDK's libxml2.so.16 (see
        # _build_environment / _sdk_llvm_libdir). On non-OHOS hosts this is
        # a no-op (empty Environment).
        with self._build_environment().vars(self).apply():
            # 1) Build the deliverable library (produces both libscrypt.so.0
            #    and libscrypt.a as the `ar`/`$(AR)` side effect).
            self.run("make -C {} libscrypt.so.0 {}".format(src, " ".join(base_args)))

            # 2) Build the upstream test binary `reference` (main.c). This is
            #    NOT a deliverable — it is the upstream automated test suite
            #    (13 tests: 2x RFC-7914 scrypt KAT, hexconvert, b64, MCF
            #    encode, mcf check, salt gen, hash+check round-trip). We
            #    build it explicitly rather than via `make check`, because
            #    `make check` re-invokes the link step with make's built-in
            #    `cc` default and would re-link with the host toolchain.
            self.run("make -C {} reference {}".format(src, " ".join(base_args)))

            # 3) Execute the upstream test suite. The heaviest case uses
            #    N=16384, r=8, p=16 (~16 MiB) — fast and CI-safe. On OHOS the
            #    PATH clang auto-signs the ELF via its -Wl,--code-sign
            #    wrapper, so ./reference runs without manual binary-sign-tool.
            #    can_run() guards cross-compile cases where the target binary
            #    cannot execute on the build host. The local `LD_LIBRARY_PATH=.`
            #    (to find the just-built libscrypt.so.0) is composed on top of
            #    the SDK lib dir the context already set.
            if can_run(self):
                self.run("LD_LIBRARY_PATH=. ./reference", cwd=src)

    def package(self):
        inc = os.path.join(self.package_folder, "include")
        lib = os.path.join(self.package_folder, "lib")
        copy(self, "libscrypt.h", self.source_folder, inc, keep_path=False)
        if self.options.shared:
            copy(self, "libscrypt.so.0", self.source_folder, lib, keep_path=False)
            # Provide the -lscrypt linker symlink libscrypt.so -> libscrypt.so.0
            so = os.path.join(lib, "libscrypt.so")
            if not os.path.lexists(so):
                os.symlink("libscrypt.so.0", so)
        else:
            copy(self, "libscrypt.a", self.source_folder, lib, keep_path=False)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # -lscrypt resolves to libscrypt.a (static) or libscrypt.so (shared).
        self.cpp_info.libs = ["scrypt"]
        # libscrypt links -lm (and -lc); static consumers must provide -lm.
        self.cpp_info.system_libs = ["m"]
