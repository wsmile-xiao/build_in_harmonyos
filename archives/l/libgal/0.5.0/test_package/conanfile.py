import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibgalTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        self._build_consumer_with_log(cmake)

    def _build_consumer_with_log(self, cmake):
        """Build the consumer with its output bound to a log file.

        Letting the recipe process output streams be inherited by the child
        makes the first compiler invocation on this platform fail without a
        single diagnostic line; binding the build output to a file keeps the
        build reproducible and the compiler output readable (see the
        libncurses 6.6 adaptation, PR #10975).
        """
        log_path = os.path.join(self.build_folder, "cmake-build.log")
        try:
            with open(log_path, "w", encoding="utf-8") as stream:
                cmake.build(build_tool_args=["-j1"], stdout=stream, stderr=stream)
        except Exception as error:
            self.output.error("consumer build failed; last lines of cmake-build.log:")
            self.output.error("\n".join(self._log_tail(log_path)))
            raise error
        with open(log_path, encoding="utf-8", errors="replace") as stream:
            content = stream.read().splitlines()
        self.output.info(f"--- cmake-build.log ({len(content)} lines) ---")
        for start in range(0, len(content), 500):
            self.output.info("\n".join(content[start : start + 500]))

    @staticmethod
    def _log_tail(path, lines=80):
        if not os.path.isfile(path):
            return [f"<missing log file: {path}>"]
        with open(path, encoding="utf-8", errors="replace") as stream:
            return stream.read().splitlines()[-lines:]

    def test(self):
        if not can_run(self):
            return
        # The consumer binary's exit code is the canonical PASS/FAIL signal.
        bindir = self.cpp.build.bindirs[0]
        self.run(f'"{os.path.join(bindir, "test_gal")}"', cwd=bindir)
