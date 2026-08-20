#!/usr/bin/env python3
"""Conan recipe for NQP 2025.11 on HarmonyOS PC."""

import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class NqpConan(ConanFile):
    name = "nqp"
    version = "2025.11"
    description = "Not Quite Perl, a lightweight Raku-like compiler toolchain"
    license = "Artistic-2.0"
    homepage = "https://github.com/Raku/nqp"
    url = "https://github.com/Raku/nqp"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("moarvm/2025.11", run=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("NQP MoarVM backend supports Linux and OHOS")
        if str(self.settings.arch) not in ("armv8", "x86_64"):
            raise ConanInvalidConfiguration("NQP recipe supports armv8 and x86_64")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _moar(self):
        return os.path.join(self.dependencies["moarvm"].package_folder, "bin", "moar")

    def _stage(self):
        return os.path.join(self.build_folder, "stage")

    def _moar_make_args(self):
        moar = self.dependencies["moarvm"].package_folder
        include_root = os.path.join(moar, "include")
        include_dirs = [
            include_root,
            *(
                os.path.join(include_root, name)
                for name in ("moar", "libuv", "libtommath", "dyncall", "mimalloc")
            ),
        ]
        include_flags = " ".join(f'-I"{path}"' for path in include_dirs)
        link_flags = f'-L"{os.path.join(moar, "lib")}" -lmoar'
        return (
            f'M_MOAR_INC_PATHS="{include_flags}" '
            f'M_LD_INST_NQP_POST="{link_flags}"'
        )

    def build(self):
        apply_conandata_patches(self)
        moar_mast = os.path.join(
            self.dependencies["moarvm"].package_folder, "share", "nqp", "lib", "MAST"
        )
        stage_mast = os.path.join(self._stage(), "share", "nqp", "lib", "MAST")
        copy(self, "*.nqp", src=moar_mast, dst=stage_mast)
        self.run(
            'perl Configure.pl --backends=moar --relocatable '
            f'--prefix="{self._stage()}" --with-moar="{self._moar()}"',
            cwd=self.source_folder,
            env=["conanbuild", "conanrun"],
        )
        self.run(
            f"make -j1 {self._moar_make_args()}",
            cwd=self.source_folder,
            env=["conanbuild", "conanrun"],
        )
        test_log = os.path.join(self.build_folder, "upstream-tests.log")
        result = self.run(
            f'make test > "{test_log}" 2>&1',
            cwd=self.source_folder,
            env=["conanbuild", "conanrun"],
            ignore_errors=True,
        )
        with open(test_log, encoding="utf-8", errors="replace") as stream:
            output = stream.read()
        self.output.info(output)
        if result:
            expected = (
                "Failed to link file: operation not permitted",
                "Failed 41/112 subtests",
                "t/nqp/019-file-ops.t                 (Wstat: 256 (exited 1) Tests: 71 Failed: 0)",
                "Parse errors: Bad plan.  You planned 112 tests but ran 71.",
                "Files=144, Tests=13431",
                "Result: FAIL",
            )
            failure_counts = {
                "Dubious, test returned": 1,
                "Failed 41/112 subtests": 1,
                "Test Summary Report": 1,
                "Parse errors:": 1,
                "(Wstat: 256 (exited 1) Tests: 71 Failed: 0)": 1,
                "make: *** [": 1,
            }
            known_hmdfs_failure = (
                str(self.settings.os) == "OHOS"
                and all(marker in output for marker in expected)
                and all(output.count(marker) == count for marker, count in failure_counts.items())
                and not re.search(r"^not ok\b", output, re.MULTILINE)
            )
            if not known_hmdfs_failure:
                raise ConanException("NQP upstream test suite failed unexpectedly")
            self.output.warning(
                "13,431 assertions passed; t/nqp/019-file-ops.t stopped at the "
                "unsupported HMDFS hard-link operation"
            )

    def package(self):
        self.run(
            f"make install {self._moar_make_args()}",
            cwd=self.source_folder,
            env=["conanbuild", "conanrun"],
        )
        copy(self, "*", src=self._stage(), dst=self.package_folder)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
