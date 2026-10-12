#!/usr/bin/env python3
"""Conan recipe for tnftpd 20231001 — NetBSD FTP daemon port (Autotools).

Builds and installs the ``tnftpd`` FTP server daemon (intended to run under
inetd).  The tarball ships a generated ``configure`` (no autoreconf needed),
and — unlike radvd — the parser ``ftpcmd.c`` is *not* in the release tarball:
it is generated from ``ftpcmd.y`` at build time, so **bison/yacc is a hard
build-time dependency** (configure errors "missing bison or yacc" without it).

OHOS notes
----------
* configure runs ``config.guess``/``config.sub`` because ``LT_INIT()``
  internally calls ``AC_CANONICAL_HOST``.  The shipped 2018-vintage
  config.guess does not recognise ``uname -s = HarmonyOS``, so configure
  fails with "cannot guess build type"; config.sub likewise rejects the
  ``aarch64-unknown-linux-ohos`` triplet.  Patches 0001/0002 add the
  HarmonyOS branch and the ``linux-ohos*`` OS entries (native build: no
  --build/--host/--target per R1).
* autoconf's ``configure`` creates its scratch dir with
  ``(umask 077 && mktemp -d "./confXXXXXX")``; on the OHOS shared
  filesystem (HMDFS, setgid parent) that yields an unwritable
  ``drwx--S---`` directory -> "could not setup config files machinery".
  Patch 0003 replaces ``mktemp`` with ``false`` so the script's own
  ``mkdir`` fallback creates the temp dir, and turns both ``umask 077``
  into ``umask 022`` so the created ``./conf$-$RANDOM`` is writable by
  config.status (E011/E112/E114 family; libradsec/avfs/autocutsel same
  method).  This is the single autoconf temp-dir block, reused by the
  generated config.status via ``$ac_tmp``.
* E074: parallel make hits the HMDFS jobserver fifo EPERM -> ``make -j1``.
* getcwd on HMDFS: the toolchain bash (profile CONFIG_SHELL/SHELL =
  /data/service/hnp/bin/bash) fails getcwd() on the HMDFS build dir, and
  this autoconf 2.69 configure re-execs itself under $CONFIG_SHELL, so
  ``ac_pwd=`pwd` `` aborts with "working directory cannot be determined".
  On OHOS build() runs configure via ``sh`` with CONFIG_SHELL/SHELL=/bin/sh
  (mksh) which can getcwd; make/install append ``SHELL=/bin/sh``
  (libfec/libdisasm same proven fix).
* The daemon is installed via ``libexec_PROGRAMS`` to ``$prefix/libexec``;
  ``package()`` renames it into ``$prefix/bin`` so ``tnftpd`` lands on PATH
  and the consumer test can invoke it.  Private helper libraries
  (libnetbsd.la, libls.la) are ``noinst_LTLIBRARIES`` and are not installed.
* Optional PAM / S/Key / blocklist auth are explicitly disabled: none are
  published for OHOS and the daemon works with Unix passwd auth alone.
* Upstream ships NO tests (no test dir, no TESTS/check target, no gtest).
  Verification is done in test_package/ via the self-terminating
  ``-C <user>`` access-check invocation plus ELF/executable checks.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class TnftpdConan(ConanFile):
    name = "tnftpd"
    version = "20231001"
    description = (
        "tnftpd: a portable NetBSD FTP server daemon (lukemftpd), "
        "runnable under inetd with IPv6, ftpusers/ftpd.conf support"
    )
    license = "BSD-2-Clause"  # NetBSD-style 2-clause, see COPYING
    homepage = "https://www.NetBSD.org/"
    url = "https://cdn.netbsd.org/pub/NetBSD/misc/tnftp/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: 平台判断必须同时接受 Linux 与 OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tnftpd targets Unix-like kernels; got os="
                + str(self.settings.os))

    def build_requirements(self):
        # ftpcmd.c 由 ftpcmd.y 现场生成（release 包不含），configure 的
        # AC_PROG_YACC 硬性要求 bison/yacc。bison/3.8.2 已在制品仓发布
        # （radvd 2.20 同款 tool_require，R36 已核）。
        self.tool_requires("bison/3.8.2")

    def layout(self):
        basic_layout(self)  # in-source 构建（tarsnap/radvd 同款）

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 可选认证组件 OHOS 制品仓未发布，显式禁用保证确定性
        tc.configure_args.append("--without-pam")
        tc.configure_args.append("--without-skey")
        tc.configure_args.append("--without-sia")
        tc.configure_args.append("--with-blocklist=no")
        tc.generate()
        # 保存 configure 参数供 build() 用 sh 显式调用时复用
        # （libfec 同款；避免 build() 依赖 Autotools 辅助内部再跑一遍生成）
        args_file = os.path.join(self.build_folder, "conan", "configure_args.txt")
        os.makedirs(os.path.dirname(args_file), exist_ok=True)
        with open(args_file, "w", encoding="utf-8") as f:
            f.write(" ".join(tc.configure_args))

    def _setup_fs_env(self):
        """HMDFS（setgid、getcwd 不可达、/tmp 只读）下的构建期环境准备：
        * 一个可写 TMPDIR/TMP/TEMP（HMBS 注入的候选优先，回退到 build 内
          $(build_folder)/hmbs-tmp），供 configure/make/config.status 的
          临时文件使用（E002；apertium/radvd 同法）；
        * PWD 钉到 build_folder——HMDFS 对该目录 getcwd() 失败时，让 shell
          的 `pwd` 回落到 $PWD（working directory cannot be determined）；
        * SHELL/CONFIG_SHELL 统一钉到 /bin/sh（mksh，无 getcwd 问题），
          避免 autoconf 2.69 前导 CONFIG_SHELL 重执行块切到 getcwd 失败的
          hnp bash（libfec/libdisasm 同墙）。

        仅在 os.environ 上就地设置，让后续 configure/make/install 的每个
        self.run 子进程都能读到；不影响配方 / package() 的其它路径取值。
        """
        if str(self.settings.os) != "OHOS":
            return
        cand = []
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key, "")
            if val:
                cand.append(val)
        try:
            import json
            caps = json.loads(os.environ.get("HMBS_PLATFORM_CAPABILITIES", "{}"))
            t = caps.get("tmpdir", "")
            if t:
                cand.append(t)
        except Exception:
            pass
        fb = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if fb:
            cand.append(fb)
        cand.append(os.path.join(self.build_folder, "hmbs-tmp"))
        for d in cand:
            if not d:
                continue
            try:
                os.makedirs(d, exist_ok=True)
                if os.path.isdir(d):
                    for key in ("TMPDIR", "TMP", "TEMP"):
                        os.environ[key] = d
                    break
            except OSError:
                continue
        os.environ["PWD"] = self.build_folder
        os.environ["SHELL"] = "/bin/sh"
        os.environ["CONFIG_SHELL"] = "/bin/sh"

    def build(self):
        # 三个 OHOS 移植补丁：config.guess / config.sub / configure(umask；
        # 并把 autoconf 临时目录的 mktemp 换成 false，强制走 mkdir fallback)
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            # OHOS HMDFS 上工具链 hnp bash 对工作目录 getcwd() 失败
            # （PWD 为空，errno=Bad address），而本包是 autoconf 2.69 生成的
            # configure：前导 CONFIG_SHELL 重执行块会把自己切到那个坏 bash
            # 上，随后 ac_pwd=`pwd` 挂掉 ⇒ "working directory cannot be
            # determined"（libfec/libdisasm 同墙）。先做 HMDFS 文件系统级
            # 环境准备（可写 TMPDIR + PWD + SHELL/CONFIG_SHELL=/bin/sh），
            # 再用 sh 显式调用 configure；变量前缀压过 buildenv 的
            # CONFIG_SHELL=/data/service/hnp/bin/bash。
            self._setup_fs_env()
            configure_cmd = os.path.join(self.source_folder, "configure")
            with open(os.path.join(self.build_folder, "conan",
                                   "configure_args.txt"), encoding="utf-8") as f:
                configure_args = f.read().strip()
            self.run(
                f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh "{configure_cmd}" '
                f'{configure_args}',
                env="conanbuild")
        else:
            autotools = Autotools(self)
            autotools.configure()
        autotools = Autotools(self)
        # E074: make -j1；OHOS 上再把 SHELL 钉到 /bin/sh（make 配方行/install
        # 不再落到 getcwd 失败的 hnp bash 上，libfec 同款）。
        make_shell = ["SHELL=/bin/sh"] if str(self.settings.os) == "OHOS" else []
        autotools.make(args=["-j1"] + make_shell)
        # 上游无测试套件：无 test/、TESTS、check 目标 ⇒ 不执行 make check
        # （见 test_package/MANIFEST.yml upstream_test_audit）

    def _write_install_shim(self):
        """HMBS 的 install shim（runtime/<task>/bin/install）只接受单文件
        两参调用；automake 批量安装 `install -c -m 644 f1..fN dir/` 直接
        exit 64 (EX_USAGE)（本包 examples 安装 ftpd.conf+ftpusers 命中；
        adms 2.3.7 / libgsf 1.14.58 / avahi 0.9_rc5 / xeyes 1.3.1 已过门禁
        同款）。这里写一个 cp/mkdir shim 替代：解析 -c/-m/-d 等选项，
        末参为目标（目录或文件），逐源 cp 复制；HMFS 不支持 chmod
        （HMBS_CAP_CHMOD=0），chmod 步骤容错跳过。返回 shim 绝对路径
        供 Makefile INSTALL 重定向。
        """
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        # HMFS 在创建时按 open mode 给权限（chmod 能力为 0），用 os.open
        # 指定 0o755 直接生成可执行 shim（adms 2.3.7 / avahi 同款）。
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "if [ \"$count\" -gt 1 ]; then\n"
                    "  # 多源形态：末参是目标目录，先确保目录存在\n"
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  mkdir -p \"$(dirname \"$dest\")\"\n"
                    "fi\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  # HMFS 不支持 chmod（HMBS_CAP_CHMOD=0），设权限失败不阻断复制\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then\n"
                    "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else\n"
                    "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                    "    fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:  # noqa: BLE001 - 写 shim 失败不静默，关闭 fd 后上抛
            os.close(fd)
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass  # HMFS 可能不支持 chmod（HMBS_CAP_CHMOD=0）
        return install

    def _redirect_install_to_shim(self, root, shim_install):
        # configure 已把探测到的 install 路径写死进各生成 Makefile 的
        # INSTALL 变量。把 `INSTALL = <.../install ...>` 替换为
        # `INSTALL = <shim>`，INSTALL_DATA/INSTALL_PROGRAM 默认
        # `${INSTALL} -m 644`/`${INSTALL}` 引用 ${INSTALL} 自动重算，
        # make install 全程走 shim（adms 2.3.7 / avahi 0.9_rc5 同款）。
        for _root, _dirs, _files in os.walk(root):
            if "Makefile" not in _files:
                continue
            _mp = os.path.join(_root, "Makefile")
            try:
                with open(_mp, "r", encoding="utf-8", errors="ignore") as _f:
                    _content = _f.read()
            except OSError:
                continue
            if "INSTALL =" not in _content:
                continue
            _lines = []
            _changed = False
            for _line in _content.splitlines(True):
                _stripped = _line.lstrip()
                if _stripped.startswith("INSTALL = ") and "/install" in _stripped:
                    _indent = _line[:len(_line) - len(_stripped)]
                    _lines.append(f"{_indent}INSTALL = {shim_install}\n")
                    _changed = True
                else:
                    _lines.append(_line)
            if _changed:
                with open(_mp, "w", encoding="utf-8") as _f:
                    _f.write("".join(_lines))

    def package(self):
        # HMBS 的 install shim 只接受单文件两参调用，automake 批量安装
        # `install -c -m 644 f1..fN dir/` 报 exit 64 (EX_USAGE)（examples
        # 的 ftpd.conf+ftpusers 批量安装即命中）。写 cp/mkdir shim 并把它
        # 重定向进 configure 生成的各 Makefile 的 INSTALL 变量，
        # INSTALL_DATA/INSTALL_PROGRAM 引用 ${INSTALL} 自动重算，
        # make install 全程走 shim（adms 2.3.7 / libgsf 1.14.58 / avahi
        # 0.9_rc5 / xeyes 1.3.1 已过门禁同款）。
        autotools = Autotools(self)
        install_shell = ["SHELL=/bin/sh"] if str(self.settings.os) == "OHOS" else []
        if str(self.settings.os) == "OHOS":
            shim = self._write_install_shim()
            self._redirect_install_to_shim(self.build_folder, shim)
        autotools.install(args=["-j1"] + install_shell)
        # tnftpd 是 libexec_PROGRAMS，默认装到 $prefix/libexec/tnftpd；
        # 在 package() 阶段归一化到 $prefix/bin，便于 PATH 与消费者测试。
        libexec_dir = os.path.join(self.package_folder, "libexec")
        bin_dir = os.path.join(self.package_folder, "bin")
        src = os.path.join(libexec_dir, "tnftpd")
        if os.path.isfile(src):
            os.makedirs(bin_dir, exist_ok=True)
            os.rename(src, os.path.join(bin_dir, "tnftpd"))
            if not os.listdir(libexec_dir):
                os.rmdir(libexec_dir)
        # 私有 noinst 库（libnetbsd/libls）本就不会被安装，无需清理；
        # 顺带清掉任何残留 .la，防止 libtool 的绝对路径污染（R19）。
        la_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(la_dir):
            for root, _dirs, files in os.walk(la_dir):
                for fn in files:
                    if fn.endswith(".la"):
                        os.remove(os.path.join(root, fn))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_find_mode", "none")
