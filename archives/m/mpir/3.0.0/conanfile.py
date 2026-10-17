#!/usr/bin/env python3
"""Conan recipe — mpir 3.0.0 (autotools)"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MpirConan(ConanFile):
    name = "mpir"
    version = "3.0.0"
    description = "MPIR (Multiple Precision Integers and Rationals), a high-precision math library forked from GMP"
    license = ("LGPL-3.0-or-later", "GPL-2.0-or-later")
    homepage = "https://github.com/wbhart/mpir"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
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

    def build_requirements(self):
        # CI worker 的 HNP 只有 autoconf/m4/perl，无 automake（aclocal）与
        # libtool（libtoolize），GitHub tag 归档的 autoreconf 自举无法在 CI
        # 完成（PR !10607 构建实测）；conan 侧 perl 运行时在本平台不可用
        # （generate() 注释），故只取 automake/libtool 的脚本与数据树，由
        # HNP 的 perl/autoconf/autom4te/m4 驱动（_bootstrap_autoreconf）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # MPIR 3.0.0 自带 config.guess/sub 是 GMP 包装脚本（内嵌 2015 年 FSF 版），
        # 无法识别 OHOS 环境；与构建三元组保持一致显式指定，mpn 走 generic C 路径。
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--enable-cxx")
        # profile buildenv 的 CONFIG_SHELL 指向 /data/service/hnp/bin/bash，其
        # job-control getcwd 在 HMDFS 上偶发失败并触发 configure "working
        # directory cannot be determined"（E011 同族现象）。系统 /bin/sh 行为
        # 可靠；conanbuild.sh 最后加载 conanbuildenv（recipe buildenv 覆盖
        # profile 值），故经 self.buildenv 覆盖才能生效。
        self.buildenv.define("CONFIG_SHELL", "/bin/sh")
        # 记录 conan automake/libtool 包目录供 build() 组装自举环境：
        # 这两个包在本平台的可重定位前缀与 perl 运行时是坏的（实测 perl/5.42.2
        # 自带 Cwd.so 缺 Perl_my_cxt_init 符号；libtoolize 内置数据目录为空
        # 前缀 //share），只能取其 aclocal/automake/libtoolize 脚本与数据树，
        # 由 HNP 的 perl/autoconf/autom4te/m4（/data/service/hnp/bin）驱动。
        for dep in self.dependencies.values():
            if getattr(dep, "context", "") != "build":
                continue
            if dep.ref.name == "automake":
                self._bootstrap_automake = dep.package_folder
            elif dep.ref.name == "libtool":
                self._bootstrap_libtool = dep.package_folder
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # E490（知识图谱）：HMDFS 路径可能丢失 autotools 辅助脚本执行位，
        # 自举/执行前仅对已知脚本恢复 +x。
        for name in ("configure", "config.guess", "config.sub", "configfsf.guess",
                     "configfsf.sub", "install-sh", "missing", "depcomp",
                     "compile", "test-driver", "ylwrap"):
            path = os.path.join(self.source_folder, name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
        # GitHub tag 归档只提交 configure.ac，不含生成的 configure；缺失时先
        # autoreconf 自举。判在运行期而非生成期，同一份配方两种源都能用。
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（GitHub tag 归档常见），先 autoreconf 自举")
            self._bootstrap_autoreconf()
            # autoreconf 重新生成的 configure 里 config.status 用
            # `umask 077 && mktemp -d ./confXXXXXX` 建 0700 临时目录，HMDFS/SELinux
            # 环境随后在其中创建文件报 Permission denied；必须在自举之后放宽为 022。
            for cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
                with open(cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                if "umask 077" in text:
                    with open(cfg, "w", encoding="utf-8") as f:
                        f.write(text.replace("umask 077", "umask 022"))
        autotools.configure()
        autotools.make(args=["-j1"])
        # 上游测试三步法（R51）：tests/ 全量 207 个测试程序（shared-only 打包下
        # 的实际附加集合）随 W3/CI 同源执行；测试失败视为构建失败。
        # HMBS_UPSTREAM_TEST_RESULT：新版工作流（ci: enforce full upstream test
        # results）要求声明 upstream_test_in_build 的包输出机器可读的
        # registered/pass 标记，供 L1c 核验。
        self.output.info('HMBS_UPSTREAM_TEST_RESULT={"suite":"mpir-upstream-tests",'
                         '"status":"registered","registered":207}')
        autotools.make(args=["check"])
        self.output.info('HMBS_UPSTREAM_TEST_RESULT={"suite":"mpir-upstream-tests",'
                         '"status":"pass","registered":207}')

    def _bootstrap_autoreconf(self):
        """autoreconf 自举：HNP 提供 autoconf/autom4te/m4/perl，
        conan automake/libtool 只出 aclocal/automake/libtoolize 脚本与数据树。
        两边的可重定位前缀/perl 运行时都不能直接混用（generate() 注释），
        故整条链的路径与环境变量在此显式闭合；已在本机实测 autoreconf 0 退出。
        """
        hnp = "/data/service/hnp/bin"
        am = getattr(self, "_bootstrap_automake", None)
        lt = getattr(self, "_bootstrap_libtool", None)
        require_all = [p for p in (am, lt) if p]
        if len(require_all) < 2:
            raise ConanException("tool_requires automake/libtool 未就绪，无法自举")
        vendor = os.path.join(self.build_folder, "autotools-vendor")
        # libtoolize 按 _lt_pkgdatadir/{build-aux,libltdl,m4} 取数据，其内置
        # 前缀已坏，用包内数据树组装出它期望的布局。
        os.makedirs(os.path.join(vendor, "m4"), exist_ok=True)
        shutil.copytree(os.path.join(lt, "share", "libtool", "build-aux"),
                        os.path.join(vendor, "build-aux"), dirs_exist_ok=True)
        shutil.copytree(os.path.join(lt, "share", "libtool", "libltdl"),
                        os.path.join(vendor, "libltdl"), dirs_exist_ok=True)
        for m4 in glob.glob(os.path.join(lt, "share", "aclocal", "*.m4")):
            shutil.copy(m4, os.path.join(vendor, "m4"))
        automake_share = glob.glob(os.path.join(am, "share", "automake-*"))
        env_prefix = (
            f"PERL5LIB={shlex.quote(automake_share[-1])} "
            f"ACLOCAL_PATH={shlex.quote(os.path.join(vendor, 'm4'))} "
            f"_lt_pkgdatadir={shlex.quote(vendor)} "
            f"ACLOCAL={shlex.quote(os.path.join(am, 'bin', 'aclocal'))} "
            f"AUTOMAKE={shlex.quote(os.path.join(am, 'bin', 'automake'))} "
            f"LIBTOOLIZE={shlex.quote(os.path.join(lt, 'bin', 'libtoolize'))} "
            f"AUTOCONF={hnp}/autoconf AUTOHEADER={hnp}/autoheader "
            f"AUTOM4TE={hnp}/autom4te AUTORECONF={hnp}/autoreconf "
            f"AUTOSCAN={hnp}/autoscan AUTOUPDATE={hnp}/autoupdate M4={hnp}/m4 "
        )
        self.run(f"{env_prefix} autoreconf --force --install",
                 env="conanbuild", cwd=self.source_folder)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool 的 .la 烤死 libdir 绝对路径，conan 包按 prefix=/ 构建会指向
        # '/lib'；链接信息由 cpp_info/.pc 提供（gmp 6.3.0.1 同款处理）。
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["mpirxx", "mpir"]
        self.cpp_info.set_property("cmake_file_name", "mpir")
        self.cpp_info.set_property("cmake_target_name", "mpir::mpir")
        self.cpp_info.set_property("pkg_config_name", "mpir")
