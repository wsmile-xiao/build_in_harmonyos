import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class MtfmtConan(ConanFile):
    name = "mtfmt"
    version = "0.1.3"
    description = (
        "MtFmT (Mini template formatter) — a pure C string formatting library "
        "implementing a dialect of PEP-3101 plus a .NET-style date/time subset"
    )
    # SPDX-License-Identifier in upstream sources is LGPL-3.0, the root LICENSE
    # is the LGPL v3 text and the README badge says LGPL-V3.
    license = "LGPL-3.0-only"
    homepage = "https://mtfmt.cc/mtfmt/"
    url = "https://github.com/MtFmT-Lib/mtfmt"
    topics = ("format", "string", "formatter", "pep3101", "embedded")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 dependency check: every `#include` reachable from src/ and inc/ is
        # a C or C++ standard header (assert/stdarg/stddef/stdint/stdio/stdlib/
        # string plus <array>/<string>/<tuple>/<utility> for the C++ wrappers).
        # There is no third-party and no optional dependency to declare.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # `tests/` includes "unity.h", provided by the upstream git submodule
        # thirds/unity (pinned by the v0.1.3 tree, empty in the release
        # tarball). It is a *test-only* build input: it never reaches the
        # packaged artifact, it only lets build() run upstream's own suite.
        unity = self.conan_data["test_sources"]["unity"]
        unity_dir = os.path.join(self.source_folder, "thirds", "unity")
        get(
            self,
            unity["url"],
            destination=unity_dir,
            strip_root=True,
            sha256=unity["sha256"],
        )

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream option names (CMakeLists.txt); BUILD_SHARED_LIBS is not read
        # by this project, so the conan "shared" option maps onto it directly.
        tc.variables["MTFMT_BUILD_SHARED"] = (
            "ON" if self.options.shared else "OFF"
        )
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = (
            "ON" if self.options.fPIC else "OFF"
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run upstream's own test entry point: `make test`.

        The CMakeLists.txt ships its whole `enable_testing()` / `add_test()`
        block commented out, so the Makefile is the only registered entry: it
        compiles tests/*.c, tests/*.cpp and thirds/unity/src/*.c into
        target/mtfmt_run.out and executes it. A failing suite therefore fails
        the build (and G2/CI) instead of being reported as a silent skip.
        """
        src = self.source_folder
        # The upstream Makefile has no clean target; drop its own outputs so
        # the suite is always recompiled from the freshly exported sources —
        # a leftover object tree makes make print "Nothing to be done" and
        # pass without running a single case (silent false green).
        #
        # The object directory is overridden on purpose: upstream defaults to
        # `BUILD_DIR = build`, which is exactly conan's cmake_layout build
        # root (<build_folder>/build/Release lives inside it) — deleting or
        # sharing it would destroy the CMake build tree. The value must stay
        # *relative* (and so must OUTPUT_DIR): the `test` rule runs
        # `"$(addprefix ./$(OUTPUT_DIR)/,...)"`, and an absolute value there
        # yields `.//abs/path`, which the shell reports as "inaccessible or
        # not found".
        obj_dir = os.path.join(src, "build-test")
        out_dir = os.path.join(src, "target")
        for stale in (obj_dir, out_dir):
            if os.path.isdir(stale):
                rmdir(self, stale)
        executables = (
            self.conf.get("tools.build:compiler_executables", default={}) or {}
        )
        # The Makefile defaults to `CC = gcc`, which does not exist on this
        # toolchain; take the compiler from the profile instead of hardcoding.
        cc = executables.get("c", "clang")
        jobs = self.conf.get("tools.build:jobs", default=4) or 4
        self.run(
            f"make -C {shlex.quote(src)} -j{jobs} test "
            f"CC={shlex.quote(cc)} BUILD_DIR=build-test",
            env="conanbuild",
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        pkg = self.package_folder
        # Upstream installs everything below a nested "mtfmt/" prefix and
        # parks static archives in lib/static. Flatten both so the package
        # matches the layout conan consumers (and the artifact checks) expect:
        # include/ and lib/ directly under the package root.
        nested = os.path.join(pkg, "mtfmt")
        if os.path.isdir(nested):
            for entry in sorted(os.listdir(nested)):
                os.rename(
                    os.path.join(nested, entry), os.path.join(pkg, entry)
                )
            rmdir(self, nested)
        static_dir = os.path.join(pkg, "lib", "static")
        if os.path.isdir(static_dir):
            for entry in sorted(os.listdir(static_dir)):
                os.rename(
                    os.path.join(static_dir, entry),
                    os.path.join(pkg, "lib", entry),
                )
            rmdir(self, static_dir)
        # install(EXPORT) writes mtfmt-config.cmake with import paths for the
        # pre-flatten layout ("${_IMPORT_PREFIX}/lib/static/..."), which no
        # longer exists once flattened, so it would break a bare find_package.
        # Conan consumers get their package config from CMakeDeps instead.
        rmdir(self, os.path.join(pkg, "lib", "cmake"))
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(pkg, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mtfmt")
        self.cpp_info.set_property("cmake_target_name", "mtfmt::mtfmt")
        self.cpp_info.set_property("pkg_config_name", "mtfmt")
        self.cpp_info.libs = ["mtfmt"]
