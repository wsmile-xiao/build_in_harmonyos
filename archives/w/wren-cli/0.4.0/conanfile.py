#!/usr/bin/env python3
"""Conan recipe — wren-cli 0.4.0

Wren 的命令行工具与 REPL（单个可执行文件，内嵌 Wren 虚拟机）。

上游构建系统：projects/make/ 下 premake 生成的 GNU Makefile，
`make -C projects/make config=release_64bit`，把三部分编成一个可执行文件：
src/{cli,module}/*.c、vendored 的 Wren 虚拟机（deps/wren）、vendored 的 libuv
（deps/libuv）。本配方保留上游源码布局与测试套件，但用 CMake 驱动编译，原因：
  * release_64bit 把 x86 专用开关写死（`ALL_CFLAGS += ... -m64`、
    `ALL_LDFLAGS += ... -L/usr/lib64 -m64`，是 += 追加，命令行传 CFLAGS= 也挤不掉）；
  * release_64bit-no-nan-tagging 虽然不带那两个开关，但它会把两份 vendored 源码一起编进
    可执行文件，让制品仓已发布的 wren/0.4.0 以第二个制品名重复交付、也用不上 libuv 的
    OHOS 移植补丁；
  * 两个 vendored 依赖在制品仓里已有 OHOS 适配好的发布包。

依赖（ohpcd 制品仓均已发布，os=OHOS/arch=armv8/clang=15 有现成二进制包）：
  - wren/0.4.0      虚拟机。本 tarball 的 deps/wren 与 wren-lang/wren tag 0.4.0 逐文件
                    比对：整个 src/ 只有 src/vm/wren_compiler.c 差 1 行、且那行是注释
                    （"a token a token" -> "a token"），include/ 与官方 src/include/
                    完全一致；CLI 只用公开 API（src 里 #include 的第三方头只有 wren.h
                    与 uv.h），故链发布包等价于链 vendored 副本。
  - libuv/1.52.1.1  异步 I/O。tarball 内嵌的是 deps/libuv 1.38.0 且不带任何 OHOS 适配
                    （无 configure），发布包携带 OHOS 移植补丁；CLI 只用 uv_* 公共 API。

上游测试（build() 中真实执行，详见 test_package/MANIFEST.yml）：
  - python3 ./util/test.py   官方 CI 入口（.travis.sh）：用 bin/wren_cli 逐个跑
                             test/**/*.wren 与 example/*.wren，校验每一行 `// expect:`。
  - test/unit                上游针对 src/cli/path.c 的 C 单元测试（官方 CI 未接入，
                             本配方编译并运行）。
License: MIT
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class WrenCliConan(ConanFile):
    name = "wren-cli"
    version = "0.4.0"
    description = "Command-line tool and REPL for the Wren programming language"
    license = "MIT"
    homepage = "https://wren.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("wren", "scripting-language", "repl", "cli")

    # R38: 产物含 bin/wren_cli，软件级 commands.json 已在 archives/w/wren-cli/ 声明
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("wren/0.4.0")
        self.requires("libuv/1.52.1.1")

    # R32: 平台白名单
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wren-cli is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload 源末段是 tag 名、没有 .tar.gz 后缀，必须显式给 filename，
        # 否则 conan 按 zip 猜格式报 BadZipFile。
        get(self, filename="wren-cli-0.4.0.tar.gz",
            **self.conan_data["sources"], strip_root=True)

    def _dep_libdirs(self):
        """依赖包里真实存在的 lib 目录（绝对路径）。

        libuv 发布的是 shared（libuv.so.1），而打包出的 wren_cli 不带 RUNPATH，
        真机上 musl 直接报 "Error relocating ... uv_strerror: symbol not found"
        （build() 里自跑子进程也不继承 conanrun 的 LD_LIBRARY_PATH）。
        所以由配方把目录显式交给 CMake 烧进 RUNPATH，并在跑上游套件时同时导出
        LD_LIBRARY_PATH，两条路都通。
        """
        dirs = []
        for ref in ("libuv", "wren"):
            dep = self.dependencies[ref]
            pkg = str(dep.package_folder)
            for d in (dep.cpp_info.libdirs or ["lib"]):
                abs_d = d if os.path.isabs(d) else os.path.join(pkg, *d.split("/"))
                if os.path.isdir(abs_d) and abs_d not in dirs:
                    dirs.append(abs_d)
        if not dirs:
            raise Exception("wren-cli: 依赖的 lib 目录一个都没找到，无法设置 RUNPATH")
        return dirs

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        toolchain = CMakeToolchain(self)
        toolchain.cache_variables["WREN_CLI_RPATH_DIRS"] = ";".join(self._dep_libdirs())
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        ld = ":".join(self._dep_libdirs())
        rt = f'LD_LIBRARY_PATH="{ld}:$LD_LIBRARY_PATH"'

        # 上游套件 1/2：test/unit（path.c 归一化用例，打印 "All N tests passed!"）
        unit = os.path.join(self.build_folder, "upstream-unit", "path_test")
        self.run(f'{rt} "{unit}"', env="conanbuild conanrun")

        # 上游套件 2/2：官方 CI 入口，必须在仓库根运行（util/test.py 用 relpath
        # 拼测试文件路径，并把 bin/wren_cli 作为被测程序）
        self.run(f'{rt} python3 ./util/test.py',
                 cwd=self.source_folder, env="conanbuild conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # application 包：只导出可执行文件，不导出库信息
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        # 依赖 libuv 是 shared，而 conan 2.29 在 POSIX 目标上不会把依赖的 libdirs
        # 拼进消费者的 LD_LIBRARY_PATH → 安装包里跑 wren_cli 会报
        # "Error loading shared library libuv.so.1"。除了链接期烧 RUNPATH，这里再把
        # 目录导出到 run/build 两个环境（与 archives/j/jose/14 同法），两条路都通。
        for d in self._dep_libdirs():
            self.runenv_info.append_path("LD_LIBRARY_PATH", d)
            self.buildenv_info.append_path("LD_LIBRARY_PATH", d)
