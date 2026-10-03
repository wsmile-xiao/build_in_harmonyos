#!/usr/bin/env python3
"""Conan recipe for ktimer 26.04.0 on HarmonyOS PC.

KTimer 是 KDE 定时提醒小工具（倒计时到点执行命令 / 弹通知），纯 Qt Widgets GUI
（KDE release-service 26.04.0，invent.kde.org/utilities/ktimer）。

OHOS 适配要点：
  - **Qt6 DBus 单一提供者**：上游 main.cpp 构造 `KDBusService`（kdbusaddons 的
    Qt6DBus 客户端）、ktimer.cpp 用 `KStatusNotifierItem`（DBus 托盘协议）。
    Qt6DBus 由 **qtbase/6.11.1.1（FEATURE_dbus=ON 变体）** 直接提供
    （qtbase/6.11.1 是 FEATURE_dbus=OFF），因此不需要 qtbase-sql-dbus 变体，
    避免同一 Qt6Core/Qt6Widgets 出现两个提供者 —— 与
    statusnotifieritem/6.26.0 的文档口径一致（kmousetool 26.04.0 同款配对）。
  - **KF6StatusNotifierItem 取 archives/s 的 `statusnotifieritem/6.26.0`
    （USE_DBUS=ON），不是 archives/k 的 `kstatusnotifieritem/6.26.0`
    （USE_DBUS=OFF）**：后者把 StatusNotifierItem 的 DBus adaptor 整段编译掉，
    托盘在 OHOS 上静默失效；两者同版本、同上游、同产物名，只有靠目录与
    docstring 才分得清。
  - **KF6 闭包取 6.18 线 + `karchive/6.19.0`，代价只剩 kio 本地重建**：
    ① KIO **必须**保留 —— `prefwidget.ui` 用 `KUrlRequester`，其
    `kurlrequester.h` 属 **KIOWidgets**，C++ 侧 `m_commandLine->lineEdit()` 4 处
    依赖它（只 grep `*.cpp/*.h` 会漏判，必须连 `.ui` 一起扫）；
    ② `kwindowsystem` **不得低于 6.18.0** —— `statusnotifieritem/6.26.0` 自己的
    `CMakeLists.txt:52` 硬性 `find_package(KF6WindowSystem 6.18.0)`，
    压到 6.14.0 会在**它**的 configure 阶段直接红；
    ③ `kiconthemes/6.18.0` 的**已发布二进制**钉 `karchive/6.19.0`，
    对齐后它不再本地重建 —— 而它一旦重建，其**自己的上游测试**会因 KF6 预编译包
    坏 RPATH 挂在 `Error relocating libKF6ColorScheme.so`（依赖配方、本机改不了）；
    ④ 结果：`conan graph info` 实测 **Missing = 仅 kio**，且 kio 配方自带
    `BUILD_TESTING=OFF` 不跑上游测试。
  - **`override=True` 只对「存在传递引用」的包生效**：Conan 2 会把只由本配方
    声明、却无任何传递依赖引用的 override 边**整条丢出依赖图**（实测
    `knotifications`/`kcrash` 在 `conan graph info` 中出现 0 次，去掉 override
    后立即出现），症状却伪装成 CMake `Could NOT find KF6 ...`。
  - **KF6DocTools 不在发布闭包内**：上游 `find_package(KF6DocTools)` 非 REQUIRED，
    `doc/` 与 `kdoctools_install(po)` 均由 `KF6DocTools_FOUND` 守卫 ⇒ 无需补丁，
    代价仅是在线手册（KHelpClient::invokeHelp 手册路径为空）。
  - KF_IGNORE_PLATFORM_CHECK=TRUE（OHOS 不在 KDE 平台列表）
  - KF_SKIP_PO_PROCESSING=ON（ki18n_install(po) 的 lconvert/msgfmt 不可用，
    .qm 翻译目录非必需 —— kteatime/kmousetool 同款）
  - ECM_MODULE_PATH 手工设置 + conan_cmakedeps_paths.cmake
    （qtbase 与 KF6 包用 cmake_find_mode=none，CMakeDeps 不会把 lib/cmake
    加进 CMAKE_PREFIX_PATH）
  - 构建期 host 工具（moc/uic/rcc/kconfig_compiler）由 conan 包提供，是 OHOS
    二进制 ⇒ 需要 LD_LIBRARY_PATH 指到依赖 lib 与 /system/lib64。
  - 上游无测试套件（无 tests/、无 add_test）：N_static=0，由 test_package
    消费者冒烟覆盖。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class KtimerConan(ConanFile):
    name = "ktimer"
    version = "26.04.0"
    description = "KDE timer / countdown reminder - ktimer for HarmonyOS PC"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/utilities/ktimer"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Core/Widgets/DBus 唯一提供者（6.11.1.1 = FEATURE_dbus=ON）；
        # override=True 统一掉各 KF6 包内部钉的 qtbase/6.11.1。
        self.requires("qtbase/6.11.1.1", override=True)
        # 上游 main.cpp: KDBusService service; → Qt6DBus + KF6DBusAddons
        self.requires("kdbusaddons/6.29.0")
        # 上游 ktimer.cpp: new KStatusNotifierItem(this) → 托盘（DBus 版）
        self.requires("statusnotifieritem/6.26.0")
        # find_package(KF6 REQUIRED COMPONENTS I18n WidgetsAddons KIO
        #              DBusAddons Notifications ConfigWidgets Crash)
        # KIO 必需：prefwidget.ui 用 KUrlRequester，kurlrequester.h 属 KIOWidgets，
        # C++ 侧 m_commandLine->lineEdit() 4 处依赖它。
        self.requires("kio/6.14.0")
        # ★闭包取 6.18 线；kio/6.14.0 内部钉 6.14.0 ⇒ 用 override=True 抬齐
        #（ki18n/kwidgetsaddons/knotifications/kcrash 是直接依赖，也必须带
        # override，否则 kio 的 6.14 钉版会直接撞出 Version conflict）。
        self.requires("kconfigwidgets/6.18.0")
        self.requires("ki18n/6.18.0", override=True)
        self.requires("kwidgetsaddons/6.18.0", override=True)
        self.requires("knotifications/6.18.0", override=True)
        self.requires("kcrash/6.18.0", override=True)
        for dep in (
            "kconfig", "kcoreaddons", "kservice", "kcolorscheme",
            "kguiaddons", "kitemviews", "kjobwidgets", "kwindowsystem",
            "kauth", "solid", "kbookmarks", "kcompletion", "kiconthemes",
            "kcodecs",
        ):
            self.requires(f"{dep}/6.18.0", override=True)
        # ★kiconthemes/6.18.0 的**已发布二进制**钉的是 karchive/6.19.0
        # （对齐它才能命中二进制、免掉它那套会因 KF6 坏 RPATH 必挂的上游测试）。
        # karchive 6.19 相对 6.14/6.18 向前兼容，kio 按发布配方本地重建即可。
        self.requires("karchive/6.19.0", override=True)
        # 唯一要本地重建的是 kio：其配方自带 BUILD_TESTING=OFF，不跑上游测试。
        #
        # ★让 openssl 的**二进制必下载**（CI build #65871 首错的直接修法）：
        # ① karchive/6.19.0 是被 kiconthemes/6.18.0 的已发布二进制钉死的
        #    （不可换 6.18.0，否则 kiconthemes 必本地重建、撞它那套坏 RPATH
        #    的上游测试）；它的已安装 lib/cmake/KF6Archive/KF6ArchiveConfig.cmake
        #    第 34 行 KArchive_HAVE_OPENSSL="TRUE"、第 50-52 行硬编码
        #    find_dependency(OpenSSL) ⇒ **任何** find_package(KF6Archive) 的
        #    消费方 configure 都必须能找到 OpenSSL。
        # ② 但 karchive 配方自己不声明 openssl ⇒ 图里 openssl 只经
        #    kiconthemes 传递进来，下游看到的边是 headers=False/libs=False
        #    ⇒ conan 的 _skip_binaries() 判它 files=False、不在 required_nodes
        #    ⇒ BINARY_SKIP ⇒ 包不落地 ⇒ kio 重建时其 generate() 写出的
        #    conan_cmakedeps_paths.cmake 里**没有** openssl 的 include/lib
        #    ⇒ find_package(OpenSSL) 在无系统 OpenSSL 的 CI worker 上必红
        #    （本机过是**假绿**：靠 ~/.harmonybrew/lib/cmake/OpenSSL，
        #     CI 日志里 .harmonybrew 命中 0 次）。
        # ③ 本条把它变成本配方的**直接** requires：root 是 consumer、直接边
        #    files=True ⇒ openssl 进 required_nodes、二进制下载、
        #    package_folder 有值 ⇒ kio 的 generate() 会把它的 include/lib
        #    写进 CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH（同机制已在 CI 日志里
        #    命中过：Found ZLIB: .../conan2/p/zlib.../p/lib/libz.a）。
        # ④ 不改 kio 的 package_id：kio→openssl 这条边 package_id_mode=None、
        #    不进 kio 的 info.requires（实测仍是 e2d99fa2705c2fdbeb8cbfce6c69f949aca1033a）。
        self.requires("openssl/3.5.6.1")

    def build_requirements(self):
        # 上游 find_package(ECM ${KF_MIN_VERSION} REQUIRED NO_MODULE)。
        # kdbusaddons/6.29.0 的 tool_requires 已带 extra-cmake-modules/6.29.0，
        # 与本条一致（kmousetool 26.04.0 同款；statusnotifieritem 另带
        # ecm/6.26.0，两者 recipe 名不同、不冲突）。
        self.tool_requires("extra-cmake-modules/6.29.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # 上游 ki18n_wrap_ui 只用 uic；ki18n_install(po) 的 msgfmt/lconvert
        # 在本平台不可用，.qm 翻译目录非必需（kteatime/kmousetool 同款）。
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # OHOS loader workaround（audiocd 26.04.3 / ktuberling 26.04.0 先例）：
        # lld 默认 max-page-size 可能拆开 .dynsym/.dynstr 到高地址 RW LOAD，
        # OHOS musl loader 拒绝 mmap ⇒ 钉 4K 页布局。
        # 本段只收集旗标，统一在 tc.generate() 之前写入
        # CMAKE_EXE_LINKER_FLAGS_INIT（该通道已被页宽旗标实测证明可用：
        # link.txt 里确实出现了 -Wl,-z,max-page-size=0x1000）。
        link_flags = []
        if self.settings.os == "OHOS":
            link_flags.append("-Wl,-z,max-page-size=0x1000")
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )

        # ECM 自己安装的 ECMConfig.cmake 会设 ECM_MODULE_PATH，但 CMakeDeps
        # 生成的那份不传播 ⇒ 手工设置（kxmlgui/kteatime 同款）。
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        self._write_cmake_paths(ecm)

        # ★主二进制 RPATH 注入（kteatime 26.04.0 先例）：OHOS musl 加载器不认
        # LD_LIBRARY_PATH（E088 同族），而本体与 KF6 预编译包都**没有**
        # DT_RPATH/DT_RUNPATH ⇒ 裸名 NEEDED（libQt6Widgets.so.6、
        # libKF6KIOCore.so…）无处解析、必报 Error loading shared library。
        #
        # 第 9 轮两道保险（前两轮实测定出来的根因）：
        #   ① CMAKE_BUILD_RPATH 是 **CMake 列表语义、必须用 ';'** —— 第 7/8 轮
        #      用了 ':'（os.pathsep），CMake 把整串当成「一个不存在的目录」
        #      整条丢弃：CMakeCache 里有值、CMAKE_SKIP_RPATH=NO，但
        #      link.txt 中 -Wl,-rpath 出现 0 次、产物 DT_RPATH/DT_RUNPATH 双 False。
        #   ② 兜底（关键）：把旗标直接写进 CMAKE_EXE_LINKER_FLAGS_INIT，
        #      用 -Wl,--disable-new-dtags 强制产出 **DT_RPATH** —— ELF 语义上
        #      DT_RPATH 对**整棵依赖树**生效，正好覆盖自身没有 RUNPATH 的
        #      KF6 预编译包去解析裸名 NEEDED（DT_RUNPATH 只管直接依赖）。
        #      链接器侧运行期分隔符是 ':'（-Wl,-rpath, 整串作一个参数传入）。
        dep_lib_dirs = [
            os.path.join(d.package_folder, "lib")
            for d in self.dependencies.values()
            if d and d.package_folder
            and os.path.isdir(os.path.join(d.package_folder, "lib"))
        ]
        if dep_lib_dirs:
            tc.variables["CMAKE_BUILD_RPATH"] = ";".join(dep_lib_dirs)
            tc.variables["CMAKE_INSTALL_RPATH"] = ";".join(dep_lib_dirs)
            link_flags += [
                "-Wl,--disable-new-dtags",
                "-Wl,-rpath," + os.pathsep.join(dep_lib_dirs),
            ]

        if link_flags:
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = " ".join(link_flags)

        tc.generate()

    def _write_cmake_paths(self, ecm):
        # qtbase/KF6 包 cmake_find_mode=none ⇒ CMakeDeps 不会把它们的
        # lib/cmake 放进 CMAKE_PREFIX_PATH，手工写 conan_cmakedeps_paths.cmake
        # （kxmlgui / libkdegames / ktuberling 26.04.0 同款）。
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                self._append_dependency_paths(lines, dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        dep_lib_dirs = [
            os.path.join(d.package_folder, "lib")
            for d in self.dependencies.values()
            if d and d.package_folder
            and os.path.isdir(os.path.join(d.package_folder, "lib"))
        ]
        rpath = ";".join(dep_lib_dirs) if dep_lib_dirs else None
        with self._cmake_build_env().vars(self).apply():
            cmake.configure(
                variables={"CMAKE_BUILD_RPATH": rpath,
                           "CMAKE_INSTALL_RPATH": rpath} if rpath else None)
            cmake.build()

    def _cmake_build_env(self):
        # host 工具（moc/uic/rcc/kconfig_compiler）是 conan 包里的 OHOS
        # 二进制：需要依赖 lib 目录 + /system/lib64 的兼容 libc++_shared
        # （audiocd 26.04.3 / kconfig 6.26.0 / ktuberling 26.04.0 先例）。
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            # OHOS SDK lld 依赖 SDK llvm/lib 里的 libxml2，CI worker 不一定导出。
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # 沙箱 LD_LIBRARY_PATH 里有不兼容的 libc++_shared，先压 /system/lib64。
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 应用包：仅 bin/ktimer，无库交付物。
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        # 运行期加载 Qt6/KF6 依赖：把依赖 lib 目录写进 runenv，
        # 消费者 test_package 的 conanrun 可直接解析。
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(
                "ktimer/26.04.0 is a HarmonyOS PC adaptation (R32: os 判断用 in)"
            )
