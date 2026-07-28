import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class At51Conan(ConanFile):
    name = "at51"
    version = "1.1.1"
    description = "Command-line tools for reverse engineering 8051 firmware"
    license = "MIT"
    homepage = "https://github.com/8051Enthusiast/at51"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cargo_target_dir(self):
        return os.path.join(self.build_folder, "cargo-target")

    def build(self):
        target_dir = shlex.quote(self._cargo_target_dir())
        self.run(
            f"cargo build --release --locked --target-dir {target_dir}",
            cwd=self.source_folder,
            env="conanbuild",
        )

        # Cargo succeeds when a crate has no tests.  This recipe deliberately
        # treats that as an error so the upstream test requirement cannot be
        # satisfied by an empty test run.
        test_log = os.path.join(self.build_folder, "cargo-test.log")
        self.run(
            "cargo test --release --locked "
            f"--target-dir {target_dir} > {shlex.quote(test_log)} 2>&1",
            cwd=self.source_folder,
            env="conanbuild",
        )
        with open(test_log, encoding="utf-8", errors="replace") as log_file:
            test_output = log_file.read()
        passed = sum(
            int(count)
            for count in re.findall(r"test result: ok\. (\d+) passed;", test_output)
        )
        if passed == 0:
            raise ConanException("at51 upstream cargo test reported zero passing tests")
        self.output.info(f"at51 upstream cargo test: {passed} tests passed")

    def package(self):
        binary_dir = os.path.join(self._cargo_target_dir(), "release")
        binary_path = os.path.join(binary_dir, "at51")
        if not os.path.isfile(binary_path):
            raise ConanException(f"at51 binary was not built: {binary_path}")
        copy(self, "at51", src=binary_dir, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
