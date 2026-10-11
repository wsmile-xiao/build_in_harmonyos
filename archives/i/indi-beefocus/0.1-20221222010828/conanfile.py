#!/usr/bin/env python3
"""Conan recipe for indi-beefocus 0.1-20221222010828 — INDI driver for the
Bee Focuser (an open-source hardware/software telescope focuser controlled
over TCP/IP), shipped as a subproject of the INDI 3rdparty monorepo.

The package product is a single INDI driver executable, bin/indi_beefocus,
plus its INDI driver description share/indi/indi_beefocus.xml — so this is an
"application" package (R38: a commands.json is required at software level).

Adaptation notes (full record in notes.md):
  * E092 — CMake does not know the HarmonyOS platform, so CMAKE_SYSTEM_NAME is
    forced to Linux (patch 0004) and CMAKE_SYSTEM_PROCESSOR pinned to aarch64
    (same workaround already proven for libindi/2.2.2.1 and
    libfli/2.0-20221221182632 in this repo).
  * CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF — the driver ships the 2022-era
    cmake_modules/FindINDI.cmake and needs it to win over CONFIG lookups.
  * Patch 0001 backports the upstream FindINDI version regex: INDI >= 2.0
    writes `#define INDI_VERSION "2.2.2"` with quotes, which the 2022-era regex
    cannot match ("failed to detect INDI version").
  * Patch 0002 raises the vendor CMakeCommon.cmake standard from C++14 to C++17:
    both the INDI 2.x headers (defaultdevice.h uses std::any) and gtest 1.17
    require C++17. Identical to upstream master.
  * Patch 0003 ports driver/beefocus.cpp to the INDI 2.x property API
    (FocusAbsPosN/FocusMaxPosN members -> FocusAbsPosNP/FocusMaxPosNP accessors,
    `.s = ...` -> setState()/getState(), IDSetNumber() -> apply()). Line-for-line
    the same port upstream master already carries.
  * Patch 0004 fixes two genuine upstream build defects: cmake_minimum_required
    3.0 is rejected by CMake >= 4, and the unit-test POST_BUILD step invokes the
    test through a bare `COMMAND ${TEST}` which the shell cannot resolve
    (Error 127); `$<TARGET_FILE:...>` makes it run.
  * E537 — the OHOS shared objects shipped under the Conan cache cannot be
    mapped by this platform's loader here, so INDI is consumed as its *static*
    archive (libindidriver.a) instead of libindidriver.so. This is the same
    approach libindi's own test_package takes in this repository, and it is also
    why the driver is linked with --allow-multiple-definition (the archive
    contributes its own `main`/`me` alongside the unit test's).
  * GTEST_ROOT — the upstream unit-test branch does a plain
    `find_package(GTest REQUIRED)` and uses the legacy ${GTEST_*}; with
    PREFER_CONFIG off CMake's bundled FindGTest module runs, and GTEST_ROOT
    points it at the Conan gtest package.

The upstream CTest suite (unit_tests/test_driver.cpp, 8 gtest cases driving the
software-simulated focuser firmware, no hardware needed) is built and run inside
build(), so `conan create` fails if the upstream tests fail (R51).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.build import can_run


class PreferConfigOffBlock(Block):
    """Force CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF so the vendored
    cmake_modules/FindINDI.cmake (and CMake's bundled FindGTest module) win
    over CONFIG package lookups. The block runs last, overriding the
    toolchain's default ON."""
    template = "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)\n"


class IndiBeefocusConan(ConanFile):
    name = "indi-beefocus"
    version = "0.1-20221222010828"
    description = ("INDI driver for the Bee Focuser: open source hardware/software "
                   "telescope focuser controlled over TCP/IP (INDI 3rdparty)")
    license = "LGPL-2.1+"
    homepage = "https://github.com/indilib/indi-3rdparty"
    url = "https://github.com/indilib/indi-3rdparty"
    topics = ("astronomy", "indi", "focuser", "driver", "telescope")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The driver links the INDI driver framework (FindINDI locates it).
        self.requires("libindi/2.2.2.1")

    def build_requirements(self):
        # Upstream unit tests are gtest-based and run during build(); they must
        # not leak into the delivered package.
        self.test_requires("gtest/1.17.0")

    # R32: only Linux-family targets are supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"indi-beefocus is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _indi_static_archive(self):
        """Absolute path of libindi's static driver archive, or None."""
        libindi = self.dependencies["libindi"]
        if not libindi.package_folder:
            return None
        candidate = os.path.join(libindi.package_folder, "lib", "libindidriver.a")
        return candidate if os.path.isfile(candidate) else None

    def _transitive_link_flags(self):
        """-L/-l flags for libindi's dependency closure.

        The vendored FindINDI.cmake resolves INDI through legacy find_library()
        variables only; it has no CONFIG package awareness, so the libraries INDI
        itself was linked against must be supplied explicitly (exactly what the
        upstream CMake build gets for free from its pkg-config / system layout).
        Derived from the real Conan dependency graph rather than hardcoded.
        """
        libdirs, libs = [], []
        for dep in self.dependencies.host.values():
            if dep.ref.name == "libindi":
                continue
            for d in dep.cpp_info.libdirs:
                if d and d not in libdirs:
                    libdirs.append(d)
            for name in dep.cpp_info.libs:
                if name and name not in libs:
                    libs.append(name)
        return ([f"-L{d}" for d in libdirs] + [f"-l{n}" for n in libs]
                + ["-lm", "-lpthread", "-ldl"])

    def _transitive_rpath_flags(self):
        """RPATH entries for libindi's dependency closure.

        The upstream driver and its unit test are executed from the build tree
        (the POST_BUILD step and ctest), and the OHOS loader does not search the
        Conan cache by itself, so the shared dependencies have to be reachable at
        build-tree run time. Package-time relocation is unaffected: these are
        build-tree binaries, and the packaged deliverable is the driver, whose
        consumers resolve dependencies through their own Conan environment.
        """
        seen = []
        for dep in self.dependencies.host.values():
            if dep.ref.name == "libindi":
                continue
            for d in dep.cpp_info.libdirs:
                if d and d not in seen:
                    seen.append(d)
        return [f"-Wl,-rpath,{d}" for d in seen]

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform; drive the Linux path instead.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Build and exercise the upstream CTest suite (8 gtest cases against the
        # simulated focuser firmware — no hardware required).
        tc.variables["INDI_BUILD_UNITTESTS"] = "ON"
        # Upstream does a plain find_package(GTest REQUIRED) and uses the legacy
        # GTEST_* variables. With PREFER_CONFIG off, CMake's bundled FindGTest
        # module is used; GTEST_ROOT points it at the Conan gtest package.
        # gtest is a test_require and is legitimately absent when this recipe is
        # consumed as a dependency, so look it up by name over the build set.
        gtest = next((d for d in self.dependencies.build.values()
                      if d.ref.name == "gtest"), None)
        if gtest is not None and gtest.package_folder:
            tc.variables["GTEST_ROOT"] = gtest.package_folder
        # E537: link INDI's dependency closure explicitly (the vendored
        # FindINDI.cmake has no CONFIG awareness). --allow-multiple-definition
        # lets the archived indidrivermain coexist with the unit test's own main.
        tc.extra_exelinkflags.extend(
            ["-Wl,--allow-multiple-definition"] + self._transitive_link_flags()
            + self._transitive_rpath_flags())
        # Make the vendored Find*.cmake modules win over CONFIG lookups.
        tc.blocks["prefer_config_off"] = PreferConfigOffBlock
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)

        # Upstream sets cmake_minimum_required(VERSION 3.0); CMake >= 4 removed
        # compatibility below 3.5. This MUST be a real -D cache entry: a value
        # written via tc.variables lands in conan_toolchain.cmake, which CMake
        # evaluates in its internal "system" scope and therefore does not survive
        # into the project directory scope (verified on libfli in this repo).
        cli_args = ["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"]

        # E537: prefer INDI's static archive over the OHOS shared object, which
        # this platform's loader cannot map. FindINDI.cmake hands its cached
        # _INDI_LIB_RELEASE_driver variable to find_library(), which skips the
        # search entirely when that variable is already set to an existing path.
        static_archive = self._indi_static_archive()
        if static_archive:
            cli_args.append(f"-D_INDI_LIB_RELEASE_driver={static_archive}")
        else:
            self.output.warning(
                "libindi static archive not found; INDI will be linked from its "
                "shared object, which this platform's loader may refuse to map "
                "(E537)")

        cmake.configure(cli_args=cli_args)
        # R9: conservative parallelism; tools.build:jobs can raise it.
        jobs = self.conf.get("tools.build:jobs", default=2)
        cmake.build(cli_args=[f"-j{jobs}"])

        # ── upstream official tests (TEST_QUALITY_SPEC §3, R51) ──
        # CMakeLists.txt registers add_test(run-tests test_driver) and also runs
        # the binary as a POST_BUILD step, so a green build already implies the
        # suite ran; ctest re-runs it with a named, machine-readable transcript.
        if can_run(self):
            self.run("ctest --output-on-failure", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream ships the LGPL text only as firmware/LICENSE (the driver
        # sources carry the same LGPL-2.1+ header).
        copy(self, "LICENSE", os.path.join(self.source_folder, "firmware"),
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Application package: the deliverable is the driver executable.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
