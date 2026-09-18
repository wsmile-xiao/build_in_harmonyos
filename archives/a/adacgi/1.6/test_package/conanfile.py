#!/usr/bin/env python3
"""Consumer test for the packaged adacgi 1.6 Ada CGI library.

Compiles a downstream Ada program against the packaged ``CGI`` and
``Ustrings`` source units with the ``gcc-ada/9.5.0`` GNAT toolchain, signs the
resulting OHOS ELF, and executes nine functional assertions through
``verify_adacgi.py``.
"""

import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment


class AdacgiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = ("VirtualBuildEnv", "VirtualRunEnv")
    test_type = "explicit"
    exports_sources = (
        "test_adacgi.adb",
        "verify_adacgi.py",
        "upstream/*.adb",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("gcc-ada/9.5.0")

    def generate(self):
        env = Environment()
        if str(self.settings.os) == "OHOS":
            # Same HNP binutils PATH fix as the main recipe: gnatmake needs
            # GNU as/ld from /data/service/hnp/bin to assemble and link.
            env.prepend_path("PATH", "/data/service/hnp/bin")
        env.vars(self).save_script("adacgi_binutils_env")

    def _tool(self, name):
        dependency = self.dependencies.build["gcc-ada"]
        bindirs = dependency.cpp_info.bindirs or ["bin"]
        executable = os.path.join(
            dependency.package_folder, bindirs[0], name
        )
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The packaged {} executable was not found: {}".format(
                    name, executable
                )
            )
        return executable

    def _adacgi_include_dir(self):
        dependency = self.dependencies["adacgi"]
        includedirs = dependency.cpp_info.includedirs
        if not includedirs:
            raise ConanInvalidConfiguration(
                "The adacgi package does not declare an include directory"
            )
        return os.path.join(dependency.package_folder, includedirs[0])

    def _sign_program(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = (
            shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        readelf = (
            shutil.which("llvm-readelf")
            or "/data/service/hnp/bin/llvm-readelf"
        )
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "Running GNAT output on OHOS requires binary-sign-tool, "
                "llvm-objcopy and llvm-readelf"
            )

        header = subprocess.run(
            [readelf, "-h", path],
            capture_output=True,
            text=True,
            check=True,
        )
        if not re.search(r"Type:\s+(?:EXEC|DYN)\b", header.stdout):
            raise ConanInvalidConfiguration(
                "GNAT did not produce a runnable ELF file: {}".format(path)
            )

        original_mode = stat.S_IMODE(os.stat(path).st_mode)
        with tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=os.path.dirname(path)
        ) as temp_dir:
            os.chmod(temp_dir, 0o775)
            unsigned = os.path.join(temp_dir, "unsigned")
            signed = os.path.join(temp_dir, "signed")
            shutil.copy2(path, unsigned)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", unsigned],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    unsigned,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            sections = subprocess.run(
                [readelf, "-S", signed],
                capture_output=True,
                text=True,
                check=True,
            )
            if ".codesign" not in sections.stdout:
                raise ConanInvalidConfiguration(
                    "Signing did not add .codesign: {}".format(path)
                )
            os.replace(signed, path)
            os.chmod(
                path,
                original_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )

    def build(self):
        gnatmake = self._tool("gnatmake")
        self._tool("gnatbind")
        self._tool("gnatlink")
        self.run(
            "{} --version".format(shlex.quote(gnatmake)),
            env=["conanbuild", "adacgi_binutils_env"],
        )

        source = os.path.join(self.source_folder, "test_adacgi.adb")
        executable = os.path.join(self.build_folder, "test_adacgi")
        include_dir = self._adacgi_include_dir()
        self.run(
            "{} -q -gnata -O2 -gnat95 -I{} {} -o {}".format(
                shlex.quote(gnatmake),
                shlex.quote(include_dir),
                shlex.quote(source),
                shlex.quote(executable),
            ),
            env=["conanbuild", "adacgi_binutils_env"],
        )
        self._sign_program(executable)

        # Compile the four upstream test programs unchanged from the source
        # archive.  They are built and run in test() so the PR's upstream
        # test pass rate reflects real execution rather than a skip.
        self._upstream_tests = ("test_get", "test_cookie", "test_encode", "test_send")
        for name in self._upstream_tests:
            upstream_source = os.path.join(
                self.source_folder, "upstream", name + ".adb"
            )
            upstream_exe = os.path.join(self.build_folder, name)
            self.run(
                "{} -q -gnat95 -I{} {} -o {}".format(
                    shlex.quote(gnatmake),
                    shlex.quote(include_dir),
                    shlex.quote(upstream_source),
                    shlex.quote(upstream_exe),
                ),
                env=["conanbuild", "adacgi_binutils_env"],
            )
            self._sign_program(upstream_exe)

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: GNAT compile, bind and link completed; "
                "execution skipped"
            )
            return
        executable = os.path.join(self.build_folder, "test_adacgi")
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The adacgi test executable was not found: {}".format(
                    executable
                )
            )
        verifier = os.path.join(self.source_folder, "verify_adacgi.py")
        self.run(
            "{} {} {}".format(
                shlex.quote(sys.executable),
                shlex.quote(verifier),
                shlex.quote(executable),
            ),
            env="conanrun",
        )

        # Run the four upstream test programs.  test_get/test_encode read
        # lines from stdin until a blank line; a single "hello" line plus an
        # empty line drives them deterministically.  test_cookie/test_send
        # need no input.  Any non-zero exit fails conan create.
        for name in self._upstream_tests:
            upstream_exe = os.path.join(self.build_folder, name)
            if not os.path.isfile(upstream_exe):
                raise ConanInvalidConfiguration(
                    "Upstream test executable was not built: {}".format(name)
                )
            if name in ("test_get", "test_encode"):
                command = 'printf "hello\\n\\n" | {}'.format(
                    shlex.quote(upstream_exe)
                )
            else:
                command = shlex.quote(upstream_exe)
            self.output.info("UPSTREAM_TEST_RUN={}".format(name))
            self.run(command, env="conanrun")
