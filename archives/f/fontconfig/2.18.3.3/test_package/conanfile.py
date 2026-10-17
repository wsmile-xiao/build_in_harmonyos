import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import save


class TestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        # Preserve a profile sysroot as one CMake value when the SDK path
        # contains spaces. Older Conan generic_system templates omit quotes.
        block = toolchain.blocks["generic_system"]
        block.template = block.template.replace(
            "set(CMAKE_SYSROOT {{ cmake_sysroot }})",
            'set(CMAKE_SYSROOT "{{ cmake_sysroot }}")',
        )
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Target consumer execution pending; compile is not PASS")
            return
        package = self.dependencies["fontconfig"].package_folder
        config = os.path.join(package, "etc", "fonts", "fonts.conf")
        invalid = os.path.join(self.build_folder, "invalid-fonts.conf")
        missing = os.path.join(self.build_folder, "missing-fonts.conf")
        save(self, invalid, "<fontconfig><dir>broken</fontconfig>")
        cache = os.path.join(self.build_folder, "private-cache")
        os.makedirs(cache, exist_ok=True)
        environment = Environment()
        environment.define_path("XDG_CACHE_HOME", cache)
        executable = os.path.join(self.cpp.build.bindirs[0], "test_probe")
        if self.settings.os == "Windows":
            executable += ".exe"
        quote = lambda p: ('"' + p.replace('"', '\\"') + '"') if self.settings.os == "Windows" else shlex.quote(p)
        with environment.vars(self).apply():
            for filename, mode in ((config, "match"), (invalid, "reject"), (missing, "reject")):
                self.run("%s %s %s" % (quote(executable), quote(filename), mode), env="conanrun")
            if self.settings.os == "OHOS":
                script = os.path.join(self.source_folder, "harmony_tests", "projected_config.py")
                self.run("%s %s %s %s %s" % tuple(quote(p) for p in
                         (sys.executable, script, executable, config, self.build_folder)),
                         env="conanrun")
