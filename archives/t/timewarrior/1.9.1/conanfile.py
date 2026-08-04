#!/usr/bin/env python3
"""Conan recipe for Timewarrior 1.9.1."""
import os
import stat
from datetime import datetime, timezone

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)


class TimewarriorConan(ConanFile):
    name = "timewarrior"
    version = "1.9.1"
    description = "Command-line time tracking application"
    license = "MIT"
    homepage = "https://timewarrior.net/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Timewarrior supports Linux and OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "cmake", "CXXSniffer.cmake"),
            '${CMAKE_SYSTEM_NAME} MATCHES "Linux"',
            '${CMAKE_SYSTEM_NAME} MATCHES "Linux|OHOS|HarmonyOS"',
        )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            test_source = os.path.join(self.source_folder, "test")
            test_build = os.path.join(self.build_folder, "test")
            copy(self, "*.t", src=test_source, dst=test_build)
            for directory in ("basetest", "simpletap", "test_extensions"):
                copy(
                    self,
                    "*",
                    src=os.path.join(test_source, directory),
                    dst=os.path.join(test_build, directory),
                )
            for helper in (
                "bash_tap.sh",
                "bash_tap_ti.sh",
                "timemachine",
            ):
                copy(self, helper, src=test_source, dst=test_build)
            # Upstream test/problems is an executable Python file, not a directory.
            problems_helper = os.path.join(test_source, "problems")
            if not os.path.isfile(problems_helper):
                raise ConanInvalidConfiguration(
                    "Missing upstream test helper file: problems"
                )
            copy(self, "problems", src=test_source, dst=test_build)
            copy(self, "run_all", src=test_source, dst=test_build)
            for required_helper in ("problems", "run_all"):
                if not os.path.isfile(os.path.join(test_build, required_helper)):
                    raise ConanInvalidConfiguration(
                        f"Missing staged upstream test helper: {required_helper}"
                    )
            copy(
                self,
                "totals.py",
                src=os.path.join(self.source_folder, "ext"),
                dst=test_build,
            )
            copy(
                self,
                "*",
                src=os.path.join(self.source_folder, "doc"),
                dst=os.path.join(self.build_folder, "doc"),
            )
            # Center local wall-clock time at noon so relative ranges cannot
            # cross a date boundary while the upstream suite is running.
            utc_hour = datetime.now(timezone.utc).hour
            posix_offset = utc_hour - 12
            previous_tz = os.environ.get("TZ")
            previous_path = os.environ.get("PATH")
            os.environ["TZ"] = f"UTC{posix_offset:+d}"
            self._stage_man_shim(test_build)
            try:
                self.run("chmod +x *.t problems run_all", cwd=test_build)
                cmake.build(target="test")
                self.run("./AtomicFileTest", cwd=test_build)
            finally:
                if previous_tz is None:
                    os.environ.pop("TZ", None)
                else:
                    os.environ["TZ"] = previous_tz
                if previous_path is None:
                    os.environ.pop("PATH", None)
                else:
                    os.environ["PATH"] = previous_path

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    def _stage_man_shim(self, test_build):
        shim = os.path.join(test_build, "man")
        script = """#!/usr/bin/env sh
set -eu
topic=
for arg in "$@"; do
    topic="$arg"
done
if [ -z "$topic" ]; then
    echo "No manual entry" >&2
    exit 16
fi
IFS=:
for root in ${MANPATH:-}; do
    for section in 1 7; do
        page="$root/man$section/$topic.$section"
        if [ -f "$page" ]; then
            cat "$page"
            exit 0
        fi
    done
done
echo "No manual entry for $topic" >&2
exit 16
"""
        with open(shim, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(script)
        os.chmod(shim, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)
        os.environ["PATH"] = test_build + os.pathsep + os.environ.get("PATH", "")
