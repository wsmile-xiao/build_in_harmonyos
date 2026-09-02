#!/usr/bin/env python3
import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load
from conan.tools.layout import basic_layout


class MunitConan(ConanFile):
    name = "munit"
    version = "0.2.0"
    description = "Small C unit-testing framework"
    license = "MIT"
    homepage = "https://github.com/nemequ/munit"
    url = "https://github.com/nemequ/munit"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("munit/0.2.0 supports Linux and OHOS only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _compiler_executables(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return (
            executables.get("c", "clang"),
            executables.get("ar", "llvm-ar"),
            executables.get("ranlib", "llvm-ranlib"),
        )

    def _cflags(self):
        flags = ["-std=c99", "-fPIC"]
        if str(self.settings.build_type) == "Debug":
            flags.extend(["-O0", "-g"])
        else:
            flags.append("-O2")
        return flags

    def build(self):
        apply_conandata_patches(self)
        cc, ar, ranlib = self._compiler_executables()
        cflags = self._cflags()
        os.makedirs(self.build_folder, exist_ok=True)

        object_file = os.path.join(self.build_folder, "munit.o")
        compile_command = shlex.join(
            [
                cc,
                *cflags,
                "-I" + self.source_folder,
                "-c",
                os.path.join(self.source_folder, "munit.c"),
                "-o",
                object_file,
            ]
        )
        self.run(compile_command, cwd=self.build_folder)

        if self.options.shared:
            library = os.path.join(self.build_folder, "libmunit.so")
            self.run(
                shlex.join(
                    [cc, "-shared", "-Wl,-soname,libmunit.so", "-o", library, object_file]
                ),
                cwd=self.build_folder,
            )
        else:
            library = os.path.join(self.build_folder, "libmunit.a")
            self.run(shlex.join([ar, "rcs", library, object_file]), cwd=self.build_folder)
            self.run(shlex.join([ranlib, library]), cwd=self.build_folder)

        make_environment = f"CC={shlex.quote(cc)} CFLAGS={shlex.quote(' '.join(cflags))}"
        self.run(f"make {make_environment} -j1", cwd=self.source_folder)

        test_tmpdir = os.path.join(self.build_folder, "munit-tmp")
        os.makedirs(test_tmpdir, exist_ok=True)
        test_log = os.path.join(self.build_folder, "munit-upstream-test.log")
        test_command = (
            f"MUNIT_TMPDIR={shlex.quote(test_tmpdir)} make -j1 test > {shlex.quote(test_log)} 2>&1; "
            f"rc=$?; cat {shlex.quote(test_log)}; exit $rc"
        )
        self.run(test_command, cwd=self.source_folder)
        self._emit_upstream_test_result(test_log)

    def _emit_upstream_test_result(self, test_log):
        output = load(self, test_log)
        match = re.search(
            r"(\d+) of (\d+) \(\d+%\) tests successful, "
            r"(\d+) \(\d+%\) test skipped",
            output,
        )
        if not match:
            raise ConanInvalidConfiguration(
                "could not parse the upstream munit test summary from " + test_log
            )

        passed = int(match.group(1))
        discovered = int(match.group(2))
        skipped = int(match.group(3))
        executed = discovered - skipped
        failed = executed - passed
        example_source = load(self, os.path.join(self.source_folder, "example.c"))
        table_match = re.search(
            r"static MunitTest test_suite_tests\[\] = \{(.*?)\n\};",
            example_source,
            re.DOTALL,
        )
        registered = len(re.findall(r'"/example/[^"\\]+"', table_match.group(1))) if table_match else 0
        if registered != 3:
            raise ConanInvalidConfiguration(
                f"unexpected upstream example test registration count: {registered}"
            )

        result = {
            "status": "passed" if failed == 0 and skipped == 0 else "not_passed",
            "framework": "munit",
            "command": "make -j1 test",
            "registered_suite_entries": registered,
            "discovered_cases": discovered,
            "executed_cases": executed,
            "passed_cases": passed,
            "failed_cases": failed,
            "skipped_cases": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, sort_keys=True))

    def package(self):
        copy(self, "munit.h", self.source_folder, os.path.join(self.package_folder, "include"))
        library_name = "libmunit.so" if self.options.shared else "libmunit.a"
        copy(self, library_name, self.build_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["munit"]
