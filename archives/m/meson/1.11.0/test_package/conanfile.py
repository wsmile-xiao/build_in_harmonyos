import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment


class MesonTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def build(self):
        # OHOS 下 tool_requires 的 bin 目录不会自动注入 conanbuild 的 PATH
        # （VirtualBuildEnv 仅注入 profile buildenv），故用完整路径调用。
        meson_bin = os.path.join(
            self.dependencies.build["meson"].package_folder, "bin", "meson"
        )
        # CI worker 的 conan 进程 PATH 不含 /data/service/hnp/bin（工具链目录），
        # 仅靠 env="conanbuild" 注入 profile [buildenv] 不可靠（实测 meson setup
        # 探测编译器时仍报 "No such file or directory: 'clang'"，即 #24311
        # conan-build-test 失败点）。与主包 conanfile.py build() 同机制，
        # 显式注入工具链目录与 CC/CXX/NINJA/AR 等，保证 setup/compile 子进程
        # 能定位 clang/ninja/llvm-ar/lld。
        test_env = Environment()
        test_env.prepend_path("PATH", "/data/service/hnp/bin")
        test_env.prepend_path("PATH", "/storage/Users/currentUser/usr/local/bin")
        test_env.define("NINJA", "/data/service/hnp/bin/ninja")
        test_env.define("CC", "/data/service/hnp/bin/clang")
        test_env.define("CXX", "/data/service/hnp/bin/clang++")
        # 链接器/静态库工具同样不在 worker PATH 中，显式注入绝对路径，
        # 避免 meson 探测 "Unknown linker(s)" / ar 缺失。
        test_env.define("AR", "/data/service/hnp/bin/llvm-ar")
        test_env.define("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
        test_env.define("NM", "/data/service/hnp/bin/llvm-nm")
        # lld 动态依赖 SDK llvm/lib 下 libxml2.so.16（与主包同一问题）。
        test_env.prepend_path(
            "LD_LIBRARY_PATH",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
        )
        with test_env.vars(self).apply():
            self.run('"{}" setup build'.format(meson_bin), env="conanbuild")
            self.run('"{}" compile -C build'.format(meson_bin), env="conanbuild")

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: package execution is skipped.")
            return
        self.run("./build/conan-probe")
