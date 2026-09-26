#!/usr/bin/env python3
"""Conan recipe — orbuculum 2.2.0 (Meson, C).

orbuculum captures SWO/SWV ITM trace from ARM Cortex-M targets (via an
orbtrace/BMP probe, a TTL serial link or file/socket streams) and ships a set
of post-processing tools built around the shared ``liborb`` library:

    orbuculum  orbfifo  orbcat  orbtop  orbdump  orbstat
    orbmortem  orbprofile  orbtrace  orbzmq  orblcd

Adapted to HarmonyOS PC (aarch64, clang 15 / OHOS 6.0).  The upstream project
builds with Meson and pulls ``libdwarf`` from a Meson wrap subproject that is
downloaded at configure time; this recipe replaces that with the Conan-provided
``libdwarf`` so the build is self-contained (see patches/ and notes.md).

Dependencies come from the OHOS Conan registry and are discovered with
pkg-config (PkgConfigDeps), which keeps the upstream meson.build untouched for
everything except the libdwarf subproject.
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class OrbuculumConan(ConanFile):
    name = "orbuculum"
    version = "2.2.0"
    description = ("Orbuculum — Cortex-M SWO/SWV trace capture and post-processing "
                   "tools (orbuculum/orbcat/orbdump/orbstat/orbmortem/orbtop/…)")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/orbcode/orbuculum"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("debug", "swo", "swv", "itm", "cortex-m", "trace", "embedded")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True, "ncurses/*:shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # C-only project: no C++ settings are consumed.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        # meson's default backend is ninja; declaring it keeps the build
        # self-contained on workers where ninja is not on PATH.
        self.tool_requires("ninja/1.12.1")

    def requirements(self):
        # Direct dependencies named by the upstream meson.build:
        #   dependency('libusb-1.0'), ('libzmq'), ('ncurses', 'ncursesw'),
        #   ('libelf'), ('libdwarf')  +  optional ('capstone' >= 4), ('SDL2')
        self.requires("libusb/1.0.27")
        self.requires("libzmq/4.3.5")
        self.requires("ncurses/6.6")
        self.requires("libelf/0.8.13.1")
        self.requires("libdwarf/0.11.1")
        self.requires("capstone/5.0.7")
        self.requires("sdl2/2.32.10")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps writes one .pc per dependency into the generators
        # folder; MesonToolchain points meson's pkg_config_path there, so the
        # upstream dependency('…') lookups resolve against the Conan packages.
        PkgConfigDeps(self).generate()

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # The libdwarf subproject is gone (patched out); make sure meson never
        # tries to download anything at configure time.
        tc.project_options["wrap_mode"] = "nodownload"
        # meson derives a bare "llvm-ar" for the clang brand and probes it on
        # PATH; the OHOS CI worker does not always expose /data/service/hnp/bin,
        # which makes `meson setup` abort with
        #   "ERROR: Unknown linker(s): [['llvm-ar']]".
        # Pin the absolute paths of the LLVM archiver/strip and pkg-config.
        tc.ar = self._meson_tool("llvm-ar", "ar")
        tc.strip = self._meson_tool("llvm-strip", "strip")
        tc.pkgconfig = self._meson_tool("pkg-config", "pkgconf")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests()

    def package(self):
        Meson(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # meson only installs the library/tools; ship the public headers too so
        # consumers (and test_package) can use the liborb C API.
        copy(self, "*.h", src=os.path.join(self.source_folder, "Inc"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "Inc", "external"),
             dst=os.path.join(self.package_folder, "include", "external"))
        # drop the template header used to generate git_version_info.h
        rm(self, "git_version_info.h.in", os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["orb"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "orbuculum")
        self.cpp_info.set_property("cmake_target_name", "orbuculum::orbuculum")
        self.cpp_info.set_property("pkg_config_name", "orbuculum")

    # ── helpers ─────────────────────────────────────────────────────────────

    def _meson_tool(self, *names):
        """Resolve a build tool to an absolute path.

        OHOS CI workers do not always put ``/data/service/hnp/bin`` on PATH, so
        looking the tools up next to the configured C compiler (and next to its
        symlink target, i.e. inside the OHOS SDK) is more reliable than relying
        on PATH alone.
        """
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict) or {}
        cc = compilers.get("c") or ""
        search_dirs = []
        if cc and os.path.sep in cc:
            search_dirs.append(os.path.dirname(cc))
            search_dirs.append(os.path.dirname(os.path.realpath(cc)))
        # last resort: the LLVM bin directory inside the OHOS SDK
        search_dirs.extend(sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin")))
        for directory in search_dirs:
            for name in names:
                candidate = os.path.join(directory, name)
                if os.path.isfile(candidate):
                    return candidate
        return None

    def _c_compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict) or {}
        return compilers.get("c") or shutil.which("clang") or "clang"

    def _run_upstream_tests(self):
        """Build and run the upstream Tests/test_cobs.c suite.

        orbuculum wires no meson ``test()`` target, so the upstream test is
        compiled and executed explicitly (as documented in the test header).
        The program always exits 0, hence the pass/fail decision is taken from
        its output ("FAILED" marks a failing vector).
        """
        workdir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(workdir, exist_ok=True)
        binary = os.path.join(workdir, "test_cobs")
        log = os.path.join(workdir, "test_cobs.log")
        compiler = self._c_compiler()
        self.run(
            f'"{compiler}" -D_GNU_SOURCE -I"{os.path.join(self.source_folder, "Inc")}" '
            f'"{os.path.join(self.source_folder, "Src", "cobs.c")}" '
            f'"{os.path.join(self.source_folder, "Tests", "test_cobs.c")}" '
            f'-o "{binary}"',
            cwd=workdir,
        )
        self.run(f'"{binary}" > "{log}" 2>&1', cwd=workdir, ignore_errors=True)
        with open(log, encoding="utf-8", errors="replace") as handle:
            output = handle.read()
        ok_count = output.count("OK")
        self.output.info(f"upstream Tests/test_cobs.c: {ok_count} OK result(s)")
        if "FAILED" in output:
            raise ConanException(
                "Upstream Tests/test_cobs.c reported FAILED case(s); see " + log
            )
        if ok_count == 0:
            raise ConanException(
                "Upstream Tests/test_cobs.c produced no results; see " + log
            )
