#!/usr/bin/env python3
"""Conan recipe — ayatana-indicator-session 26.6.1.

Ayatana Indicators 会话指示器服务（org.ayatana.indicator.session 的 D-Bus 服务端）。

OHOS 适配说明：
  - 依赖 libayatana-common/0.9.13 + glib/2.88.0.1（pkg-config: libayatana-common>=0.9.2、
    glib-2.0>=2.36、gio-unix-2.0>=2.36）。PkgConfigDeps 把依赖组件的 .pc 生成到
    generators 目录（conan_toolchain.cmake 自动把该目录注入 PKG_CONFIG_PATH）。
  - glib/2.88.0.1 配方未声明 gio-unix 组件 → PkgConfigDeps 不产出 gio-unix-2.0.pc；
    上游 CMakeLists 的 pkg_check_modules(REQUIRED ... gio-unix-2.0) 需要它。
    generate() 手工写一个（头文件在 glib 包 include/gio-unix-2.0，API 在 libgio-2.0）。
  - ENABLE_RDA=OFF：rda pkg-config 包未发布；RDA（远程桌面感知）代码全部在
    #ifdef RDA_ENABLED 内，关闭后整段裁剪，与会话服务主路径无关。
  - SKIP_DATA_PO=ON（0001 补丁新增选项）：OHOS 无 GSettings/Intltool CMake 模块，
    跳过 data/（GSettings schema/systemd 单元/autostart）与 po/ 子目录。
    这些是桌面发行集成数据，非服务运行必需。
  - ENABLE_TESTS=OFF：上游测试（tests/CMakeLists.txt）依赖 GTest + D-Bus 会话，
    OHOS 环境不可用。
  - 产物为单可执行文件 ayatana-indicator-session-service。上游把它装到
    CMAKE_INSTALL_LIBEXECDIR/ayatana-indicator-session/（OHOS 上 LIBEXECDIR=bin），
    package() 提升到 bin/ 顶层，符合 Conan bin/ 约定与 commands.json/L2 冒烟。
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class AyatanaIndicatorSessionConan(ConanFile):
    name = "ayatana-indicator-session"
    version = "26.6.1"
    description = "Ayatana Indicators session indicator D-Bus service (session menu / shutdown / lock / user switching)"
    license = "GPL-3.0"
    homepage = "https://github.com/AyatanaIndicators/ayatana-indicator-session"
    url = "https://github.com/AyatanaIndicators/ayatana-indicator-session"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # src/*.c 直接使用 libayatana-common 与 glib/gio-unix API，两依赖都是编译/链接必需
        self.requires("libayatana-common/0.9.13", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.88.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # rda pkg-config 包未发布，关闭 RDA 可选特性（#ifdef RDA_ENABLED 整段裁剪）
        tc.variables["ENABLE_RDA"] = "OFF"
        # OHOS 无 GSettings/Intltool CMake 模块 → 跳过 data/ po/ 子目录（0001 补丁选项）
        tc.variables["SKIP_DATA_PO"] = "ON"
        # 上游测试需 GTest/Vala/D-Bus，不可用
        tc.variables["ENABLE_TESTS"] = "OFF"
        tc.variables["ENABLE_WERROR"] = "OFF"
        # CI #39406 暴露的构建真因：OHOS SDK 的 /data/service/hnp/bin/gdbus-codegen
        # 是坏条目（shebang #!/usr/bin/python3 指向不存在的解释器，执行即
        # "No such file or directory" / make Error 126）。上游 cmake/GdbusCodegen.cmake
        # 用 find_program(GDBUS_CODEGEN gdbus-codegen) 从 PATH 定位，命中该坏条目，
        # 导致 backend-dbus 的 lomiri-session.h/c 生成步失败（并行日志里表现为
        # [48%] 静默 Error 2）。glib 包内自带可用 gdbus-codegen（#!/usr/bin/env
        # python3）。find_program 优先查询 CMAKE_PROGRAM_PATH（官方搜索顺序先于
        # PATH），把 glib bin 钉死为解析结果，避免命中 SDK 坏条目（gtk4 同款思路
        # 的 CMake 侧实现）。
        glib_dep = self.dependencies["glib"]
        glib_bin = None
        if glib_dep and glib_dep.package_folder:
            glib_bin = os.path.join(glib_dep.package_folder, "bin")
            cur_path = tc.variables.get("CMAKE_PROGRAM_PATH")
            tc.variables["CMAKE_PROGRAM_PATH"] = (
                glib_bin + (";" + cur_path if cur_path else "")
            )
        tc.generate()

        # glib/2.88.0.1 未声明 gio-unix 组件，PkgConfigDeps 不产出 gio-unix-2.0.pc；
        # 手工写入 generators 目录（已在 PKG_CONFIG_PATH 上）
        if glib_dep and glib_dep.package_folder:
            pc_path = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
            with open(pc_path, "w", encoding="utf-8") as _pc:
                _pc.write(
                    "prefix={0}\n"
                    "libdir=${{prefix}}/lib\n"
                    "includedir=${{prefix}}/include\n"
                    "\n"
                    "Name: GIO unix specific APIs\n"
                    "Description: unix specific headers for glib I/O library\n"
                    "Version: 2.88.0\n"
                    "Requires: gobject-2.0, gio-2.0\n"
                    "Cflags: -I${{prefix}}/include/gio-unix-2.0\n"
                    "Libs: -L${{libdir}} -lgio-2.0\n".format(glib_dep.package_folder)
                )

        # E266/E106: OHOS SDK 的 lld 链接器运行时依赖 libxml2.so.16，CI 沙箱默认
        # 库搜索路径找不到它 → 可执行文件链接步骤（静态库之后）静默失败（make
        # Error 2、日志无错误输出，见 CI #36727/#37440）。前置 SDK llvm/lib 到
        # LD_LIBRARY_PATH 让 lld 能加载正确的 libxml2（plzip/debianutils/babeld
        # 同方案，均已 CI 绿）。注意不能用 -fuse-ld=GNU ld——GNU ld 产物在 OHOS
        # 沙箱中 Permission denied (exit 126) 不可执行，可执行包必须走默认 lld。
        env = Environment()
        for lib_dir in glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"):
            if os.path.isfile(os.path.join(lib_dir, "libxml2.so.16")):
                env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                break
        if glib_bin:
            # 兜底：PATH 前置 glib bin，覆盖任何按裸名 gdbus-codegen 调用的自定义命令
            # （find_program 已由 CMAKE_PROGRAM_PATH 钉死，此处双保险，gtk4 同款）。
            env.prepend_path("PATH", glib_bin)
        env.vars(self).save_script("lld_fix")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 串行构建 -j1（strace/plzip/babeld 同款，均 CI 绿）：CI 沙箱击杀多作业并行构建——
        # 全并行（conan 默认 -j=cpu 数）在 [48%] 静默失败（4 个 worker 同点复现，零输出）；
        # 限 -j4 探针（CI #39381）仍在 target2 起始处同模式失败（进度漂移至 27%）→ 沙箱
        # 并行阈值 <4，跟随本仓可执行包通行做法改全串行。build_tool_args 追加在默认
        # -j{njobs} 之后的 `--` 段，GNU make 以最后一个 -j 生效。generate() 的 lld_fix
        # （LD_LIBRARY_PATH）保留防 E266（configure 试链接 lld/libxml2，见 #36946）。
        cmake.build(build_tool_args=["-j", "1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游 install 到 bin/ayatana-indicator-session/ayatana-indicator-session-service
        # （CMAKE_INSTALL_LIBEXECDIR + ${CMAKE_PROJECT_NAME}）。提升到 bin/ 顶层，
        # 便于 conan bin/ 约定、commands.json 与 L2 冒烟定位。
        nested_dir = os.path.join(self.package_folder, "bin", "ayatana-indicator-session")
        nested = os.path.join(nested_dir, "ayatana-indicator-session-service")
        top = os.path.join(self.package_folder, "bin", "ayatana-indicator-session-service")
        if os.path.exists(nested) and not os.path.exists(top):
            os.makedirs(os.path.dirname(top), exist_ok=True)
            os.replace(nested, top)
            try:
                os.rmdir(nested_dir)
            except OSError:
                pass

    def package_info(self):
        # 产物为可执行文件，无库/头文件可消费
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
