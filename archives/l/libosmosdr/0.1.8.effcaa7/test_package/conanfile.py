#!/usr/bin/env python3
"""Consumer tests for libosmosdr.

Upstream libosmosdr ships no test suite at all (no tests/ directory, no
enable_testing()/add_test() call and no check/ctest target), so every assertion
below belongs to the OHOS adaptation and is reported as such in the PR.

TC-01/TC-02/TC-03 live in test_libosmosdr.c and run as one consumer test binary;
TC-04 executes the packaged osmo_sdr tool.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import load


class LibosmosdrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        includes = []
        libdirs = []
        libs = []
        for dependency in self.dependencies.values():
            info = dependency.cpp_info
            package_folder = dependency.package_folder
            includes.extend(self._absolute_paths(package_folder, info.includedirs))
            libdirs.extend(self._absolute_paths(package_folder, info.libdirs))
            libs.extend(info.libs)
            libs.extend(info.system_libs)

        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = executables.get("c") or os.environ.get("CC")
        if not cc:
            raise ConanException("C compiler not found in tools.build:compiler_executables or CC")

        include_flags = " ".join(f'-I"{path}"' for path in self._unique(includes))
        libdir_flags = " ".join(f'-L"{path}"' for path in self._unique(libdirs))
        lib_flags = " ".join(f"-l{name}" for name in self._unique(libs))
        expect_shared = 1 if self.dependencies[self.tested_reference_str].options.shared else 0

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        source = os.path.join(self.source_folder, "test_libosmosdr.c")
        self.run(
            f'TMPDIR="{tmpdir}" {cc} "{source}" -DTEST_EXPECT_SHARED={expect_shared} '
            f'-o test_libosmosdr {include_flags} {libdir_flags} {lib_flags} -ldl'
        )

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile and link test completed")
            return

        binary = os.path.join(self.build_folder, "test_libosmosdr")
        self._sign_if_needed(binary)
        self.run(binary, env="conanrun")

        # TC-04 (OHOS specific): the packaged command line tool must execute.
        tool = self._find_executable("osmo_sdr")
        if tool is None:
            raise ConanException("osmo_sdr executable is missing from the package")

        logfile = os.path.join(self.build_folder, "osmo_sdr.log")
        # osmo_sdr prints its usage and exits with 1 when called without arguments
        self.run(f'"{tool}" > "{logfile}" 2>&1', env="conanrun", ignore_errors=True)

        output = load(self, logfile)
        if "Usage:" not in output:
            raise ConanException(
                f"osmo_sdr did not execute correctly on OHOS, output was:\n{output}"
            )
        self.output.info("TC-04 osmo_sdr executes on OHOS and reports its usage")

    def _find_executable(self, name):
        dependency = self.dependencies[self.tested_reference_str]
        for bindir in dependency.cpp_info.bindirs:
            candidate = os.path.join(dependency.package_folder, bindir, name)
            if os.path.isfile(candidate):
                return candidate
        return None

    def _sign_if_needed(self, binary):
        if str(self.settings.os) != "OHOS":
            return

        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return

        subprocess.run([objcopy, "--remove-section", ".codesign", binary], check=False)
        signed = binary + ".signed"
        subprocess.run([signer, "sign", "-inFile", binary, "-outFile", signed, "-selfSign", "1"],
                       check=True)
        os.replace(signed, binary)
        os.chmod(binary, 0o755)

    @staticmethod
    def _unique(items):
        seen = set()
        result = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @staticmethod
    def _absolute_paths(root, paths):
        return [
            path if os.path.isabs(path) else os.path.join(root, path)
            for path in paths
        ]
