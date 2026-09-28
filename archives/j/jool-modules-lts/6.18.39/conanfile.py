#!/usr/bin/env python3
"""Conan recipe — jool-modules-lts 6.18.39（上游软件 Jool v4.1.14）

Jool 是 SIIT/NAT64 翻译器：上游交付物 = Linux 内核模块（jool / jool_siit，Kbuild
obj-m + DKMS）+ 用户态 netlink 客户端（jool / jool_siit 两个 CLI）+ 用户态会话代理
守护进程（joold）。本包在 OHOS PC 侧交付**用户态三件套**（bin/jool、bin/jool_siit、
bin/joold），内核模块源码以**上游源码快照**随包交付（share/jool-modules-lts/upstream/
= 任务指定 tarball 原样再解压，无任何构建产物），供 fail-closed 契约测试与平台未来
提供内核构建树时复用。内核态构建/加载在 OHOS 侧不可行（无内核构建树、无 root），
本包不伪造内核态通过——交付边界详见 notes.md 与 PR 描述。

适配要点（全部经本机 OHOS clang 交叉验证 + 仓库 CI 实证先例）：

- 源码为 codeload tarball，**不含 configure**：build() 用 conan Autotools.autoreconf()
  自举（tool_requires automake/1.18 + libtool/2.5.4，同 argp-standalone 先例）。
- configure 强制依赖 libnl-genl-3.0 >= 3.2.22（PKG_CHECK_MODULES）：制品仓 libnl/3.11.0
  的组件 pkg_config_name 即 libnl-genl-3.0，用 PkgConfigDeps 生成 .pc 并把
  PKG_CONFIG_PATH 指到 generators 目录（同 abiword-plugin-eml 先例）。
- configure 另有 AC_CHECK_LIB(argp, argp_parse)：argp-standalone/1.5.0 为静态库，
  经 LDFLAGS/CPPFLAGS 显式注入 -L/-I（cpp_info 路径归一化到 package_folder）。
- 可选依赖按上游开关禁用：--with-xtables=no（iptables 扩展，制品仓无 xtables；
  上游 Makefile.am 会自动给 libjoolargp 加 -DXTABLES_DISABLED 并裁掉 iptables/ 子目录）
  与 --with-bash-completion-dir=no（bash 补全脚本，非功能路径）。
- E119（OHOS sysroot 的 linux/netlink.h 使用未定义的 __kernel_sa_family_t，且
  linux/socket.h 的无前缀 sockaddr_storage 与 musl sys/socket.h 冲突）：与 libnl
  test_package 同一处置，经 CPPFLAGS 预定义 _UAPI_LINUX_SOCKET_H 与
  __kernel_sa_family_t=ushort（libnl/3.11.0 MANIFEST「消费者须知」要求）。
- E236（libnl/3.11.0 的 .la 烤死 libdir='//lib'，libtool 解析其 dependency_libs
  报 "not a valid libtool archive"；且 jool 靠 in-tree .la 链传递 libnl，绝对 .a
  路径不进 dependency_libs）：generators 下建 libnl-nola/ 只放 .a 拷贝，把这些
  .pc 的 -L 改指该目录，让 libtool 视 -lnl-* 为普通库并完整传递（同 babeltrace
  E236 家族的延伸修法）。
- E114（HMDFS 上 autoconf 临时目录子进程写入被拦）：autoreconf 之后、configure 之前
  修补生成的 configure（ac_tmp 重定向到预建可写目录 + trap 不删目录 + umask 077→022，
  同 abiword-plugin-eml / argp-standalone 先例）。
- E074：make -j1。
- R15：显式 --build/--host 走绕 config.guess（OHOS 不被识别）。
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class JoolModulesLtsConan(ConanFile):
    name = "jool-modules-lts"
    version = "6.18.39"
    description = (
        "Jool SIIT/NAT64 用户态三件套（jool / jool_siit netlink 客户端 + joold 会话代理），"
        "附内核模块源码快照（Kbuild/DKMS，OHOS 侧不构建 .ko）"
    )
    license = "GPL-2.0-only"
    homepage = "https://github.com/NICMx/Jool"
    url = ""
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32：平台判断用 in，不用 ==
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported by jool-modules-lts")

    def requirements(self):
        # configure.ac: PKG_CHECK_MODULES(LIBNLGENL3, libnl-genl-3.0 >= 3.2.22)
        self.requires("libnl/3.11.0")
        # configure.ac: AC_CHECK_LIB([argp], [argp_parse])（OHOS musl 无 argp）
        self.requires("argp-standalone/1.5.0")

    def build_requirements(self):
        # codeload tarball 只有 configure.ac，须 autoreconf 自举；OHOS 沙箱
        # (USER=100) 看不到手工安装的 autotools，故显式引入（tool_requires 按
        # build profile 解析，conan create 需 -pr:h 与 -pr:b 都给全）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        sdata = self.conan_data["sources"][str(self.version)]
        # codeload URL 的 basename（v4.1.14）无压缩后缀，CI Pre-download 缓存
        # file://.../<hash>_v4.1.14 亦无后缀：两种形态下 conan 推断出无扩展名
        # 临时文件名并误入 zip 解压分支（BadZipFile）→ 显式指定 .tar.gz 文件名
        # 强制走 tar 分支（sha256 校验不受影响，仍由 download() 执行）。
        get(self, **sdata, strip_root=True,
            filename="%s.tar.gz" % os.path.basename(str(sdata["url"])))

    def generate(self):
        # PKG_CHECK_MODULES 找 libnl-genl-3.0：libnl 组件 pkg_config_name 恰为
        # libnl-genl-3.0，PkgConfigDeps 在 generators 目录生成正确的 .pc（含
        # Requires: libnl-3.0 链与绝对 include 路径）。
        PkgConfigDeps(self).generate()
        # E236：libnl/3.11.0 的 .la 烤死 libdir='//lib'（--prefix=/ 产物），libtool
        # 对 -lnl-* 会在 -L 目录优先找同名 .la，解析其 dependency_libs 时读
        # //lib/libnl-3.la 报 "not a valid libtool archive"（babeltrace 的 pcre2
        # 先例）。但 pcre2 式「.pc Libs 改绝对 .a 路径」在这里行不通：jool 最终
        # 程序经 in-tree 便捷库链（libjoolargp.la → libjoolnl.la）链接，libnl
        # 必须靠 .la 的 dependency_libs 传递，而绝对 .a 路径 libtool 不记入
        # dependency_libs（实测最终链接行丢失 libnl → undefined symbol）。
        # 改用「干净库目录」：拷贝 libnl 的 .a 到 generators 下的 libnl-nola/
        # （只放 .a 不放 .la），并把这些 .pc 的 -L 改指该目录——libtool 找不到
        # .la 便把 -lnl-* 当普通库，-L/-l 完整记入 dependency_libs 并随 in-tree
        # .la 链传递到最终链接。包路径从 self.dependencies 拿（CI 干净环境哈希
        # 目录不同，不能硬编码本机缓存路径）。
        import shutil as _shutil
        try:
            _libnl_lib = os.path.join(self.dependencies["libnl"].package_folder, "lib")
        except Exception:
            _libnl_lib = ""
        if _libnl_lib and os.path.isdir(_libnl_lib):
            _nola_dir = os.path.join(self.generators_folder, "libnl-nola")
            os.makedirs(_nola_dir, exist_ok=True)
            for _a in os.listdir(_libnl_lib):
                if _a.endswith(".a"):
                    _shutil.copy2(os.path.join(_libnl_lib, _a),
                                  os.path.join(_nola_dir, _a))
            for _pc in os.listdir(self.generators_folder):
                if not _pc.endswith(".pc"):
                    continue
                _pc_path = os.path.join(self.generators_folder, _pc)
                with open(_pc_path, "r", encoding="utf-8") as _f:
                    _txt = _f.read()
                if "-lnl-" not in _txt:
                    continue
                _patched = _txt.replace('-L"${libdir}"', '-L"%s"' % _nola_dir)
                if _patched != _txt:
                    with open(_pc_path, "w", encoding="utf-8") as _f:
                        _f.write(_patched)
                    self.output.info("  [ok] E236: %s 的 -L 改指 libnl-nola（无 .la）" % _pc)
        # tool_requires(automake/libtool) 的 aclocal/automake/libtoolize 注入
        # conanbuild 环境 PATH（CI 沙箱看不到 $HOME/.local，实测 aclocal not found）。
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # 上游可选依赖开关：xtables（iptables 扩展）与 bash 补全目录。
        tc.configure_args.append("--with-xtables=no")
        tc.configure_args.append("--with-bash-completion-dir=no")
        # R15：OHOS 不被 config.guess 识别，显式给 --build/--host 走绕。
        tc.configure_args.append("--build=aarch64-linux")
        tc.configure_args.append("--host=aarch64-linux")
        # AC_CHECK_LIB(argp, argp_parse) 与 <argp.h>：argp-standalone 的
        # cpp_info 路径是相对路径，须用 package_folder 归一化成绝对路径后
        # 显式注入（AutotoolsDeps 对相对路径的展开不可靠，同 abiword 先例
        # 用手工注入而非生成器）。
        argp = self.dependencies["argp-standalone"]
        argp_root = getattr(argp, "package_folder", None)
        if not argp_root:
            raise ConanException("argp-standalone package_folder unavailable")
        tc.configure_args.append(
            "CPPFLAGS={}".format(" ".join([
                "-I{}".format(os.path.join(argp_root, "include")),
                # E119（libnl/3.11.0 MANIFEST「消费者须知」的既定处置）
                "-D_UAPI_LINUX_SOCKET_H",
                "-D__kernel_sa_family_t=ushort",
            ]))
        )
        tc.configure_args.append(
            "LDFLAGS=-L{}".format(os.path.join(argp_root, "lib")))
        # configure 的 PKG_CHECK_MODULES 需要 PKG_CONFIG_PATH 指到 PkgConfigDeps
        # 的产物目录（conanbuild 环境不会自动注入，CI 实测 No package found）。
        tc.configure_args.append("PKG_CONFIG_PATH={}".format(self.generators_folder))
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        # tarball 无 configure（GitHub codeload 常态）：autoreconf 自举。
        # 判在运行期而非生成期：同一份配方两种源都能用（同 argp-standalone）。
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure，先 autoreconf 自举")
            autotools.autoreconf()
        # ⚠️ E114 修补必须在 autoreconf 之后：自举会重新生成 configure。
        self._patch_configure_for_ohos()
        autotools.configure()
        # E074：HMDFS 下并行 make 曾触发竞态，先例配方一律 -j1。
        autotools.make(args=["-j1"])

    def _patch_configure_for_ohos(self):
        """E114：HMDFS 拦截 autoconf 临时目录的子进程写入（同 abiword-plugin-eml
        的 CI 实证修法）：TMPDIR 指向预建可写目录 + configure 内嵌 ac_tmp 改指该
        目录 + 退出 trap 不再删除它；另将 umask 077 放宽为 022（同
        argp-standalone）。非 OHOS 平台不动 configure。"""
        import tempfile
        if self.settings.os != "OHOS":
            return
        fixed_tmp = os.path.join(tempfile.gettempdir(), "jool-ac-tmp")
        os.makedirs(fixed_tmp, exist_ok=True)
        os.environ["TMPDIR"] = fixed_tmp

        cfg_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg_path):
            raise ConanException("E114: configure not generated (autoreconf failed?)")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = f.read()
        changed = False
        if "ac_tmp=$tmp" in cfg:
            # config.status/子进程的临时目录改指预建目录
            cfg = cfg.replace("ac_tmp=$tmp", "ac_tmp={}".format(fixed_tmp))
            # trap 原本会 rm -fr "$ac_tmp"，删掉预建目录会让后续轮次失明
            old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
            new_trap = "exit $exit_status"
            if old_trap in cfg:
                cfg = cfg.replace(old_trap, new_trap)
            changed = True
        if "umask 077" in cfg:
            cfg = cfg.replace("umask 077", "umask 022")
            changed = True
        if not changed:
            # autoconf 模板变更时宁可作为 warning 也不静默失败：
            self.output.warning(
                "E114: neither 'ac_tmp=$tmp' nor 'umask 077' found in generated "
                "configure; autoconf template may have changed")
            return
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write(cfg)
        os.chmod(cfg_path, 0o755)
        self.output.info("  [ok] E114: configure ac_tmp/TMPDIR -> {}".format(fixed_tmp))

    def package(self):
        pkg = self.package_folder
        src = self.source_folder

        # 1) 用户态三件套（上游 bin_PROGRAMS：src/usr/{nat64,siit,joold}）
        #    不用 make install：conan 2.x 的 make() 不追加 DESTDIR，--prefix=/
        #    会把文件装到系统目录（同 abiword-plugin-eml 的 glob+copy 先例）。
        #    basic_layout 是 VPATH 构建：产物在 build_folder（build-release/src/...）
        #    而非 source_folder，两处都查（防布局变化）。
        bindir = os.path.join(pkg, "bin")
        for sub, name in (("nat64", "jool"), ("siit", "jool_siit"), ("joold", "joold")):
            cand = None
            for root in (self.build_folder, src):
                _c = os.path.join(root, "src", "usr", sub, name)
                if os.path.isfile(_c):
                    cand = _c
                    break
            if cand is None:
                raise ConanException(
                    "expected upstream binary missing after build: "
                    f"{os.path.join(src, 'src', 'usr', sub, name)} (also checked build folder)")
            copy(self, name, os.path.dirname(cand), bindir)
            # HMDFS 上 copy 可能丢可执行位，显式恢复
            os.chmod(os.path.join(bindir, name), 0o755)

        # 2) 上游手册页（dist_man_MANS：jool.8 / jool_siit.8 / joold.8）
        #    copy() 会保留相对子目录结构（实测 glob 拷成 man8/nat64/jool.8），
        #    测试契约要求平铺 man8/，故逐文件以各自所在目录为源（与二进制同法）。
        mandir = os.path.join(pkg, "share", "man", "man8")
        for sub, name in (("nat64", "jool"), ("siit", "jool_siit"), ("joold", "joold")):
            man = None
            for root in (src, self.build_folder):
                _m = os.path.join(root, "src", "usr", sub, name + ".8")
                if os.path.isfile(_m):
                    man = _m
                    break
            if man is None:
                raise ConanException(
                    "expected upstream man page missing after build: "
                    f"{os.path.join(src, 'src', 'usr', sub, name + '.8')} (also checked build folder)")
            copy(self, name + ".8", os.path.dirname(man), mandir)

        # 3) 许可证
        copy(self, "COPYING", src, os.path.join(pkg, "licenses"))

        # 4) 上游源码快照：任务指定 tarball **原样再解压**（零构建产物、零改动，
        #    供 fail-closed 契约测试逐文件校验 + 平台未来提供内核构建树时复用；
        #    同 lenovolegionlinux 0.0.20 的「内核模块源码快照交付模式」）。
        #    不能复制 source_folder：autotools 在源内构建后混有 configure/
        #    Makefile/*.o/.libs 等生成物，快照必须保持上游原貌。
        snapshot = os.path.join(pkg, "share", "jool-modules-lts", "upstream")
        sdata = self.conan_data["sources"][str(self.version)]
        get(self, **sdata, strip_root=True, destination=snapshot,
            filename="%s.tar.gz" % os.path.basename(str(sdata["url"])))
        # HMDFS 不保 tar 权限位：恢复脚本可执行位
        for root, _, files in os.walk(snapshot):
            for f in files:
                if f.endswith((".sh", ".bash")):
                    os.chmod(os.path.join(root, f), 0o755)

    def package_info(self):
        # bin 交付（package_type=application）：无链接库，入口全在 bin/
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
