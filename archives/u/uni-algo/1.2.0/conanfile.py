#!/usr/bin/env python3
"""Conan recipe — uni-algo 1.2.0（CMake / C++ Unicode 算法库，纯静态库交付）。

uni-algo 是 Robert Riebisch 出品的 Unicode 算法实现（UTF-8/16/32 转换、大小写映射、
NFC/NFD/NFKC/NFKD 归一化、字素/词/句/行断句、码点属性、Script 检测、IDNA/UTS39），
只依赖 C++ 标准库（C++17 起），零第三方依赖。

- 上游是**两个独立 CMake 工程**：根工程出库，`test/` 是自带 project() 的独立工程。
  上游 CI（.github/workflows/linux.yml）跑法就是
  `cmake -S test -B build && cmake --build build && cd build && ctest --verbose`，
  本配方 build() 内按同一方式真实执行，不用 test_package 冒充上游测试。
- 测试工程只注册 1 个 ctest 用例（`add_test(NAME uni-algo-test ...)`），
  二进制内部由 3447 个 `TESTX` 断言点、15 个 `DONE:` 分区组成，
  任一断言失败即 `exit(111)`，ctest 随之失败 → 通过率由退出码硬保证。
- `DOWNLOAD_UNICODE_TEST_FILES` 保持上游默认 OFF（上游自己的 CI 也是默认值）：
  打开它要在 configure 阶段从 unicode.org 拉 3 个测试数据文件，
  `func_download()` 对下载失败直接 `FATAL_ERROR`，在离线构建环境里会让整个 create 红掉。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class UniAlgoConan(ConanFile):
    name = "uni-algo"
    version = "1.2.0"
    description = ("Unicode Algorithms Implementation: UTF-8/16/32 conversion, case "
                   "conversion, normalization (NFC/NFD/NFKC/NFKD), text segmentation "
                   "(grapheme/word/sentence/line), code point properties, scripts and IDNA")
    topics = ("unicode", "utf8", "normalization", "case-conversion",
              "text-segmentation", "idna", "collation")
    license = ("Unlicense", "MIT")
    homepage = "https://github.com/uni-algo/uni-algo"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}
    exports_sources = "patches/*.patch"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        # codeload URL 末段是 tag 名、没有 .tar.gz 后缀，必须显式给 filename，
        # 否则 get() 会误判成 zip 报 BadZipFile。
        get(self, filename="uni-algo-1.2.0.tar.gz",
            **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # os=OHOS 时 conan 默认把 CMAKE_SYSTEM_NAME 写成 "HarmonyOS"，而 cmake 的
        # 平台模块叫 Modules/Platform/OHOS.cmake，名字对不上会让平台变量留空。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # 64 位下上游 GNUInstallDirs 可能装到 lib64/，conan cpp_info.libdirs 找 lib/。
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # 纯静态库交付（头文件里 inline + 数据表在 libuni-algo.a）。
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["UNI_ALGO_HEADER_ONLY"] = False
        tc.variables["UNI_ALGO_INSTALL"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 上游只有 src/data.cpp 与 test/main.cpp 两个大翻译单元，-j1 控制峰值内存。
        self.run('cmake --build "%s" -j 1' % self.build_folder, env="conanbuild")
        self._build_and_run_upstream_tests()

    def _find_conan_toolchain(self):
        build_root = self.build_folder.replace("\\", "/")
        for root, _dirs, files in os.walk(build_root):
            if "conan_toolchain.cmake" in files:
                return os.path.join(root, "conan_toolchain.cmake").replace("\\", "/")
        raise ConanException("找不到 conan_toolchain.cmake（CMakeToolchain 未生成？）")

    def _build_and_run_upstream_tests(self):
        """按上游 CI 的方式真实执行官方测试套件：单独 configure test/ 工程后跑 ctest。

        必须用 conan 的 toolchain 文件，否则第二个工程会退回宿主机默认编译器，
        编出来的就不是 OHOS aarch64，测试也就不是在验本包。
        """
        test_src = os.path.join(self.source_folder, "test").replace("\\", "/")
        test_bin = os.path.join(self.build_folder, "upstream-test").replace("\\", "/")
        toolchain = self._find_conan_toolchain()
        os.makedirs(test_bin, exist_ok=True)

        self.run('cmake -S "%s" -B "%s" '
                 '-DCMAKE_TOOLCHAIN_FILE="%s" '
                 '-DCMAKE_BUILD_TYPE=%s '
                 '-DBUILD_UNI_ALGO=OFF '
                 '-DDOWNLOAD_UNICODE_TEST_FILES=OFF'
                 % (test_src, test_bin, toolchain, self.settings.build_type),
                 env="conanbuild")
        self.run('cmake --build "%s" -j 1' % test_bin, env="conanbuild")
        # --verbose 与上游 CI 一致：让 create 日志里能看到二进制自己的 DONE 分区与
        # "ALL TESTS PASSED!"，而不是只有一行 Passed。ctest 非 0 退出会让 create 失败。
        self.run('ctest --verbose --output-on-failure', cwd=test_bin, env="conanbuild")
        self.output.info("上游官方测试套件执行完成（ctest：uni-algo-test 1/1）")

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        lib = os.path.join(self.package_folder, "lib", "libuni-algo.a")
        if not os.path.isfile(lib):
            raise ConanException("静态库未产出：%s" % lib)
        inc = os.path.join(self.package_folder, "include", "uni_algo", "conv.h")
        if not os.path.isfile(inc):
            raise ConanException("公开头文件未安装：%s" % inc)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "uni-algo")
        self.cpp_info.set_property("cmake_target_name", "uni-algo::uni-algo")
        self.cpp_info.libs = ["uni-algo"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
