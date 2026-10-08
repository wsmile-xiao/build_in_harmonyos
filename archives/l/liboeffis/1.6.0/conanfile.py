#!/usr/bin/env python3
"""Conan recipe for liboeffis 1.6.0 — Meson.

liboeffis — XDG RemoteDesktop portal DBus 助手库（libei 项目的第三子组件）。
freedesktop 输入仿真协议栈组件：通过 DBus 与 XDG RemoteDesktop portal 通信，
获取 EIS socket fd，供 libei 客户端连接使用。

本包只交付 liboeffis.so（-Dliboeffis=enabled -Dlibei=disabled -Dlibeis=disabled）；
客户端 libei.so 与服务端 libeis.so 由各自任务处理（同族先例 archives/l/libei/1.5.0
与 archives/l/libeis/1.6.0）。

适配要点：
- meson 构建；-Dliboeffis=enabled 显式开启，依赖 sd-bus（systemd 261.1 提供）
- -Dlibei=disabled -Dlibeis=disabled：裁剪客户端与服务端库（各自独立任务）
- -Dtests=auto：CI worker 无 pytest/structlog/dbusmock 时 meson 自动降级为只跑 C 测试
  （munit 已 vendor 进 subprojects/，CI 离线可跑）
- systemd 261.1 在 ohpcd 已发布，但无 .pc 文件——手动创建使 meson 可解析
- OHOS musl 不跟随符号链接解析 DT_NEEDED → 摊平 systemd 库实体到 build 目录
- 测试基建适配（2 个补丁，全部只作用于测试/构建校验目标）：
  0001 musl tmpfile() 硬编码只读 /tmp → $TMPDIR 唯一文件（立即 unlink）
  0002 munit wrap-git 子项目 CI 离线不可拉取 → vendor 进 subprojects/

上游测试：meson test（unit-tests-oeffis 2 个 munit 用例 + oeffis-pytest 需 python
dbusmock，tests=auto 下不注册）。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LiboeffisConan(ConanFile):
    name = "liboeffis"
    version = "1.6.0"
    description = "XDG RemoteDesktop portal DBus helper library (liboeffis)"
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

    def requirements(self):
        # sd-bus provider: systemd 261.1 在 ohpcd 已发布
        self.requires("systemd/261.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_tmpdir()
        # systemd 261.1 在 ohpcd 已发布，但无 .pc 文件——手动创建使 meson
        # dependency('libsystemd') 可解析
        self._create_libsystemd_pc()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        # 本包只交付 portal 助手库：客户端 libei 与服务端 libeis 裁剪
        tc.project_options["liboeffis"] = "enabled"
        tc.project_options["libei"] = "disabled"
        tc.project_options["libeis"] = "disabled"
        # sd-bus-provider: 显式指定 libsystemd（systemd 261.1 提供）
        tc.project_options["sd-bus-provider"] = "libsystemd"
        # tests=auto：pytest/structlog/dbusmock 缺失时 meson 自动降级为仅 C 测试
        tc.project_options["tests"] = "auto"
        tc.project_options["documentation"] = "[]"
        tc.generate()
        self._inject_native_file_ar()
        # 注入 systemd pkgconfig 路径到 native file
        self._inject_pkgconfig_path()
        # OHOS 沙箱：pip-global 的 meson 在 HarmonyOS 上 ninja 探测失败
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
        # 注入 systemd pkgconfig 路径，使 meson dependency('libsystemd') 可解析
        systemd_ref = self.dependencies["systemd"]
        systemd_pc_dir = os.path.join(systemd_ref.package_folder, "lib", "pkgconfig")
        if os.path.isdir(systemd_pc_dir):
            os.environ["PKG_CONFIG_PATH"] = systemd_pc_dir + os.pathsep + os.environ.get("PKG_CONFIG_PATH", "")
        # OHOS musl 不跟随符号链接解析 DT_NEEDED，需摊平 systemd 库实体
        self._flatten_systemd_libs(systemd_ref.package_folder)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # 上游测试在 build() 中真实执行（AGENTS §10）
        self._run_upstream_tests(meson)

    def package(self):
        Meson(self).install()
        if self.options.shared and self.settings.os == "OHOS":
            self._restore_build_shared_libs()
            self._create_shared_lib_aliases()

    def package_info(self):
        # liboeffis.so —— portal 助手库；公共头 include/libei-1.0/liboeffis.h
        self.cpp_info.libs = ["oeffis"]
        self.cpp_info.includedirs = ["include"]
        # 传递 systemd 依赖给下游
        self.cpp_info.requires = ["systemd::systemd"]
        self.cpp_info.set_property("pkg_config_name", "liboeffis-1.0")
        self.cpp_info.set_property("cmake_file_name", "liboeffis")
        self.cpp_info.set_property("cmake_target_name", "liboeffis::liboeffis")

    # ── Helper methods ──────────────────────────────────────────

    def _create_libsystemd_pc(self):
        """systemd 261.1 在 ohpcd 已发布，但无 .pc 文件——手动创建使 meson
        dependency('libsystemd') 可解析。
        """
        systemd_ref = self.dependencies["systemd"]
        systemd_pkg = systemd_ref.package_folder
        if not systemd_pkg:
            return
        pc_dir = os.path.join(systemd_pkg, "lib", "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        pc_path = os.path.join(pc_dir, "libsystemd.pc")
        # 使用 build 目录下的摊平 libdir（OHOS musl 不跟随符号链接解析 DT_NEEDED）
        flat_libdir = os.path.join(self.build_folder, "systemd-libs")
        pc_content = f"""prefix={systemd_pkg}
libdir={flat_libdir}
includedir=${{prefix}}/include

Name: libsystemd
Description: systemd client library (sd-bus/sd-event/sd-daemon)
Version: 261.1
Libs: -L${{libdir}} -lsystemd
Cflags: -I${{includedir}}
"""
        with open(pc_path, "w") as f:
            f.write(pc_content)
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", pc_dir)
        env.vars(self, scope="build").save_script("conanbuild_pkgconfig")

    def _inject_pkgconfig_path(self):
        """注入 systemd pkgconfig 路径到 native file，使 meson 可找到 libsystemd。"""
        native_file = self.generators_folder + "/conan_meson_native.ini"
        if not os.path.isfile(native_file):
            return
        systemd_ref = self.dependencies["systemd"]
        systemd_pc_dir = os.path.join(systemd_ref.package_folder, "lib", "pkgconfig")
        if not os.path.isdir(systemd_pc_dir):
            return
        with open(native_file) as f:
            content = f.read()
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('pkg_config_path = '):
                old_value = line.split('=', 1)[1].strip().strip("'").strip('"')
                new_value = f"{systemd_pc_dir}:{old_value}"
                lines[i] = f"pkg_config_path = '{new_value}'"
                break
        with open(native_file, 'w') as f:
            f.write('\n'.join(lines))

    def _flatten_systemd_libs(self, systemd_pkg_folder):
        """OHOS musl 不跟随符号链接解析 DT_NEEDED，需摊平 systemd 库实体。"""
        import shutil
        src_libdir = os.path.join(systemd_pkg_folder, "lib")
        flat_libdir = os.path.join(self.build_folder, "systemd-libs")
        os.makedirs(flat_libdir, exist_ok=True)
        for name in ("libsystemd.so.0.44.0", "libsystemd.so.0", "libsystemd.so"):
            src = os.path.join(src_libdir, name)
            dst = os.path.join(flat_libdir, name)
            if os.path.islink(src) or not os.path.exists(dst):
                if os.path.islink(src):
                    real_src = os.path.realpath(src)
                    shutil.copy2(real_src, dst)
                else:
                    shutil.copy2(src, dst)

    def _ensure_tmpdir(self):
        """OHOS: /tmp 只读（E002），显式落到可写 TMPDIR。"""
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp"
        )
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _inject_native_file_ar(self):
        """只在 toolchain 文件没有 ar 条目、且本机确有可用 ar 时才补。"""
        import re
        import shutil
        native_file = self.generators_folder + "/conan_meson_native.ini"
        if not os.path.isfile(native_file):
            return
        with open(native_file) as f:
            content = f.read()
        if re.search(r"^ar\s*=", content, re.M):
            return
        ar_path = shutil.which("llvm-ar") or shutil.which("ar")
        if not ar_path:
            if os.path.isfile("/data/service/hnp/bin/ar"):
                ar_path = "/data/service/hnp/bin/ar"
        if not ar_path:
            return
        content = content.replace(
            "[binaries]\nc =",
            f"[binaries]\nar = '{ar_path}'\nc =",
        )
        with open(native_file, "w") as f:
            f.write(content)

    def _run_upstream_tests(self, meson):
        """跑上游 meson test。"""
        tmpdir = os.environ.get("TMPDIR", os.path.join(os.path.expanduser("~"), "tmp"))
        runtime_dir = os.path.join(tmpdir, "liboeffis-xdg")
        os.makedirs(runtime_dir, exist_ok=True)
        env = Environment()
        env.define("XDG_RUNTIME_DIR", runtime_dir)
        env.define("TMPDIR", tmpdir)
        with env.vars(self, scope="build").apply():
            meson.test()

    def _restore_build_shared_libs(self):
        """用构建目录产物覆盖 meson install 安装出的 .so。

        根因：meson install 的 depfixer 会重写 ELF 的 RUNPATH（把链接期写入的
        `$ORIGIN/../systemd-libs` 抹掉并填充占位字节）。在 OHOS 上，经该重写
        产出的共享对象无法被 musl 动态链接器加载：

            dlopen(liboeffis.so.1) -> Error loading shared library ...:
            Permission denied

        而构建目录中未经重写的同一对象可以正常 dlopen。因此这里直接以构建
        目录产物为准，保证交付的共享对象可被 OHOS musl 加载。
        """
        import shutil
        libdir = os.path.join(self.package_folder, "lib")
        target = os.path.join(libdir, f"liboeffis.so.{self.version}")
        if not os.path.exists(target):
            return
        src = None
        for root, _dirs, files in os.walk(self.build_folder):
            if f"liboeffis.so.{self.version}" in files:
                src = os.path.join(root, f"liboeffis.so.{self.version}")
                break
        if not src or os.path.abspath(src) == os.path.abspath(target):
            return
        shutil.copy2(src, target)
        os.chmod(target, 0o755)

    def _create_shared_lib_aliases(self):
        """确保 liboeffis.so 链接别名存在。
        
        OHOS musl 不跟随符号链接解析 DT_NEEDED，且 meson install
        生成的绝对路径符号链接在 test_package 中不可解析。
        直接复制实体文件而非依赖符号链接。
        """
        import shutil
        libdir = os.path.join(self.package_folder, "lib")
        base = "oeffis"
        real_lib = os.path.join(libdir, f"lib{base}.so.{self.version}")
        if not os.path.exists(real_lib):
            return
        # 摊平为实体文件（OHOS 安全）
        for name in (f"lib{base}.so.1", f"lib{base}.so"):
            dst = os.path.join(libdir, name)
            if os.path.islink(dst) or not os.path.exists(dst):
                if os.path.islink(dst):
                    os.remove(dst)
                shutil.copy2(real_lib, dst)
