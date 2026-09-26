import os

from conan import ConanFile
from conan.errors import ConanException


class WeborfTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["weborf"].package_folder
        binpath = os.path.join(pkg, "bin", "weborf")
        if not os.path.isfile(binpath):
            raise ConanException("weborf 可执行文件缺失: %s" % binpath)
        checker = os.path.join(self.recipe_folder, "weborf_consumer_check.py")
        python = self._python()
        # env="conanrun" 带上 package_info() 传播的 MAGIC 与依赖 lib 路径
        self.run('"%s" "%s" "%s"' % (python, checker, binpath), env="conanrun")

    def _python(self):
        import shutil
        for name in ("python3", "python"):
            found = shutil.which(name)
            if found:
                return found
        raise ConanException("消费者测试需要可用的 python 解释器")
