#!/usr/bin/env python3
"""Conan recipe — ayatana-indicator-messages 24.5.2.

Ayatana System Indicator — Messages：消息菜单系统指示器服务
（messaging menu，Unity7/MATE/Lomiri 桌面使用，提供 libmessaging-menu 库）。

OHOS 适配说明：
  - 依赖 glib-2.0/gio-unix-2.0（顶层 CMakeLists 的 pkg_check_modules
    PROJECT_DEPS REQUIRED），通过 PkgConfigDeps 生成 .pc（CMakeToolchain
    自动把 generators 目录注入 PKG_CONFIG_PATH）。
  - glib 配方 cpp_info 未声明 gio-unix-2.0 组件，PkgConfigDeps 不会生成
    转发 gio-unix-2.0.pc；_augment_glib_unix_pkg_config() 从 glib 包内
    复制该 .pc 并改写 prefix（与 ayatana-ido/ayatana-indicator-display 同法）。
  - 0001 补丁：accountsservice 是顶层 REQUIRED 依赖，但仓库/制品仓均无
    accountsservice 配方（OHOS 无 AccountsService 系统守护进程）——
    ENABLE_ACCOUNTS_SERVICE=OFF 时不再 REQUIRED；同时 SKIP_DATA_PO=ON 跳过
    data/（GSettings CMake 模块缺失）与 po/（Intltool REQUIRED）、SKIP_DOC=ON
    跳过 doc/（gtk-doc 工具缺失）。
  - 0002 补丁：im-accounts-service.c 以 HAVE_ACCOUNTS_SERVICE 编译开关包裹
    act/act.h 实现；OFF 时编译 stub（draws-attention no-op、show-on-greeter
    恒 FALSE），保证 IM_ACCOUNTS_SERVICE_* 符号齐全，产品消息菜单核心不受影响。
  - 0003 补丁：libmessaging-menu 的 GObjectIntrospection/Vala 生成 gir/typelib/
    vapi 为桌面绑定所需，OHOS 制品仓无此工具链，ENABLE_INTROSPECTION=OFF 跳过。
  - 产物：libmessaging-menu.so（SHARED）+ 可执行 ayatana-indicator-messages-service
    （安装到 libexec/ayatana-indicator-messages，GNUInstallDirs 在 OHOS 上
    LIBEXECDIR 取默认 bin）。
  - 上游 tests/ 依赖 GMock/GTEST/dbustest-1/gtk-doc 等，OHOS 不可用，
    ENABLE_TESTS=OFF（上游默认即 OFF）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class AyatanaindicatormessagesConan(ConanFile):
    name = "ayatana-indicator-messages"
    version = "24.5.2"
    description = "Ayatana System Indicator — Messages：消息菜单系统指示器服务（messaging menu）"
    license = "GPL-3.0"
    homepage = "https://github.com/AyatanaIndicators/ayatana-indicator-messages"
    url = "https://github.com/AyatanaIndicators/ayatana-indicator-messages"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 顶层 CMakeLists pkg_check_modules(PROJECT_DEPS REQUIRED glib-2.0 gio-unix-2.0)
        self.requires("glib/2.88.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_unix_pkg_config()
        tc = CMakeToolchain(self)
        # accountsservice：OHOS 无此守护进程/库，裁剪（0001/0002 补丁配套）
        tc.variables["ENABLE_ACCOUNTS_SERVICE"] = "OFF"
        # data//po/（GSettings/Intltool CMake 模块缺失）、doc/（gtk-doc 缺失）跳过
        tc.variables["SKIP_DATA_PO"] = "ON"
        tc.variables["SKIP_DOC"] = "ON"
        # libmessaging-menu 的 gir/typelib/vapi：OHOS 无 GObjectIntrospection/Vala 工具链
        tc.variables["ENABLE_INTROSPECTION"] = "OFF"
        # 上游测试依赖 GMock/GTEST/dbustest-1，OHOS 不可用（上游默认 OFF）
        tc.variables["ENABLE_TESTS"] = "OFF"
        tc.variables["ENABLE_WERROR"] = "OFF"
        # OHOS SDK 的 /data/service/hnp/bin/gdbus-codegen 是坏条目（shebang
        # #!/usr/bin/python3 指向不存在的解释器，执行即 "No such file or directory" /
        # make Error 126）。上游 cmake/GdbusCodegen.cmake 用
        # find_program(GDBUS_CODEGEN gdbus-codegen) 从 PATH 定位，命中该坏条目，
        # 导致 indicator-messages-service.h/c 生成步失败。glib 包内自带可用
        # gdbus-codegen（#!/usr/bin/env python3）。find_program 优先查询
        # CMAKE_PROGRAM_PATH（官方搜索顺序先于 PATH），把 glib bin 钉死为解析结果，
        # 避免命中 SDK 坏条目（ayatana-indicator-session/gtk4 同款思路）。
        glib_dep = self.dependencies["glib"]
        glib_bin = None
        if glib_dep and glib_dep.package_folder:
            glib_bin = os.path.join(glib_dep.package_folder, "bin")
            cur_path = tc.variables.get("CMAKE_PROGRAM_PATH")
            tc.variables["CMAKE_PROGRAM_PATH"] = (
                glib_bin + (";" + cur_path if cur_path else "")
            )
            # E267: glib 静态库的 pkg-config Libs.private 链式展开出 -lintl/-lffi，
            # 库名会被 OHOS 工具链系统同名库抢占（符号 intl_*/ffi_* vs
            # g_libintl_*）→ ld.lld: undefined symbol: g_libintl_*（CI #48779，
            # 与 libkylin-ai-system-private 同根因）。0005 补丁在
            # PROJECT_DEPS_LIBRARIES 中把库名替换为 glib 包内绝对路径，
            # 此处注入（glib 包内自带 libintl.a/libffi.a）。
            intl_lib = os.path.join(glib_dep.package_folder, "lib", "libintl.a")
            ffi_lib = os.path.join(glib_dep.package_folder, "lib", "libffi.a")
            if os.path.isfile(intl_lib) and os.path.isfile(ffi_lib):
                tc.variables["INTL_LIB_ABS"] = intl_lib.replace(os.sep, "/")
                tc.variables["FFI_LIB_ABS"] = ffi_lib.replace(os.sep, "/")
            else:
                raise SystemExit(
                    "FAIL: glib package lacks libintl.a/libffi.a for absolute-path "
                    "linking (0005 patch requires them): "
                    f"{intl_lib} / {ffi_lib}"
                )
        tc.generate()

        # E266: OHOS SDK 的 lld 链接器运行时依赖 libxml2.so.16，CI 沙箱默认
        # 库搜索路径找不到它 → 可执行文件链接步骤（静态库之后）静默失败。
        # 前置 SDK llvm/lib 到 LD_LIBRARY_PATH 让 lld 能加载正确的 libxml2。
        env = Environment()
        for lib_dir in glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"):
            if os.path.isfile(os.path.join(lib_dir, "libxml2.so.16")):
                env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                break
        if glib_bin:
            # 兜底：PATH 前置 glib bin，覆盖任何按裸名 gdbus-codegen 调用的自定义命令
            # （find_program 已由 CMAKE_PROGRAM_PATH 钉死，此处双保险）。
            env.prepend_path("PATH", glib_bin)
        env.vars(self).save_script("lld_fix")

    def _augment_glib_unix_pkg_config(self):
        # glib 配方 cpp_info 未声明 gio-unix-2.0 组件，PkgConfigDeps 不生成
        # 转发 gio-unix-2.0.pc（顶层 pkg_check_modules PROJECT_DEPS REQUIRED
        # 需要它）。从 glib 包内复制该 .pc 到 generators 目录并改写 prefix，
        # 使其 Cflags 指向 glib 包内头文件（与 ayatana-ido/display 同法）。
        glib_folder = self.dependencies["glib"].package_folder
        src = os.path.join(glib_folder, "lib", "pkgconfig", "gio-unix-2.0.pc")
        if not os.path.isfile(src):
            return
        dst = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        prefix = glib_folder.replace(os.sep, "/")
        content = open(src, encoding="utf-8").read()
        content = content.replace("prefix=/", f"prefix={prefix}")
        open(dst, "w", encoding="utf-8", newline="\n").write(content)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 产物为 service 可执行文件 + libmessaging-menu.so；cmake install 中
        # service 落到 ${prefix}/bin/ayatana-indicator-messages/（GNUInstallDirs
        # 在 OHOS 未知系统上 LIBEXECDIR 取默认 bin），共享库落到 lib/。
        self.cpp_info.bindirs = ["bin/ayatana-indicator-messages"]
        self.cpp_info.libs = ["messaging-menu"]
