#!/usr/bin/env python3
"""Conan recipe for sockperf 3.7 — network throughput/latency benchmark CLI.

sockperf (Mellanox/NVIDIA) measures network latency and throughput over
TCP/UDP.  C++ sources under src/, classic Autotools build WITHOUT a
pre-generated configure (must bootstrap via autoreconf).

OHOS adaptation notes:
  - the GitHub tag archive omits `build/current-version`, which
    configure.ac's esyscmd reads to seed AC_INIT's version — a build-time
    stub is written before autoreconf (upstream versioning.sh derives the
    same string from git describe at tag 3.7).
  - autoreconf -fi bootstraps with automake/libtool from tool_requires
    (CI workers ship neither); the generated configure's `umask 077`
    temp-dir wrappers are stripped (E114, HMDFS setgid).
  - the ohos-aarch64 profile [buildenv] pins SHELL/CONFIG_SHELL to the hnp
    bash which getcwd-hangs inside HMDFS build dirs (E386, §12.70①) — the
    aggregated env scripts are rewritten in place at build() start.
  - triplets per checklist: --build=aarch64-unknown-linux-gnu with
    --host=aarch64-unknown-linux-ohos (bootstrap ships a modern config.sub
    that parses the ohos triplet; host must canonicalize to aarch64 or
    configure errors with "has not been ported").
  - backtrace() (checked via AC_SEARCH_LIBS against libexecinfo) resolves
    from OHOS musl libc directly — no libexecinfo package needed (probed
    on device with clang).
  - tests/ are manual paired-host shell benchmarks (need a server IP);
    nothing registers as automake TESTS, so `make check` is a no-op and
    the consumer loopback test in test_package covers behavior (R34).
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

_HNP_BASH = "/data/service/hnp/bin/bash"


def _prepare_autotools_env():
    """The toolchain-installed automake/aclocal hardcode absolute helper
    paths that may not exist here; point the env vars at the PATH ones."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir whose files even the owner cannot write
    (config.status dies with `can't create ./confstat*/out: Permission
    denied`).  Strip every `(umask 077 && ...)` wrapper from the generated
    configure — autoconf generations differ, so match generically."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = re.sub(r"\(umask 077 && ([^()]+)\)", r"\1", data)
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _route_hnp_bash_to_sh(generators_folder):
    """E386 (§12.70①): profile [buildenv] pins SHELL/CONFIG_SHELL to the hnp
    bash, which fails getcwd() inside HMDFS build dirs.  Rewrite the
    aggregated env scripts in place; never re-save_script("conanbuild") — a
    same-named second script is sourced into itself and recurses forever."""
    if not generators_folder or not os.path.isdir(generators_folder):
        return
    for sh in glob.glob(os.path.join(generators_folder, "**", "*.sh"),
                        recursive=True):
        with open(sh, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
        if _HNP_BASH in data:
            with open(sh, "w", encoding="utf-8") as f:
                f.write(data.replace(_HNP_BASH, "/bin/sh"))
    for var in ("SHELL", "CONFIG_SHELL"):
        if os.environ.get(var, "").startswith(_HNP_BASH):
            os.environ[var] = "/bin/sh"


class SockperfConan(ConanFile):
    name = "sockperf"
    version = "3.7"
    description = ("sockperf: network throughput and latency benchmarking "
                   "tool for TCP/UDP (Mellanox/NVIDIA)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/mellanox/sockperf"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # No pre-generated configure in the tag archive: bootstrap here.
        # CI workers ship no automake/libtool (cliquer/abiword precedent).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        # librt/libpthread/libdl resolve in musl libc; backtrace() likewise
        # (device-probed).  tests/ manual benchmarks are not packaged.
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sockperf is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # host must canonicalize to aarch64 (configure.ac errors otherwise);
        # keep the build triplet gnu per workspace checklist.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # 2012-era sources use `register` storage (C++17-hard error) and
        # std::unary_function (removed in C++17) — appended after the
        # profile flag so clang takes the later -std (checklist pattern).
        # The GCC `typeof` keyword in os_abstract.h macros maps to clang's
        # __typeof__ spelling.  -D_GNU_SOURCE mirrors upstream's own
        # CMakeLists.txt add_definitions(): musl hides
        # pthread_setaffinity_np (used by os_abstract.cpp) without it.
        tc.extra_cxxflags.append("-std=c++14")
        tc.extra_cxxflags.append("-Dtypeof=__typeof__")
        tc.extra_cxxflags.append("-D_GNU_SOURCE")
        tc.generate()

    def build(self):
        # The tag archive ships a root-level `version` doc file; with -I.
        # it shadows libcxx's <version> header (pulled in by <exception>)
        # and breaks every C++ TU.  It is only a dist_doc_DATA entry —
        # the 0001 patch drops it from the install list, here we drop the
        # file itself.
        version_doc = os.path.join(self.source_folder, "version")
        if os.path.exists(version_doc):
            os.remove(version_doc)
        # The tag archive omits build/current-version; configure.ac's
        # esyscmd reads it to set the package version.  Restore the string
        # upstream's versioning.sh derives for tag 3.7 before bootstrapping.
        version_file = os.path.join(self.source_folder, "build",
                                    "current-version")
        if not os.path.exists(version_file):
            os.makedirs(os.path.dirname(version_file), exist_ok=True)
            with open(version_file, "w", encoding="utf-8") as f:
                f.write("3.7")
        _prepare_autotools_env()
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        _route_hnp_bash_to_sh(self.generators_folder)
        autotools = Autotools(self)
        autotools.configure()
        # R9/E074: single job — parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone benchmarking binary
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
