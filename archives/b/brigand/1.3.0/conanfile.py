#!/usr/bin/env python3
"""Conan recipe for brigand 1.3.0.

brigand is a header-only C++11 template meta-programming library (light-weight,
instant-compile-time). No compiled artifacts: package() installs the ``brigand/``
header tree into ``include/``.

Upstream tests: the CMake test set is 51 ``test/*.cpp`` sources; ``main.cpp``
drives three runtime checks (for_each/select/real) and the rest are compile-time
``static_assert`` unit tests. Two suites (``fusion_test.cpp``/``variant_test.cpp``)
require Boost (upstream only builds them when ``Boost_FOUND``) so they are excluded
under ``BRIGAND_NO_BOOST_SUPPORT``. ``predicate_reduction_test.cpp`` relies on a
C++14 constexpr ``std::initializer_list`` member (``brigand::detail::all_same``),
so the suites are compiled with ``-std=c++14``. Build() compiles all 49 non-Boost
suites, links them with ``main.cpp`` and runs the resulting ``brigand_test``.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BrigandConan(ConanFile):
    name = "brigand"
    version = "1.3.0"
    description = "brigand - light-weight, fully functional, instant-compile-time C++11 template meta-programming library"
    license = "BSL-1.0"
    homepage = "https://github.com/edouarda/brigand"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/b/brigand/1.3.0"
    topics = ("meta-programming", "templates", "header-only", "cpp11")
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # header-only: identical package content for every configuration
        self.info.clear()

    def validate(self):
        # R32: use `in`, never `==`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is validated for Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not self.options.run_upstream_tests:
            return
        if not can_run(self):
            self.output.info("Cross-building: upstream suites skipped at build time")
            return

        # R33: compiler must come from Conan conf, never bare shell env vars.
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = exes.get("cpp") or "clang++"

        sf = self.source_folder
        inc = sf  # tests include <brigand/...> directly from source root
        build = self.build_folder

        # Non-Boost suites (fusion_test/variant_test require Boost and are
        # excluded by the upstream CMake when Boost is not found).
        skip = {"fusion_test.cpp", "variant_test.cpp"}
        suites = sorted(
            f for f in os.listdir(os.path.join(sf, "test"))
            if f.endswith(".cpp") and f not in skip and f != "main.cpp"
        )

        objs = []
        for src in suites:
            obj = os.path.join(build, src + ".o")
            self.run(
                f'"{cxx}" -std=c++14 -DBRIGAND_NO_BOOST_SUPPORT -I"{inc}" '
                f'-c "{os.path.join(sf, "test", src)}" -o "{obj}"',
                env="conanbuild",
            )
            objs.append(obj)

        exe = os.path.join(build, "brigand_test")
        self.run(
            f'"{cxx}" -std=c++14 "{os.path.join(sf, "test", "main.cpp")}" '
            f'{" ".join(objs)} -o "{exe}"',
            env="conanbuild",
        )
        self.output.info("Running upstream brigand_test")
        self.run(f'"{exe}"', env="conanbuild")

    def package(self):
        copy(self, "*", src=os.path.join(self.source_folder, "brigand"),
             dst=os.path.join(self.package_folder, "include", "brigand"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        # brigand's Boost adapters (fusion/variant) are only included when
        # BRIGAND_NO_BOOST_SUPPORT is undefined; we ship without Boost so
        # consumers must see the macro automatically.
        self.cpp_info.defines = ["BRIGAND_NO_BOOST_SUPPORT"]
        self.cpp_info.set_property("cmake_target_name", "brigand::brigand")
