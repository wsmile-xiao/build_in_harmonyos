#!/usr/bin/env python3
"""Conan recipe — vprerex 6.5.1 (Qt5 GUI front-end / viewer for prerex charts).

上游: CTAN 的 prerex 宏包 (http://www.ctan.org/tex-archive/graphics/prerex)。
vprerex ("visual prerex") 6.5.1 是该宏包内含的 Qt-5 版 GUI 前端与 PDF 预览器
（ChangeLog: "Version 6.5.1 2017-11-26 — modified for qt5 and poppler-qt5"）。

上游构建依赖（vprerex.pro / INSTALL）:
    QT += widgets
    INCLUDEPATH += /usr/include/poppler/qt5 /usr/include/qt5 ...
    LIBS += -L/usr/lib64 -lpoppler-qt5

OHOS 适配（W0/R39 决策）:
  - qt5-qtbase/5.15.2.2 提供 Qt5 Core/Gui/Widgets，可直接消费。
  - 制品仓 poppler 的**全部**版本都以 ENABLE_QT5=OFF 发布（无 Qt 绑定），
    也没有独立的 poppler-qt5 包 → 无法满足上游的 -lpoppler-qt5。
  - 适配方案：新增 poppler-qt5 兼容 shim（patches/0002，poppler-qt5.h/.cpp），
    在 poppler 包自带的 **core** 库（libpoppler.so + include/poppler 头）之上
    重实现 vprerex 实际用到的 Poppler::Document/Page/Link/LinkBrowse 子集
    （含渲染与链接提取），上游 3 个 .cpp / 2 个 .h 源文件零修改。
  - 上游 qmake 工程（vprerex.pro 硬编码 /usr/include/poppler/qt5）用自研
    CMakeLists 替换（patches/0001），moc/uic 由 qt5-qtbase/bin 工具显式调用。
  - zlib 图内冲突：qt5-qtbase/5.15.2.2 链 zlib/1.3.1，poppler 链 zlib/1.3.1.1
    → consumer 侧 override 统一到 1.3.1.1（-fPIC 适配修复版）。

测试 (R51/R34/R40): 上游 tarball 无测试套件（无 tests/、无 CTest/make check，
见 test_package/MANIFEST.yml 清点证据）。OHOS 无显示环境，test_package 以
headless 冒烟 + shim 功能验证：`vprerex --version` / `--help`（QApplication
初始化 + 参数解析）与 `vprerex --check-pdf <pdf>`（经 shim 加载 PDF、渲染
每页并按页提取链接，见 patches/0003）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class VprerexConan(ConanFile):
    name = "vprerex"
    version = "6.5.1"
    description = "vprerex (visual prerex) — Qt5 GUI front-end and viewer for prerex prerequisite charts"
    license = "GPL-2.0-or-later"
    homepage = "https://www.ctan.org/pkg/prerex"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"  # 可执行文件（R38: 需要 commands.json）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt5 基础模块（Widgets/Gui/Core 均在 qtbase 内）
        self.requires("qt5-qtbase/5.15.2.2")
        # poppler core（shim 的后端；制品仓 poppler 无 Qt5 绑定）
        self.requires("poppler/25.12.0.1")
        # 依赖图版本统一：qt5-qtbase 链 zlib/1.3.1，poppler 链 zlib/1.3.1.1
        # → "Version conflict"。统一到 1.3.1.1（1.3.1 的 -fPIC 适配修复版）。
        self.requires("zlib/1.3.1.1", override=True)

    def validate(self):
        # R32: settings.os 判断用 in
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"vprerex only supports Linux and OHOS, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        # conandata 的 sources 段还带 spec 要求的 tar_format 字段，而
        # conan.tools.files.get() 不接受该 kwarg，故显式取名/取校验和。
        source_data = self.conan_data["sources"]
        get(self, url=source_data["url"], sha256=source_data.get("sha256", ""), strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # E092/ML-0035: CMake 无 HarmonyOS 平台文件，映射为 OHOS.cmake
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"

        qt5 = self.dependencies["qt5-qtbase"]
        qt5_pkg = qt5.package_folder
        qt5_inc = os.path.join(qt5_pkg, "include")
        # qt5 头文件布局：源码以 <QtCore/...> / <QWidget> 两种形式解析，
        # 需要 include/ 根 + 各模块目录 + 版本目录。
        qt_module_dirs = [qt5_inc]
        for m in ("QtCore", "QtGui", "QtWidgets"):
            qt_module_dirs.append(os.path.join(qt5_inc, m))
            ver_dir = os.path.join(qt5_inc, m, "5.15.2")
            if os.path.isdir(ver_dir):
                qt_module_dirs.append(ver_dir)
        qt_module_dirs = [d for d in qt_module_dirs if os.path.isdir(d)]
        tc.variables["VPREX_QT5_INCLUDE_DIRS"] = ";".join(qt_module_dirs)
        tc.variables["VPREX_QT5_LIB_DIR"] = os.path.join(qt5_pkg, "lib")
        tc.variables["VPREX_QT5_BIN_DIR"] = os.path.join(qt5_pkg, "bin")
        tc.variables["VPREX_QT5_MOC_INCLUDES"] = " ".join("-I" + d for d in qt_module_dirs)

        poppler = self.dependencies["poppler"]
        poppler_pkg = poppler.package_folder
        poppler_include = poppler.cpp_info.includedirs[0] if poppler.cpp_info.includedirs else "include"
        if not os.path.isabs(poppler_include):
            poppler_include = os.path.join(poppler_pkg, poppler_include)
        poppler_lib = poppler.cpp_info.libdirs[0] if poppler.cpp_info.libdirs else "lib"
        if not os.path.isabs(poppler_lib):
            poppler_lib = os.path.join(poppler_pkg, poppler_lib)
        tc.variables["VPREX_POPPLER_INCLUDE_DIR"] = poppler_include
        tc.variables["VPREX_POPPLER_LIB_DIR"] = poppler_lib
        tc.variables["VPREX_POPPLER_LIBRARY"] = "poppler"

        # Qt5 moc/uic 是本机 arm64 ELF，运行时需要 qt5 lib 目录与
        # OHOS SDK 的 libc++_shared.so。
        env = Environment()
        env.append_path("LD_LIBRARY_PATH", os.path.join(qt5_pkg, "lib"))
        sdk_libcxx = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/c++"
        if os.path.isdir(sdk_libcxx):
            env.append_path("LD_LIBRARY_PATH", sdk_libcxx)
        env.vars(self, scope="build").save_script("vprerex_qt5_tools_env")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM: 可执行文件需代码签名，否则报 Permission denied；
        # 非 OHOS 平台直接跳过（poppler 配方同款实现）。
        if self.settings.os != "OHOS":
            return
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for name in os.listdir(bindir):
            target = os.path.join(bindir, name)
            if not os.path.isfile(target) or os.path.islink(target):
                continue
            if not self._is_elf(target):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=target))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=target))

    def package_info(self):
        # 可执行程序包：无库文件供下游链接；把 bin 注入运行环境 PATH
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
