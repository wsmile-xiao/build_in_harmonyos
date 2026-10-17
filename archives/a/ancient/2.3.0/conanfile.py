#!/usr/bin/env python3
"""Conan recipe — ancient 2.3.0 (autotools, no pre-generated configure).

上游发布 tarball 不含预生成 configure（configure.ac/Makefile.am 需 autogen）。
本配方按 abiword 系先例：tool_requires automake/libtool（制品仓已发布），
export_sources 携带 autoconf-archive/pkg m4 宏，build() 内 aclocal → autoconf
生成 configure 后走标准 Autotools 流程；configure.ac 无 AC_CONFIG_HEADERS，
不调用 autoheader。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class AncientConan(ConanFile):
    name = "ancient"
    version = "2.3.0"
    description = "ancient 2.3.0 — decompression library for old computer formats"
    license = "MIT"
    homepage = "https://github.com/temisu/ancient"
    url = "https://github.com/temisu/ancient"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # autoconf-archive + pkg-config m4 宏：发布 tarball 的 m4/ 只含 libtool
        # 宏，configure.ac 引用的 AX_CXX_COMPILE_STDCXX/AX_CHECK_COMPILE_FLAG/
        # AX_CXXFLAGS_WARN_ALL/PKG_PROG_PKG_CONFIG 需随配方导出（CI 沙箱
        # 无 $HOME/.local/share/aclocal）
        copy(self, "m4/*.m4", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        pass

    def build_requirements(self):
        # automake/libtool 已发布制品仓（abiword 系配方同版本先例）
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 先注入 ACLOCAL_PATH 指向配方导出的 m4 宏，再 VirtualBuildEnv
        _m4_dir = os.path.join(self.source_folder, "m4")
        if os.path.isdir(_m4_dir):
            self.buildenv_info.append_path("ACLOCAL_PATH", _m4_dir)
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # OHOS 不被 config.guess(2024-07-27) 识别（uname -s=HarmonyOS），
        # 显式等值 build/host 跳过猜测（abiword 系配方同法 E540 / DRAFT-5982）。
        # 仅 OHOS/Linux aarch64 原生构建适用；其它 arch 不强制三元组。
        if self.settings.os in ("OHOS", "Linux") and str(self.settings.arch).startswith("armv"):
            tc.configure_args.append("--build=aarch64-linux")
            tc.configure_args.append("--host=aarch64-linux")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._run_autogen()
        # E011 (HMDFS umask 077): configure 生成的 config.status 用
        # `mktemp -d ./confXXXXXX` 时先执行 umask 077，HMDFS 上 0700 临时目录
        # 对当前进程不可写（subs1.awk Permission denied）。按 E011 方法 1/2
        # 处理：放宽 configure 与 config.status 中的 umask（acl/addrwatch/advancescan
        # 同法先例，077→022），确保 config.status 能创建 conf 临时目录。
        self._relax_generated_umask()
        autotools = Autotools(self)
        autotools.configure()
        self._relax_config_status_umask()
        autotools.make(args=["-j1"])

    def _relax_generated_umask(self):
        """把 autoconf 现场生成的 configure 中 `umask 077` 放宽为 022。

        config.status 由 configure 从模板现场生成，先改 configure 即可让
        config.status 继承放宽后的 umask（E011 rec_approach edit-umask-in-configure）。
        """
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure):
            raise Exception("configure missing after autogen (E011 fix aborted)")
        self.output.info("E011: relaxing umask 077 -> 022 in generated configure ...")
        self.run(
            "sed -i 's/umask 077/umask 022/g' configure",
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,
        )
        with open(configure, "r", errors="replace") as fh:
            leaked = [ln for ln in fh if "umask 077" in ln]
        if leaked:
            raise Exception(
                "E011 fix failed: umask 077 still present in configure: %s" % leaked[:3])

    def _relax_config_status_umask(self):
        """config.status 已是生成物时直接放宽其中 umask（E011 fallback）。"""
        cstatus = os.path.join(self.source_folder, "config.status")
        if not os.path.exists(cstatus):
            return
        with open(cstatus, "r", errors="replace") as fh:
            if not any("umask 077" in ln for ln in fh):
                return
        self.output.info("E011: relaxing umask 077 -> 022 in config.status ...")
        self.run(
            "sed -i 's/umask 077/umask 022/g' config.status",
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,
        )
        with open(cstatus, "r", errors="replace") as fh:
            leaked = [ln for ln in fh if "umask 077" in ln]
        if leaked:
            raise Exception(
                "E011 fallback failed: umask 077 still present in config.status: %s" % leaked[:3])

    def _run_autogen(self):
        """生成 configure + build-aux 辅助文件（tarball 无预生成 configure）。

        configure.ac 声明 AC_CONFIG_AUX_DIR(build-aux)/AC_CONFIG_MACRO_DIR(m4)
        且使用 LT_INIT/libtool，需按 autoreconf -i 等价链：
        libtoolize（ltmain.sh + libtool.m4 系列）→ aclocal（AM_* + 导出的
        ax_*/pkg 宏）→ autoconf（configure.ac 无 AC_CONFIG_HEADERS，不调用
        autoheader）→ automake --add-missing（config.guess/config.sub/compile/
        ar-lib/missing/install-sh/depcomp/test-driver 落 build-aux）。
        tool_requires 的 $LIBTOOLIZE/$ACLOCAL/$AUTOMAKE 由 VirtualBuildEnv
        注入（abiword 系配方同源）。
        """
        self.output.info("Running libtoolize (ltmain.sh + libtool m4)...")
        self.run(
            '"${LIBTOOLIZE:-libtoolize}" --force --copy --install',
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,
        )
        self.output.info("Running aclocal to generate aclocal.m4...")
        self.run(
            'ACLOCAL_PATH="{}:$ACLOCAL_PATH" "${{ACLOCAL:-aclocal}}" --force -I m4'.format(
                os.path.join(self.source_folder, "m4")),
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,
        )
        self.output.info("Running autoconf to generate configure...")
        self.run(
            "autoconf -o configure configure.ac",
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,
        )
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise Exception("autoconf failed to generate configure")
        self.output.info("Running automake --add-missing (build-aux)...")
        self.run(
            '"${AUTOMAKE:-automake}" --add-missing --copy --force-missing',
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ancient"]
