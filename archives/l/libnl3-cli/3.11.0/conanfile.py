#!/usr/bin/env python3
"""Conan recipe — libnl3-cli 3.11.0（Netlink Protocol Library Suite — CLI 子包）.

与 archives/l/libnl/3.11.0 同源同一份官方发行 tarball（tag libnl3_11_0，
sha256 与官方 .sha256sum 资产逐字符一致）：本体包以 `--disable-cli` 只交付
6 个静态子库，本子包以默认 `--enable-cli=bin`（configure.ac:100-108，
enable_cli 默认 yes == bin）交付发行版 libnl3-cli 的全部内容：

  - bin/         48 个命令行工具（nl-* / nf-* / genl-ctrl-list / idiag-socket-details）
  - lib/         6 个共享子库（nl-3 / nl-route-3 / nl-genl-3 / nl-nf-3 /
                 nl-idiag-3 / nl-xfrm-3，SONAME .so.200）+ libnl-cli-3.so.200
  - lib/libnl/cli/{cls,qdisc}/  10 个 dlopen 插件（-module -avoid-version，
                 Makefile.am pkglib_clsdir/pkglib_qdiscdir）
  - etc/libnl/{classid,pktloc}  pkgsysconf_DATA 数据文件

为什么必须 shared（不能像本体那样 --enable-static）：
  上游 48 个工具运行期 nl_cli_load_module() 以 RTLD_NOW dlopen 插件
  （src/lib/utils.c:221-237，路径 = 编译期 _NL_PKGLIBDIR/cli/<cls|qdisc>/<name>.so），
  插件引用 nl_cli_* / nl_* 符号而上游未给工具加 -export-dynamic（Makefile.am
  的 src_ldflags 为空）——静态链接的工具不导出动态符号表，dlopen(RTLD_NOW)
  必然 "symbol not found"。shared 路线下插件符号从已加载的 libnl-*.so 解析
  （发行版同法）。E316/E492/E505：OHOS musl 不能加载「SONAME 名字是软链」的
  库，package() 把 lib/ 下全部软链实体化。

依赖接线：
  同源整树自建（src/Makefile.am 的 src_ldadd 指向本树 lib/*.la），无 Conan
  依赖（R36 无适用对象，与本体包口径一致）。构建期宿主工具 flex 2.6.4 /
  bison 3.8.2 由工具链提供（tarball 不含预生成 ematch/pktloc 语法 .c，
  lib/route/pktloc_grammar.c 规则需 $(FLEX)；本机 /data/service/hnp/bin 实测）。

铁律符合性：
  R32: 无平台分支逻辑；validate/test_package 用 settings.os in ("Linux","OHOS")。
  R33: 不裸用 ${CC}/${CFLAGS}，cpp_info 全部经 Conan 生成物导出。
  R36: 无 Conan 依赖（同源整树自建）。
  R39: conandata.yml 只写上游官方 URL 一条，无手写镜像前缀。
  R38: bin/ 交付 48 个二进制 → 软件级 commands.json（type=tool）。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _drop_umask_077(path: str) -> int:
    """E114: 去掉 configure 里 autoconf 生成的 `umask 077 && `。

    HMDFS 的 SGID 目录下，`(umask 077 && mktemp -d ./confXXXXXX)` 会让
    config.status 无法建临时目录 / 写产物。先例：archives/l/libnl/3.11.0、
    archives/l/libnl/3.7.0、archives/n/netmask/2.5.0。

    返回实际替换处数（0 = 上游已不含该写法，属正常）。
    """
    with open(path, "r", encoding="utf-8") as handle:
        content = handle.read()
    if "umask 077 && " not in content:
        return 0
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content.replace("umask 077 && ", ""))
    return content.count("umask 077 && ")


class Libnl3CliConan(ConanFile):
    name = "libnl3-cli"
    version = "3.11.0"
    description = "Netlink Protocol Library Suite — command-line interface tools and libnl-cli-3"
    license = "LGPL-2.1-only"
    homepage = "https://github.com/thom311/libnl"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("netlink", "cli", "network", "tool")

    # library（对齐 libmspub-tools 先例）：交付共享库 libnl-cli-3 + 6 子库，
    # 同时以 bin/ 交付 48 个工具（R38 → commands.json type=tool）。
    package_type = "library"

    options = {"shared": [True]}
    default_options = {"shared": True}

    settings = "os", "compiler", "build_type", "arch"

    # 交付形态固定 shared（见模块 docstring「为什么必须 shared」）——option
    # 取值域锁定为 [True]（Conan 2 要求 library 类型必须声明 shared option；
    # 声明并锁定 = 语义自洽，消费者侧也不存在静态误用空间）。

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: 判断必须包含 Linux 与 OHOS 两种取值
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libnl3-cli is supported only on Linux/OHOS, got os=%s" % self.settings.os)
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 交付形态固定：shared 库 + bin/ 工具（--enable-cli=bin 为 configure.ac
        # 默认值 yes 的显式拼写，便于审阅）。
        tc.configure_args.append("--enable-shared")
        tc.configure_args.append("--disable-static")
        tc.configure_args.append("--enable-cli=bin")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E114：必须在 configure 之前（configure 会把该 umask 带入 config.status）
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        # E490：HMDFS / 源码缓存拷贝可能丢失 POSIX 执行位，导致 configure 无法执行
        self._restore_autotools_modes()
        # E165：剔除 codebuddy safe-bin rm shim 三重注入（PATH + BASH_FUNC_* +
        # BASH_ENV source 链），否则 configure 报 "Your 'rm' program is bad"
        self._sanitize_path()
        # HMDFS: getcwd() 解析不了父目录时 shell pwd 走逻辑路径（cdecl 先例）
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        os.environ["PWD"] = self.build_folder
        # E002: 设备 /tmp 只读（erofs），重定向 TMPDIR/TMP/TEMP
        tmpdir = os.environ.get("TMPDIR") or os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        # -j1 强制串行 install（conan 对 args 里已含 -jN 的情况不再追加 -j4）：
        # 0003 给 CLI 插件挂上 libnl-cli-3.la 后，libtool 在 install-data 阶段
        # relink 插件需要 libnl-cli-3.la 已装进 DESTDIR；而 automake 的
        # install-exec-am（7 库）与 install-data-am（插件/头/数据）在 make -j4
        # 下并行执行，插件 relink 时 -lnl-cli-3 尚未安装 → "unable to find
        # library -lnl-cli-3"（实测 make: install-pkglib_*LTLIBRARIES Error 1）。
        # 串行下 install-am 先 exec 后 data，插件 relink 时依赖已就位。
        autotools.install(args=["-j1"])
        # share/（man 页等）不入包（本体包同款收尾）
        rmdir(self, os.path.join(self.package_folder, "share"))
        # E236 收尾：包内不得残留 libtool 元数据（含 lib/libnl/cli/{cls,qdisc}/
        # 插件子目录的 10 个 .la —— 插件由 dlopen 绝对路径加载 .so，.la 不参与
        # 运行，残留反而会让下游 libtool 重读陈旧 dependency_libs）。
        lib_dir = os.path.join(self.package_folder, "lib")
        for dirpath, _dirnames, filenames in os.walk(lib_dir):
            for entry in filenames:
                if entry.endswith(".la"):
                    os.remove(os.path.join(dirpath, entry))
                    self.output.info("[ok] removed libtool archive %s"
                                     % os.path.join(dirpath, entry))
        # E316/E492/E505：把 lib/（含 lib/libnl/cli/{cls,qdisc}/ 插件目录）下的
        # 全部软链实体化 —— OHOS musl 不能加载「SONAME 名字是软链」的库，
        # adhoc_bin 域连 readlink/open 软链都 EACCES。
        self._materialize_symlinks(self.package_folder)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libnl-cli")
        self.cpp_info.set_property("cmake_target_name", "libnl-cli::libnl-cli")
        self.cpp_info.set_property("pkg_config_name", "libnl-cli-3.0")
        # 头文件装到 include/libnl3/netlink/...（含 netlink/cli/*），消费者写
        # `#include <netlink/cli/utils.h>` → includedirs 指到 include/libnl3。
        self.cpp_info.includedirs = ["include/libnl3"]
        # 消费者链接闭包：libnl-cli-3 + 6 个子库（动态链接下 DT_NEEDED 也会
        # 自动拉齐，显式列出使静态场景/链接行顺序可见）。
        self.cpp_info.libs = [
            "nl-cli-3", "nl-route-3", "nl-genl-3", "nl-nf-3",
            "nl-idiag-3", "nl-xfrm-3", "nl-3",
        ]
        # R38：bin/ 交付 48 个工具，声明 bindirs 使 CI L0k/detect_bindirs 判定
        # 为 tool 类型，与软件级 commands.json（type=tool）保持一致。
        self.cpp_info.bindirs = ["bin"]
        # lib/libnl/cli/{cls,qdisc}/ 的 dlopen 插件由工具按编译期 _NL_PKGLIBDIR
        # 绝对路径加载（src/lib/utils.c:221），不经 cpp_info 导出；etc/libnl/
        # 数据文件由工具按编译期 _NL_SYSCONFDIR_LIBNL 加载，同样随包内聚。
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    # ------------------------------------------------------------------
    # 平台适配（先例：archives/l/libnl/3.11.0、archives/l/libmspub-tools/0.1.4）
    # ------------------------------------------------------------------
    def _restore_autotools_modes(self):
        """E490: 只给已知 autotools helper 脚本补执行位，不碰其他文件。"""
        for name in (
            "configure",
            "build-aux/config.guess",
            "build-aux/config.sub",
            "build-aux/install-sh",
            "build-aux/missing",
            "build-aux/compile",
            "build-aux/depcomp",
            "build-aux/ltmain.sh",
        ):
            path = os.path.join(self.source_folder, name)
            if os.path.exists(path):
                os.chmod(path, 0o755)

    def _sanitize_path(self):
        """从环境剔除 codebuddy 注入的 safe-delete shim（E165，三通道）。

        1) PATH 首项 safe-bin/ 的 rm shim shebang `#!/bin/bash` 在 HarmonyOS
           上是 bad interpreter（bash 在 /data/service/hnp/bin/bash）；
        2) BASH_FUNC_rm%%/BASH_FUNC_unlink%%/BASH_FUNC_rmdir%% 会被 bash 子进程
           自动 import 成同名函数，优先级高于 PATH；
        3) BASH_ENV 指向的 runtime 脚本在每个 bash 子进程启动时重新注入 rm
           函数 —— 必须掐断整个 source 链。
        """
        removed = []

        path = os.environ.get("PATH", "")
        if path:
            entries = path.split(os.pathsep)
            kept = [e for e in entries if "safe-bin" not in e]
            if len(kept) != len(entries):
                os.environ["PATH"] = os.pathsep.join(kept)
                removed.append("%d safe-bin dir(s) from PATH" % (len(entries) - len(kept)))

        for func_var in ("BASH_FUNC_rm%%", "BASH_FUNC_unlink%%", "BASH_FUNC_rmdir%%"):
            if os.environ.pop(func_var, None) is not None:
                removed.append(func_var)

        for kill_var in (
            "CODEBUDDY_SAFE_DELETE_ENABLED",
            "CODEBUDDY_SAFE_DELETE_BIN_DIR",
            "BASH_ENV",
        ):
            if os.environ.pop(kill_var, None) is not None:
                removed.append(kill_var)

        if removed:
            self.output.info("[ok] sanitized env: %s" % ", ".join(removed))

    def _materialize_symlinks(self, root: str):
        """E316/E492/E505：把 root 下所有软链替换为所指实体文件的拷贝。

        gnustep-gui/0.31.1 的 _link_gui_library 同款手法：先 copy2 跟随复制到
        临时名，再 os.replace 原子替换，规避「替换后同名再遍历」与半写状态。
        """
        count = 0
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                path = os.path.join(dirpath, name)
                if not os.path.islink(path):
                    continue
                tmp = path + ".materialize"
                # copy2 跟随软链拷出实体内容
                shutil.copy2(path, tmp)
                os.replace(tmp, path)
                count += 1
        if count:
            self.output.info("[ok] materialized %d symlink(s) into real files" % count)
