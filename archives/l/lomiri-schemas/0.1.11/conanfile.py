#!/usr/bin/env python3
"""Conan recipe — lomiri-schemas 0.1.11 (UBports/Lomiri GSettings 声明式数据包)。

lomiri-schemas 把 Lomiri 桌面栈的**声明式数据**单独拆包，不含任何可编译代码：
上游 CMakeLists.txt 是 `project(lomiri-schemas LANGUAGES NONE)`，只 add_subdirectory(data)，
产出 6 个 GSettings schema（*.gschema.xml.in，共 15 个 <schema> 节点：com.lomiri.Shell 及其
Greeter/Interface/Launcher/Devices/Decorations/IntegratedMenus/Gestures/Shortcuts 子 schema、
com.lomiri.phone、com.lomiri.sound、com.lomiri.notifications.settings[.applications]、
com.lomiri.touch.sound、com.lomiri.touch.system）、6 个 AccountsService D-Bus 接口 XML
（另建 accountsservice/interfaces 下的相对符号链接）、polkit policy + rules，以及
lomiri-schemas.pc。Lomiri/Ubuntu Touch 与 Ayatana Indicators 在运行期经 GSettings 读这些 schema。

OHOS 适配要点：
- 纯 CMake 数据包。build 阶段只有两类动作：把 *.gschema.xml.in 渲染成 *.gschema.xml；
  GSettings 模块为每个 schema 注册一条 CTest 校验（add_test validate-<file>）。
- **补丁 0001**：上游用 `intltool_merge_translations(... STYLE xml NO_TRANSLATIONS)`
  渲染 schema，实际执行的是 `intltool-merge --xml-style`——一个 Perl 脚本，硬依赖
  XML::Parser 模块。OHOS 设备的 perl 没有该模块，命令一律 die
  （"You must have XML::Parser installed"），6 个 schema 全部构建失败。仓库里 6 个
  `*.gschema.xml.in` 不含任何 gettext 标记（无 `_` 前缀元素、无 `translatable="yes"`），
  上游也根本没有 `po/` 目录，故 `--no-translations` 下的渲染结果与原文逐字节等价。
  补丁把它换成 `configure_file(... COPYONLY)`，并去掉不再需要的
  `find_package(Intltool REQUIRED)`。
- find_package(GSettings) 的模块来自 cmake-extras/1.9，装在
  share/cmake/GSettings/（config 模式）。Conan 的 conan_cmakedeps_paths.cmake 只写
  `<pkg>_DIR`、不写 CMAKE_PREFIX_PATH，故 generate() 在其尾部追加一条
  `list(PREPEND CMAKE_PREFIX_PATH "<cmake-extras>")`，find_package 才能命中
  `<prefix>/share/cmake/GSettings/GSettingsConfig.cmake`。
- gettext（msgfmt/msgmerge）是构建期工具：GSettingsConfig 会
  `find_package(Gettext REQUIRED)`，走 tool_requires。OHOS SDK 的
  /data/service/hnp/bin 下存在 shebang 指向不存在解释器的坏条目（gdbus-codegen 先例，
  ayatana-indicator-session CI #39406），故 generate() 把 Conan 侧 bin 目录
  PREPEND 进 CMAKE_PROGRAM_PATH，钉死 find_program 的解析结果，避免命中坏条目。
- GSettingsConfig.cmake 默认把 schema 装到
  `${pkg-config glib-2.0 --variable prefix}/share/glib-2.0/schemas`，即只读的 glib
  依赖包目录；改 `-DGSETTINGS_LOCALINSTALL=ON` 落到本包 CMAKE_INSTALL_PREFIX 下。
- `pkg-config gio-2.0 --variable glib_compile_schemas` 在 Conan 侧为空：PkgConfigDeps
  只按 cpp_info 生成 .pc，而 glib 配方未声明该自定义变量。空值会让 add_test 退化成
  `--dry-run ...`（首 token 被当成命令名）。generate() 往生成的 gio-2.0.pc 补一行
  `glib_compile_schemas=<glib>/bin/glib-compile-schemas`，恢复上游语义。
- 上游 CMakeLists.txt 顶部有 `if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
  SET(CMAKE_INSTALL_PREFIX "/usr" CACHE PATH ... FORCE)`。显式把 CMAKE_INSTALL_PREFIX
  作为 cache 变量下发（= package_folder），该兜底分支不触发，install 全落在包内。
- lomiri-schemas.pc 由 configure_file 生成，prefix 会被烘成配置期绝对路径；
  package() 重写为 ${pcfiledir}/../..（同仓 pc 重定位惯例）。
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps


def _posix(path):
    return str(path).replace("\\", "/")


class LomiriSchemasConan(ConanFile):
    name = "lomiri-schemas"
    version = "0.1.11"
    description = "Lomiri GSettings schemas, AccountsService interface XML and polkit data"
    license = "LGPL-2.1-only"
    homepage = "https://gitlab.com/ubports/development/core/lomiri-schemas"
    url = ""  # CI fills this
    topics = ("lomiri", "gsettings", "schemas", "accountsservice", "ubports")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # conandata.yml 声明的补丁必须 export 进 source folder，否则
        # build() 里的 apply_conandata_patches 会 FileNotFoundError。
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lomiri-schemas supports Linux/OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # .pc 声明 Requires: glib-2.0；schema 消费方运行期需要 glib 的 GSettings
        self.requires("glib/2.88.3", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # GSettings CMake 模块（share/cmake/GSettings/）
        self.tool_requires("cmake-extras/1.9")
        # GSettingsConfig.cmake 会 find_package(Gettext REQUIRED) -> msgfmt/msgmerge
        # 注：intltool 已不再需要——补丁 0001 用 configure_file COPYONLY 取代了
        #     intltool-merge（其 Perl 侧 XML::Parser 在 OHOS 上不存在）。
        self.tool_requires("gettext/0.22.5.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()

        tc = CMakeToolchain(self)
        # 上游 CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT 兜底分支（/usr）不触发
        tc.cache_variables["CMAKE_INSTALL_PREFIX"] = self.package_folder
        # schema 装到本包 share/glib-2.0/schemas（而非只读的 glib 依赖 prefix）
        tc.variables["GSETTINGS_LOCALINSTALL"] = "ON"
        tc.generate()

        self._extend_cmakedeps_paths()
        self._augment_gio_pc()

    def _extend_cmakedeps_paths(self):
        """CMakeToolchain 只在 conan_cmakedeps_paths.cmake 不存在时才自带
        CMAKE_PREFIX_PATH/CMAKE_PROGRAM_PATH；CMakeConfigDeps 生成的文件只写
        <pkg>_DIR，故这里把 GSettings 模块目录与构建期工具目录补进去。
        """
        lines = []
        extras = self.dependencies.build["cmake-extras"]
        if extras and extras.package_folder:
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{_posix(extras.package_folder)}")')

        contexts = (
            (self.dependencies.build, "gettext"),
            (self.dependencies, "glib"),
        )
        for context, name in contexts:
            dep = context[name]
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PROGRAM_PATH '
                    f'"{_posix(os.path.join(dep.package_folder, "bin"))}")'
                )
        if not lines:
            return
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        mode = "a" if os.path.isfile(paths_file) else "w"
        with open(paths_file, mode, encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    def _augment_gio_pc(self):
        """给 PkgConfigDeps 生成的 gio-2.0.pc 补 glib_compile_schemas 变量。

        GSettingsConfig.cmake 用 `pkg-config gio-2.0 --variable glib_compile_schemas`
        定位 schema 编译器；PkgConfigDeps 不产该自定义变量（glib 配方未声明），
        空值会让 add_schema() 里的 add_test 丢命令。
        """
        glib = self.dependencies["glib"]
        if not glib or not glib.package_folder:
            return
        pc_file = os.path.join(self.generators_folder, "gio-2.0.pc")
        if not os.path.isfile(pc_file):
            return
        with open(pc_file, "r", encoding="utf-8") as fh:
            content = fh.read()
        if "glib_compile_schemas" in content:
            return
        tool = _posix(os.path.join(glib.package_folder, "bin", "glib-compile-schemas"))
        with open(pc_file, "a", encoding="utf-8") as fh:
            fh.write(f"\nglib_compile_schemas={tool}\n")

    def build(self):
        apply_conandata_patches(self)  # 无补丁时空操作
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._relocate_pc()

    def _relocate_pc(self):
        pc_file = os.path.join(
            self.package_folder, "share", "pkgconfig", "lomiri-schemas.pc"
        )
        if not os.path.isfile(pc_file):
            return
        with open(pc_file, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        out = ["prefix=${pcfiledir}/../.." if l.startswith("prefix=") else l
               for l in lines]
        with open(pc_file, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out) + "\n")

    def package_info(self):
        # 纯数据包：无库、无头文件；schema/polkit/D-Bus 数据经 resdirs 暴露
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]
