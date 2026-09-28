"""Package the upstream ud 1.1.0 tag on HarmonyOS PC AArch64."""

import os
import shlex

from conan import ConanFile
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class UdConan(ConanFile):
    name = "ud"
    version = "1.1.0"
    description = "Convert dates to and from UNIX day numbers"
    homepage = "https://github.com/xyproto/ud"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "BSD-3-Clause"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        cmake_file = os.path.join(self.source_folder, "CMakeLists.txt")
        # The upstream order is `project(ud)` then `set(CMAKE_C_COMPILER gcc)`.
        # That override defeats -DCMAKE_C_COMPILER=clang on the actual target.
        replace_in_file(self, cmake_file, "set(CMAKE_C_COMPILER gcc)", "")
        replace_in_file(
            self, cmake_file,
            "set(TARGET ud PROPERTY C_STANDARD 18)",
            "set(CMAKE_C_STANDARD 17)",
        )

    def build(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise RuntimeError("Verified only on HarmonyOS PC AArch64")
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        build_dir = os.path.join(self.build_folder, "cmake-ud")
        prefix = f"TMPDIR={shlex.quote(tmp)} "
        self.run(
            prefix + f"cmake -S {shlex.quote(self.source_folder)} "
            f"-B {shlex.quote(build_dir)} -DCMAKE_C_COMPILER=clang "
            "-DCMAKE_BUILD_TYPE=Release",
            cwd=self.build_folder,
        )
        self.run(
            prefix + f"cmake --build {shlex.quote(build_dir)} --parallel 1",
            cwd=self.build_folder,
        )

    def package(self):
        copy(self, "ud", os.path.join(self.build_folder, "cmake-ud"),
             os.path.join(self.package_folder, "bin"), keep_path=False)
        os.chmod(os.path.join(self.package_folder, "bin", "ud"), 0o755)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
