#!/usr/bin/env python3
"""Conan recipe — scanelf 1.3.9 (GPL-2.0-only)

scanelf is one tool of Gentoo's PaX/ELF userland suite (pax-utils).  This
package is a per-tool split: it is built from the upstream pax-utils 1.3.9
tree but ships **only** the `scanelf` executable.  The other tools of the same
tree (dumpelf, pspax, scanmacho, lddtree, symtree) belong to the aggregate
package archives/p/pax-utils/1.3.10 and are pruned here.

Build system: Meson (meson.build + tests/*/meson.build).
  meson setup -Dtests=true ... && ninja && meson test

Verified facts that shaped this recipe (same measurements as pax-utils/1.3.10,
re-checked against the 1.3.9 tree):
  * The device PATH has ninja/python3/bash/git/pkg-config but **no meson**, while
    the ohpcd registry does publish meson/1.11.0, ninja/1.12.1 and pkgconf/3.0.5
    (all three resolve as prebuilt binaries there — `conan download` of each
    reference succeeds, rc=0, re-probed 2026-09-30), so the build tools come in
    as tool_requires rather than PATH assumptions.
  * xmlto is absent on the device, so man pages are disabled rather than
    'auto' (which would make the man/ subdir fail).
  * `vcs_tag()` in meson.build has no `fallback`, but meson defaults the
    fallback to project_version (mesonbuild/interpreter/interpreter.py:2089),
    so a plain GitHub tag tarball configures fine — no patch needed.
  * use_fuzzing builds two libFuzzer targets and *runs* them as tests; they are
    sanitiser probes, not functional tests, so they stay off.
  * Two independent blockers live in security_init(); both measured on device:
      1. unshare(CLONE_NEW*) is killed by the platform's own seccomp policy
         (SIGSYS, exit 159) rather than returning EPERM, which is the only
         failure the upstream fallback handles -> patches/0002 guards the
         syscall with a SIGSYS handler and degrades a trap to EPERM at runtime
         (no platform conditional compilation).
      2. With (1) fixed, the app's hand-written BPF allowlist still kills
         dumpelf and pspax (both call security_init(false) ->
         seccomp_bpf_program_base) with SIGSYS, while scanelf itself
         (security_init(true) -> the *fork* program) survives.  The allowlist is
         written for Gentoo/glibc syscall usage, so it is turned off here; the
         tool keeps working, it just no longer self-demotes.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (get, copy, rm, apply_conandata_patches,
                               export_conandata_patches)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class ScanelfConan(ConanFile):
    name = "scanelf"
    version = "1.3.9"
    description = ("scanelf: ELF/PaX information scanner from Gentoo pax-utils "
                   "(symbol lookup, DT_NEEDED, ELF header and section dump)")
    license = "GPL-2.0-only"
    homepage = "https://github.com/gentoo/pax-utils"
    url = ""  # CI fills this
    topics = ("elf", "gentoo", "pax-utils", "symbols", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # The aggregate package pax-utils/1.3.10 builds the same tree; this split
    # exists so that consumers wanting only the ELF scanner do not pull the
    # whole tool set.
    provides = "pax-utils"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # R36: all three are published on the ohpcd remote (probe rc=0).
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        # conan 2.29.1 exports only Meson/MesonToolchain from conan.tools.meson
        # (there is no meson_layout), and the Meson helper drives
        # `meson setup <build_folder> <source_folder>`, so a plain basic layout
        # is what its own docstring expects.
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        # The codeload URL has no archive extension, so name the download
        # explicitly or Conan guesses the wrong format (BadZipFile).
        get(self, filename="pax-utils-1.3.9.tar.gz",
            **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "static"
        tc.project_options["tests"] = True                 # register upstream dotest suites
        tc.project_options["use_fuzzing"] = False          # libFuzzer probes, not functional tests
        tc.project_options["use_libcap"] = "disabled"      # keeps the package dependency-free
        tc.project_options["use_seccomp"] = False          # see module docstring, blocker (2)
        tc.project_options["build_manpages"] = "disabled"  # xmlto is not available
        # lddtree is not shipped by this package, but the upstream suite
        # (tests/lddtree, tests/pspax, tests/scanelf, tests/source) exercises the
        # whole tree; the shell implementation keeps that suite dependency-free
        # (the python one needs pyelftools, which is absent on the target).
        tc.project_options["lddtree_implementation"] = "sh"
        # The OHOS profile publishes only clang/clang++ under
        # tools.build:compiler_executables, and conan's Meson helper does not
        # inject the profile buildenv into the `meson setup` subprocess (the same
        # "Meson 工具类不加载自定义 env" caveat recorded in archives/a/account-utils).
        # meson then falls back to PATH to find clang's default archiver `llvm-ar`,
        # which is absent there on the CI worker -> configure dies at
        # `meson.build:1:0: ERROR: Unknown linker(s): [['llvm-ar']]`.  Pin every
        # LLVM tool to the real directory of the resolved clang, exactly as the
        # merged archives/j/jose/15 recipe does; guarded so a plain harmonybrew
        # device (llvm-ar already on PATH) keeps using conan's defaults.
        hnp = "/data/service/hnp/bin"
        if os.path.isdir(hnp):
            llvm = os.path.realpath(os.path.join(hnp, "clang"))
            bindir = os.path.dirname(llvm)
            tc.binaries["c"] = os.path.join(bindir, "clang")
            tc.binaries["cpp"] = os.path.join(bindir, "clang++")
            tc.binaries["ar"] = os.path.join(bindir, "llvm-ar")
            tc.binaries["ranlib"] = os.path.join(bindir, "llvm-ar")
            tc.binaries["nm"] = os.path.join(bindir, "llvm-nm")
            tc.binaries["strip"] = os.path.join(bindir, "llvm-strip")
            tc.binaries["ld"] = os.path.join(bindir, "ld.lld")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Upstream official suite: meson.test() runs tests/{lddtree,pspax,scanelf,source}
        # (tests/scanelf is the one that covers this package's deliverable).
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        # Per-tool split (see module docstring): keep bin/scanelf only and drop
        # the rest of the suite that meson installs from the same tree.  Nothing
        # shared is left behind — scanelf is a self-contained executable and this
        # package builds no library.
        bindir = os.path.join(self.package_folder, "bin")
        for other in ("dumpelf", "pspax", "scanmacho", "lddtree", "symtree"):
            rm(self, other, bindir)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
