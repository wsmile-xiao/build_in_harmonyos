#!/usr/bin/env python3
"""pcc-libs — pcc compiler runtime libraries for HarmonyOS PC (AArch64).

pcc-libs ships the runtime support that code produced by the Portable C
Compiler links against: `libpcc` (core runtime), `libpccsoftfloat` (software
floating point) and the `csu` C startup objects.  The Fortran runtimes
(`libF77`/`libI77`) are not part of the default build.

The upstream tree predates HarmonyOS and only knows a fixed list of target
OSes, so this recipe applies the OHOS adaptation patches shipped under
`patches/`:

  0001  teach the 2015-vintage `config.guess`/`config.sub` the OHOS triplet
        (`aarch64-linux-ohos` -> `aarch64-unknown-linux-ohos`), plus a
        HarmonyOS branch in `config.guess` for real-hardware build detection
  0002  extend the target-OS whitelist in `configure.ac` *and* in the
        pre-generated `configure` that autotools actually runs
  0003  add the AArch64 IEEE binary128 branch to `libpcc/cxmuldiv.c`
  0004  fall back to `__BYTE_ORDER__` in `libpcc/signbit.c` when the compiler
        does not define `__FLOAT_WORD_ORDER__` (clang does not)
  0005  keep `libsoftfloat` AArch64 doubles in natural order: upstream selects
        the FPA word-swap with the 32-bit ARM macros `__VFP_FP__`/`__ARMEB__`,
        which an AArch64 compiler never defines
  0006  add `csu/ohos`, the C startup objects, with both the ctor and dtor
        table widths keyed off `__SIZEOF_POINTER__` instead of the x86-only
        macro

The library names deliberately keep the upstream spelling (`libpcc`,
`libpccsoftfloat`) because that is what generated pcc code links against.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class PccLibsConan(ConanFile):
    name = "pcc-libs"
    version = "1.2.0-devel-20211015"

    description = (
        "Runtime libraries for the Portable C Compiler (libpcc, libpccsoftfloat, csu)"
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/PortableCC/pcc-libs"
    url = "https://github.com/PortableCC/pcc-libs"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    #: pcc-libs keys its install tree on the *target triplet*, and it is the
    #: compiler that supplies that triplet, not this recipe.  A pcc driver for
    #: OHOS/AArch64 reports itself as aarch64-linux-ohos.
    _target_triplet = "aarch64-linux-ohos"

    @property
    def _is_ohos(self):
        # R32: OHOS is Linux-like, so both must be accepted.
        return self.settings.os in ("Linux", "OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if not self._is_ohos:
            raise ConanInvalidConfiguration(
                "pcc-libs is packaged for Linux/OHOS targets; got {}".format(
                    self.settings.os
                )
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "pcc-libs only produces static runtime archives; "
                "pcc links its runtime statically"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"][str(self.version)]
        # `tar_format` is provenance metadata for the archive, not a `get()`
        # keyword, so only forward the fields the downloader understands.
        get(
            self,
            url=source["url"],
            sha256=source["sha256"],
            strip_root=True,
        )

    def generate(self):
        tc = AutotoolsToolchain(self)

        # --host declares the *target* triplet the runtime is installed under
        # (pcc's install layout keys on it) and lets configure derive
        # targos/targmach from the patched whitelist (patch 0002).  This is a
        # cross-build necessity, not the E007 anti-pattern: E007 forbids using
        # --build/--host to *bypass* an unrecognized host, and this recipe
        # does the opposite - patches 0001/0002 teach config.guess/sub and the
        # whitelist the OHOS triplet first, so configure resolves it natively.
        tc.configure_args.append("--host={}".format(self._target_triplet))

        # pcc-libs has no shared-library support at all: every subdir builds a
        # plain .a archive plus startup objects, and validate() rejects
        # shared=True.  Static/shared flags are left to the toolchain defaults
        # derived from options.shared; upstream configure ignores them with a
        # warning either way.
        tc.make_args = ["-j1"]

        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # Upstream installs into <prefix>/lib/pcc/<triplet>/<version>/{lib,include}
        # and ships no licence file, so add the upstream notice for the package.
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

        runtime_root = os.path.join(
            self.package_folder,
            "lib",
            "pcc",
            "aarch64-unknown-linux-ohos",
            "1.2.0.DEVEL",
        )
        required = (
            os.path.join(runtime_root, "lib", "libpcc.a"),
            os.path.join(runtime_root, "lib", "libpccsoftfloat.a"),
            os.path.join(runtime_root, "lib", "crtbegin.o"),
            os.path.join(runtime_root, "lib", "crtend.o"),
            os.path.join(runtime_root, "include", "float.h"),
            os.path.join(runtime_root, "include", "stdarg.h"),
        )
        missing = [p for p in required if not os.path.isfile(p)]
        if missing:
            raise ConanInvalidConfiguration(
                "pcc-libs runtime was not installed correctly; missing: {}".format(
                    ", ".join(missing)
                )
            )

    def package_info(self):
        # pcc-libs does not use a conventional include/lib layout: everything
        # lives under lib/pcc/<triplet>/<version>/.  Consumers (the pcc driver
        # itself) locate the runtime through the triplet path, so do not
        # advertise it as a normal C library to avoid CMakeDeps inventing
        # -lpcc/-I flags that do not match the upstream contract.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []

        runtime_root = os.path.join(
            self.package_folder, "lib", "pcc", self._target_triplet.replace("-linux-", "-unknown-linux-"), "1.2.0.DEVEL"
        )
        self.buildenv_info.define_path("PCC_LIBS_ROOT", runtime_root)
        self.runenv_info.define_path("PCC_LIBS_ROOT", runtime_root)