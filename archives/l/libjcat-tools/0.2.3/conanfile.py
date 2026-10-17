#!/usr/bin/env python3
"""Conan recipe — libjcat-tools 0.2.3 (Meson).

libjcat-tools 是 hughsie/libjcat 项目命令行工具子包：同一源码树
libjcat/ 下 `-Dcli=true` 构建的 `jcat-tool`（Jcat 文件查看/签名/验证
CLI，上游 meson_options.txt 的 cli 选项控制）。发行版视角下由
`libjcat-tools` 单独承载工具交付（先例 archives/b/babl-tools/0.1.126、
archives/l/libjwt-tools/3.3.3——同源工具子包形态）。

与本体 archives/l/libjcat/0.2.6 的关系：
  * 本体归档为 2026-06-04 的探索记录（manifest 标 published 但制品仓
    未发布 libjcat 任何版本，制品仓查询零命中）；
    本件按平台任务 #13256 的版本 0.2.3 独立构建工具目标；
  * jcat-tool 链接 libjcat.so（同树构建），运行时依赖 glib/json-glib
    （pkg-config 链）+ gpgme/gpg-error（GPG 引擎）+ gnutls
    （PKCS7/Ed25519 引擎），全部走 Conan 制品仓已发布包。

上游测试（libjcat/jcat-self-test.c 注册 19 个 g_test 用例）：
  本机实测被 OHOS 动态库加载限制阻断——jcat-self-test 二进制可 exec，
  但其 NEEDED 依赖 libjson-glib-1.0.so.0 的 mmap(PROT_EXEC) 返回
  EACCES（本机 2026-09-19 实测：同内容同权限文件，部分可加载部分被拒，
  行为随时间漂移，详见 notes.md「上游测试」节与 E488 条目同源结论）。
  CI 侧（远端 clean 环境）无此限制（json-glib 1.10.6 本体已过 CI 发布）。
  19 个用例的注册口径与豁免证据逐项登记在 notes.md。
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class LibjcatToolsConan(ConanFile):
    name = "libjcat-tools"
    version = "0.2.3"
    description = ("Jcat (JSON with digital signatures) command-line tool "
                   "from the libjcat project — jcat-tool")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/hughsie/libjcat"
    url = "https://github.com/hughsie/libjcat"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # W0 依赖核验：全部依赖制品仓 recipe 探测实测存在
        self.requires("glib/2.84.0.1")        # gio-2.0 / gio-unix-2.0
        self.requires("json-glib/1.10.6")     # json-glib-1.0 (>=1.1.1)
        self.requires("gpgme/1.24.0")         # GPG 引擎 (cc.find_library)
        self.requires("gnutls/3.8.10")        # PKCS7/Ed25519 引擎 (>=3.6.0)

    def layout(self):
        # meson 要求 source != build（babl-tools/json-glib 同款布局）
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 上游 dependency() 走 pkg-config；PkgConfigDeps 产出各依赖 .pc
        PkgConfigDeps(self).generate()

        # glib 的 PkgConfigDeps 产物不含 gio-unix-2.0.pc（gio-unix 头文件
        # 目录在 glib 包内但组件未导出）——按包内 lib/pkgconfig/gio-unix-2.0.pc
        # 重生成一份带正确 prefix 的到 generators 目录（json-glib 配方
        # _fix_glib_pc_files 同类处理）。
        self._emit_gio_unix_pc()

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared"
        # 工具件：只构建 jcat-tool（cli 目标）。gpg/pkcs7/ed25519 引擎
        # 保持上游默认 true（依赖均已发布），tests/introspection/vapi/man
        # 关闭（self-test 属 libjcat 库测试域，工具件不构建）。
        tc.project_options["cli"] = "true"
        tc.project_options["gpg"] = "true"
        tc.project_options["pkcs7"] = "true"
        tc.project_options["ed25519"] = "true"
        tc.project_options["tests"] = "false"
        tc.project_options["introspection"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["man"] = "false"
        tc.project_options["gtkdoc"] = "false"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_binaries()
        self._add_find_library_paths()

    def _emit_gio_unix_pc(self):
        """从 glib 依赖包内复制 gio-unix-2.0.pc 并修正 prefix。"""
        glib_pkg = None
        for _ref, dep in self.dependencies.items():
            if dep.ref.name == "glib":
                glib_pkg = dep.package_folder
                break
        if not glib_pkg:
            return
        src_pc = os.path.join(glib_pkg, "lib", "pkgconfig", "gio-unix-2.0.pc")
        if not os.path.isfile(src_pc):
            return
        with open(src_pc) as f:
            content = f.read()
        content = content.replace("prefix=/",
                                  "prefix=%s" % glib_pkg, 1)
        dst = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        with open(dst, "w") as f:
            f.write(content)
        self.output.info("emitted gio-unix-2.0.pc -> %s" % dst)

    def _add_find_library_paths(self):
        """把 gpgme/gpg-error/libassuan 的 lib 目录写入 conan_meson_*.ini
        的 c_link_args（上游 gpgme 用 cc.find_library()，链接器搜索路径
        必须显式给出——conan 进程的 os.environ 不会被 meson 子进程吸收，
        meson 配方实测有效通道是 native file 的 c_link_args）。"""
        libdirs = []
        for _ref, dep in self.dependencies.items():
            if dep.ref.name in ("gpgme", "libgpg-error", "libassuan"):
                d = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(d):
                    libdirs.append(d)
        if not libdirs:
            return
        flags = ", ".join("'-L%s'" % d for d in libdirs)
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "c_link_args = []" in content:
                content = content.replace(
                    "c_link_args = []",
                    "c_link_args = [%s]" % flags, 1)
            # cc.find_library 走链接器搜索，但 #include <gpgme.h> 还需
            # 编译期 -I：补进 c_args
            incdirs = [d.replace("/lib", "/include") for d in libdirs]
            cargs = ", ".join("'-I%s'" % d for d in incdirs if
                              os.path.isdir(d))
            if cargs and "c_args = []" in content:
                content = content.replace(
                    "c_args = []",
                    "c_args = [%s]" % cargs, 1)
            with open(nf, "w") as f:
                f.write(content)
        self.output.info("c_link_args += [%s]" % flags)

    def _inject_meson_binaries(self):
        """把 ar/ranlib/pkg-config 注入 conan_meson_native.ini
        （OHOS 上 llvm-ar 不在 meson 默认搜索路径——json-glib/babl-tools
        同款处理）。"""
        ce = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            new_lines = []
            for line in content.splitlines(True):
                new_lines.append(line)
                if line.strip() == "[binaries]":
                    if ar and "\nar =" not in content:
                        new_lines.append("ar = '%s'\n" % ar)
                    if rl and "\nranlib =" not in content:
                        new_lines.append("ranlib = '%s'\n" % rl)
                    if pkg_config and "\npkg-config =" not in content:
                        new_lines.append("pkg-config = '%s'\n" % pkg_config)
            new_content = "".join(new_lines)
            if new_content != content:
                with open(nf, "w") as f:
                    f.write(new_content)

    def build(self):
        # meson 工具缺失时 pip 安装（babl-tools/json-glib 同款）
        if not shutil.which("meson"):
            self.run(f"{sys.executable} -m pip install --user meson")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        # 交付物：bin/jcat-tool（meson install 安装到 prefix/bin）
        meson = Meson(self)
        meson.install()
        # 只保留 bin/（工具件交付形态；lib/ include/ share/ 系库交付域，
        # 由本体件承载，本包不重复交付）
        pkg = self.package_folder
        for sub in ("lib", "include", "share"):
            d = os.path.join(pkg, sub)
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        # 命令行工具包：声明 bindirs（R38 commands.json 校验触发）
        self.cpp_info.bindirs = ["bin"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
        # 供消费者/CI 直接定位入口（babl-tools 同款 conf_info）
        self.conf_info.define("user.libjcat-tools:bin",
                              os.path.join(self.package_folder, "bin"))
        self.conf_info.define("user.libjcat-tools:exe",
                              os.path.join(self.package_folder, "bin",
                                           "jcat-tool"))
