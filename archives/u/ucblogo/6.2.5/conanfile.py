#!/usr/bin/env python3
"""Conan recipe for UCBLogo 6.2.5 (terminal interpreter)."""

import hashlib
import os
import shlex
import shutil
import ssl
import tarfile
import tempfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UCBLogoConan(ConanFile):
    name = "ucblogo"
    version = "6.2.5"
    description = "Berkeley Logo interpreter for the Logo programming language"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/jrincayc/ucblogo-code"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    _upstream_suites = 10
    _upstream_cases = 94

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The artifact repository publishes a static wide-character build.
        self.requires("ncurses/6.4", options={"shared": False})

    def layout(self):
        basic_layout(self)

    def _download_archive(self, urls, destination, expected_sha256, context):
        if isinstance(urls, str):
            urls = [urls]
        last_error = None
        for url in urls:
            request = urllib.request.Request(
                url, headers={"User-Agent": "ohpcd-conan-source/1.0"}
            )
            try:
                with urllib.request.urlopen(
                    request, timeout=300, context=context
                ) as response, open(destination, "wb") as output:
                    shutil.copyfileobj(response, output)
                break
            except Exception as exc:
                last_error = exc
        else:
            raise ConanException(
                f"UCBLogo archive download failed for all candidates: {last_error}"
            )

        digest = hashlib.sha256()
        with open(destination, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256:
            raise ConanException(
                "UCBLogo archive sha256 mismatch: "
                f"expected {expected_sha256}, got {actual_sha256}"
            )

    def source(self):
        # The OHOS worker does not guarantee the external curl/wget tool
        # required by Conan's default downloader. Download with the Python
        # standard library and verify the pinned upstream checksum.
        source_data = self.conan_data["sources"]
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with tempfile.TemporaryDirectory(dir=self.source_folder) as temp_dir:
            archive = os.path.join(temp_dir, "upstream.tar.gz")
            self._download_archive(
                source_data["url"], archive, source_data["sha256"], context
            )

            unpack_dir = os.path.join(temp_dir, "unpacked")
            os.makedirs(unpack_dir)
            with tarfile.open(archive, "r:gz") as bundle:
                bundle.extractall(unpack_dir)

            roots = [
                os.path.join(unpack_dir, entry)
                for entry in os.listdir(unpack_dir)
            ]
            if len(roots) != 1 or not os.path.isdir(roots[0]):
                raise ConanException(
                    "UCBLogo source archive does not contain a single root directory"
                )
            shutil.copytree(roots[0], self.source_folder, dirs_exist_ok=True)

            completion = self.conan_data.get("test_completion")
            if completion:
                test_archive = os.path.join(temp_dir, "upstream-tests.tar.gz")
                self._download_archive(
                    completion["url"],
                    test_archive,
                    completion["sha256"],
                    context,
                )
                with tarfile.open(test_archive, "r:gz") as bundle:
                    for relative_path, expected in completion["files"].items():
                        member_name = f"{completion['root']}/{relative_path}"
                        member = bundle.extractfile(member_name)
                        if member is None:
                            raise ConanException(
                                f"UCBLogo test archive is missing {member_name}"
                            )
                        destination = os.path.join(
                            self.source_folder, relative_path
                        )
                        os.makedirs(os.path.dirname(destination), exist_ok=True)
                        with member, open(destination, "wb") as output:
                            shutil.copyfileobj(member, output)
                        digest = hashlib.sha256()
                        with open(destination, "rb") as stream:
                            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                                digest.update(chunk)
                        actual = digest.hexdigest()
                        if actual != expected:
                            raise ConanException(
                                f"UCBLogo test file {relative_path} sha256 mismatch: "
                                f"expected {expected}, got {actual}"
                            )

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--enable-objects",
                "--disable-wx",
                "--disable-x11",
                "--disable-docs",
                "LIBS=-lncursesw",
            ]
        )
        # The release configure script predates OHOS and does not probe
        # termios.h. The patched term.c consumes this standard macro.
        tc.extra_defines.append("HAVE_TERMIOS_H=1")
        # libncursesw provides the termcap compatibility globals PC, UP and
        # BC. Suppress the application-local definitions to avoid duplicate
        # symbols in the static OHOS package.
        tc.extra_defines.append("UCBLOGO_USE_NCURSES_TERMCAP=1")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # The pinned upstream release asset contains generated Autotools
        # files. Replace Autoconf's restrictive umask 077 with 022 because
        # HMDFS temporary directories otherwise become inaccessible.
        configure = os.path.join(self.source_folder, "configure")
        os.chmod(configure, 0o755)
        for helper in ("compile", "depcomp", "install-sh", "missing"):
            helper_path = os.path.join(self.source_folder, helper)
            if os.path.exists(helper_path):
                os.chmod(helper_path, 0o755)
        replace_in_file(self, configure, "umask 077", "umask 022")

        autotools = Autotools(self)
        autotools.configure()

        # The upstream help-index generator hard-codes relative paths to
        # usermanual and helpfiles/. Conan builds out of tree, so stage those
        # runtime inputs in the build folder before invoking the normal
        # upstream make target.
        shutil.copy2(
            os.path.join(self.source_folder, "usermanual"),
            os.path.join(self.build_folder, "usermanual"),
        )
        shutil.copytree(
            os.path.join(self.source_folder, "helpfiles"),
            os.path.join(self.build_folder, "helpfiles"),
            dirs_exist_ok=True,
        )
        autotools.make(args=["-j1"])

        # Run the upstream suite exactly once in its source directory.  The
        # official CI invokes the same UnitTests.lg harness with -f and -x;
        # xvfb-run is unnecessary because wx/X11 are disabled for OHOS.
        tests_dir = os.path.join(self.source_folder, "tests")
        executable = os.path.join(self.build_folder, "ucblogo")
        logolib = os.path.join(self.source_folder, "logolib")
        results = os.path.join(self.build_folder, "logo-unit-test-results.txt")

        test_command = " ".join(
            [
                f"LOGOLIB={shlex.quote(logolib)}",
                shlex.quote(executable),
                "UnitTests.lg",
                "-",
                "-f",
                shlex.quote(results),
                "-x",
            ]
        )
        self.run(test_command, cwd=tests_dir)

        # Mirror the official CI grader, then enforce the exact suite and case
        # count so a truncated output file cannot pass silently.
        self.run(
            "awk '/\\.\\.\\./ && ! /Ok$/ { bad=1; print } END { exit bad }' "
            + shlex.quote(results)
        )

        case_lines = []
        suite_lines = []
        with open(results, "r", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                if "..." in line:
                    case_lines.append(line.rstrip("\n"))
                if "Test Suites:" in line:
                    suite_lines.append(line.strip())

        if len(suite_lines) != 1 or not suite_lines[0].endswith(
            str(self._upstream_suites)
        ):
            raise ConanException(
                "UCBLogo upstream test run did not report "
                f"{self._upstream_suites} suites: {suite_lines!r}"
            )
        if len(case_lines) != self._upstream_cases:
            raise ConanException(
                "UCBLogo upstream test run reported "
                f"{len(case_lines)} cases, expected {self._upstream_cases}"
            )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
