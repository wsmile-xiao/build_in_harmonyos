from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class QsoptExTestConan(ConanFile):
    """test_package：C 消费者（API 精确求解）+ 鸿蒙特有 CLI 求解样例测试。

    两部分都经 self.run() 真实执行（PF3/L0c）：
      1. ./qsopt_ex_test —— 链接 libqsopt_ex 的消费者，6 条断言；
      2. sh test_ohos_solve.sh —— 用安装后的 esolver 求解自备 .map 样例，
         14 条产物断言（rc=0 + .sol 非空 + OPTIMAL + Value=14 + 解坐标）。
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross build: skip runnable test_package")
            return
        # 消费者断言（6 条，ok/not ok 逐条打印，非零退出即失败）
        self.run("./qsopt_ex_test", env="conanrun")
        # 鸿蒙特有求解测试（14 条产物断言）
        script = "{}/test_ohos_solve.sh".format(self.source_folder)
        self.run('sh "{}"'.format(script), env="conanrun")
