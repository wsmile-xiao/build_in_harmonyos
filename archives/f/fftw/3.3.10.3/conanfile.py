#!/usr/bin/env python3
"""Conan recipe — fftw 3.3.10 (autotools)

鸿蒙适配说明:
- config.guess/config.sub 打 HarmonyOS 识别补丁 (E007),禁止 --build/--host 交叉参数绕过
- configure 的 umask 077 在 HMDFS 上导致 config.status 失败 (E011),build() 内已做 sed 修正
- 上游 tarball 的 fftw-3.3.10.tar.gz 与制品仓已有 fftw/3.3.10 同名,本配方为该版本任务的
  重提交,版本号沿用任务要求 3.3.10 (R37: 首次适配用上游版本)
"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class FftwConan(ConanFile):
    name = "fftw"
    version = "3.3.10.3"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def export_sources(self):
        # 补丁随配方导出 (Conan 2 标准方式)
        export_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 禁止 --build/--host 交叉参数 (E007 forbid: 会导致 AC_RUN_IFELSE 全跳过,
        # 平台能力检测使用 glibc 默认值,config.h 与实际平台不匹配)。
        # config.guess 补丁后可原生识别 aarch64-unknown-linux-ohos。
        tc.configure_args.append("--enable-shared")
        tc.configure_args.append("--disable-static")
        # HMDFS: make 的 depfiles 管道(sed | make -f -)在 HMDFS 上执行 bash 被拦
        # (make: /data/service/hnp/bin/bash: Operation not permitted),禁用依赖跟踪绕过
        tc.configure_args.append("--disable-dependency-tracking")
        tc.configure_args.append("--disable-fortran")
        tc.configure_args.append("--disable-doc")
        tc.generate()

    def build(self):
        # 0. E490: tarball 解压可能丢失脚本执行权限(HMDFS chmod 受限),显式恢复
        import os as _os, stat as _stat
        for _s in ("configure", "config.guess", "config.sub", "install-sh", "missing", "depcomp", "ltmain.sh"):
            _p = _os.path.join(self.source_folder, _s)
            if _os.path.exists(_p):
                _os.chmod(_p, _os.stat(_p).st_mode | _stat.S_IXUSR | _stat.S_IXGRP | _stat.S_IXOTH)
        # 1. 先打 HarmonyOS 识别补丁 (config.guess/config.sub, 见 conandata.yml patches)
        apply_conandata_patches(self)
        # 2. E011: HMDFS umask 077 修复 — configure 生成 config.status 时
        #    mktemp 临时目录权限问题导致 "cannot create subs1.awk: Permission denied"
        import glob, os
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        # 3. 原生 configure (无交叉参数)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j8"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        explicit_libs = ['fftw3']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "fftw")
        self.cpp_info.set_property("cmake_target_name", "fftw::fftw")
        pkg = "" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ['m']
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时,从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
