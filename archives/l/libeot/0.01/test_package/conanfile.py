import filecmp
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibeotTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("consumer tests require executing the target binary")

        builddir = self.build_folder
        # 23 API checks against the packaged library; the consumer also writes
        # fixture.eot and expected.ttf into the build folder for the roundtrip.
        consumer = os.path.join(self.cpp.build.bindirs[0], "libeot_test")
        self.run('"%s"' % consumer, env="conanrun", cwd=builddir)
        # The packaged eot2ttf tool, invoked by explicit path (E529: PATH
        # lookup for dependency tools is unreliable in the test_package
        # context) under the conanrun environment.
        tool = os.path.join(self.dependencies["libeot"].cpp_info.bindirs[0], "eot2ttf")
        self.run('"%s" fixture.eot roundtrip.ttf' % tool, env="conanrun", cwd=builddir)
        if not filecmp.cmp(os.path.join(builddir, "expected.ttf"),
                           os.path.join(builddir, "roundtrip.ttf"), shallow=False):
            raise ConanException("eot2ttf roundtrip output differs from the expected TTF payload")
