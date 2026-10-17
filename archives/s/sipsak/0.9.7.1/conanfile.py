#!/usr/bin/env python3
"""Conan recipe for sipsak 0.9.7 on HarmonyOS.

Builds the upstream C sources directly with the Conan build-environment
compiler (no autotools host detection), and runs the upstream Check-based
unit tests (tests/check_helper.c, tests/check_md5.c) via the bundled
minimal Check-compatible shim. The real test run is parsed into
upstream_test_summary.json, carried into the package as res/, and the
test_package stage re-emits it as HMBS_UPSTREAM_TEST_RESULT so the hmbs
preflight sees the actual executed/passed counts even when a later build
is served from the Conan cache.
"""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get


class SipsakConan(ConanFile):
    name = "sipsak"
    version = "0.9.7.1"
    description = "SIP stress and diagnostics command-line utility"
    license = "GPL-2.0-or-later"
    homepage = "https://sipsak.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        # Keep source and build together: the recipe compiles the upstream
        # sources directly with clang and needs the bundled Check shim
        # (shipped via export_sources) visible from build().
        self.folders.build = "."
        self.folders.generators = "."

    def export_sources(self):
        # Ship the bundled minimal Check-compatible shim so the upstream
        # unit tests can be compiled and executed without the Check
        # framework, which is not available in the OHOS build environment.
        copy(
            self,
            "*",
            os.path.join(self.recipe_folder, "files"),
            os.path.join(self.export_sources_folder, "files"),
            keep_path=True,
        )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        sources = (
            "transport.c auth.c header_f.c helper.c md5.c request.c "
            "shoot.c sipsak.c exit_code.c"
        )
        source_args = " ".join(
            '"{}"'.format(os.path.join(self.source_folder, "src", item))
            for item in sources.split()
        )
        build_type_flags = {
            "Debug": "-g -O0",
            "Release": "-O2 -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
        }[str(self.settings.build_type)]
        flags = (
            build_type_flags + " "
            "-DPACKAGE_NAME=\\\"sipsak\\\" "
            "-DPACKAGE_BUGREPORT=\\\"nils@sipsak.org\\\" "
            "-DDEFAULT_TIMEOUT=500 "
            "-fcommon -D_GNU_SOURCE -DPACKAGE_VERSION=\\\"0.9.7\\\" "
            "-DHAVE_STDIO_H -DHAVE_STDLIB_H -DHAVE_STDARG_H "
            "-DHAVE_STDINT_H -DHAVE_STRING_H -DHAVE_STRINGS_H "
            "-DHAVE_CTYPE_H -DHAVE_ERRNO_H -DHAVE_UNISTD_H "
            "-DHAVE_SYS_TYPES_H -DHAVE_SYS_TIME_H -DHAVE_SYS_PARAM_H "
            "-DHAVE_SYS_SOCKET_H -DHAVE_SYS_UTSNAME_H -DHAVE_SYS_POLL_H "
            "-DHAVE_NETDB_H -DHAVE_NETINET_IN_H -DHAVE_ARPA_INET_H "
            "-DHAVE_REGEX_H -DHAVE_SIGNAL_H -DHAVE_LIMITS_H "
            "-DHAVE_SYSLOG_H -DHAVE_SYS_WAIT_H "
            "-DHAVE_GETOPT_H -DHAVE_GETOPT_LONG -DHAVE_INET_NTOP "
            "-DHAVE_STRNCASECMP -DHAVE_STRCASESTR -DHAVE_CALLOC "
            "-DHAVE_GETDOMAINNAME -DTIME_WITH_SYS_TIME"
        )
        output = os.path.join(self.build_folder, "sipsak")
        self.run(
            '"{}" {} -I"{}" {} -o "{}"'.format(
                cc, flags, os.path.join(self.source_folder, "src"), source_args, output
            ),
            env="conanbuild",
        )
        self._run_upstream_tests(cc, flags)

    def _run_upstream_tests(self, cc, flags):
        """Compile and run the upstream Check-based unit tests using the
        bundled minimal Check-compatible shim, so the upstream test sources
        are exercised even when the Check framework is not installed.

        The shim's runner prints one summary line per program in the form
        "N tests run, M failed" (see check_shim.c); the real counts are
        parsed from that output and written to upstream_test_summary.json,
        which the test_package stage re-emits as HMBS_UPSTREAM_TEST_RESULT.
        Any failed test raises, so conan create fails honestly.
        """
        source_folder = self.source_folder
        shim_dir = os.path.join(source_folder, "files")
        # The upstream tests include "../config.h", which autoconf normally
        # generates. Emit a minimal OHOS-compatible config header.
        config_h = os.path.join(source_folder, "config.h")
        if not os.path.isfile(config_h):
            with open(config_h, "w", encoding="utf-8") as handle:
                handle.write(
                    "#define HAVE_CHECK_H 1\n"
                    "#define HAVE_STDIO_H 1\n"
                    "#define HAVE_STDLIB_H 1\n"
                    "#define HAVE_STRING_H 1\n"
                    "#define HAVE_STRINGS_H 1\n"
                    "#define HAVE_UNISTD_H 1\n"
                )
        # Reuse the full feature macro set of the main build and enable the
        # upstream prototypes used by the old-style md5 sources.
        test_flags = (
            flags
            + " -DRUNNING_CHECK -DHAVE_CHECK_H -DPROTOTYPES=1 "
            + '-I"{src}" -I"{src}/src" -I"{shim}" '.format(
                src=source_folder, shim=shim_dir
            )
        )
        tests = (
            (
                "check_helper",
                [
                    os.path.join(source_folder, "tests", "check_helper.c"),
                    os.path.join(source_folder, "src", "helper.c"),
                    os.path.join(source_folder, "src", "exit_code.c"),
                    os.path.join(shim_dir, "check_shim.c"),
                ],
            ),
            (
                "check_md5",
                [
                    os.path.join(source_folder, "tests", "check_md5.c"),
                    os.path.join(source_folder, "src", "md5.c"),
                    os.path.join(shim_dir, "check_shim.c"),
                ],
            ),
        )
        discovered = 0
        executed = 0
        passed = 0
        failed = 0
        for name, test_sources in tests:
            source_args = " ".join('"{}"'.format(item) for item in test_sources)
            binary = os.path.join(self.build_folder, name)
            self.run(
                '"{}" {} {} -o "{}"'.format(cc, test_flags, source_args, binary),
                env="conanbuild",
            )
            # NOTE: Conan's self.run() returns the exit code, not the command
            # output, so the test output must be captured via subprocess
            # instead of relying on the return value.
            proc = subprocess.run(
                [binary],
                env=os.environ.copy(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                timeout=1800,
            )
            output = proc.stdout or ""
            self.output.info("upstream test {} output:\n{}".format(name, output))
            if proc.returncode != 0:
                raise ConanException(
                    "upstream test {} exited with code {}:\n{}".format(
                        name, proc.returncode, output[-4000:]
                    )
                )
            match = re.search(r"(\d+) tests run, (\d+) failed", output)
            if not match:
                raise ConanException(
                    "cannot parse upstream {} test summary from output:\n{}".format(
                        name, output[-4000:]
                    )
                )
            run_count = int(match.group(1))
            failed_count = int(match.group(2))
            discovered += run_count
            executed += run_count
            passed += run_count - failed_count
            failed += failed_count
        summary = {
            "status": "passed" if (executed > 0 and failed == 0) else "failed",
            "framework": "check-shim",
            "command": "check_helper; check_md5",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        summary_path = os.path.join(self.build_folder, "upstream_test_summary.json")
        with open(summary_path, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, ensure_ascii=False)
        self.output.info("upstream test summary written: " + summary_path)
        if failed != 0 or executed == 0:
            raise ConanException(
                "upstream tests failed: " + json.dumps(summary, ensure_ascii=False)
            )

    def package(self):
        copy(
            self,
            "sipsak",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "sipsak.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # Carry the upstream test summary into the package so the
        # test_package stage can emit HMBS_UPSTREAM_TEST_RESULT even when a
        # later preflight reuses the cached binary (build() skipped).
        summary_src = os.path.join(self.build_folder, "upstream_test_summary.json")
        if os.path.isfile(summary_src):
            copy(
                self,
                "upstream_test_summary.json",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "res"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]