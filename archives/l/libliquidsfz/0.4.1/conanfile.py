#!/usr/bin/env python3
"""Conan recipe for libliquidsfz 0.4.1 (SFZ sampler library) on HarmonyOS (OHOS).

liquidsfz renders SFZ instrument definitions through libsndfile.  Upstream
builds with Autotools (pre-generated configure) and defaults to a static-only
library (AC_DISABLE_SHARED + LT_INIT([pic-only])).

OHOS-specific handling (evidence in notes.md):
- bundled 2018 old-style config.guess/config.sub cannot identify the HarmonyOS
  host (no GUESS= variable): patches/0001-config-guess-sub-ohos.patch adds the
  aarch64:HarmonyOS guess branch and teaches config.sub linux-ohos (double
  anchor, DRAFT-E564 methodology)
- configure/make/check/install run under SHELL/CONFIG_SHELL=/system/bin/sh
  (E551: profile CONFIG_SHELL=bash corrupts libtool quoting; HNP bash getcwd
  failures inside HMDFS build folders) -- libicns 0.8.1 pattern
- the two upstream "umask 077" sites in configure are rewritten to "umask 022"
  before configure runs (E011/HMDFS temporaries), fail-closed on count != 2
- TMPDIR bound to a build-local .tmp directory, MKDIR_P pinned to
  /system/bin/mkdir -p (toybox), every make invocation serial
- jack and lv2 front-ends disabled (--without-jack --without-lv2): no jackd
  runtime and no X11/xrandr/xcursor stack on OHOS
- libsndfile discovered via PKG_CHECK_MODULES with a PkgConfigDeps generated
  sndfile.pc and explicit PKG_CONFIG_PATH injection
"""

import os
import re
import shlex
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LiquidsfzConan(ConanFile):
    name = "libliquidsfz"
    version = "0.4.1"
    description = "SFZ sampler library rendering sample-based instruments through libsndfile"
    license = "MPL-2.0"
    homepage = "https://github.com/swesterfeld/liquidsfz"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # Upstream is static-only by design (AC_DISABLE_SHARED); shared=True is
    # supported by upstream libtool switches but discouraged.
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # sndfile is a mandatory dependency (PKG_CHECK_MODULES(SNDFILE, [sndfile]))
        # and liquidsfz.pc embeds its Libs/Cflags, so it is a public dependency.
        self.requires("libsndfile/1.2.2")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"liquidsfz supports Linux and OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Patch at source() time: conan keeps the cached source folder between
        # rebuilds, so applying in build() would re-apply onto an already
        # patched tree (GNU patch prompt) -- same rationale as libicns 0.8.1.
        apply_conandata_patches(self)

    def generate(self):
        # PkgConfigDeps generates sndfile.pc into the generators folder;
        # configure PKG_CHECK_MODULES(SNDFILE, [sndfile]) finds it through the
        # explicit PKG_CONFIG_PATH set in _build_environment().
        PkgConfigDeps(self).generate()
        self._autotools_toolchain().generate()
        # No default shared-library search path for conan-cached dependencies;
        # prepend dependency libdirs so configure conftests and the upstream
        # test binaries keep running if a shared libsndfile is ever selected.
        environment = Environment()
        for dependency in self.dependencies.values():
            for libdir in dependency.cpp_info.libdirs:
                environment.prepend_path("LD_LIBRARY_PATH", libdir)
        environment.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        self._pin_autotools_timestamps()
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._prepare_ohos_configure()
                self._configure_ohos()
                self._run_ohos("make -j1")
                # Upstream test suite (automake harness, tests/Makefile.am):
                # TESTS = testsynth testsfzreader, fully offline/self-contained
                # (generates its own wav/sfz fixtures in the tests build dir).
                self._run_ohos("make -j1 check")
            else:
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-j1"])
                autotools.make(target="check", args=["-j1"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 install DESTDIR={destination}")
            else:
                Autotools(self).install(args=["-j1"])
        self._relocate_metadata()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["liquidsfz"]
        self.cpp_info.requires = ["libsndfile::libsndfile"]
        self.cpp_info.set_property("cmake_file_name", "liquidsfz")
        self.cpp_info.set_property("cmake_target_name", "liquidsfz::liquidsfz")
        self.cpp_info.set_property("pkg_config_name", "liquidsfz")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    # ── helpers ──────────────────────────────────────────────────────────

    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            # Explicit (matches the upstream default) so the build is
            # deterministic regardless of libtool heuristics.
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])
        toolchain.configure_args.extend(["--without-jack", "--without-lv2"])
        return toolchain

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
            # PKG_CHECK_MODULES probes with pkg-config; the generated
            # sndfile.pc lives in the generators folder (the sndfile.pc baked
            # into the published package carries a foreign absolute prefix
            # and must not win).
            environment.define_path("PKG_CONFIG_PATH", self.generators_folder)
        return environment

    def _prepare_ohos_configure(self):
        configure = self._ohos_configure_path()
        content = configure.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException("configure umask contract changed")
        configure.write_text(
            content.replace(needle, "umask 022"),
            encoding="utf-8",
            newline="\n",
        )

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        configure = self._ohos_configure_path()
        arguments = " ".join(
            shlex.quote(argument)
            for argument in self._autotools_toolchain().configure_args
        )
        quoted = "\"{0}\" \"{1}\"".format(shell, configure)
        self._run_ohos(quoted + " " + arguments)

    def _ohos_configure_path(self):
        configure = Path(self.source_folder, "configure")
        if not configure.is_file():
            raise ConanException(f"configure script is missing: {configure}")
        return configure

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _pin_autotools_timestamps(self):
        # Pin every file participating in the autotools dependency chain to one
        # identical timestamp so the maintainer rules never regenerate
        # configure/Makefile.in through missing(1) on the device.  GNU make
        # treats equal mtimes as up to date, so no regeneration fires.
        stamp = 978307200  # 2001-01-01, older than any real input edit
        src = self.source_folder
        keep = (".m4", ".am", ".in", ".ac")
        keep_exact = ("configure", "config.guess", "config.sub", "ltmain.sh",
                      "compile", "depcomp", "missing", "install-sh",
                      "mkinstalldirs", "aclocal.m4", "config.h.in")
        for root, _dirs, files in os.walk(src):
            for name in files:
                if name.endswith(keep) or name in keep_exact:
                    os.utime(os.path.join(root, name), (stamp, stamp))

    def _relocate_metadata(self):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "liquidsfz.pc")
        if not pc_path.is_file():
            raise ConanException("installed liquidsfz.pc is missing")
        pc_content = pc_path.read_text(encoding="utf-8")
        pc_content, count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("liquidsfz.pc has no unique prefix field")
        # The upstream pc template embeds SNDFILE_LIBS/SNDFILE_CFLAGS verbatim,
        # which resolve to this build machine conan cache at configure time.
        # Strip the absolute -L/-I paths, keeping the logical -lsndfile
        # requirement (consumers resolve sndfile through their own dependency
        # metadata instead of a foreign absolute path).
        pc_content = re.sub(r"\s+-L/\S+", "", pc_content)
        pc_content = re.sub(r"\s+-I/\S+", "", pc_content)
        pc_path.write_text(pc_content, encoding="utf-8", newline="\n")
