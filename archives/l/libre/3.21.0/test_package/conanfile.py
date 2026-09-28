import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

class LibreTestConan(ConanFile):
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

    def _bindirs(self):
        # 只收 CMake 产出的可执行文件：同一目录里还有 t_*.c.obj / t_*.c
        # 之类以 t_ 开头的中间产物，必须排除（否则会去执行 .obj，报 126）。
        found = []
        for root, _dirs, files in os.walk(self.build_folder):
            for f in files:
                if not f.startswith("t_") or "." in f:
                    continue
                path = os.path.join(root, f)
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    found.append(path)
        return sorted(found)

    def test(self):
        if not can_run(self):
            self.output.info("交叉构建，消费者测试程序不可执行")
            return
        bins = self._bindirs()
        assert len(bins) >= 20, "消费者测试程序数量异常: %d" % len(bins)
        # E298/E529: 用 VirtualRunEnv 生成的 conanrun 脚本注入运行时搜索路径
        # （libre 是 shared 包，消费者需要 LD_LIBRARY_PATH 指向包内 lib/）。
        # 注意 conan 2.29 的 run(env=...) 只接受脚本名（str）或其列表，
        # 传 dict 会抛 AssertionError: env argument ... should be a list。
        for exe in bins:
            self.run('"%s"' % exe, env="conanrun")
        self.output.info("消费者测试通过: %d 个程序" % len(bins))
