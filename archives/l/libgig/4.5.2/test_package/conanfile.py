import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

# 上游 `make install` 交付的 14 个命令行工具（实测 `make install` 清单，见 reports/）
CLI_TOOLS = (
    "rifftree", "dlsdump", "gigdump", "gigextract", "gigmerge", "gig2mono",
    "gig2stereo", "sf2dump", "sf2extract", "korgdump", "korg2gig", "akaidump",
    "akaiextract", "wav2gig",
)


class LibgigTestConan(ConanFile):
    """libgig 消费者测试包。

    ① C++ 消费者程序（test_libgig.cpp）链接被测静态库，断言版本指纹与
       RIFF/gig 两层往返 —— 这是 rule12 的「鸿蒙特有测试」计数来源。
    ② 交付的 14 个 CLI 工具在**裸环境**（显式 unset LD_LIBRARY_PATH）下
       `--version` / `--help` 必须 rc=0：conanrun 的 LD_LIBRARY_PATH 会掩盖
       错误的 RUNPATH，只有在裸环境下才测得到产物本身（libfstfar 的
       `//lib` RUNPATH 即由此漏出）。
    """

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _package_folder(self):
        # 依赖的 package_folder 必须从 dependencies 取；不要用
        # IMPORTED_LOCATION_<CONFIG> 之类的生成物字段（构建配置一变即失效）。
        return self.dependencies[self.tested_reference_str].package_folder

    def test(self):
        if not can_run(self):
            raise ConanException("Cannot run tests: not a runnable (build==host) context")

        # ── ① C++ 消费者程序（绝对路径，避免裸命令名在 OHOS 上不做 PATH 搜索） ──
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_libgig"), env="conanrun")

        # ── ② CLI 工具裸环境 smoke ──
        pkg_bin = os.path.join(self._package_folder(), "bin")
        if not os.path.isdir(pkg_bin):
            raise ConanException("delivered package has no bin/ directory: %s" % pkg_bin)
        for tool in CLI_TOOLS:
            path = os.path.join(pkg_bin, tool)
            if not os.path.isfile(path):
                raise ConanException("missing delivered CLI tool: %s" % path)
            # 裸环境：显式清掉 conanrun 注入的库搜索路径，测产物自身是否可运行
            self.run('sh -c "unset LD_LIBRARY_PATH; unset LD_PRELOAD; exec ./%s --version"' % tool,
                     cwd=pkg_bin)
            self.run('sh -c "unset LD_LIBRARY_PATH; unset LD_PRELOAD; exec ./%s --help"' % tool,
                     cwd=pkg_bin)
