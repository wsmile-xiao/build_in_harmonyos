#!/usr/bin/env python3
"""Conan recipe — qpdfview 0.5.0（Qt5 标签式 PDF 阅读器，HarmonyOS PC aarch64 适配）。

qpdfview 是可定制的标签页式文档查看器（PDF/PS/DjVu/图像），构建系统为
qmake：顶层 `qpdfview.pro`（TEMPLATE = subdirs）按功能拆成
application.pro + {pdf,ps,djvu,image}-plugin.pro，每个子工程独立链接。

依赖
----
W0 依赖发布检查（制品仓查询，remote 由环境指定）结论：

  * **registry 无 poppler 的 Qt5 绑定制品**：`poppler*` 只有
    25.12.0/25.12.0.1/25.12.0.2（`ENABLE_QT5=OFF`、只装 C++/glib
    API），且制品仓**没有**独立的 poppler-qt5 配方。
    → W0/PF4「依赖必须先发布」：禁止在同一个 PR 捎带适配依赖
      （见 notes.md「为什么不另起 poppler-qt5 PR」）。
    → 本配方在 build() 内**内嵌编译**上游 poppler 自带的 Qt5 绑定
      （poppler-25.12.0 源码包 qt5/src/ 共 17 个 .cc），编成**静态库**
      `libpoppler-qt5.a` 直接链入 pdf 插件，**不安装**进 package ——
      运行时只依赖制品仓的 libpoppler.so.155。实配见 notes.md
      「内嵌 poppler-qt5」。
  * `qt5-qtbase/5.15.2.2`（baka 先例：5.15.2 为 -no-widgets 构建）+
    `qt5-qtsvg/5.15.2`（qpdfview 全部图标都是 SVG；qtsvg 的 .pri 声明
    精确 qt5-qtbase/5.15.2，与本配方冲突 → override 统一到 5.15.2.2，
    补丁版本 API 兼容，qtsvg 二进制无需重建）。
  * `poppler/25.12.0.2`（PDF 渲染后端）以及 `fontconfig/2.18.1.1`、
    `zlib/1.3.1.1`、`expat/2.8.2.1`（后两者为依赖图版本冲突的
    override，见 requirements() 内注释）。

禁用的上游子工程（无对应依赖制品 / 受限功能）
--------------------------------------------
  * ps-plugin    —— libspectre 不在制品仓 → CONFIG+=without_ps
  * djvu-plugin  —— djvulibre 不在制品仓 → CONFIG+=without_djvu
  * sql（QSettings）—— qt5-qtbase/5.15.2.2 未构建 Qt5Sql
    （`libQt5Sql.so` 不存在）→ CONFIG+=without_sql，QSettings 回退
  * cups（打印）  —— 同版本无 Qt5PrintSupport 的 cups 插件
    → CONFIG+=without_cups，PDF 打印不可用
  * fitz-plugin —— 上游 `with_fitz` 默认即关闭，无需处理

其它要点
--------
  * UI 翻译：`translations/*.ts` 需 lrelease；制品仓 qt5-qttools 缺位
    （只有 Qt6 的 qttools）、系统也没有 lrelease（`find / -name lrelease`
    空）→ 无可执行 .qm，按上游默认（不存在即不装）处理，见 notes.md。
  * 插件安装到 `<pkg>/bin`：`sources/pluginhandler.cpp` 优先查找
    `QApplication::applicationDirPath()`，回落到编译期 PLUGIN_INSTALL_PATH。
  * 签章：package() 最后一步对 bin/ 下 3 个 ELF（可执行 + 2 个插件）
    做 OHOS 代码签名（不签名无法 exec / dlopen）。
"""
import os
import re
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class QpdfviewConan(ConanFile):
    name = "qpdfview"
    version = "0.5.0"
    description = (
        "qpdfview — a tabbed document viewer using Qt5 and the poppler "
        "library for PDF documents (HarmonyOS PC aarch64 adaptation)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://launchpad.net/qpdfview"
    url = "https://launchpad.net/qpdfview"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 本配方暂无补丁（conandata.yml patches: []），保留标准入口以兼容
        # 后续补丁追加与 CI L0 门禁（G1 要求 export_sources/apply_conandata_patches）。
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qpdfview only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        # 主源码（官方 Launchpad 发布页，非 Debian 的 +ds 重打包）
        get(self, **self.conan_data["sources"]["qpdfview"], strip_root=True)
        # poppler 源码包：只取其自带的 Qt5 绑定（qt5/src/* 与少量私有头）。
        get(
            self,
            destination=os.path.join("poppler-source"),
            strip_root=True,
            **self.conan_data["sources"]["poppler"],
        )

    # ── 工具链 ────────────────────────────────────────────────────────────

    def _toolchain(self):
        """R33：编译器一律取自 Conan conf，禁止裸用 ${CC}/${CXX}。

        注意 `tools.build:compiler_executables` 是**字典** conf，必须整体
        取出后按键访问（`conf.get(...:c)` 会抛 ConanException）。
        """
        execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = execs.get("c") or "/data/service/hnp/bin/clang"
        cxx = execs.get("cpp") or "/data/service/hnp/bin/clang++"
        if not (os.path.isfile(cc) and os.path.isfile(cxx)):
            raise ConanInvalidConfiguration(f"未找到 clang 工具链: cc={cc} cxx={cxx}")
        return cc, cxx

    @staticmethod
    def _lib_dir(dep):
        return os.path.join(dep.package_folder, "lib")

    def _all_lib_dirs(self, skip=()):
        """全部依赖（含传递依赖）的 lib 目录，按依赖名排序去重。"""
        dirs = []
        for require, dep in sorted(
            self.dependencies.items(), key=lambda kv: kv[0].ref.name
        ):
            name = require.ref.name
            if name in skip:
                continue
            if dep.package_folder is None:
                continue
            libdir = self._lib_dir(dep)
            if os.path.isdir(libdir) and libdir not in dirs:
                dirs.append(libdir)
        return dirs

    # ── 内嵌 poppler-qt5 绑定（W0/PF4 工作区）────────────────────────────

    _VENDOR_CONFIG_H = (
        "/* qpdfview 0.5.0 / HarmonyOS PC 适配——由配方生成 */\n"
        "/*\n"
        " * 上游 poppler 的 qt5 绑定源码（poppler-25.12.0/qt5/src）会\n"
        " * `#include \"config.h\"`（poppler 打包进 qt5/src 的 config.h.cmake\n"
        " * 模板，默认指向已不再安装的 config.h/cmake-config.h）。\n"
        " * poppler-config.h 自带说明：We duplicate some of the config.h\n"
        " * #define's here since they are used in some of the header files\n"
        " * we install —— 安装头所需的那部分宏已由它提供。本配方逐条核查\n"
        " * qt5/src 引用的 config.h.cmake 宏（ENABLE_NSS3/ENABLE_GPGME/\n"
        " * ENABLE_SIGNATURES/USE_CMS/VERSION，全部关闭或已由\n"
        " * poppler-config.h 覆盖），以及制品仓 poppler 安装头里唯一未公开的\n"
        " * ENABLE_ZLIB_UNCOMPRESS（Stream.h，上游该选项关闭），确认单行转发\n"
        " * 即足够。\n"
        " */\n"
        "#include <poppler/poppler-config.h>\n"
    )

    _VENDOR_CMAKELISTS = """\
# qpdfview 0.5.0 内嵌 poppler-qt5 绑定（HarmonyOS PC 适配）——由配方生成。
# 只编译上游 poppler 自带的 Qt5 绑定源码（qt5/src/*.cc），产物是**静态库**
# libpoppler-qt5.a，直接链入 qpdfview 的 pdf 插件；本子工程不安装、不导出。
cmake_minimum_required(VERSION 3.16)
project(poppler-qt5-vendor CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_AUTOMOC ON)

include(GenerateExportHeader)

# poppler 25.12 的头部用到 libc++ 的 C++23 设施（<version>/span 等），
# OHOS NDK 的 libc++ 头在 C++23 下要求该开关（实配，见 notes.md）。
add_compile_options(-fexperimental-library)

configure_file(${SRC_DIR}/poppler-version.h.in
               ${CMAKE_CURRENT_BINARY_DIR}/poppler-version.h @ONLY)

find_package(Qt5 REQUIRED COMPONENTS Core Gui Xml Widgets)

file(GLOB PQ5_SRCS ${SRC_DIR}/*.cc)
add_library(poppler-qt5 STATIC ${PQ5_SRCS})
generate_export_header(poppler-qt5 BASE_NAME poppler-qt5
                       EXPORT_FILE_NAME
                       ${CMAKE_CURRENT_BINARY_DIR}/poppler-export.h)

target_include_directories(poppler-qt5
    SYSTEM PUBLIC ${SRC_INC_DIR}
    PRIVATE ${SRC_DIR} ${CMAKE_CURRENT_BINARY_DIR} ${POPPLER_INC})
target_compile_definitions(poppler-qt5 PRIVATE
    QT_STRICT_ITERATORS QT_DISABLE_DEPRECATED_BEFORE=0x050E00
    QT_NO_DEPRECATED_WARNINGS)
target_link_libraries(poppler-qt5 PUBLIC Qt5::Core Qt5::Gui Qt5::Xml
                       Qt5::Widgets PRIVATE ${POPPLER_LIBS})
"""

    def _build_vendor_poppler_qt5(self, cc, cxx, qtbase):
        """在 build 目录下内嵌编译 poppler 的 Qt5 绑定为静态库。

        返回 `(vendor_dir, static_lib, include_dir)`。cmake 子工程与
        qpdfview 本体**解耦**（独立 build 目录 + 独立 config.h 占位），
        因为上游 `pdf-plugin.pro` 会执行 `pkg-config --exists synctex`：
        若构建目录里出现 Qt5Core/QtCore 痕迹（cmake automoc 依赖 Qt5Core
        头），就可能把 synctex 重定向到 poppler 自带的 synctex.pc，链接
        找不到 `synctex_scanner_*` 符号（实撞）。隔离到
        build/poppler-qt5-vendor/ 后 synctex 稳定走「上游捆绑源码 + 系统
        zlib」分支。
        """
        poppler = self.dependencies["poppler"]
        poppler_src = os.path.join(self.source_folder, "poppler-source", "qt5", "src")
        if not os.path.isdir(poppler_src):
            raise ConanInvalidConfiguration(
                f"poppler 源码内未找到 qt5 绑定源码: {poppler_src}"
            )

        vendor_dir = os.path.join(self.build_folder, "poppler-qt5-vendor")
        gen_dir = os.path.join(vendor_dir, "include", "poppler-qt5")
        os.makedirs(gen_dir, exist_ok=True)
        # config.h 占位：单行转发到已安装头文件 poppler/poppler-config.h。
        # 不能放进源码目录——上游未打包同名 config.h，自写文件就成了「改
        # 上游源码树」，且会干扰 pdf-plugin.pro 的 synctex 探测；放此 gen
        # 目录借 -I 解析即可。
        save(self, os.path.join(gen_dir, "config.h"), self._VENDOR_CONFIG_H)

        # 头文件搜索路径：**按上游 poppler 自己的构建方式来**——以源码树
        # 优先，制品仓安装头殿后。
        #
        # 原因（均已实撞）：
        #   * poppler 制品**不安装全部私有头**：`goo/ft_utils.h`、
        #     `poppler/FontEncodingTables.h` 都只在源码树里；而 qt5 绑定的
        #     QPainterOutputDev.cc 会直接 `#include "goo/ft_utils.h"` /
        #     `#include <Object.h>`。
        #   * 这些私有头又 `#include "poppler_private_export.h"` / 其它
        #     生成头，需 `include/poppler` 与生成目录在搜索路径上。
        # 顺序：gen_dir（config.h/导出头）→ 源码树 → 源码树/poppler
        #      → 安装头（configure 过的 poppler/*.h 与 poppler-config.h）
        #      → freetype/lcms2/fontconfig。
        poppler_src_root = os.path.join(self.source_folder, "poppler-source")
        inc_dirs = [
            gen_dir,
            poppler_src_root,
            os.path.join(poppler_src_root, "poppler"),
            os.path.join(poppler.package_folder, "include"),
            os.path.join(poppler.package_folder, "include", "poppler"),
            os.path.join(poppler.package_folder, "include", "poppler", "goo"),
            os.path.join(poppler.package_folder, "include", "poppler", "fofi"),
            os.path.join(poppler.package_folder, "include", "poppler", "splash"),
        ]
        inc_dirs = [d for d in inc_dirs if os.path.isdir(d)]
        for dep_name, subs in (
            ("fontconfig", ("include",)),
            ("freetype", ("include/freetype2", "include")),
            ("lcms2", ("include",)),
        ):
            dep = self.dependencies[dep_name]
            for sub in subs:
                candidate = os.path.join(dep.package_folder, sub)
                if os.path.isdir(candidate) and candidate not in inc_dirs:
                    inc_dirs.append(candidate)

        # 链接对象：制品仓 libpoppler.so（绝对路径）+ freetype/lcms2。
        poppler_lib = os.path.join(self._lib_dir(poppler), "libpoppler.so")
        if not os.path.isfile(poppler_lib):
            raise ConanInvalidConfiguration(f"未找到 libpoppler.so: {poppler_lib}")
        poppler_libs = [poppler_lib]
        for dep_name, libname in (("freetype", "freetype"), ("lcms2", "lcms2")):
            dep = self.dependencies[dep_name]
            poppler_libs.append(f"-L{self._lib_dir(dep)}")
            poppler_libs.append(f"-l{libname}")

        save(
            self, os.path.join(vendor_dir, "CMakeLists.txt"), self._VENDOR_CMAKELISTS
        )
        build_dir = os.path.join(vendor_dir, "build")
        cmake_args = [
            "-G", "Ninja",
            "-S", vendor_dir,
            "-B", build_dir,
            "-DCMAKE_SYSTEM_NAME=OHOS",
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_C_COMPILER={cc}",
            f"-DCMAKE_CXX_COMPILER={cxx}",
            f"-DCMAKE_PREFIX_PATH={qtbase.package_folder}",
            f"-DSRC_DIR={poppler_src}",
            f"-DSRC_INC_DIR={gen_dir}",
            # cmake list 分隔符必须是 `;`：用空格会让 `-D` 变成单个字符串，
            # 展开成 `-isystem "dir1 dir2 ..."` 这种不存在的路径（实撞）。
            f"-DPOPPLER_INC={';'.join(inc_dirs)}",
            f"-DPOPPLER_LIBS={';'.join(poppler_libs)}",
        ]
        with Environment().vars(self).apply():
            self.run(" ".join(f'"{a}"' for a in ["cmake", *cmake_args]))
            self.run(f'cmake --build "{build_dir}" --parallel 1')
        static_lib = os.path.join(build_dir, "libpoppler-qt5.a")
        if not os.path.isfile(static_lib):
            raise ConanInvalidConfiguration(
                f"内嵌 poppler-qt5 静态库未生成: {static_lib}"
            )
        # 公开头文件：照搬上游 qt5/src/CMakeLists.txt 的 install 列表
        # （qt5 绑定的公开 API 头 + 两个生成头）。qpdfview 的
        # pdf-plugin.pro 走 pkg-config，只从 .pc 拿到 `-I<gen_dir>`；
        # 公开头不在 gen_dir 就编译报 `poppler-qt5.h file not found`
        # （实撞）。公开头只引用 Qt 与 poppler-* 同名头，自洽。
        public_headers = (
            "poppler-qt5.h",
            "poppler-link.h",
            "poppler-annotation.h",
            "poppler-form.h",
            "poppler-optcontent.h",
            "poppler-page-transition.h",
            "poppler-media.h",
        )
        for header in public_headers:
            shutil.copy2(
                os.path.join(poppler_src, header), os.path.join(gen_dir, header)
            )
        for generated in ("poppler-export.h", "poppler-version.h"):
            shutil.copy2(
                os.path.join(build_dir, generated), os.path.join(gen_dir, generated)
            )
        return vendor_dir, static_lib, gen_dir

    # ── qmake 模块（qt5-qtsvg 的 .pri）───────────────────────────────────

    def _setup_qmake_modules(self, build_env):
        """复制 qt5-qtsvg 的 mkspecs/modules/*.pri 并改写构建期绝对路径。

        qt5-qtsvg 包内 `mkspecs/modules/qt_lib_svg.pri` 记录的是**构建时**
        的绝对路径（`.../.conan2/p/b/qt5-qXXXX/b`，随 conan 清理消失），
        qmake 直接引用报 `Project ERROR: Unknown module(s) in QT: ... svg`。
        复制到 build 目录、把路径改成依赖包的 package 目录后，经
        `QMAKEMODULES` 暴露给 qmake（baka 先例同解）。
        """
        modules_root = os.path.join(self.build_folder, "qmake-modules")
        modules_dir = os.path.join(modules_root, "modules")
        modules_inst_dir = os.path.join(modules_root, "modules-inst")
        for directory in (modules_dir, modules_inst_dir):
            os.makedirs(directory, exist_ok=True)
        # 必须以 `/` 起始：锚定到路径开头。若允许匹配起始处任意非空白
        # 字符，`include(/…/conan2/p/b/…/b/…)` 里的 `include(` 会被一并
        # 吃掉，生成的 .pri 变 `…/b/…)` → qmake 报
        # `Unknown module(s) in QT: svg`（实撞）。
        pattern = re.compile(r"/[^\s]*?conan2/p/b/[^/\s]+/b")
        for dep_name in ("qt5-qtsvg",):
            dep = self.dependencies[dep_name]
            pkg_root = dep.package_folder
            for sub, target in (
                ("mkspecs/modules", modules_dir),
                ("mkspecs/modules-inst", modules_inst_dir),
            ):
                src = os.path.join(pkg_root, sub)
                if not os.path.isdir(src):
                    continue
                for pri in os.listdir(src):
                    if pri.endswith(".pri"):
                        shutil.copy2(os.path.join(src, pri), os.path.join(target, pri))
            # 改写复制后的 .pri：构建目录绝对路径 → 本依赖 package 目录
            for directory in (modules_dir, modules_inst_dir):
                for pri in os.listdir(directory):
                    if not pri.endswith(".pri"):
                        continue
                    path = os.path.join(directory, pri)
                    with open(path, "r", encoding="utf-8") as handle:
                        content = handle.read()
                    fixed = pattern.sub(lambda _m: pkg_root, content)
                    if fixed != content:
                        with open(path, "w", encoding="utf-8") as handle:
                            handle.write(fixed)
        build_env.define("QMAKEMODULES", modules_dir)

    # ── 生成的 poppler-qt5.pc ────────────────────────────────────────────

    def _write_poppler_qt5_pc(self, vendor_dir, static_lib, include_dir, dep_lib_dirs):
        """生成只描述 poppler-qt5 的 .pc（pdf-plugin.pro 靠 pkg-config 探测）。

        刻意**不带 Requires**：poppler 的私有头与目标库已由「绝对路径
        静态库 + 直接 -I/-L」内联进来，再走 poppler.pc 的 Requires 只会
        把冲突描述重复引入。Cflags 只列引用方真正需要的 -I。
        """
        dep_flags = " ".join(f"-I{d}" for d in dep_lib_dirs)
        save(
            self,
            os.path.join(vendor_dir, "poppler-qt5.pc"),
            "prefix={libdir}\n"
            "libdir={libdir}\n"
            "includedir={includedir}\n"
            "\n"
            "Name: poppler-qt5\n"
            "Description: Qt5 bindings for poppler (inlined build)\n"
            "Version: 25.12.0\n"
            "Libs: -L${{libdir}} {static_lib} {dep_flags} -lpoppler\n"
            "Cflags: -I${{includedir}}\n".format(
                libdir=vendor_dir,
                includedir=include_dir,
                static_lib=static_lib,
                dep_flags=dep_flags,
            ),
        )

    # ── 构建 ─────────────────────────────────────────────────────────────

    def build(self):
        # 应用 conandata.yml 声明的补丁（当前为空列表，no-op）
        apply_conandata_patches(self)
        cc, cxx = self._toolchain()
        qtbase = self.dependencies["qt5-qtbase"]
        qtsvg = self.dependencies["qt5-qtsvg"]
        poppler = self.dependencies["poppler"]
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanInvalidConfiguration(f"qt5-qtbase 包内未找到 qmake: {qmake}")

        # 1) 内嵌 poppler-qt5 静态库（W0/PF4：不新建独立包）
        vendor_dir, static_lib, include_dir = self._build_vendor_poppler_qt5(
            cc, cxx, qtbase
        )

        # 2) 生成 poppler-qt5.pc（链接期直接依赖 freetype/lcms2/libpoppler）
        pc_dep_lib_dirs = []
        for dep_name in ("freetype", "lcms2", "poppler"):
            libdir = self._lib_dir(self.dependencies[dep_name])
            if libdir not in pc_dep_lib_dirs:
                pc_dep_lib_dirs.append(libdir)
        self._write_poppler_qt5_pc(vendor_dir, static_lib, include_dir, pc_dep_lib_dirs)

        build_env = Environment()
        # 编译器目录：qmake 探测目标编译器时用**裸名字** clang++ 走 PATH
        # 查找（知识图谱 E540），PATH 不含工具链目录即
        # `Project ERROR: Cannot run target compiler 'clang++'`。
        for exe in (cc, cxx):
            tool_dir = os.path.dirname(exe)
            if tool_dir:
                build_env.prepend_path("PATH", tool_dir)
        # qmake/moc/uic/rcc 是 Qt 链接的可执行文件，需要构建期库路径。
        for libdir in self._all_lib_dirs():
            build_env.prepend_path("LD_LIBRARY_PATH", libdir)

        # 模块 .pri（qt5-qtsvg 的 svg 模块）→ QMAKEMODULES
        self._setup_qmake_modules(build_env)

        # 链接期库路径：clang 识别 LIBRARY_PATH。**不含 zlib** —— synctex
        # 分支 `LIBS += -lz` 必须解析到 HarmonyOS **系统库**（OHOS NDK
        # sysroot 的 libz.so，无 SONAME → DT_NEEDED 只写 `libz.so`，与
        # libQt5Core.so 自身的 DT_NEEDED 一致；制品仓 zlib 的 libz.so.1
        # 会把 DT_NEEDED 污染成 libz.so.1，详见 notes.md）。
        lib_path_dirs = self._all_lib_dirs(skip=("zlib",))
        build_env.define("LIBRARY_PATH", os.pathsep.join(lib_path_dirs))

        # pkg-config：**只用**刚生成的 poppler-qt5.pc（PKG_CONFIG_LIBDIR 会
        # 替换默认搜索路径）→ `pkg-config --modversion poppler-qt5` 得
        # 25.12.0（application.pro 用），`pkg-config --exists synctex` 恒为
        # 假（否则命中 poppler 自带 synctex.pc、链不到符号，实撞）。
        build_env.define("PKG_CONFIG_PATH", vendor_dir)
        build_env.define("PKG_CONFIG_LIBDIR", vendor_dir)

        # 源码目录内 in-source build（产物与 Makefile.* 都在源码目录），
        # 与仓内 Qt 应用先例（baka/yasw）一致。
        src = self.source_folder
        package_folder = self.package_folder
        dep = self.dependencies
        qmake_args = [
            os.path.join(src, "qpdfview.pro"),
            # 插件裁剪：无依赖制品 / 不可用的子工程（见模块 docstring）
            "CONFIG+=without_ps",
            "CONFIG+=without_djvu",
            "CONFIG+=without_sql",
            "CONFIG+=without_cups",
            # poppler-form.h 无条件使用 std::optional，C++17 是硬下限
            "CONFIG+=c++17",
            # QMAKE_STRIP 置空：OHOS 加载器**拒绝 stripped ELF**
            # （HMDFS 无法 mmap PROT_EXEC，知识图谱 E500 / E215）
            "QMAKE_STRIP=",
            # 编译器（R33：来自 conf，不裸用 ${CC}/${CXX}）
            f"QMAKE_CC={cc}",
            f"QMAKE_CXX={cxx}",
            f"QMAKE_LINK={cxx}",
            f"QMAKE_LINK_SHLIB={cxx}",
            # RPATH：多前缀 conan Qt 安装，Qt5Svg/libpoppler 所在 lib 目录
            # 不是可执行文件自己的目录，显式补进 RUNPATH（否则
            # `Error loading shared library libQt5Svg.so.5`）。
            # 具体目录在下面用 `_all_lib_dirs()` 动态追加：部分仅作（依赖图
            # override 的）条目（如 zlib/expat）可能没有可用 package_folder。
            # 安装前缀变量：打包时 `make install` 直接把全部文件安进
            # package（手工拷贝会漏 desktop/man/metainfo/help）
            f"TARGET_INSTALL_PATH={os.path.join(package_folder, 'bin')}",
            f"PLUGIN_INSTALL_PATH={os.path.join(package_folder, 'bin')}",
            f"DATA_INSTALL_PATH={os.path.join(package_folder, 'share', 'qpdfview')}",
            f"MANUAL_INSTALL_PATH={os.path.join(package_folder, 'share', 'man', 'man1')}",
            f"ICON_INSTALL_PATH={os.path.join(package_folder, 'share', 'icons', 'hicolor', 'scalable', 'apps')}",
            f"LAUNCHER_INSTALL_PATH={os.path.join(package_folder, 'share', 'applications')}",
            f"APPDATA_INSTALL_PATH={os.path.join(package_folder, 'share', 'metainfo')}",
        ]
        # RPATH：全部依赖（含传递依赖）的 lib 目录。跳过没有 package 的
        # 条目（overrides 可能引入无制品节点的依赖）。
        for libdir in self._all_lib_dirs():
            qmake_args.append(f"QMAKE_RPATHDIR+={libdir}")
        with build_env.vars(self).apply():
            self.run(
                f'"{qmake}" ' + " ".join(f'"{a}"' for a in qmake_args),
                cwd=src,
            )
            # R9: make -j1（本环境 `make -j` 的 jobserver mkfifo 报
            # Operation not permitted，只能用 -j1/-j2）
            self.run('make -j1 QMAKE_STRIP=""', cwd=src)

    # ── 打包 ─────────────────────────────────────────────────────────────

    _SIGN_SECTION = ".codesign"

    @staticmethod
    def _elf_type(path):
        try:
            with open(path, "rb") as handle:
                header = handle.read(18)
        except OSError:
            return None
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            return None
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(env_var, executable):
        """定位签章工具：环境变量 > PATH > OHOS 工具链默认位置。"""
        configured = os.environ.get(env_var)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if not resolved and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            resolved = os.path.abspath(candidate)
        if not resolved and not configured:
            fallback = os.path.join("/data/service/hnp/bin", executable)
            if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
                resolved = fallback
        if not resolved:
            raise ConanInvalidConfiguration(
                f"未找到 {executable}（需要 OHOS 工具链来完成 ELF 签章）"
            )
        return resolved

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=120
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    def _has_codesign_section(self, objdump, path):
        sections = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}"
        )
        return any(self._SIGN_SECTION in line.split() for line in sections.splitlines())

    def _sign_elfs(self, bindir):
        """对 bin/ 下的可执行文件与插件做 HarmonyOS 代码签名。

        签章是对 ELF 内容的哈希，必须在所有后续处理（修补/权限）**之后**
        执行，故放在 package() 最后一步。用临时目录「unsigned → signed」
        再 os.replace 回写，并在最后一次强校验 `.codesign` 段确实存在
        （adwaita-qt/1.4.2 同法）。
        """
        if str(self.settings.os) != "OHOS":
            return
        targets = []
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            if self._elf_type(path) in (2, 3):
                targets.append(path)
        if not targets:
            return

        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")

        for binary in targets:
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", self._SIGN_SECTION, unsigned],
                        f"remove the old code signature from {binary}",
                    )
                self._run_tool(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        unsigned,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    f"sign {binary}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def package(self):
        # `make install` 使用 build() 里由 self.package_folder 烘焙的
        # *_INSTALL_PATH（同一 conan 进程内 package_folder 与 build 期一致，
        # 已用 scratch 配方实测验证）
        self.run("make install", cwd=self.source_folder)
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            raise ConanInvalidConfiguration(f"未生成 bin 目录: {bindir}")
        # 签章必须放最后：任何后置改动都会让 .codesign 哈希失效
        self._sign_elfs(bindir)

    def requirements(self):
        # qt5-qtbase/5.15.2 为 -no-widgets 构建（无 Qt5Widgets），
        # qpdfview 声明 QT += widgets → 用 5.15.2.2（baka 先例同解）。
        # qt5-qtsvg/5.15.2 的 recipe 声明精确 qt5-qtbase/5.15.2，
        # 与本配方 5.15.2.2 冲突 → override 强制统一到 5.15.2.2
        # （补丁版本 API 兼容，qtsvg 二进制无需重建；两者预编译包 id
        # 实测一致）。
        self.requires("qt5-qtbase/5.15.2.2", override=True)
        self.requires("qt5-qtsvg/5.15.2")
        # poppler = PDF 后端（W0 已确认 25.12.0.2 有 OHOS/armv8 预编译包）
        self.requires("poppler/25.12.0.2")
        # 依赖图版本冲突：cairo（来自 poppler）声明 fontconfig/2.18.1，
        # 需要 2.18.1.1 → override 统一（补丁版本兼容）
        self.requires("fontconfig/2.18.1.1", override=True)
        # 依赖图版本冲突：glib/dbus 链声明 zlib → 统一到 1.3.1.1
        # （zlib 仅作图一致性 override；-lz 实际解析到 OHOS 系统库，
        # 见 build() 中 LIBRARY_PATH 的说明）
        self.requires("zlib/1.3.1.1", override=True)
        # 依赖图版本冲突：fontconfig/2.18.1.1 声明精确 expat/2.8.2.1，
        # 与其它链的 2.8.2 冲突 → override 统一
        self.requires("expat/2.8.2.1", override=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # 运行期环境：本包的 Qt/poppler 依赖链横跨**多个 conan package
        # 前缀**（qt5-qtbase、qt5-qtsvg、poppler、freetype、lcms2、
        # fontconfig…），运行期加载器必须知道所有 lib 目录。
        for require, dep in sorted(
            self.dependencies.items(), key=lambda kv: kv[0].ref.name
        ):
            dep_name = require.ref.name
            if not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
            bindir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bindir) and dep_name.startswith("qt5-"):
                self.runenv_info.prepend_path("PATH", bindir)
        # Qt 插件目录：qtsvg 的 iconengines / imageformats 是图标与 SVG
        # 正常加载的关键（OHOS 无系统级 Qt 插件目录）
        for require, dep in sorted(
            self.dependencies.items(), key=lambda kv: kv[0].ref.name
        ):
            if not require.ref.name.startswith("qt5-"):
                continue
            plugins = os.path.join(dep.package_folder, "plugins")
            if os.path.isdir(plugins):
                self.runenv_info.prepend_path("QT_PLUGIN_PATH", plugins)
        # fontconfig 默认配置文件（否则运行期
        # `Fontconfig error: Cannot load default config file`）
        fonts_dir = os.path.join(
            self.dependencies["fontconfig"].package_folder, "etc", "fonts"
        )
        if os.path.isdir(fonts_dir):
            self.runenv_info.prepend_path("FONTCONFIG_PATH", fonts_dir)
