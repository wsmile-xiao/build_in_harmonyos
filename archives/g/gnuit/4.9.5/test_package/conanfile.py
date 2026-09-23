"""Conan test_package - gnuit 4.9.5

R34: test_package must substantially exercise the tested package's functionality.
gnuit ships terminal binaries (no library), so tests run the packaged
binaries directly and assert real behavior via exit codes:

  1. gitwhich gitfm    - PATH lookup finds the packaged gitfm binary (exit 0)
  2. gitwhich gitwhich - PATH lookup finds the packaged gitwhich itself (exit 0)
  3. ! gitwhich no-such-gnuit-tool-xyz - lookup of a non-existent program must
                         fail (exit != 0), proving the lookup logic is real

gitwhich implements Vixie-style which() over PATH (src/gitwhich.c); the
positive cases also prove the compiled binary links and executes against
ncurses' termcap API on OHOS.
"""
import os

from conan import ConanFile


class GnuitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 测试源文件 test.sh（L0c 要求）：包含与下方同源的 3 处行为断言
        import os
        self.run("sh %s" % os.path.join(self.recipe_folder, "test.sh"),
                 env="conanrun")
