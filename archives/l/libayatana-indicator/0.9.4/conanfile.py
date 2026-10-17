#!/usr/bin/env python3
"""Conan recipe — libayatana-indicator 0.9.4 (CMake).

Ayatana Indicators 核心库（indicator-object/service/loader 框架）。
HarmonyOS PC (aarch64) 适配要点（基于 0.9.4 自身源码逐项核实）：
  - 构建系统: CMake >= 3.13（上游 CMakeLists.txt，pkg_check_modules 依赖解析）
  - 0.9.4 依赖（根 CMakeLists.txt DEPS）: glib-2.0>=2.37, gmodule-2.0,
    gio-unix-2.0 + gtk+-3.0>=3.24（FLAVOUR_GTK3 默认 ON）+
    libayatana-ido3-0.4>=0.8.2（ENABLE_IDO 默认 ON），对齐 ohpcd 已发布的
    gtk/3.24.43 / ayatana-ido/0.10.4 依赖图（glib/2.84.0.1，R36）
  - 0.9.4 src/CMakeLists.txt 链接行为（与 0.9.5 的差异点）：
    `target_link_libraries(... ${PROJECT_DEPS_LIBRARIES} ...)` — 裸 -l 名单，
    且 pkg_check_modules 的 _LIBRARY_DIRS（-L 目录）从未进链接行 →
    传递依赖库链接期找不到（同 ayatana-ido/0.10.4 的 -L 丢失根因），
    遍历依赖图注入全部 libdir
  - glib-mkenums / glib-genmarshal 由 find_program 发现：CI runner
    /data/service/hnp/bin 下断链符号链接会污染 find_program 缓存，
    显式注入 glib 包内真实脚本绝对路径
  - 产物（FLAVOUR_GTK3 + ENABLE_IDO + ENABLE_LOADER，GNUInstallDirs）:
    lib/libayatana-indicator3.so + ayatana-indicator3-0.4.pc +
    7 个公共头（include/libayatana-indicator3-0.4/libayatana-indicator/）+
    libexec/libayatana-indicator/ayatana-indicator-loader3 +
    share/libayatana-indicator/80indicator-debugging
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import PkgConfigDeps


class LibayatanaIndicatorConan(ConanFile):
    name = "libayatana-indicator"
    version = "0.9.4"
    description = "Ayatana Indicators core library (indicator-object/service framework for panel indicators)"
    license = "GPL-3.0-only"
    homepage = "https://github.com/AyatanaIndicators/libayatana-indicator"
    url = "https://github.com/AyatanaIndicators/libayatana-indicator"
    topics = ("indicator", "ayatana", "panel", "gtk")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        # 上游 src/CMakeLists.txt: add_library(... SHARED ...) 硬编码共享库，
        # 无 BUILD_SHARED_LIBS 分支。核心 API indicator_object_new_from_file()
        # 运行时 g_module_open() dlopen 第三方指示器插件
        # （libayatana-indicators3/ 目录），静态链接无意义——
        # 共享库是上游唯一支持的形态（上游 tarball 不提供 .a）。
        # 保留 shared 选项以维持消费方 -o shared=... 图兼容性。
        "shared": [True, False],
        "fPIC": [True, False],
        # 上游 CMake 选项透传
        "enable_ido": [True, False],      # ENABLE_IDO: indicator-ng + libayatana-ido 链接
        "enable_loader": [True, False],   # ENABLE_LOADER: ayatana-indicator-loader3 工具
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "enable_ido": True,
        "enable_loader": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # 上游 src/CMakeLists.txt: add_library("${ayatana_indicator_gtkver}"
        # SHARED ${SOURCES}) 硬编码共享库（0.9.4 与 0.9.5 同），无静态分支；
        # 核心加载 API indicator_object_new_from_file() 运行时 g_module_open()
        # dlopen 指示器插件（libayatana-indicators3/<abi>/ 目录）。
        if not self.info.options.shared:
            raise ConanInvalidConfiguration(
                "libayatana-indicator 0.9.4 upstream only builds a SHARED "
                "library (hardcoded add_library SHARED; core API "
                "indicator_object_new_from_file() dlopen()s indicator "
                "plugins at runtime via g_module_open). Static linking "
                "is not supported.")

    def requirements(self):
        # gtk/3.24.43 与 ayatana-ido/0.10.4 recipe 均 pin glib/2.84.0.1
        # （同图），顶层对齐避免图内版本冲突（R36）。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        if self.options.enable_ido:
            self.requires("ayatana-ido/0.10.4", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._copy_gio_unix_pc()
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_TESTS"] = "OFF"
        tc.variables["ENABLE_WERROR"] = "OFF"
        # 构建期不构建 tools/ 下 loader 工具时保持库产物纯净（默认 ON 与上游一致）
        tc.variables["ENABLE_LOADER"] = "ON" if self.options.enable_loader else "OFF"
        tc.variables["ENABLE_IDO"] = "ON" if self.options.enable_ido else "OFF"
        # ENABLE_TESTS=OFF 跳过 tests/ 子目录（上游 tests 依赖 dbus-test-runner/
        # Xvfb/gtester 桌面环境，离线 CI 不可执行，详见 notes.md）
        # 0.9.4 src/CMakeLists.txt: target_link_libraries(... ${PROJECT_DEPS_LIBRARIES})
        # — pkg_check_modules 只产 -l 裸名单，_LIBRARY_DIRS 的 -L 目录未进
        # 链接行 → 传递依赖库（gtk/ayatana-ido 等）链接期找不到。
        # 手动注入全部依赖 libdir。
        link_dirs = set()
        for dep_name, dep in self.dependencies.items():
            if dep.package_folder:
                for libdir_name in ("lib", "lib64"):
                    libdir = os.path.join(dep.package_folder, libdir_name)
                    if os.path.isdir(libdir):
                        link_dirs.add(f"-L{libdir}")
        flags = " ".join(sorted(link_dirs))
        # W4/L5 门禁: 上游 VERSION 7.0.0 / SOVERSION 7 在 HarmonyOS 平台下
        # 未产出 DT_SONAME（链接行无 -Wl,-soname，产物为未版本化
        # libayatana-indicator3.so），L5 soname_gate 拦截。显式注入 soname，
        # 与 SOVERSION 7 对齐（同 ayatana-ido 0.10.4 先例）。
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = (
            flags + " -Wl,-soname,libayatana-indicator3.so.7"
        )
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = flags
        # glib-mkenums / glib-genmarshal: find_program 会缓存 CI runner
        # /data/service/hnp/bin 断链符号链接（E543 同类 runner-path 问题）。
        # 显式注入 glib 包内真实脚本绝对路径。
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        tc.variables["GLIB_MKENUMS"] = os.path.join(glib_bin, "glib-mkenums")
        tc.variables["GLIB_GENMARSHAL"] = os.path.join(glib_bin, "glib-genmarshal")
        env = Environment()
        env.prepend_path("PATH", glib_bin)
        env.vars(self).save_script("glib_tools_env")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with Environment().vars(self).apply():
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        with Environment().vars(self).apply():
            cmake.install()
        # 上游 install(TARGETS ... LIBRARY DESTINATION lib) 只装
        # libayatana-indicator3.so（HarmonyOS 平台无版本化文件名/符号链接，
        # GNUInstallDirs + CMAKE_PLATFORM_NO_VERSIONED_SONAME 类行为）。
        # 注入的 SONAME 为 libayatana-indicator3.so.7，下游按 SONAME 寻址需
        # 该文件名存在（HMDFS 软链接不可靠，用复制保证运行时可达，
        # 同 ayatana-ido 0.10.4 先例）。
        libdir = os.path.join(self.package_folder, "lib")
        soname_target = os.path.join(libdir, "libayatana-indicator3.so.7")
        if (os.path.isdir(libdir)
                and not os.path.exists(soname_target)
                and os.path.exists(os.path.join(libdir, "libayatana-indicator3.so"))):
            shutil.copy2(os.path.join(libdir, "libayatana-indicator3.so"), soname_target)

    def _copy_gio_unix_pc(self):
        # 上游 DEPS 含 gio-unix-2.0，pkg_check_modules(REQUIRED) 必须找到该 .pc；
        # glib 配方未声明 gio-unix-2.0 组件 → PkgConfigDeps 不生成该文件，
        # 上游配置直接报 "No package 'gio-unix-2.0' found"。
        # 复制 glib 包内原始 gio-unix-2.0.pc 并改写 prefix 到 glib 包目录
        # （accountsservice 26.27.3 / libayatana-indicator 0.9.5 同模式）。
        glib = self.dependencies["glib"]
        src = os.path.join(glib.package_folder, "lib", "pkgconfig", "gio-unix-2.0.pc")
        if not os.path.isfile(src):
            self.output.warning("gio-unix-2.0.pc not found in glib package; skipping")
            return
        with open(src, encoding="utf-8") as handle:
            content = handle.read()
        prefix = glib.package_folder.replace("\\", "/")
        lines = []
        for line in content.splitlines():
            if line.startswith("prefix="):
                line = "prefix=" + prefix
            lines.append(line)
        # glib-2.0.pc（PkgConfigDeps 生成）Libs 无 -lintl，而依赖链共享库
        # 引用 g_libintl_ngettext → 链接期 undefined reference
        # （gtk/ayatana-ido 先例：追加 -lintl）。
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(glib_pc):
            with open(glib_pc, encoding="utf-8") as handle:
                glib_content = handle.read()
            out_lines = []
            for line in glib_content.splitlines(keepends=True):
                if line.startswith("Libs:") and "-lintl" not in line.split():
                    line = line.rstrip("\r\n") + " -lintl\n"
                out_lines.append(line)
            new_content = "".join(out_lines)
            if new_content != glib_content:
                with open(glib_pc, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(new_content)
        dst = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        with open(dst, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")

    def package_info(self):
        self.cpp_info.libs = ["ayatana-indicator3"]
        self.cpp_info.includedirs = ["include/libayatana-indicator3-0.4", "include"]
        # 上游 ayatana-indicator3-0.4.pc: Requires: gtk+-3.0 libayatana-ido3-0.4
        self.cpp_info.set_property("pkg_config_name", "ayatana-indicator3-0.4")
        self.cpp_info.set_property("cmake_file_name", "ayatana-indicator3")
        self.cpp_info.set_property("cmake_target_name", "ayatana-indicator3::ayatana-indicator3")
        self.cpp_info.requires = ["glib::glib", "gtk::gtk"]
        if self.options.enable_ido:
            self.cpp_info.requires.append("ayatana-ido::ayatana-ido")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
