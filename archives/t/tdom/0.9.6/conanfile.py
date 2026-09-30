#!/usr/bin/env python3
"""Conan recipe — tdom 0.9.6（Tcl 的 XML/DOM/XPath/XSLT/JSON 扩展，纯 C）。

tdom 是 Tcl 语言的 XML 处理库：XML 解析（含 bundled expat）、DOM 树（domNode 的
完整增删改查 API）、XPath 1.0/Pullparser/JSON、以及 schema 支持。它是 **TEA
（Tcl Extension Architecture）** 扩展：构建出 `libtdom0.9.6.so`，由 tclsh 在运行时
`load` 进解释器（`package require tdom`）。

OHOS 适配要点
  1. 唯一外部依赖是 **tcl**（`tcl/8.6.16`，仓库已发布）：tdom 链接 tcl 的
     **stub 库**（`libtclstub8.6.a`），所以运行期 tcl 符号由宿主解释器提供 —— 这正是
     TEA 的跨版本加载机制。expat **随源码自带**（configure: `Using bundled expat`），
     不需要外部 expat 包；HTML5（gumbo）默认关闭且仓库无 gumbo → 保持关闭。
  2. TEA configure 需要 `--with-tcl=<含 tclConfig.sh 的目录>`：conan 的 tcl 包把
     tclConfig.sh 放在 `lib/`，并用 `${TCL_ROOT}` 变量指向包目录（tcl 配方 P1 改动），
     所以这里显式把 tcl 包的目录与 `include/` 传进去（tkpng 0.9 同款做法）。
  3. 上游 configure 里有 `umask 077`，在 HMDFS/SELinux 下会让临时目录不可写
     （E011）→ 构建前改写成 022。
  4. HMDFS 时间戳偏移会让 make 误以为 `configure.ac`/`tdom.m4` 比生成物新，从而调
     automake 重新生成并报 `newly created file is older than distributed files`
     （libvo-amrwbenc 实证）→ 构建前把 `configure.ac`/`tdom.m4` 设成 now-5、生成物
     （`configure`/`Makefile.in`/`aclocal.m4`）设成 now。
  5. 上游 `make install` 走的 install-sh 会把 `exec_prefix` 解析成 `/usr`（与
     `--prefix` 不一致），所以 `package()` 先把安装 stage 到构建目录，再按 TEA 布局
     显式收集到 conan 包（tkpng 0.9 先例）。

真实测试（平台 rule12 / L1c）
  * build() 内真跑**上游官方测试套件** `make check`（= 上游 `test`：`tests/all.tcl`
    的 tcltest 套件，含 OASIS XML 一致性用例）→ 实测 2459 个用例，解析
    `all.tcl: Total/Passed/Skipped/Failed` 汇总行，Failed ≠ 0 直接让构建失败。
  * test_package 另有一份**完整消费者用例**（`test_tdom.tcl`，用交付的 .so 通过
    `package require tdom` 跑真实 XML 业务流程）+ 交付形态自检（M）。
"""
import os
import re
import shutil
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# TEA 安装到 lib/<PKG_DIR>/ 的文件（与上游 Makefile 的 pkglibdir 一致）
TEA_LIB_FILES = (
    "libtdom0.9.6.so",
    "libtdomstub0.9.6.a",
    "pkgIndex.tcl",
    "tdom.tcl",
)


def _find_one(root, name):
    """在（stage 出来的）安装树里找唯一命名的文件。"""
    hits = []
    for dirpath, _dirnames, filenames in os.walk(root):
        if name in filenames:
            hits.append(os.path.join(dirpath, name))
    return hits[0] if hits else None


class TdomConan(ConanFile):
    name = "tdom"
    version = "0.9.6"
    description = ("tDOM — Tcl XML/DOM/XPath/XSLT/JSON extension: XML parsing, "
                   "full DOM API, XPath 1.0, pull parser and schema support (pure C)")
    license = "MPL-2.0"
    homepage = "http://tdom.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("xml", "dom", "xpath", "tcl", "extension")

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tdom 0.9.6 仅适配 Linux/OHOS，收到 '%s'" % self.settings.os)

    def requirements(self):
        # 唯一外部依赖：tcl（tdom 链接 tcl 的 stub 库，运行时符号由宿主 tclsh 提供）
        self.requires("tcl/8.6.16")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ------------------------------------------------------------------ #
    # 构建期小工具
    # ------------------------------------------------------------------ #
    def _tcl_package_folder(self):
        return self.dependencies["tcl"].package_folder

    def _tcl_config_dir(self):
        """tclConfig.sh 所在目录（TEA 的 --with-tcl 要的是目录，不是文件）。"""
        root = self._tcl_package_folder()
        for dirpath, _dirnames, filenames in os.walk(root):
            if "tclConfig.sh" in filenames:
                return dirpath
        raise ConanException("tcl 包里找不到 tclConfig.sh（--with-tcl 无法配置）")

    def _drop_umask_077(self):
        """E011：configure 里的 umask 077 在 HMDFS/SELinux 下不可用。"""
        path = os.path.join(self.source_folder, "configure")
        with open(path, encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        if "umask 077" in text:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text.replace("umask 077", "umask 022"))

    def _relax_generated_file_timestamps(self):
        """HMDFS 时间戳偏移：别让 make 认为 configure.ac 比 configure/Makefile.in 新。

        生成物设成 now、源设成 now-5，且都不落在未来时刻（否则 CONFIG_SHELL 的
        sanity 检查会失败）；与 libvo-amrwbenc / aldo 0.7.8 同款处理。
        """
        now = time.time()
        for name in ("configure", "Makefile.in", "aclocal.m4"):
            path = os.path.join(self.source_folder, name)
            if os.path.exists(path):
                os.utime(path, (now, now))
        for name in ("configure.ac", "tdom.m4"):
            path = os.path.join(self.source_folder, name)
            if os.path.exists(path):
                os.utime(path, (now - 5, now - 5))

    # ------------------------------------------------------------------ #
    # generate / build / package
    # ------------------------------------------------------------------ #
    def generate(self):
        toolchain = AutotoolsToolchain(self)
        # TEA：--with-tcl 指到含 tclConfig.sh 的目录；头文件也显式给出
        toolchain.configure_args.append("--with-tcl=%s" % self._tcl_config_dir())
        toolchain.configure_args.append(
            "--with-tclinclude=%s" % os.path.join(self._tcl_package_folder(), "include"))
        # HTML5 需要未发布的 gumbo → 保持上游默认关闭
        toolchain.configure_args.append("--disable-html5")
        # TEA configure 在无 /proc/sys/kernel 等信息的沙箱里需要这两个缓存变量
        toolchain.configure_args.append("tcl_cv_sys_version=Linux-6.6")
        toolchain.configure_args.append("ac_cv_prog_cc_works=yes")
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        self._drop_umask_077()
        self._relax_generated_file_timestamps()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """上游官方测试套件：tests/all.tcl（tcltest）。失败即让 build 失败。"""
        # TEA 的 test 目标用 `TCLSH_ENV = TCL_LIBRARY=<TCL_SRC_DIR>/library`，而
        # tcl 包里 TCL_SRC_DIR 指向已不存在的构建目录 → 这里用交付的 tcl 运行时
        # 库目录覆盖它（redis 6.2 同款：TCL_LIBRARY=<tcl pkg>/lib/tcl8.6）。
        tcl_library = os.path.join(self._tcl_package_folder(), "lib", "tcl8.6")
        log_path = os.path.join(self.build_folder, "upstream_test.log")
        self.run(
            'make check TCLSH_ENV="TCL_LIBRARY=%s" > "%s" 2>&1'
            % (tcl_library, log_path),
            env="conanrun",
            ignore_errors=True,
        )
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        self.output.info("=== upstream tcltest (tail) ===")
        for line in out.splitlines()[-20:]:
            self.output.info(line)

        match = re.search(
            r"all\.tcl:\s+Total\s+(\d+)\s+Passed\s+(\d+)\s+Skipped\s+(\d+)\s+Failed\s+(\d+)",
            out)
        if not match:
            raise ConanException(
                "上游 tcltest 套件没有产出汇总行（测试未真正运行），完整日志见 "
                "构建目录 upstream_test.log")
        total, passed, skipped, failed = (int(x) for x in match.groups())
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT total=%d passed=%d skipped=%d failed=%d"
            % (total, passed, skipped, failed))
        if failed:
            raise ConanException(
                "上游 tcltest 套件有 %d 个用例失败（Total %d / Passed %d）—— 见 "
                "upstream_test.log" % (failed, total, passed))

    def package(self):
        # TEA install-sh 会把 exec_prefix 解析成 /usr，与 --prefix 不一致 →
        # 先 stage 再按 TEA 布局显式收集（tkpng 0.9 先例）。
        stage = os.path.join(self.build_folder, "install-stage")
        self.run('make install DESTDIR="%s"' % stage, env="conanbuild")

        tea_dir = os.path.join(self.package_folder, "lib", "tdom0.9.6")
        os.makedirs(tea_dir, exist_ok=True)
        for name in TEA_LIB_FILES:
            found = _find_one(stage, name)
            if not found:
                raise ConanException("make install 未产出 %s（TEA 布局变化？）" % name)
            shutil.copy2(found, os.path.join(tea_dir, name))

        header = _find_one(stage, "tdom.h")
        if header:
            include_dir = os.path.join(self.package_folder, "include")
            os.makedirs(include_dir, exist_ok=True)
            shutil.copy2(header, os.path.join(include_dir, "tdom.h"))

        config_sh = _find_one(stage, "tdomConfig.sh")
        if config_sh:
            shutil.copy2(config_sh, os.path.join(self.package_folder, "lib", "tdomConfig.sh"))

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # tdom 是 Tcl 扩展：不参与 C/C++ 链接（运行期由 tclsh load），因此 libs 为空。
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = [os.path.join("lib", "tdom0.9.6")]
        # 消费者（Tcl 应用）把 TDOM_TCL_DIR 加进 auto_path 即可 package require tdom
        for environment in (self.buildenv_info, self.runenv_info):
            environment.define(
                "TDOM_TCL_DIR",
                os.path.join(self.package_folder, "lib", "tdom0.9.6"))
