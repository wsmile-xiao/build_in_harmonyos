#!/usr/bin/env python3
"""Conan recipe — tdbc 1.1.14 (Tcl Database Connectivity 基础包).

上游构建系统: TEA (autotools)。tdbc 不是独立可执行程序，而是 Tcl 扩展包：
构建期需要 tcl 的 tclConfig.sh / tcl.h / libtclstub，运行期由 tclsh dlopen
libtdbc1.1.14.so 并经 auto_path 找到 lib/tdbc1.1.14/pkgIndex.tcl。

OHOS(HarmonyOS PC) 适配点（全部在本配方 build() 内复现，见 notes.md）:
  1. autoconf 生成的 config.status 用 `umask 077` 创建临时目录并写入
     subs1.awk —— HMDFS 权限归一化后该目录/文件不可访问，configure 直接
     `Permission denied` 失败（与 tcl/8.6.16 recipe 的 E011 同源）。→ 022。
  2. TEA 的 tcl.m4 没有 HarmonyOS 分支，`uname -s` 得到
     "HarmonyOS-HongMeng Kernel ..." → SHLIB_LD/SHLIB_SUFFIX 为空，共享库
     链接命令残缺。→ 传 `tcl_cv_sys_version=Linux-6.6` 走官方 Linux 分支。
  3. TEA_PREFIX 在未显式给 --exec_prefix 时会把 exec_prefix 设为 Tcl 的
     TCL_EXEC_PREFIX（即 ${TCL_ROOT}），导致 pkglibdir 落进 tcl 依赖包的
     cache 目录。→ 显式指定 prefix/exec_prefix（DESTDIR 隔离），安装全部经
     DESTDIR 落到本包 staging。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# TEA 安装前缀（必须绝对路径）；实际安装落点由 DESTDIR=staging 决定，
# 不写入共享系统前缀（R49/PF6）
INSTALL_PREFIX = os.path.join(os.sep, "usr", "local")
# TEA 需要知道目标系统；OHOS 的 uname 输出无对应分支，显式给 Linux 缓存变量
TEA_SYS_VERSION = "Linux-6.6"


class TdbcConan(ConanFile):
    name = "tdbc"
    version = "1.1.14"
    description = "Tcl Database Connectivity (TDBC) base package — SQL 接口基类与 SQL 分词器"
    license = "TCL"
    homepage = "https://core.tcl-lang.org/tdbc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("tcl", "database", "tdbc")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # tdbc 的构建期（tclConfig.sh / tcl.h / libtclstub）与运行期（tclsh +
        # libtcl8.6.so + TclOO）依赖，均来自 tcl 包（已发布并可消费）
        self.requires("tcl/8.6.16")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        # patches/0001-configure.patch 已把 configure（及其生成的 config.status）里的
        # umask 077 修为 022 —— OHOS HMDFS 下该临时目录不可访问。补丁见 conandata.yml。
        apply_conandata_patches(self)

        tcl_pkg_folder = self.dependencies["tcl"].package_folder
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c", "clang")

        shared = "yes" if self.options.shared else "no"
        configure_cmd = (
            f'cd "{self.source_folder}" && bash configure'
            f" --prefix={INSTALL_PREFIX} --exec_prefix={INSTALL_PREFIX}"
            f' --with-tcl="{os.path.join(tcl_pkg_folder, "lib")}"'
            f" --enable-shared={shared}"
            f" CC={cc} tcl_cv_sys_version={TEA_SYS_VERSION}"
        )
        # HMDFS 上 configure 可能丢失执行位，统一经 bash 调用
        self.run(configure_cmd, env="conanbuild")
        # OHOS 不支持 make jobserver 的 mkfifo（Operation not permitted）→ -j1
        self.run(f'cd "{self.source_folder}" && make -j1', env="conanbuild")

        self._run_upstream_tests()

        staging = os.path.join(self.build_folder, "staging")
        self.run(
            f'cd "{self.source_folder}" && make install DESTDIR="{staging}"',
            env="conanbuild",
        )

    def _run_upstream_tests(self):
        """真实运行上游测试套件（tests/all.tcl，tcltest 驱动）并校验通过率。"""
        test_log = os.path.join(self.build_folder, "upstream_test.log")
        rc = self.run(
            f'cd "{self.source_folder}" && make test TESTFLAGS="-verbose pass"'
            f" > {test_log} 2>&1",
            env="conanbuild",
            ignore_errors=True,
        )
        with open(test_log, encoding="utf-8", errors="ignore") as handle:
            log_text = handle.read()

        summary = re.search(
            r"^all\.tcl:\s+Total\s+(\d+)\s+Passed\s+(\d+)\s+Skipped\s+(\d+)\s+Failed\s+(\d+)",
            log_text,
            re.MULTILINE,
        )
        if not summary:
            raise ConanException(
                f"上游测试未产生 tcltest 汇总行（rc={rc}），请查看 {test_log}"
            )
        total, passed, skipped, failed = (int(g) for g in summary.groups())
        cases = re.findall(r"^\+\+\+\+ (\S+) PASSED", log_text, re.MULTILINE)
        self.output.info(
            f"L1_UPSTREAM_RESULT: total={total} passed={passed} "
            f"skipped={skipped} failed={failed} cases={len(cases)}"
        )
        if failed or passed != total:
            raise ConanException(
                f"上游测试失败: Total={total} Passed={passed} Skipped={skipped} "
                f"Failed={failed}（详见 {test_log}）"
            )

    def package(self):
        staging_prefix = os.path.join(self.build_folder, "staging", INSTALL_PREFIX.lstrip("/"))
        if not os.path.isdir(staging_prefix):
            raise ConanException(f"make install 未产生 staging 目录: {staging_prefix}")
        # staging/usr/local/{lib/tdbc1.1.14,include,share/man} → 保留相对结构
        copy(self, "*", src=staging_prefix, dst=self.package_folder)
        for artifact in ("lib", "include"):
            if not os.path.isdir(os.path.join(self.package_folder, artifact)):
                raise ConanException(f"包内缺少 {artifact}/（staging={staging_prefix}）")

    def package_info(self):
        # Tcl 包的标准消费方式：pkgIndex.tcl 由 tclsh 经 auto_path/TCLLIBPATH 发现
        # 纯库包（无 bin/ 可执行产物），故不声明 bindirs（R38/CI L0k 据此判库）
        self.cpp_info.includedirs = ["include"]
        # tdbc1.1.14 目录内同时提供共享库与 stub 静态库，供 C 扩展直接链接
        self.cpp_info.libs = ["tdbc1.1.14"]
        self.cpp_info.libdirs.append(os.path.join("lib", f"tdbc{self.version}"))
        for environment in (self.buildenv_info, self.runenv_info):
            environment.prepend_path(
                "TCLLIBPATH", os.path.join(self.package_folder, "lib")
            )
