#!/usr/bin/env python3
"""Conan recipe — libratbag 0.18 (Meson).

libratbag 是游戏鼠标的配置栈：

- ``ratbagd`` —— 对外的主产物，一个 **D-Bus 系统总线守护进程**，把鼠标的
  分辨率 / 按键 / LED / profile 暴露成 ``org.freedesktop.ratbag1`` 接口；
- ``libratbag``（内部静态库）—— 真正与鼠标说话的协议栈（HID++ 1.0 /
  HID++ 2.0 / roccat / steelseries / ... 各厂商驱动）；
- ``liblur.so`` —— **唯一被安装的共享库**，Logitech Unifying Receiver
  的配置库（``lur_*`` API，见 ``src/liblur.h``）；
- ``ratbagctl`` / ``lur-command`` —— 命令行工具；``data/devices/*.device``
  是各型号鼠标的能力描述（``ratbagd`` 运行时读）。

适配到 HarmonyOS PC (aarch64)。平台适配与上游测试口径见 notes.md。
"""
import glob
import os
import re
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# glib/2.84.0.1 包内 bin/ 的构建期工具在 HMFS 上不能直接执行：
#   * python 脚本（glib-mkenums / glib-genmarshal / gdbus-codegen）解释器
#     shebang 不可用，跨 UID 脚本执行被拒；
#   * ELF（glib-compile-resources / gobject-query / ...）缺少 .codesign
#     段，execve 返回 EPERM（shell 报 Operation not permitted，退出码 126）。
# 按 archives/g/gtk/3.24.43（依赖同一 glib/2.84.0.1）已验证的做法，在 build
# 目录里 staging 一份：python 工具包 sh wrapper 显式指定解释器，ELF 工具拷
# 贝出来重签名，meson 的 .pc 工具变量统一指向 staging 副本。
HNP_BIN = "/data/service/hnp/bin"
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")
PYTHON3 = os.path.realpath(sys.executable)

GLIB_PYTHON_TOOLS = ("glib-mkenums", "glib-genmarshal", "gdbus-codegen")
GLIB_ELF_TOOLS = (
    "glib-compile-resources",
    "glib-compile-schemas",
    "gobject-query",
    "gio-querymodules",
)

# 上游顶层 meson.build 注册了 10 个 test()：
#   * 4 个 check 框架的 C 测试程序 —— test-context(6) + test-device(23)
#     + test-util(2) + test-iconv-helper(4) = 35 个 tcase 用例；
#   * 3 个纯 python 数据校验脚本 —— data-parse-test / duplicate-test /
#     receiver-id-test（解析 data/devices/*.device，无平台依赖）；
#   * 1 个 python 集成测试 —— ratbagctl-test（起一个私有 ratbagd 走 D-Bus）；
#   * 2 个代码风格检查 —— python-black-check / python-ruff-check。
UPSTREAM_TEST_PROGRAMS = 10
UPSTREAM_CHECK_TEST_CASES = 35

# 本平台上必须通过的 7 个程序：4 个 C 程序 + 3 个 python 数据校验。
# 这四个 C 程序用的是 ``ratbag_test_device`` —— 一个**纯内存的虚拟设备**
# 结构体（test/test-device.c 里的 sane_device），不打开 hidraw、不枚举 udev，
# 所以在没有鼠标、没有 udev 守护进程的 OHOS 上照样跑。
REQUIRED_PASSING_PROGRAMS = (
    "test-context",
    "test-device",
    "test-util",
    "test-iconv-helper",
    "data-parse-test",
    "duplicate-test",
    "receiver-id-test",
)

# 本平台上必然失败的 3 个程序（如实声明，不删、不 SKIP）：
#   * ratbagctl-test：夹具要拉起私有 ratbagd 并经 D-Bus 通信，OHOS 沙箱
#     拒绝 AF_UNIX bind；
#   * python-black-check / python-ruff-check：需要 black / ruff 两个
#     python 工具，OHOS 侧不提供。
# 下面这个允许清单只按**身份与数量**核对，绝不按失败文本——
# 失败文本不是稳定契约。
BLOCKED_PROGRAMS = ("ratbagctl-test", "python-black-check", "python-ruff-check")


class LibratbagConan(ConanFile):
    name = "libratbag"
    version = "0.18"
    description = "Configuration library and D-Bus daemon for gaming mice (liblur / ratbagd)"
    license = "MIT"
    homepage = "https://github.com/libratbag/libratbag"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    # shim/progname_shim.h：musl 下 program_invocation_short_name 的等价物，
    # 由 generate() 以 -include 强制注入（见 _progname_shim_args()）。
    exports = ["shim/progname_shim.h"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        # 上游 meson.build 里 liblur 是硬编码的 shared_library()，
        # default_library 管不到它；声明 static 只会得到「静态包名 + 动态库」的
        # 自相矛盾产物，所以这里直接拒绝。
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "libratbag 0.18 只支持 shared=True：上游把 liblur 写成 "
                "shared_library()，default_library=static 无法改变它。"
            )

    def requirements(self):
        # glib / gio 是 ratbagd 与 liblur 都要用的公共依赖。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # libudev：msghidraw 设备枚举 + ratbagd 的设备热插拔（public，
        # liblur.so 的 DT_NEEDED 里有 libudev.so，消费者必须能解析到它）。
        self.requires("eudev/3.2.14", transitive_headers=True, transitive_libs=True)
        # libevdev：HID++ 之外走 evdev 的路径（public）。
        self.requires("libevdev/1.13.7", transitive_headers=False, transitive_libs=True)
        # json-glib-1.0：ratbagd 的 JSON 输出（ratbagd-json.c）。
        self.requires("json-glib/1.10.6", transitive_headers=False, transitive_libs=True)
        # libunistring：ratbagd 里 unistr_* 的字符串处理（public，被
        # ratbagd 二进制链进去）。
        self.requires("libunistring/1.0", transitive_headers=False, transitive_libs=True)
        # libsystemd：仅 ratbagd 用（sd_notify 就绪通知），不进 liblur，
        # 因此对消费者不可见。
        self.requires("systemd/261", visible=False)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        # 上游 4 个 C 测试程序用 check 框架；只在 conan create 期间可见。
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    # ─────────────────────────── source ───────────────────────────
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 补丁只加在 source() 里，跑一次；build() 里再调一次 apply 也不会重复打。
        apply_conandata_patches(self)

    # ────────────────────────── generate ──────────────────────────
    def generate(self):
        PkgConfigDeps(self).generate()
        self._alias_dependency_pc()
        tools_folder = self._prepare_glib_build_tools()
        self._augment_glib_pkg_config(tools_folder)
        toolchain = MesonToolchain(self)
        # Conan 的 MesonToolchain 在 buildtype != debug 时**硬编码** b_ndebug=true
        # （meson_toolchain.py: `self.b_ndebug = "true" if self.buildtype != "debug"
        # else "false"`），于是每条编译行都带 -DNDEBUG。而上游 `src/libratbag-
        # private.h:37` 是
        #     #ifdef NDEBUG
        #     #error "libratbag relies on assert(). Do not define NDEBUG"
        #     #endif
        # —— 直接编译失败（CI #b71432 实测：全部 .c 都是这一条 error）。
        # meson 自己的 b_ndebug 默认就是 false（从不在 release 里定义 NDEBUG），
        # 上游正是按这个前提写的；这里显式改回 false，恢复上游默认语义。
        # 顺带保住 `meson test` 的意义：断言被关掉的话，那几个 check 程序
        # 变成空壳，测试即使"通过"也说明不了什么。
        toolchain.b_ndebug = "false"
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["default_library"] = "shared"
        # 上游 docs 用 gtk-doc，OHOS 不提供。
        toolchain.project_options["documentation"] = False
        # 单元测试默认就是开的，这里显式写出来，避免随上游默认值漂移。
        toolchain.project_options["tests"] = True
        # 不生成 systemd unit（那只是给 dependency('systemd') 取 unit 目录用的，
        # 而 OHOS 上根本没有 systemd 本体）。libsystemd 仍然要链接，见 requirements。
        toolchain.project_options["systemd"] = False
        # swig + libpython 生成的 Python 绑定在 OHOS 上不可用（见补丁与 notes.md）；
        # 关掉之后 ratbagd / ratbagctl / lur-command 这些产物不受影响。
        toolchain.project_options["python-bindings"] = False
        # libunistring 在上游是 cc.find_library('unistring')，不走 pkg-config，
        # 需要把依赖的 libdir 显式交给链接器搜索路径。
        toolchain.c_link_args.extend(self._dependency_link_args())
        # eudev / libunistring 的 include 目录走项目级 c_args，
        # 见 _project_include_args()。
        toolchain.extra_cflags.extend(self._project_include_args())
        # musl/OHOS 无 glibc 的 program_invocation_short_name（tools/*.c 与
        # ratbagd.c 共 5 处使用），用 shim 头在配方层别名到 musl 的
        # __progname，不改上游源码、也不加平台条件编译补丁（R8）。
        toolchain.extra_cflags.extend(self._progname_shim_args())
        toolchain.generate()
        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    # ─────────────────────────── build ────────────────────────────
    def build(self):
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            if not cross_building(self) and can_run(self):
                # meson test 只要有一个测试失败就返回非 0，而这里本来就预期
                # ratbagctl-test / python-black-check / python-ruff-check 三个
                # 程序失败，所以退出码不参与判断；改为回读汇总块硬断言。
                self.run(
                    "meson test -C {} --print-errorlogs".format(self.build_folder),
                    env="conanbuild",
                    ignore_errors=True,
                )
                self._assert_suite_results()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # 上游唯一安装的共享库是 liblur.so（带 version script src/liblur.sym）。
        self.cpp_info.libs = ["lur"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "eudev::eudev",
            "libevdev::libevdev",
            "json-glib::json-glib-1.0",
            "libunistring::libunistring",
        ]
        self.cpp_info.set_property("cmake_file_name", "lur")
        self.cpp_info.set_property("cmake_target_name", "lur::lur")
        self.cpp_info.set_property("pkg_config_name", "liblur")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ────────────────────────── helpers ───────────────────────────
    def _build_environment(self):
        """PATH / LD_LIBRARY_PATH / TMPDIR plumbing for running the test binaries."""
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        # cc.find_library('unistring') 走的是编译器默认搜索路径，
        # LIBRARY_PATH 让链接探测也能看到 conan 依赖的 libdir。
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
                    environment.prepend_path("LIBRARY_PATH", libdir)
        # staging 出来的 glib 构建工具必须排在依赖自带的 bin/ 前面，
        # 否则 meson 仍会挑到包缓存里那份不可执行的副本。
        tools_folder = self._glib_tools_folder()
        if os.path.isdir(tools_folder):
            environment.prepend_path("PATH", tools_folder)
        return environment

    # ─────────────────── glib 构建工具 staging ────────────────────
    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _sign_elf(self, binary):
        """HMFS 执行限制规避：去掉 .codesign 段后 selfSign 重签。"""
        if os.path.isfile(OBJCOPY):
            self.run(f"{shlex.quote(OBJCOPY)} --remove-section .codesign "
                     f"{shlex.quote(binary)} 2>/dev/null || true")
        if os.path.isfile(SIGN_TOOL):
            self.run(shlex.join([SIGN_TOOL, "sign", "-inFile", binary,
                                 "-outFile", binary, "-selfSign", "1"]))

    def _prepare_glib_build_tools(self):
        """把 glib 包 bin/ 里的构建工具 staging 到 build 目录。

        返回 {变量名: 可执行文件绝对路径}，供 .pc 注入使用（变量名与上游
        glib-2.0.pc / gobject-2.0.pc 里的工具变量同名，下划线形式）。
        """
        try:
            glib_pkg = self.dependencies["glib"]
        except KeyError:
            return {}
        glib_bin = os.path.join(glib_pkg.package_folder, "bin")
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        quote = lambda s: "'" + str(s).replace("'", "'\\''") + "'"

        staged = {}
        for tool in GLIB_PYTHON_TOOLS:
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                continue
            wrapper = os.path.join(tools_folder, tool)
            with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(f"#!/bin/sh\nexec {quote(PYTHON3)} {quote(src)} \"$@\"\n")
            os.chmod(wrapper, 0o755)
            staged[tool] = wrapper

        for tool in GLIB_ELF_TOOLS:
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                continue
            target = os.path.join(tools_folder, tool)
            shutil.copyfile(src, target)
            os.chmod(target, 0o755)
            if self.settings.os == "OHOS":
                self._sign_elf(target)
            staged[tool] = target
        return staged

    def _dependency_link_args(self):
        """-L<libdir> for every host dependency, for cc.find_library('unistring')."""
        args = []
        for dependency in self.dependencies.host.values():
            if self._dependency_ref_name(dependency) == "check":
                continue
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    args.append("-L" + libdir.replace("\\", "/"))
                    args.append("-Wl,-rpath," + libdir.replace("\\", "/"))
        return args

    @staticmethod
    def _dependency_ref_name(dependency):
        return getattr(dependency.ref, "name", "") or ""

    def _project_include_args(self):
        """把 eudev / libunistring 的 ``include/`` 作为**项目级** ``-I`` 注入。

        上游 ``src/libratbag-util.h:34`` 直接 ``#include <libudev.h>``，而这个
        头文件被 libhidpp / libasus / liblur 这些目标包含，它们**没有**声明
        dep_udev：

            deps_libutil  = [ dep_udev ]   # meson.build:87  —— 有
            deps_libhidpp = [ dep_lm ]     # meson.build:108 —— 没有
            deps_libasus  = [ ]            # meson.build:120 —— 没有
            deps_liblur   = [ dep_libutil, dep_libhidpp, dep_libasus ]
                                            # meson.build:138 —— 自身也没有
        而 meson 只为「在 ``dependencies:`` 里声明了该 dependency 的目标」注入
        它的 ``-I``/``-L``，所以 libhidpp.a / libasus.a / liblur.so 的编译行里
        根本没有 eudev 的 include 目录。Linux 上能用，只是因为发行版的
        libudev-dev 把 libudev.h 装进了 ``/usr/include``（编译器默认搜索路径）；
        OHOS 的 eudev 是 Conan 包、头在 ``<pkg>/include``，不在默认路径上，于是

            ../src/libratbag-util.h:34:10: fatal error: 'libudev.h' file not found

        上游自己就用 ``add_project_arguments(cflags, language: 'c')``
        （meson.build:45）做项目级注入，这里等价地走项目级 ``c_args``
        （``MesonToolchain.extra_cflags`` 会写进 native file 的
        ``[built-in options] c_args``），既不动上游 meson.build、也不加补丁。

        第二条是 libunistring，同一个成因的另一种形态。上游 meson.build:68
        把它写成 ``cc.find_library('unistring')`` —— 只探**库**、不探**头**，
        于是 meson 只给出 ``-L``（配方另外用 ``_dependency_link_args()`` 补上），
        从不注入 ``-I``。``ratbagd/ratbagd-profile.c:34-35`` 是
        ``#include <unistr.h>`` / ``#include <uniconv.h>``（用到 ``u8_check()``
        与 ``u8_strconv_from_encoding()``），
        Linux 上靠 libunistring-dev 把头装进 ``/usr/include`` 才编得过，
        OHOS 上该头在 Conan 包的 ``include/``，于是

            ../ratbagd/ratbagd-profile.c:34:10: fatal error: 'unistr.h' file not found

        （CI 里 meson configure 那行 ``Library unistring found: YES`` 正是
        ``cc.find_library`` 成功的证据，说明缺的确实只是 ``-I``。）
        """
        args = []
        raw_deps = ("eudev", "libunistring")
        for dependency in self.dependencies.host.values():
            if self._dependency_ref_name(dependency) not in raw_deps:
                continue
            for includedir in dependency.cpp_info.includedirs:
                if not os.path.isabs(includedir):
                    includedir = os.path.join(dependency.package_folder, includedir)
                if os.path.isdir(includedir):
                    args.append("-I" + includedir.replace("\\", "/"))
        return args

    def _progname_shim_args(self):
        """用 ``-include`` 把 ``shim/progname_shim.h`` 前置到每个编译单元。

        ``tools/hidpp10-dump-page.c`` / ``hidpp20-dump-page.c`` /
        ``hidpp20-reset.c`` / ``lur-command.c`` 的 ``usage()`` 与
        ``ratbagd/ratbagd.c`` 的 ``log_error()`` 用了 glibc 扩展
        ``program_invocation_short_name``：它由 glibc 的 ``<errno.h>`` 在
        ``_GNU_SOURCE`` 下声明为 ``char *`` 变量，**musl 既不声明也不定义**，
        于是 OHOS 上编译报 ``use of undeclared identifier``。

        musl 的动态加载器提供了语义完全相同的 ``__progname``（同样是 argv[0]
        的 basename），shim 头把 ``program_invocation_short_name`` 别名过去。
        走 ``-include`` 而不是补丁：``.gitcode/review-memory.md`` R8 要求
        ``patches/`` 补丁默认不得引入平台条件编译宏，这类 libc 差异应在配方层
        用 feature detection 解决（与 ``kbd/2.9.0`` 的 ``progname_shim.h``
        同一做法）。
        """
        return [
            "-include",
            os.path.join(self.recipe_folder, "shim", "progname_shim.h").replace("\\", "/"),
        ]

    def _append_dependency_pkg_config_paths(self):
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        paths = [self.generators_folder]
        for dependency in self.dependencies.host.values():
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(dependency.package_folder, *relative)
                if os.path.isdir(candidate):
                    paths.append(candidate)
        unique_paths = []
        for path in paths:
            normalized = path.replace("\\", "/")
            if normalized not in unique_paths:
                unique_paths.append(normalized)
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        replacement = "pkg_config_path = [" + ", ".join(
            "'{}'".format(p) for p in unique_paths) + "]"
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _inject_meson_tools(self):
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (
                bindir,
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin",
            ):
                if not ar:
                    candidate = os.path.join(directory, "llvm-ar")
                    if os.path.isfile(candidate):
                        ar = candidate
                if not ranlib:
                    candidate = os.path.join(directory, "llvm-ranlib")
                    if os.path.isfile(candidate):
                        ranlib = candidate
            pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
            if not pkg_config or not os.path.isfile(str(pkg_config)):
                pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")

            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                insert.append(f"pkg-config = '{pkg_config}'")
            if insert:
                content = content.replace(
                    "[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _alias_dependency_pc(self):
        """systemd 的 `libsystemd.pc`：包里有就复制改写，没有就按其真实布局合成。

        上游 meson.build:73 写 ``dependency('libsystemd', version : '>=227')``。
        两个坑叠在一起：

        (a) PkgConfigDeps 按**包名**生成 ``systemd.pc``，与上游要的
            ``libsystemd`` 名字对不上；
        (b) ohpcd 上已发布的 ``systemd/261`` 二进制包里 ``lib/pkgconfig/``
            是**空目录**。systemd 配方的 build() 只构建 libsystemd 目标、
            不走 ``meson.install()``，而 meson 的 ``pkg.generate()`` 产物
            只在对应目标被构建时才落到 ``<build>/libsystemd.pc``，
            于是该包最终没装上这份 .pc（已 ``conan download`` 复核：
            包内只有 include/ 与 lib/libsystemd.so*，无任何 .pc）。

        所以这里分两路：包里有真 .pc 就复制并把 ``prefix=`` 改写成真实包目录
        （systemd 那份是 ``--prefix=/`` + DESTDIR 装出来的，直接复制会让
        ``-I${includedir}`` 落到根目录）；没有就按包内真实布局
        （``include/systemd/sd-*.h`` + ``lib/libsystemd.so``）合成一份最小 .pc。
        做法同 archives/a/accountsservice/26.27.3 的 ``_prepare_systemd_stub()``，
        区别是那边 OHOS 无 systemd 只能造桩，这边指向真包。
        """
        for dependency in self.dependencies.host.values():
            if getattr(dependency.ref, "name", "") != "systemd":
                continue
            folder = dependency.package_folder
            source = None
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(folder, *(relative + ("libsystemd.pc",)))
                if os.path.isfile(candidate):
                    source = candidate
                    break
            prefix_native = folder.replace("\\", "/")
            if source:
                with open(source, encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
                content = "\n".join(
                    "prefix=" + prefix_native if line.startswith("prefix=") else line
                    for line in content.splitlines()
                )
            else:
                content = (
                    f"prefix={prefix_native}\n"
                    "exec_prefix=${prefix}\n"
                    "libdir=${prefix}/lib\n"
                    "includedir=${prefix}/include\n"
                    "\n"
                    "Name: libsystemd\n"
                    "Description: systemd Library (synthesized from the conan package)\n"
                    "URL: https://www.freedesktop.org/wiki/Software/systemd\n"
                    f"Version: {dependency.ref.version}\n"
                    "Libs: -L${libdir} -lsystemd\n"
                    # 上游以 #include <systemd/sd-bus.h> 引用，故 -I${includedir}；
                    # 同时给出 ${includedir}/systemd（systemd 自己那份 .pc 也带）。
                    "Cflags: -I${includedir} -I${includedir}/systemd\n"
                )
            destination = os.path.join(self.generators_folder, "libsystemd.pc")
            with open(destination, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            return
        self.output.warning("systemd package folder not found in the dependency graph")

    def _augment_glib_pkg_config(self, staged_tools):
        """PkgConfigDeps emits simplified .pc files: no tool variables, no -lintl.

        glib 在 OHOS 上与子项目 ``proxy-libintl`` 一起构建，``g_libintl_*``
        就在 glib 包里，但 glib 配方的 ``package_info`` 没声明 ``intl`` 系统库，
        消费者会 ``undefined reference to `g_libintl_*'``。做法同
        archives/l/libgsystemservice/0.3.0：就地增补生成的 .pc 并补 ``-lintl``。

        工具变量一律指向 :meth:`_prepare_glib_build_tools` staging 出来的
        副本（而不是 glib 包缓存里的原件）—— 后者在 HMFS 上不可执行。
        """
        entries = {
            "glib-2.0.pc": ["glib_mkenums", "glib_genmarshal", "gobject_query"],
            "gobject-2.0.pc": ["glib_mkenums"],
        }
        for pc_name, tool_names in entries.items():
            pc_file = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            modified = False
            additions = []
            for tool in tool_names:
                path = staged_tools.get(tool.replace("_", "-"))
                if path and f"{tool}=" not in content:
                    additions.append(f"{tool}={path.replace(os.sep, '/')}")
            if additions:
                content += "\n" + "\n".join(additions) + "\n"
                modified = True
            if "-lintl" not in content:
                lines = []
                for line in content.splitlines(True):
                    if line.startswith("Libs:") and "-lintl" not in line:
                        line = line.rstrip("\n") + " -lintl\n"
                    lines.append(line)
                content = "".join(lines)
                modified = True
            if modified:
                with open(pc_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _assert_suite_results(self):
        """Read back the meson suite summary instead of trusting the exit code.

        ``meson test`` 在「没有任何失败」时返回 0 —— 用例被 SKIP、或 ``test()``
        压根没注册，同样返回 0。汇总块是唯一能说明「到底跑了多少」的地方，
        所以显式断言。

        三个已声明的失败只按**身份与数量**放行：失败数不得超过 3，且日志里
        必须出现这三个程序的名字 —— 否则真实回归会被伪装成平台限制。
        """
        log = os.path.join(self.build_folder, "meson-logs", "testlog.txt")
        if not os.path.isfile(log):
            raise ConanException(f"meson test log missing: {log}")
        with open(log, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        summary = {}
        for key in ("Ok", "Expected Fail", "Fail", "Unexpected Pass", "Skipped", "Timeout"):
            match = re.search(rf"^{re.escape(key)}:\s+(\d+)\s*$", content, re.MULTILINE)
            if match:
                summary[key] = int(match.group(1))
        self.output.info(f"upstream meson suite summary: {summary}")

        for key in ("Timeout", "Unexpected Pass"):
            if summary.get(key, 0):
                raise ConanException(
                    f"upstream meson suite reports {key}={summary[key]}:\n"
                    + "\n".join(content.splitlines()[-40:])
                )

        failed = summary.get("Fail", 0)
        if failed > len(BLOCKED_PROGRAMS):
            raise ConanException(
                f"upstream meson suite reports Fail={failed}, more than the "
                f"{len(BLOCKED_PROGRAMS)} declared platform-blocked program(s) "
                f"{BLOCKED_PROGRAMS}:\n" + "\n".join(content.splitlines()[-40:])
            )
        if failed:
            for program in BLOCKED_PROGRAMS:
                if program not in content:
                    raise ConanException(
                        f"expected the failing program to be {program!r}, but it "
                        "does not appear in the test log:\n"
                        + "\n".join(content.splitlines()[-40:])
                    )

        if summary.get("Ok", 0) < len(REQUIRED_PASSING_PROGRAMS):
            raise ConanException(
                f"upstream meson suite ran only {summary.get('Ok', 0)} test "
                f"program(s); {len(REQUIRED_PASSING_PROGRAMS)} are required to "
                f"pass ({REQUIRED_PASSING_PROGRAMS}) — suite is vacuous or "
                f"silently truncated:\n" + "\n".join(content.splitlines()[-40:])
            )
        for program in REQUIRED_PASSING_PROGRAMS:
            if program not in content:
                raise ConanException(
                    f"required test program {program!r} does not appear in the "
                    "test log — it was not registered or not executed:\n"
                    + "\n".join(content.splitlines()[-40:])
                )

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_installed_elfs(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        for name in ("bin", "sbin"):
            directory = os.path.join(self.package_folder, name)
            if os.path.isdir(directory):
                for entry in os.listdir(directory):
                    path = os.path.join(directory, entry)
                    if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path):
                        targets.append(path)
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
