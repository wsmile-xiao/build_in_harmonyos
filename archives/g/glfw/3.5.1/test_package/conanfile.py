import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class GlfwTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Compile the test against the installed glfw headers + lib (R34).
        dep = self.dependencies["glfw"].cpp_info
        inc = " ".join("-I" + d for d in dep.includedirs)
        libdir = dep.libdirs[0]
        cc = os.environ.get("CC", "clang")
        self.run(
            f"{shlex.quote(cc)} test.c -o test_glfw_null {inc} "
            f"-L{libdir} -lglfw -Wl,--allow-shlib-undefined -lm -pthread"
        )

    def test(self):
        if not can_run(self):
            self.output.info("cannot run on this host: cross-building, compile+link only")
            return
        # OHOS /bin/sh (mksh) cannot execute ELF binaries directly.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_bin = os.path.join(self.build_folder, "test_glfw_null")
        command = f"{shlex.quote(bash)} -c {shlex.quote(test_bin)}"
        self.run(command, env="conanrun")
