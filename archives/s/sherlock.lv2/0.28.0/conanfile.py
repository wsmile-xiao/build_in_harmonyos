#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, copy
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class SherlockLv2Conan(ConanFile):
    name = "sherlock.lv2"
    version = "0.28.0"
    description = "Investigative LV2 plugin bundle（Atom/MIDI/OSC Inspector 插件）"
    license = "Artistic-2.0"
    homepage = "https://www.ventosus.ch/sherlock.lv2/"
    url = "https://git.ventosus.ch/sherlock.lv2"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # library 类型必须声明 shared 选项（conan 2 校验，否则报
    # "Package type is 'library', but no 'shared' option declared"——
    # cattle 同款问题先例）；LV2 插件为共享模块（.so），默认静态偏好
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # 导出 patches/ 目录（apply_conandata_patches 需要；multitail 教训）
    exports_sources = "patches/*"

    def requirements(self):
        # sherlock.lv2 的 DSP 插件（sherlock.so）仅依赖 LV2（>=1.14.0）。
        # sratom 只被 UI 模块（sherlock_nk 等 *_nk.c）使用，而 UI 模块已由
        # 0001-disable-ui.patch 禁用（OHOS 无 GL/X11）；故不声明 sratom 依赖，
        # 缩短依赖链并避免 CI 探测未发布的 sratom/0.6.22-git 失败（L0i）
        self.requires("lv2/1.18.11-git")

    def layout(self):
        basic_layout(self)

    def generate(self):
        # PkgConfigDeps：为依赖（lv2）生成 .pc 到 generators 目录，
        # meson 经 pkg_config_path 找到 lv2 依赖（sherlock 无此则
        # "Dependency lv2 not found"）
        pcd = PkgConfigDeps(self)
        pcd.generate()
        tc = MesonToolchain(self)
        # meson 安装到 lib/lv2/sherlock.lv2（插件 bundle 目录）
        tc.project_options["lv2libdir"] = "lib/lv2"
        tc.generate()
        # 本地验证用：OHOS 沙箱 subprocess 裸命令 clang 查找失败
        # （sord 先例注入 ar 绝对路径），此处注入 clang/clang++ 绝对路径
        import shutil
        clang_path = shutil.which("clang") or "/data/service/hnp/bin/clang"
        clangpp_path = shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        with open(native_file) as f:
            content = f.read()
        content = content.replace(
            "c = 'clang'",
            f"c = '{clang_path}'"
        ).replace(
            "cpp = 'clang++'",
            f"cpp = '{clangpp_path}'"
        )
        # sord 先例：注入 ar 绝对路径（meson 无法经 PATH 找到）
        ar_path = shutil.which("ar") or "/data/service/hnp/bin/ar"
        content = content.replace(
            "[binaries]\nc =",
            f"[binaries]\nar = '{ar_path}'\nc ="
        )
        with open(native_file, "w") as f:
            f.write(content)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 应用 conandata.yml 注册的补丁（0001-disable-ui：禁用 OpenGL GUI 模块，
        # OHOS 无 GL/X11——multitail 教训：必须显式调用才会应用）
        apply_conandata_patches(self)

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
