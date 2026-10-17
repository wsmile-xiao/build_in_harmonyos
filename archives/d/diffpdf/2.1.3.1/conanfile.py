#!/usr/bin/env python3
"""Conan recipe — diffpdf 2.1.3.1 (Qt5 PDF 对比 GUI 工具, HarmonyOS PC aarch64).

上游 (qtrac.eu, Simon Guest) 2.1.3.1 = Qt5 + CMake 移植版（见上游 CHANGES）。
上游构建依赖: ECM (extra-cmake-modules) + poppler-qt5 绑定 + Qt5Widgets/PrintSupport。

OHOS 适配（R39/W0 决策）:
  - 制品仓 poppler/25.12.0.2 以 ENABLE_QT5=OFF/ENABLE_QT6=OFF 发布（无 Qt 绑定），
    且无独立 poppler-qt5 包 → 无法满足上游 find_package(Poppler Qt5)。
  - 适配方案: 新增 poppler-qt5 兼容 shim（patches/poppler-qt5.h/.cpp），把上游用到的
    Poppler::Document/Page/TextBox API 重实现在 poppler-cpp 前端之上（poppler 包
    libpoppler-cpp.so 已随包发布），上游 21 个 .cpp/.hpp 源文件零修改。
  - Qt5 来自 qt5-qtbase/5.15.2.2（Core/Gui/Widgets/PrintSupport 俱备）。
  - 新增自研 CMakeLists.txt（上游的不含 ECM/FindPoppler 无法用），moc/rcc/uic 由
    CMAKE_AUTOMOC + qt5-qtbase 的 bin/ 工具完成；翻译 .qm 用 lrelease 离线生成后
    以静态资源替换（CI 环境无 lrelease 运行问题时走 qrc 源文件列表）。

测试 (R40): diffpdf 是 Qt GUI 应用，OHOS PC 当前无 Qt 平台插件运行时保证
（qt5-qtbase 提供 offscreen/minimal 插件），测试以链路级验证为主:
  test_package 运行 `diffpdf --help`（QApplication 初始化 + 参数解析 + usage 输出），
  校验 banner 与 usage 关键字。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class DiffpdfConan(ConanFile):
    name = "diffpdf"
    version = "2.1.3.1"
    description = "DiffPDF — Qt5 GUI tool that compares two PDF files (words/characters/appearance)"
    license = "GPL-2.0-or-later"
    homepage = "http://www.qtrac.eu/diffpdf.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"  # 可执行文件（R38: 需要 commands.json）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt5 基础模块（Widgets/PrintSupport 在 qtbase 内）
        self.requires("qt5-qtbase/5.15.2.2")
        # poppler-cpp 前端（shim 的后端；上游用的是 poppler-qt5 绑定，制品仓无）
        # 用 25.12.0.1 而非 25.12.0.2：其依赖链极简（freetype+zlib，无 cairo/
        # glib/boost/fontconfig），与 qt5-qtbase 同图共存代价最小（见下 zlib 注）。
        self.requires("poppler/25.12.0.1")
        # 依赖图版本统一：qt5-qtbase/5.15.2.2 链 requires zlib/1.3.1，poppler 链
        # requires zlib/1.3.1.1 → "Version conflict"（G2 实测）。consumer 侧
        # override 统一到 1.3.1.1（zlib/1.3.1.1 = 1.3.1 的 -fPIC 适配修复版，
        # 其 libz.a 可链进共享库；1.3.1 的非 PIC libz.a 链 poppler .so 时报
        # R_AARCH64 relocation 错误，G2 实测）。
        # 统一到 1.3.1.1 的代价：qt5-qtbase 二进制（基于 zlib/1.3.1 构建）的
        # package_id 变化 → 从源码构建（baka 2.0.4 已验证此路径可行，其 CI
        # 绿：PR !6487）。源码构建要求运行环境能解析 qt5 工具链 libc++ 符号
        # （LD_LIBRARY_PATH 含 SDK c++ 目录或干净 /system/lib64）。
        self.requires("zlib/1.3.1.1", override=True)

    def validate(self):
        # R32: settings.os 判断用 in
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"diffpdf only supports Linux and OHOS, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        # 注意：不 strip_root。上游 tarball 顶层目录为 diffpdf-v2.1.3.1/，
        # 补丁路径（a/diffpdf-v2.1.3.1/...）以该目录为根，保留以对齐。
        get(self, **self.conan_data["sources"], strip_root=False)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # E092: CMake 无 HarmonyOS 平台文件，映射为 OHOS.cmake
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"

        qt5 = self.dependencies["qt5-qtbase"]
        qt5_pkg = qt5.package_folder
        qt5_inc = os.path.join(qt5_pkg, "include")
        # qt5 头文件布局：源码 #include <QtCore/qstring.h> 形式要求以
        # include/ 为根解析；模块内的转发头再指向 ../../src/...（包内自带）。
        # 同时补各模块目录与版本目录（qdatetime.h 内部 #include <QtCore/...>
        # 的双路径解析需要）。
        qt_module_dirs = [qt5_inc]
        for m in ("QtCore", "QtGui", "QtWidgets", "QtPrintSupport"):
            qt_module_dirs.append(os.path.join(qt5_inc, m))
            ver_dir = os.path.join(qt5_inc, m, "5.15.2")
            if os.path.isdir(ver_dir):
                qt_module_dirs.append(ver_dir)
        tc.variables["DIFFPDF_QT5_INCLUDE_DIRS"] = ";".join(
            d for d in qt_module_dirs if os.path.isdir(d)
        )
        tc.variables["DIFFPDF_QT5_LIB_DIR"] = os.path.join(qt5_pkg, "lib")
        tc.variables["DIFFPDF_QT5_BIN_DIR"] = os.path.join(qt5_pkg, "bin")
        # moc 的 -I 参数（转发头解析需要与编译一致的 include 集）
        tc.variables["DIFFPDF_QT5_MOC_INCLUDES"] = " ".join(
            "-I" + d for d in qt_module_dirs if os.path.isdir(d)
        )

        poppler = self.dependencies["poppler"]
        poppler_pkg = poppler.package_folder
        # shim 用 #include <poppler/cpp/poppler-document.h>（poppler-cpp 头）。
        # poppler/25.12.0.1 的 cpp_info.includedirs = include + include/poppler
        # （poppler-cpp 头物理在 include/poppler/cpp/），从 include 根解析。
        cpp_root = None
        for d in poppler.cpp_info.includedirs:
            if os.path.basename(d) == "include":
                cpp_root = d
                break
        if cpp_root is None:
            cpp_root = os.path.join(poppler_pkg, "include")
        tc.variables["DIFFPDF_POPPLER_CPP_INCLUDE_DIR"] = cpp_root
        tc.variables["DIFFPDF_POPPLER_CPP_LIB_DIR"] = poppler.cpp_info.libdirs[0]
        tc.variables["DIFFPDF_POPPLER_CPP_LIBRARY"] = "poppler-cpp"
        # aboutform.cpp 显示用的 poppler 版本号（与包版本一致）
        tc.variables["DIFFPDF_POPPLER_VERSION"] = "25.12.0.1"

        # Qt5 moc/rcc/lrelease 是本机 arm64 ELF，运行时需要 qt5 lib 目录
        # 与 OHOS SDK 的 libc++_shared.so。
        env = Environment()
        env.append_path("LD_LIBRARY_PATH", os.path.join(qt5_pkg, "lib"))
        sdk_libcxx = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/c++"
        if os.path.isdir(sdk_libcxx):
            env.append_path("LD_LIBRARY_PATH", sdk_libcxx)
        env.vars(self, scope="build").save_script("diffpdf_qt5_tools_env")

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
        # 鸿蒙 PC XPM: 可执行文件需代码签名（poppler 配方同款实现；
        # 非 OHOS 平台直接跳过）
        import glob
        if self.settings.os != "OHOS":
            return
        targets = []
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # 可执行程序包：无库文件供下游链接；将 bin 注入运行环境 PATH
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
