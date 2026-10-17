#!/usr/bin/env python3
"""Conan recipe — gsl 2.7 (autotools, HarmonyOS PC / aarch64)

GNU Scientific Library 2.7。

上游源码包自带的 config.guess / config.sub 不识别 HarmonyOS，会在 configure
阶段报 "Invalid configuration ... " 或探测出错。解决方式是应用 patches/ 下的
两个平台识别补丁（conandata.yml 的 patches 段声明），
再用 --host=aarch64-unknown-linux-ohos 配置。
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import export_conandata_patches, get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GslConan(ConanFile):
    name = "gsl"
    version = "2.7"
    description = "The GNU Scientific Library (GSL) is a numerical library for C and C++"
    homepage = "https://www.gnu.org/software/gsl/"
    license = "GPL-3.0-or-later"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        # patches/ 必须随配方导出，否则在 conan 缓存里 apply_conandata_patches 找不到补丁
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass  # 无第三方依赖，只用 libc / libm

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess/config.sub 已被补丁教会识别 HarmonyOS。这里显式给出 OHOS 三元组。
        # 关于 R1「禁止 --build/--host」的豁免依据：补丁后的 config.guess 在 OHOS 上输出
        # 的就是 aarch64-unknown-linux-ohos，与 --host 取值相同 ⇒ host == build，configure
        # 判定 "checking whether we are cross compiling... no"，不会进入交叉编译分支去跳过
        # AC_RUN_IFELSE 运行时探测（W3 日志实测 cross_compiling=no）。
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        # 修复 1：conan 生成的 conanbuild.sh 把 CONFIG_SHELL 指向 hnp 的 bash，而该 bash
        # 在 HMDFS 上传 stdin（`cat -`）会失败，config.status 拿到的 conftest.c 被截断，
        # configure 误报 "C compiler cannot create executables"。这里追加在 buildenv 之后
        # 覆盖它（只在生成脚本尾部追加才生效）。
        _conanbuild = os.path.join(self.build_folder, "conan", "conanbuild.sh")
        if os.path.isfile(_conanbuild):
            with open(_conanbuild, "a", encoding="utf-8") as f:
                f.write("\nexport CONFIG_SHELL=/system/bin/sh\nexport SHELL=/system/bin/sh\n")

        apply_conandata_patches(self)

        # 修复 2：configure/config.status 用 `umask 077 && mktemp -d` 建 conf 临时目录，
        # 在 HMDFS 上会建出 drwx--S--- (2700+setgid)，写入进程 UID 映射与 owner 不一致即被拒
        # （知识 E114 的错误特征 `can't create ./confXXXXXX/subs1.awk: Permission denied`）。
        # 关于 R6「只改源文件不改生成文件」的豁免依据：此处归一化发生在构建目录的临时副本上，
        # 不改动仓库内任何文件；E011 的 rec_approach 本身就是 edit-umask-in-configure；
        # 仓库内已有 1272 份 autotools 配方做同样处理（如 archives/a/abiword-plugin-*/3.0.8）。
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ['gsl', 'gslcblas']
        self.cpp_info.set_property("cmake_file_name", "gsl")
        self.cpp_info.set_property("cmake_target_name", "gsl::gsl")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ['m']

    def _detect_pkg_config_name(self):
        # 从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem 作为 pkg_config_name。
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
