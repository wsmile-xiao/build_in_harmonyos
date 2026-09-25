#!/usr/bin/env python3
"""Conan recipe for libeis 1.6.0 — Meson.

libeis — Emulated Input **服务端**库（libei 项目的 server 半边）。freedesktop
输入仿真协议栈组件：合成器/远端桌面服务端用它发布 seat/device，并接受
libei 客户端的连接（Unix socket 协议，纯 POSIX，无内核输入子系统依赖）。

本包只交付 libeis.so（-Dlibeis=enabled -Dlibei=disabled）；客户端 libei.so
与 portal 助手 liboeffis 由各自任务处理（同族先例 archives/l/libei/1.5.0）。

适配要点：
- 核心库零外部依赖：meson 对 libxkbcommon/libevdev/epoll-shim/sd-bus 全部
  走 `required: false`（仅在 tools/ 与 liboeffis 里用到），OHOS 上这些探测
  落空不影响 libeis 本体
- -Dlibei=disabled -Dliboeffis=disabled：客户端库与 DBus portal 助手裁剪
  （liboeffis 依赖 sd-bus，OHOS 无 libsystemd/libelogind/basu）
- -Dtests=auto：CI worker 无 pytest/structlog 时 meson 自动降级为只跑 C
  测试（1.6.0 的 test/meson.build 用 required: get_option('tests') 门控
  python 探测，feature=auto 即优雅跳过，无需源码补丁）
- 测试基建适配（3 个补丁，全部只作用于测试/构建校验目标）：
  0001 musl tmpfile() 硬编码只读 /tmp → $TMPDIR 唯一文件（立即 unlink）
  0002 munit wrap-git 子项目 CI 离线不可拉取 → vendor 进 subprojects/
  0003 上游 test-build-libeis 硬编码 -Werror 与 OHOS clang wrapper 注入的
       -Wl,--code-sign、-Wextra 的 unused argc/argv 相撞 → 仅降级这两个告警
- 上游测试：meson test（unit-tests-utils 36 + unit-tests-eis 7 + dtdcheck 1
  = 44 原子用例，全部在 build() 内真实执行）
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibeisConan(ConanFile):
    name = "libeis"
    version = "1.6.0"
    description = "Emulated Input server library (libeis) from the libei project"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/libinput/libei"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_tmpdir()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        # 本包只交付服务端库：客户端 libei 与 portal 助手 liboeffis 裁剪
        # （liboeffis 需 sd-bus，OHOS 无 libsystemd/libelogind/basu）
        tc.project_options["libeis"] = "enabled"
        tc.project_options["libei"] = "disabled"
        tc.project_options["liboeffis"] = "disabled"
        # tests=auto：pytest/structlog 缺失时 meson 自动降级为仅 C 测试
        # （munit 已 vendor 进 subprojects/munit/，CI 离线可跑）
        tc.project_options["tests"] = "auto"
        tc.project_options["documentation"] = "[]"
        tc.generate()
        self._inject_native_file_ar()
        # OHOS 沙箱：pip-global 的 meson 在 HarmonyOS 上 ninja 探测失败
        # （/data/service/hnp/bin/ninja 依赖 /system/lib64/libc++_shared.so，
        # 默认 LD_LIBRARY_PATH 含带空格脏路径项）——前置干净 /system/lib64，
        # 并让用户 site-packages 优先，使 wrapper python3 导入可用的 meson。
        import site

        user_site = site.getusersitepackages()
        env = Environment()
        if os.path.isdir(user_site):
            env.prepend_path("PYTHONPATH", user_site)
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.vars(self, scope="build").save_script("conanbuild_pyenv")

    def build(self):
        self._ensure_tmpdir()
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # 上游测试在 build() 中真实执行（AGENTS §10）
        self._run_upstream_tests(meson)

    def package(self):
        Meson(self).install()
        if self.options.shared and self.settings.os == "OHOS":
            self._create_shared_lib_aliases()

    def package_info(self):
        # libeis.so —— 服务端库；公共头 include/libei-1.0/libeis.h
        self.cpp_info.libs = ["eis"]
        self.cpp_info.includedirs = ["include/libei-1.0"]
        self.cpp_info.set_property("pkg_config_name", "libeis-1.0")
        self.cpp_info.set_property("cmake_file_name", "libeis")
        self.cpp_info.set_property("cmake_target_name", "libeis::libeis")

    # ── Helper methods ──────────────────────────────────────────

    def _ensure_tmpdir(self):
        """OHOS: /tmp 只读（E002），显式落到可写 TMPDIR。"""
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp"
        )
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _inject_native_file_ar(self):
        """只在 toolchain 文件没有 ar 条目、且本机确有可用 ar 时才补。

        同族 1.5.0 配方无条件注入 `shutil.which("ar") or
        /data/service/hnp/bin/llvm-ar`；conan 构建环境里 which 取不到 ar 时
        会把 profile 里已经正确的 ar 路径覆盖成不存在的 /data/service/... ，
        meson 便以 `Unknown linker(s)` 在 project() 处直接失败。
        """
        import re
        import shutil

        native_file = self.generators_folder + "/conan_meson_native.ini"
        if not os.path.isfile(native_file):
            return
        with open(native_file) as f:
            content = f.read()
        if re.search(r"^ar\s*=", content, re.M):
            return  # profile 已声明，尊重它
        ar_path = shutil.which("llvm-ar") or shutil.which("ar")
        if not ar_path:
            return
        content = content.replace(
            "[binaries]\nc =",
            f"[binaries]\nar = '{ar_path}'\nc =",
        )
        with open(native_file, "w") as f:
            f.write(content)

    def _run_upstream_tests(self, meson):
        """跑上游 meson test。

        conan MesonToolchain 对 OHOS 走 native 配置（host_machine.system
        =HarmonyOS），因此测试二进制可在本机构建并执行；meson.test() 非零
        退出即构建失败（真实门禁，不做 try/except 放行）。
        """
        tmpdir = os.environ.get("TMPDIR", os.path.join(os.path.expanduser("~"), "tmp"))
        runtime_dir = os.path.join(tmpdir, "libeis-xdg")
        os.makedirs(runtime_dir, exist_ok=True)
        env = Environment()
        env.define("XDG_RUNTIME_DIR", runtime_dir)
        env.define("TMPDIR", tmpdir)
        with env.vars(self, scope="build").apply():
            meson.test()

    def _create_shared_lib_aliases(self):
        """确保 libeis.so 链接别名存在（HMDFS 安全）。"""
        libdir = os.path.join(self.package_folder, "lib")
        base = "eis"
        src = os.path.join(libdir, f"lib{base}.so.{self.version}")
        mid = os.path.join(libdir, f"lib{base}.so.1")
        dst = os.path.join(libdir, f"lib{base}.so")
        if os.path.exists(src) and not os.path.exists(mid):
            os.symlink(src, mid)
        if os.path.exists(mid) and not os.path.exists(dst):
            os.symlink(mid, dst)
