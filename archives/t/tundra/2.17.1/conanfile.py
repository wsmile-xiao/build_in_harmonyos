"""Tundra 2.17.1, including its complete native upstream test suites."""

import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class TundraConan(ConanFile):
    name = "tundra"
    version = "2.17.1"
    package_type = "application"
    description = "Tundra 2 incremental build system"
    license = "MIT"
    homepage = "https://github.com/deplinenoise/tundra"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("This recipe is adapted for native OHOS")

    def build_requirements(self):
        # The seven upstream assembly scanner cases invoke yasm. NASM accepts
        # their input syntax; test-only shims bridge the executable name and
        # included-file relative path behavior. The compiler scanner cases
        # invoke gcc, while the OHOS toolchain exposes clang.
        self.tool_requires("nasm/2.16.03")
        self.tool_requires("libfile-slurp-perl/9999.32")

    def source(self):
        get(self, **self.conan_data["sources"]["tundra"], strip_root=True)
        get(
            self,
            **self.conan_data["sources"]["googletest"],
            destination=os.path.join(self.source_folder, "unittest", "googletest"),
            strip_root=True,
        )

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _build_environment(self):
        nasm = os.path.join(self.dependencies.build["nasm"].package_folder, "bin", "nasm")
        slurp = os.path.join(
            self.dependencies.build["libfile-slurp-perl"].package_folder,
            "lib", "perl5",
        )
        if not os.path.isfile(nasm):
            raise ConanException(f"NASM executable missing: {nasm}")
        if not os.path.isfile(os.path.join(slurp, "File", "Slurp.pm")):
            raise ConanException(f"File::Slurp module missing: {slurp}")
        shim_dir = os.path.join(self.build_folder, "test-tools")
        os.makedirs(shim_dir, exist_ok=True)
        shims = {
            "yasm": (
                "#!/bin/sh\n"
                "# NASM searches -I directories relative to the invocation cwd.\n"
                "# Add each include file's directory so nested relative includes\n"
                "# retain the same meaning as they have with upstream yasm.\n"
                "for f in $(find . -type f -name '*.i'); do\n"
                "  d=${f%/*}\n"
                "  [ \"$d\" = . ] || set -- \"-I$d/\" \"$@\"\n"
                "done\n"
                f"exec {shlex.quote(nasm)} -f elf64 \"$@\"\n"
            ),
            "gcc": "#!/bin/sh\nexec clang \"$@\"\n",
            "g++": "#!/bin/sh\nexec clang++ \"$@\"\n",
            "tundra2-j2": (
                "#!/bin/sh\n"
                f"exec {shlex.quote(os.path.join(self.source_folder, 'build', 'tundra2'))} "
                "-j 2 \"$@\"\n"
            ),
        }
        for name, content in shims.items():
            path = os.path.join(shim_dir, name)
            save(self, path, content)
            os.chmod(path, 0o755)
        return shim_dir, slurp

    def _run_in_source(self, command, log_name=None, test_environment=False):
        source = shlex.quote(self.source_folder)
        prefix = f"cd {source} && "
        if test_environment:
            shim_dir, slurp = self._build_environment()
            prefix += (
                f"PATH={shlex.quote(shim_dir)}:$PATH "
                f"PERL5LIB={shlex.quote(slurp)} "
            )
        if log_name:
            log = shlex.quote(os.path.join(self.build_folder, log_name))
            self.run(
                prefix + command + f" > {log} 2>&1; rc=$?; cat {log}; exit $rc",
                env="conanbuild",
            )
            with open(os.path.join(self.build_folder, log_name), encoding="utf-8", errors="replace") as stream:
                return stream.read()
        self.run(prefix + command, env="conanbuild")

    def build(self):
        # The upstream Makefile treats HarmonyOS's uname as unknown, while
        # OHOS clang exposes the Linux/POSIX APIs used by Tundra. Reuse its
        # Linux build configuration without changing upstream source.
        self._run_in_source(
            "GITHUB_SHA=c3416af04d6d5fb3c2b1c99a1550fcaae0e7a6bb "
            "GITHUB_REF=refs/tags/v2.17.1 "
            "make -j2 UNAME=Linux CHECKED=no all",
            "build.log",
        )

        # The upstream run-all-tests target comprises these two commands.
        # The test-only executable wrapper caps Tundra's internal workers at
        # two; make -j2 alone does not control those workers.
        unit = self._run_in_source(
            "GITHUB_SHA=c3416af04d6d5fb3c2b1c99a1550fcaae0e7a6bb "
            "GITHUB_REF=refs/tags/v2.17.1 "
            "make -j2 UNAME=Linux CHECKED=no run-unit-tests",
            "unit-tests.log",
            test_environment=True,
        )
        if not re.search(r"\[\s*PASSED\s*\]\s*48 tests?\.", unit):
            raise ConanException("Expected all 48 upstream C++ tests to pass")
        shim_dir, _ = self._build_environment()
        functional = self._run_in_source(
            f"perl run-tests.pl {shlex.quote(os.path.join(shim_dir, 'tundra2-j2'))}",
            "functional-tests.log",
            test_environment=True,
        )
        # The Perl harness can return 0 with zero cases, so require the
        # observed totals rather than relying only on its exit status.
        if "Running 7 test groups" not in functional or not re.search(
            r"Summary: 20 of 20 tests passed", functional
        ):
            raise ConanException("Expected all 20 upstream Perl cases in 7 groups to pass")

        # The documented Lua selftest is outside Make's run-all-tests.
        # Its runner logs failures without a nonzero exit, so count both.
        lua = self._run_in_source("build/t2-lua selftest", "lua-selftest.log")
        if len(re.findall(r"^Testing .+: ", lua, re.MULTILINE)) != 11:
            raise ConanException("Expected all 11 upstream Lua cases to execute")
        if len(re.findall(r"^Testing .+: OK$", lua, re.MULTILINE)) != 11 or "failed" in lua.lower():
            raise ConanException("An upstream Lua case failed")
        self.output.info("UPSTREAM RESULT: 79 passed, 0 failed, 0 skipped")

    def package(self):
        # Upstream's install target invokes the GNU `install` utility, which
        # is absent on this device. Reproduce its three binary copies and
        # scripts/* -> share/tundra layout with Python's file operations.
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for name in ("tundra2", "t2-lua", "t2-inspect"):
            source = os.path.join(self.source_folder, "build", name)
            if not os.path.isfile(source):
                raise ConanException(f"Built executable missing: {source}")
            target = os.path.join(bin_dir, name)
            shutil.copy2(source, target)
            os.chmod(target, 0o755)
        shutil.copytree(
            os.path.join(self.source_folder, "scripts"),
            os.path.join(self.package_folder, "share", "tundra"),
            dirs_exist_ok=True,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
