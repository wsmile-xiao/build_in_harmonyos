import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RemctlTest(ConanFile):
    # 不声明 package_type：test_package 里写 "none" 在 conan 2.29 直接报
    # Invalid package type 'none'（实测 rc=1，且发生在 Launching test_package 之后）
    settings = "os", "arch", "compiler", "build_type"
    # VirtualRunEnv 必须显式声明：只写 CMakeDeps/CMakeToolchain 时 conanrun.sh 里根本没有
    # LD_LIBRARY_PATH，self.run(..., env="conanrun") 就取不到依赖的 .so，
    # 实测报 Error loading shared library libevent-2.1.so.7 / libevent_extra / libevent_pthreads
    # 然后 rc=1（本包静态库 libremctl.a 本身不需要它们，是传递依赖被 CMake 链接进来的）。
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 真实执行消费者程序：以库使用者身份编译/链接并调用 libremctl 公共 API，
        # 断言决定退出码（§10.1 赛道二；只 include/只链接/只打印均不合格）
        exe = os.path.join(self.cpp.build.bindir, "test_remctl")
        if not os.path.exists(exe):
            raise Exception("消费者测试程序未生成：%s" % exe)
        self.run('"%s"' % exe, env="conanrun")
