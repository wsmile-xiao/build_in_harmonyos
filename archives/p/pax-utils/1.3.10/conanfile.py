#!/usr/bin/env python3
"""Conan recipe — pax-utils 1.3.10 (GPL-2.0-only)

Gentoo's PaX/ELF userland utilities: scanelf, dumpelf, pspax, scanmacho and the
lddtree / symtree scripts.

Build system: Meson (meson.build + tests/*/meson.build).
  meson setup -Dtests=true ... && ninja && meson test
Upstream CI (.github/workflows/build-test-ci.yml) runs `ninja -C build test`,
and ci-alpine-linux.yml builds the same tree on musl — a good OHOS signal.

Verified facts that shaped this recipe:
  * The device PATH has ninja/python3/bash/git/pkg-config but **no meson**, while
    the ohpcd registry does publish meson/1.11.0, ninja/1.12.1 and pkgconf/3.0.5
    (all three resolve as prebuilt binaries there — `conan download` of each
    reference succeeds, rc=0), so the build tools come in as tool_requires rather
    than PATH assumptions.
  * xmlto is absent on the device, so man pages are disabled rather than
    'auto' (which would make the `man/` subdir fail).
  * `vcs_tag()` in meson.build has no `fallback`, but meson defaults the
    fallback to project_version (mesonbuild/interpreter/interpreter.py:2089),
    so a plain GitHub tag tarball configures fine — no patch needed.
  * use_fuzzing builds two libFuzzer targets and *runs* them as tests; they are
    sanitiser probes, not functional tests, so they stay off (see notes.md).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (get, copy, apply_conandata_patches,
                               export_conandata_patches)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PaxUtilsConan(ConanFile):
    name = "pax-utils"
    version = "1.3.10"
    description = ("Gentoo PaX/ELF userland inspection tools: scanelf, dumpelf, "
                   "pspax, scanmacho, lddtree and symtree")
    license = "GPL-2.0-only"
    homepage = "https://github.com/gentoo/pax-utils"
    url = ""  # CI fills this
    topics = ("elf", "gentoo", "scanelf", "lddtree", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        get(self, filename="pax-utils-1.3.10.tar.gz",
            **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "static"   # R26
        tc.project_options["tests"] = True                 # register upstream dotest suites
        tc.project_options["use_fuzzing"] = False          # libFuzzer probes, not functional tests
        tc.project_options["use_libcap"] = "disabled"      # keeps the package dependency-free
        # Two independent blockers live in security_init(); both measured on
        # device, see notes.md:
        #   1. unshare(CLONE_NEW*) is killed by the platform's own seccomp policy
        #      (SIGSYS, exit 159) rather than returning EPERM, which is the only
        #      failure the upstream fallback handles -> patches/0002, which
        #      guards the syscall with a SIGSYS handler and degrades a trap to
        #      EPERM at runtime (no platform conditional compilation).
        #   2. With (1) fixed, the app's hand-written BPF allowlist still kills
        #      dumpelf and pspax (both call security_init(false) ->
        #      seccomp_bpf_program_base) with SIGSYS at exit, while scanelf
        #      (security_init(true) -> the *fork* program) survives.  The
        #      allowlist is written for Gentoo/glibc syscall usage, so it is
        #      turned off here; the tools keep working, they just no longer
        #      self-demote.
        tc.project_options["use_seccomp"] = False
        tc.project_options["build_manpages"] = "disabled"  # xmlto is not available
        # The python implementation imports elftools (pyelftools), which is not
        # available on the target, and dies with ModuleNotFoundError.  The shell
        # one only needs scanelf, which this same package installs.
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
        # Upstream official suite (meson test runs tests/{lddtree,pspax,scanelf,source}).
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
