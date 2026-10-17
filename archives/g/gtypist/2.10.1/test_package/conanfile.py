"""Conan test_package - gtypist 2.10.1

R34: test_package must substantially exercise the tested package's functionality.
gtypist is an ncurses terminal application (no library), so tests run the
packaged binary directly and assert real behavior via exit codes and output:

  1. gtypist --version | grep 2.10.1  - binary runs, gengetopt command line
                                        works, correct version reported
  2. gtypist --help                   - usage output, exit 0
  3. ! gtypist --no-such-option-xyz   - invalid option must fail (gengetopt
                                        standard behavior), proving real
                                        argument validation

gtypist's main loop is full-screen ncurses; the command-line path exercised
here proves the compiled binary links and executes against ncursesw on OHOS.
"""
import os

from conan import ConanFile


class GtypistTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 测试源文件 test.sh（L0c 要求）：包含与上方同源的 3 处行为断言
        self.run("sh %s" % os.path.join(self.recipe_folder, "test.sh"),
                 env="conanrun")
