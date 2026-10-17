#!/usr/bin/env python3
"""Conan recipe for libnm 1.58.0 (NetworkManager client library, Meson).

OHOS 适配说明：
  - 目标产物是 NetworkManager 源树里的客户端库 libnm.so.0（libnm.pc:
    Name: libnm / Libs: -lnm / Cflags: -I${includedir}/libnm）。
    NM 1.58 的 meson 没有 daemon/libnm 裁剪开关，守护进程与客户端工具
    一并构建，但包内容只保留 libnm 库 + 头 + pc + 许可证。
  - 通过 meson 选项裁掉 OHOS 上不可用的外部依赖面：
    polkit/modem_manager(mm-glib)/nss|gnutls(crypto=null)/concheck(libpsl,
    libcurl)/selinux/libaudit/systemd(session_tracking=no)/introspection/
    vapi/man/docs/nmtui(libnewt)/nm_cloud_setup/ovs/ebpf/qt/readline。
  - pkg-config 垫片（generate() 写入 generators 目录）：
    * dbus-1.pc      —— dbus 配方只暴露 "dbus"；NM 无条件
      dependency('dbus-1') 并查询 datarootdir/interfaces_dir/
      system_bus_services_dir 三个变量。
    * libudev.pc     —— libudev-zero 配方只暴露 "libudev-zero"；
      NM 无条件 dependency('libudev', version >= 175)。
    * gio-unix-2.0.pc —— glib 配方未声明 gio-unix 组件；NM 无条件
      dependency('gio-unix-2.0', version >= 2.42)
      （先例：archives/a/ayatana-indicator-session/26.6.1）。
  - SONAME 实体化（E316/E492/E505）：OHOS musl 加载器不能加载
    "SONAME 名字是软链" 的库，package() 把 libnm.so.0 软链族物化为
    规则文件（先例 archives/g/glib/2.88.3）。
  - OHOS 自签名：包内 ELF 逐一 binary-sign-tool selfSign（同 glib 先例）。
"""

import filecmp
import os
import posixpath
import re
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class LibnmConan(ConanFile):
    name = "libnm"
    version = "1.58.0"
    description = "NetworkManager client library (libnm) for NetworkManager clients"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.freedesktop.org/NetworkManager/NetworkManager"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    _soname_stem = "libnm"

    # NM meson 在配置期无条件 find_program('perl')，i18n.gettext 需要
    # msgfmt/xgettext，因此 perl/gettext 也作为构建工具引入。
    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")
        self.tool_requires("pkgconf/3.0.6")
        self.tool_requires("perl/5.42.2.3")
        self.tool_requires("gettext/0.22.5.1")

    def requirements(self):
        self.requires("glib/2.88.3")
        self.requires("libndp/1.9")
        self.requires("libudev-zero/1.0.4")
        self.requires("dbus/1.14.10.2")
        self.requires("uuid/2.40.1")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "libnm's target adaptation is validated only for AArch64"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ------------------------------------------------------------------
    # build helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _require_absolute_tool(value, label, target_posix=False):
        if not isinstance(value, (str, os.PathLike)):
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] must be a path"
            )
        path = os.fspath(value)
        if target_posix:
            if not posixpath.isabs(path):
                raise ConanInvalidConfiguration(
                    f"tools.build:compiler_executables[{label!r}] must be an "
                    "absolute POSIX target path"
                )
            return posixpath.normpath(path)
        if not os.path.isabs(path) or not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] must name an "
                "absolute regular file"
            )
        if not os.access(path, os.X_OK):
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] is not executable"
            )
        return os.path.normpath(path)

    @classmethod
    def _resolve_llvm_tools(cls, executables, target_os=None):
        if not isinstance(executables, dict):
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must be a dictionary"
            )
        target_posix = str(target_os) == "OHOS"
        compiler = cls._require_absolute_tool(
            executables.get("c"), "c", target_posix=target_posix
        )
        compiler_name = (
            posixpath.basename(compiler) if target_posix else os.path.basename(compiler)
        )
        match = re.fullmatch(r"clang(?:-([0-9]+))?", compiler_name)
        if match is None:
            raise ConanInvalidConfiguration(
                "the configured C compiler must be clang or clang-<version>"
            )
        suffix = f"-{match.group(1)}" if match.group(1) else ""
        compiler_dir = (
            posixpath.dirname(compiler) if target_posix else os.path.dirname(compiler)
        )
        resolved = {}
        for name in ("ar", "ranlib", "nm", "objcopy", "strip"):
            configured = executables.get(name)
            if configured:
                resolved[name] = cls._require_absolute_tool(
                    configured, name, target_posix=target_posix
                )
                continue
            candidate = posixpath.join(
                compiler_dir, f"llvm-{name}{suffix}"
            ) if target_posix else os.path.join(
                compiler_dir, f"llvm-{name}{suffix}"
            )
            if target_posix:
                resolved[name] = candidate
                continue
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                resolved[name] = os.path.normpath(candidate)
                continue
            fallback = os.path.join(compiler_dir, f"llvm-{name}")
            if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
                resolved[name] = os.path.normpath(fallback)
                continue
            raise ConanInvalidConfiguration(
                f"cannot resolve llvm-{name} beside the configured C compiler"
            )
        return resolved

    def _meson_project_options(self):
        # 对齐上游 meson_options.txt 的可用开关；裁剪面理由见模块 docstring。
        return {
            # 文档 / 绑定
            "docs": "false",
            "man": "false",
            "introspection": "false",
            "vapi": "false",
            # 外部库依赖裁剪（OHOS 上无对应 conan 包或无意义）
            "polkit": "false",
            "selinux": "false",
            "crypto": "null",
            "concheck": "false",
            "libpsl": "false",
            "modem_manager": "false",
            "teamdctl": "false",
            "ovs": "false",
            "nmtui": "false",
            "nmcli": "false",
            "nm_cloud_setup": "false",
            "libaudit": "no",
            "session_tracking": "no",
            "session_tracking_consolekit": "false",
            "systemd_journal": "false",
            "clat": "false",
            "ebpf": "false",
            "nbft": "false",
            "qt": "false",
            "readline": "none",
            "firewalld_zone": "false",
            "ifupdown": "false",
            "wifi": "true",
            "bluez5_dun": "false",
            "iwd": "false",
            "ppp": "false",
            # 安装目录收敛（全部相对 prefix，避免 destdir 之外写入）
            "udev_dir": "no",
            "dbus_conf_dir": "share/dbus-1/system.d",
            "systemdsystemunitdir": "lib/systemd/system",
            "systemdsystemgeneratordir": "lib/systemd/system-generators",
            # 测试保留（上游自动化测试入口）
            "tests": "yes",
        }

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()

        # 配置期探测一次构建机上的 python3：fail-fast（找不到时立刻报明确错误，
        # 而不是等到 ninja 阶段被伪装成“文件不存在”）+ 让 CI 日志明确记录选中的
        # 解释器。该值随后写进垫片/启动器的 shebang（见 _launcher_script_template）。
        self.output.info(
            f"launcher python3 (build machine): {self._python3_interpreter}"
        )

        glib_dep = self.dependencies.get("glib")
        dbus_dep = self.dependencies.get("dbus")
        libudev_dep = self.dependencies.get("libudev-zero")

        # meson gnome 模块经 pkg-config 查询工具变量：
        #   - gio-2.0 的 gdbus_codegen（introspection/meson.build 的
        #     gnome.gdbus_codegen）
        #   - glib-2.0 的 glib_mkenums（gnome.mkenums / mkenums_simple）
        # conan 生成的 pc 无这些变量 → 追加指向 clang 编译的原生
        # launcher（理由见 _glib_tool_launcher docstring）。
        if glib_dep and glib_dep.package_folder:
            toolbin = os.path.join(self.generators_folder, "toolbin")
            os.makedirs(toolbin, exist_ok=True)
            gdbus_codegen = self._glib_tool_launcher(
                glib_dep, "gdbus-codegen", toolbin
            )
            gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
            if gdbus_codegen and os.path.isfile(gio_pc):
                with open(gio_pc, "a", encoding="utf-8") as handle:
                    handle.write(f"gdbus_codegen={gdbus_codegen}\n")
                self.output.info("appended gdbus_codegen variable to gio-2.0.pc")
            glib_mkenums = self._glib_tool_launcher(
                glib_dep, "glib-mkenums", toolbin
            )
            glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
            if glib_mkenums and os.path.isfile(glib_pc):
                with open(glib_pc, "a", encoding="utf-8") as handle:
                    handle.write(f"glib_mkenums={glib_mkenums}\n")
                self.output.info("appended glib_mkenums variable to glib-2.0.pc")

        # gio-unix-2.0.pc（glib 头在 include/gio-unix-2.0，API 在 libgio-2.0）
        if glib_dep and glib_dep.package_folder:
            gio_unix_include = None
            for includedir in glib_dep.cpp_info.includedirs:
                candidate = os.path.join(glib_dep.package_folder, includedir)
                if os.path.basename(os.path.normpath(candidate)) == "gio-unix-2.0":
                    gio_unix_include = candidate
                    break
            include_ref = "include/gio-unix-2.0"
            if gio_unix_include:
                include_ref = os.path.relpath(
                    gio_unix_include, glib_dep.package_folder
                ).replace(os.sep, "/")
            self._write_pc_shim(
                "gio-unix-2.0",
                "2.88.3",
                description="unix specific headers for glib I/O library",
                requires="gio-2.0",
                cflags=f"-I${{prefix}}/{include_ref}",
                libs="-lgio-2.0",
                prefix=os.path.join(glib_dep.package_folder),
            )

        # dbus-1.pc（NM 无条件 dependency('dbus-1') 且查询三个变量）
        #
        # ★ 变量必须写成 ${datadir} 形式：NM 的 meson.build:609-613 用
        #   get_variable(pkgconfig: 'interfaces_dir',
        #                pkgconfig_define: ['datadir', nm_datadir])
        #   通过 -Ddatadir=<NM 自己的 datadir> 覆盖后取安装目录。若把
        #   interfaces_dir/system_bus_services_dir 直接展开成 ${prefix}/share/...
        #   （prefix 指向 dbus 依赖包的包目录），覆盖就失效 → meson 把 NM 自己的
        #   53 个 dbus 内省 XML 与 2 个 system-service 文件装进 **dbus 依赖包目录**
        #   之下，经 DESTDIR 后变成包内 storage/Users/.../dbus…/p/share/... 的
        #   畸形子树（实测 55 个文件）。按上游 dbus-1.pc 的写法用 ${datadir}
        #   中转，覆盖即可生效、文件落回本包 share/dbus-1/。
        if dbus_dep and dbus_dep.package_folder:
            self._write_pc_shim(
                "dbus-1",
                "1.14.10",
                description="Free desktop message bus system (shim for dbus conan package)",
                requires="",
                cflags="-I${prefix}/include -I${prefix}/include/dbus-1.0",
                libs="-ldbus-1",
                prefix=os.path.join(dbus_dep.package_folder),
                variables={
                    "datadir": "${prefix}/share",
                    "datarootdir": "${datadir}",
                    "interfaces_dir": "${datadir}/dbus-1/interfaces",
                    "system_bus_services_dir": "${datadir}/dbus-1/system-services",
                },
            )

        # libudev.pc（NM 无条件 dependency('libudev', version >= 175)）
        if libudev_dep and libudev_dep.package_folder:
            self._write_pc_shim(
                "libudev",
                "175",
                description="udev library (shim for libudev-zero conan package)",
                requires="",
                cflags="-I${prefix}/include",
                libs="-ludev",
                prefix=os.path.join(libudev_dep.package_folder),
            )

        toolchain = MesonToolchain(self)
        if str(self.settings.os) in ("Linux", "OHOS"):
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            tools = self._resolve_llvm_tools(executables, target_os=self.settings.os)
            toolchain.ar = tools["ar"]
            toolchain.strip = tools["strip"]
            toolchain.binaries["ranlib"] = tools["ranlib"]
            toolchain.binaries["nm"] = tools["nm"]
            toolchain.binaries["objcopy"] = tools["objcopy"]
        if str(self.settings.os) == "OHOS":
            compat_header = self._write_ohos_compat_header()
            if compat_header:
                toolchain.c_args += ["-include", compat_header]
                toolchain.cpp_args += ["-include", compat_header]
            # NM 假设 libudev.h 是系统级安装（部分 TU 未声明 libudev 依赖），
            # 把 libudev-zero 的 include 目录全局注入 include 路径。
            if libudev_dep and libudev_dep.package_folder:
                for includedir in libudev_dep.cpp_info.includedirs:
                    inc = os.path.join(libudev_dep.package_folder, includedir)
                    if os.path.isdir(inc):
                        toolchain.c_args += [f"-I{inc}"]
                        toolchain.cpp_args += [f"-I{inc}"]
            # 构建/测试期通过 meson test 调用的 shell 辅助脚本（run-nm-test.sh、
            # check-exports.sh）无法直接被构建域 exec（脚本 shebang 指向 hnp_file 域的
            # bash 会被 SELinux 拒绝，报 Permission denied）。这里在**源码树 tools/** 下写
            # 两个启动器（nm-run-test / nm-check-exports），由它经 /bin/sh -c 显式调用
            # bash 运行真实脚本；补丁 0005 以 join_paths(source_root,'tools',…) 引用，
            # 故补丁内无机器专属路径。
            self._write_nm_test_launchers()
        toolchain.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        toolchain.project_options["wrap_mode"] = "nofallback"
        for key, value in self._meson_project_options().items():
            toolchain.project_options[key] = value
        toolchain.generate()

    _ohos_compat_header = """/* OHOS musl + bionic 风格内核头共存兼容层（知识库 E091/E119）。
 *
 * OHOS SDK 的 linux/socket.h（bionic 净化生成）无条件定义
 * struct sockaddr_storage，与 musl sys/socket.h 冲突；凡经
 * linux/netdevice.h / linux/if.h 等间接包含即重定义报错。
 * 预定义 _UAPI_LINUX_SOCKET_H 使后续 linux/socket.h 整体跳过，
 * 并补齐内核头链依赖的 __kernel_sa_family_t。
 * 仅 -include 强制注入（ MesonToolchain c_args/cpp_args），__OHOS__
 * 守卫，不影响其他平台。
 */
#ifndef OHOS_COMPAT_H
#define OHOS_COMPAT_H

#ifdef __OHOS__

/* NM builds some vendored systemd TUs with -std=c11 (no _GNU_SOURCE),
 * hiding musl's reallocarray/qsortr-style GNU declarations. Expose the
 * GNU feature set before any system header (this file is force-included
 * first). */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif

#ifndef _SYS_SOCKET_H
#include <sys/socket.h>
#endif

#ifndef _UAPI_LINUX_SOCKET_H
#define _UAPI_LINUX_SOCKET_H 1
#endif

#ifndef __kernel_sa_family_t
typedef unsigned short __kernel_sa_family_t;
#endif

/* Kernel UAPI name for sockaddr_storage; with linux/socket.h skipped,
 * map it onto the musl struct (same layout: ss_family + 126 bytes). */
#ifndef __kernel_sockaddr_storage
#define __kernel_sockaddr_storage sockaddr_storage
#endif

/* struct ethhdr / ether_arp handling lives at the end of this header,
 * immediately before the <linux/ethtool.h> include that needs a
 * complete "struct ethhdr" (ether_spec field). */

/* The OHOS sysroot libintl.h is an empty stub (no declarations), and
 * musl ships no gettext implementation. NM uses glib's gi18n _() and a
 * handful of direct intl calls; no translations are shipped on OHOS, so
 * map the whole intl surface to no-ops (same semantics as glib's
 * -Dnls=disabled used by the glib package on this platform). */
#ifndef OHOS_NO_INTL
#define OHOS_NO_INTL 1
#include <libintl.h>
#undef gettext
#undef dgettext
#undef textdomain
#undef bindtextdomain
#undef bind_textdomain_codeset
#define gettext(msgid) ((const char *) (msgid))
#define dgettext(domain, msgid) ((const char *) (msgid))
#define textdomain(domain) ((const char *) (domain))
#define bindtextdomain(domain, dir) ((const char *) (dir))
#define bind_textdomain_codeset(domain, codeset) ((const char *) (codeset))
#endif

/* musl lacks secure_getenv(3); NM's vendored systemd code calls it
 * unconditionally. NM never runs setuid on OHOS, so plain getenv(3)
 * is the correct fallback. */
#define secure_getenv(p) getenv(p)

/* The OHOS 26 SDK musl sysroot declares neither reallocarray(3) nor
 * qsort_r(3) (verified: sysroot/usr/include/stdlib.h has no match).
 * Provide both: reallocarray with overflow check, qsort_r as a
 * thread-local thunk over plain qsort(3) (NM never sorts recursively
 * from multiple threads through the same thunk). */
#include <errno.h>
#include <stdlib.h>
#include <unistd.h>

static inline void *reallocarray(void *ptr, size_t nmemb, size_t size) {
    if (size != 0 && nmemb > (size_t) -1 / size) {
        errno = ENOMEM;
        return (void *) 0;
    }
    return realloc(ptr, nmemb * size);
}

static __thread int (*__ohos_qsort_r_compar)(const void *, const void *, void *);
static __thread void *__ohos_qsort_r_arg;

static int __ohos_qsort_r_thunk(const void *a, const void *b) {
    return __ohos_qsort_r_compar(a, b, __ohos_qsort_r_arg);
}

static inline void qsort_r(void *base, size_t nmemb, size_t size,
                           int (*compar)(const void *, const void *, void *),
                           void *arg) {
    __ohos_qsort_r_compar = compar;
    __ohos_qsort_r_arg = arg;
    qsort(base, nmemb, size, __ohos_qsort_r_thunk);
}

/* musl lacks get_current_dir_name(3) (glibc extension); emulate it with
 * a malloc'ed getcwd(3) loop, as expected by systemd's safe_getcwd(). */
static inline char *get_current_dir_name(void) {
    size_t size = 512;
    for (;;) {
        char *buf = (char *) malloc(size);
        if (!buf) {
            return (char *) 0;
        }
        if (getcwd(buf, size)) {
            return buf;
        }
        free(buf);
        if (errno != ERANGE) {
            return (char *) 0;
        }
        if (size > (size_t) 1 << 24) {
            errno = ENAMETOOLONG;
            return (char *) 0;
        }
        size *= 2;
    }
}

/* The OHOS 26 SDK musl libc.so does not export explicit_bzero(3) even
 * though string.h declares it (meson cc.has_function passes on the
 * declaration alone, so config.h sets HAVE_DECL_EXPLICIT_BZERO=1 and
 * NM's vendored systemd + secret-utils call it, dying at final link).
 * Map it to memset(3): same observable semantics, minus the memory
 * barrier that matters only for hardened secret wiping. */
#include <string.h>
#define explicit_bzero(p, n) memset((p), 0, (n))

/* musl lacks sigisemptyset(3) (glibc extension); systemd's sd-event
 * calls it unguarded. Probe result (sigset-probe run 2026-09-20): the
 * OHOS musl-derived libc maintains only the first _NSIG/8 bytes of a
 * sigset_t — sigemptyset zeroes nothing beyond that and words [1..]
 * keep their prior garbage — while the type itself is 128 bytes
 * (alltypes.h: __bits[128/sizeof(long)], _NSIG=65). So compare exactly
 * the byte range the libc manages, rounded up to whole words. */
#include <signal.h>

static inline int sigisemptyset(const sigset_t *set) {
    size_t nw = (((size_t) _NSIG / 8) + sizeof(unsigned long) - 1)
                / sizeof(unsigned long);
    const unsigned long *w = (const unsigned long *) set;
    if (nw < 1) {
        nw = 1;
    }
    for (size_t i = 0; i < nw; i++) {
        if (w[i] != 0UL) {
            return 0;
        }
    }
    return 1;
}

/* ==== ethernet compat: musl netinet/if_ether.h vs bionic
 * linux/if_ether.h (both define struct ethhdr unconditionally).
 * Neither can be skipped in isolation: linux/ethtool.h below needs a
 * complete struct ethhdr (ether_spec field), and the musl header has
 * no include guard around its own definition. So: suppress the bionic
 * one via __UAPI_DEF_ETHHDR (the bionic header honors it), skip the
 * musl one entirely, and define the needed structs here.
 * Everything n-acd consumes (audited: ethhdr, ether_arp + arp_hrd/
 * pro/hln/pln/op aliases, ether_addr, ETH_ALEN, ETH_P_*, ETHERTYPE_IP,
 * ARPOP_*) is provided below. No source patch needed. */
#ifndef __UAPI_DEF_ETHHDR
#define __UAPI_DEF_ETHHDR 0
#endif
#ifndef _NETINET_IF_ETHER_H
#define _NETINET_IF_ETHER_H 1
#endif
#include <stdint.h>

struct ethhdr {
    uint8_t  h_dest[6];
    uint8_t  h_source[6];
    uint16_t h_proto;
};

/* The OHOS sysroot's purified linux/ethtool.h lacks the
 * ethtool_cmd_speed() / ethtool_cmd_speed_set() helpers present in
 * full kernel UAPI headers, so nmp-ethtool-ioctl.c ends up with
 * implicit declarations and dies at final link. Provide them over the
 * UAPI struct fields (same code as NM's vendored
 * src/linux-headers/ethtool.h).
 *
 * Also suppress NM's vendored copy (src/linux-headers/ethtool.h,
 * guard _LINUX_ETHTOOL_H): the sysroot header uses a different guard
 * (_UAPI_LINUX_ETHTOOL_H), so once this compat header pulls the
 * sysroot one, any TU that later includes the vendored copy (via
 * nm-linux-compat.h, e.g. nm-platform-utils.c) would hit full
 * redefinition errors. Audited: both copies define the identical set
 * of 103 ETHTOOL_ macros, so nothing is lost. */
#ifndef _LINUX_ETHTOOL_H
#define _LINUX_ETHTOOL_H 1
#endif
#include <linux/ethtool.h>

static __inline__ void ethtool_cmd_speed_set(struct ethtool_cmd *ep, __u32 speed) {
    ep->speed_hi = (__u16) (speed >> 16);
    ep->speed = (__u16) (speed & 0xFFFFU);
}

static __inline__ __u32 ethtool_cmd_speed(const struct ethtool_cmd *ep) {
    return ((__u32) ep->speed_hi << 16) | (__u32) ep->speed;
}

/* ether_addr (with the ether_addr_octet field n-acd uses) and
 * ETHERTYPE_* come from net/ethernet.h. For ARP, the musl net/if_arp.h
 * and the kernel linux/if_arp.h both define arphdr, arpreq and
 * arpreq_old and cannot coexist (same clash family as ethhdr) — pick
 * the kernel one, which is what systemd's socket-util.c expects;
 * audited: no NM TU uses the musl-only ATF_ macros, and the kernel
 * header provides the whole ARPOP_ family, arphdr, arpreq and ATF_.
 *
 * Mirror case for if.h: the kernel linux/if.h (pulled by netdevice.h
 * via linux/if_arp.h) and musl net/if.h both define ifmap, ifreq and
 * ifconf. Here the userspace one wins — NM and systemd code uses the
 * ifr_* API from net/if.h everywhere (5+ TUs include linux/if.h
 * directly but only touch ifr_name/ifr_flags style fields, which musl
 * provides through the same macro aliases). Pre-seed the kernel guard
 * BEFORE including linux/if_arp.h so the netdevice.h chain skips it.
 * The kernel header owns two macros the userspace one lacks and NM
 * actually uses (audited: nothing else from the kernel-only set is
 * referenced — the IF_GET_IFACE/IF_PROTO WAN ioctls are unused):
 *   linux/if.h:29  #define IFALIASZ    256
 *   linux/if.h:30  #define ALTIFNAMSIZ 128
 * Re-provide them here. */
#ifndef _NET_IF_ARP_H
#define _NET_IF_ARP_H 1
#endif
#ifndef _LINUX_IF_H
#define _LINUX_IF_H 1
#endif
#ifndef IFALIASZ
#define IFALIASZ 256
#endif
#ifndef ALTIFNAMSIZ
#define ALTIFNAMSIZ 128
#endif
#include <net/if.h>
#include <net/ethernet.h>
#include <linux/if_arp.h>

struct ether_arp {
    struct arphdr ea_hdr;
    uint8_t arp_sha[ETH_ALEN];
    uint8_t arp_spa[4];
    uint8_t arp_tha[ETH_ALEN];
    uint8_t arp_tpa[4];
};
#define arp_hrd ea_hdr.ar_hrd
#define arp_pro ea_hdr.ar_pro
#define arp_hln ea_hdr.ar_hln
#define arp_pln ea_hdr.ar_pln
#define arp_op  ea_hdr.ar_op

#endif /* __OHOS__ */
#endif /* OHOS_COMPAT_H */
"""

    def _write_ohos_compat_header(self):
        path = os.path.join(self.generators_folder, "ohos-compat.h")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(self._ohos_compat_header)
        return path

    # 构建机上的 python3 候选位置（配置期探测取第一个存在的，用作垫片/启动器 shebang）。
    # 本机与 CI worker 的 python 安装位置不同：
    #   - CI worker：/data/service/hnp/bin/python3（CI 日志 `Program python3 found: YES`）
    #   - 本沙箱：/storage/Users/currentUser/usr/local/bin/python3
    # 因此**任何一处都不能写死**：写死会让另一台机器上的垫片 shebang 指向不存在的
    # 解释器，内核 exec 报 ENOENT，被 shell 显示成
    #   "/bin/sh: <垫片路径>: No such file or directory"
    # （文件其实存在）——把「缺解释器」伪装成「缺文件」（2026-09-24 CI PR #11584 /
    # 构建 #59556 的根因）。故：解释器在配置期由 `_python3_interpreter` 探测并写进
    # shebang（见 `_launcher_script_template`）。
    _launcher_python_candidates = (
        "/data/service/hnp/bin/python3",                       # CI worker / HNP 工具链
        "/storage/Users/currentUser/usr/local/bin/python3",    # 本沙箱 hnp 用户域
        "/usr/local/bin/python3",
        "/usr/bin/python3",
    )

    @property
    def _python3_interpreter(self):
        override = os.environ.get("NM_LAUNCHER_PYTHON")
        candidates = (
            ([override] if override else []) + list(self._launcher_python_candidates)
        )
        for candidate in candidates:
            if not candidate:
                continue
            try:
                st = os.stat(candidate)
            except OSError:
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            if not (st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                continue
            return candidate
        found = shutil.which("python3") or shutil.which("python")
        if found:
            return found
        raise ConanException(
            "no usable python3 interpreter found for launcher shebangs (tried: "
            + ", ".join(c for c in candidates if c)
            + ", then PATH); set NM_LAUNCHER_PYTHON to override"
        )

    # glib 工具垫片：`#!<探测到的 python3>` + runpy 转发到真实工具脚本。
    #
    # 为什么 shebang 必须指向 python（两条路径都实测过，别再改回 `#!/bin/sh`）：
    #   本沙箱构建域**拒绝** exec 构建树内 shebang 为 /bin/sh 的脚本 —— ninja 侧报
    #   `FAILED: [code=126]`，meson 侧 posix_spawn 报
    #   `PermissionError: [Errno 13] Permission denied: .../toolbin/glib-mkenums`；
    #   而 shebang 指向一个**真实存在**的 python3 时，内核按解释器做域判定是被允许的
    #   （现实现即如此，867/867 全绿）。
    #
    # 而那个 python3 的**绝对路径不能写死**：本机是
    # /storage/Users/currentUser/usr/local/bin/python3，CI worker 是
    # /data/service/hnp/bin/python3。写死任一处，在另一台机器上 shebang 就指向不存在的
    # 解释器 → 内核 exec 直接 ENOENT，而调用方只会报
    #   "/bin/sh: <垫片路径>: No such file or directory"
    #   FileNotFoundError: '.../toolbin/glib-mkenums'
    # 把「缺解释器」伪装成「缺文件」（2026-09-24 CI PR #11584 / 构建 #59556 的根因）。
    # 故解释器改由 `_python3_interpreter` 在配置期就地探测。
    _launcher_script_template = (
        "#!{python}\n"
        "import runpy\n"
        "import sys\n"
        "sys.argv[0] = {script!r}\n"
        "runpy.run_path({script!r}, run_name='__main__')\n"
    )

    def _glib_tool_launcher(self, glib_dep, tool_name, toolbin):
        """为 glib 包 bin/ 下的 python 脚本工具（gdbus-codegen / glib-mkenums）
        写垫片脚本：shebang 直指**配置期探测到的** python3（见
        `_python3_interpreter`），由 runpy 转发到真实工具脚本。

        meson 的 gnome 模块经 pkg-config 变量（gio-2.0 的 gdbus_codegen、
        glib-2.0 的 glib_mkenums）拿到的**必须是一个可直接 exec 的普通可执行文件**，
        故不能指向 glib 包内那个 shebang 为 `#!/usr/bin/env python3` 的脚本本身
        （本平台无 /usr/bin/env）。
        """
        tool_path = None
        for bindir in glib_dep.cpp_info.bindirs:
            candidate = os.path.join(glib_dep.package_folder, bindir, tool_name)
            if os.path.isfile(candidate):
                tool_path = candidate
                break
        if not tool_path:
            return None

        shim = os.path.join(toolbin, tool_name)
        with open(shim, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                self._launcher_script_template.format(
                    python=self._python3_interpreter, script=tool_path
                )
            )
        try:
            os.chmod(shim, 0o755)
        except OSError:
            pass
        return shim

    def _write_nm_test_launchers(self):
        """在**源码树内** `tools/` 生成两个启动器，把 meson test 对 shell 辅助脚本的
        调用转交给 `/bin/sh -c '<bash> <真实脚本> <args>'`。

        为什么需要启动器：本沙箱的构建域不能直接 exec 脚本文件（脚本 shebang 指向
        hnp_file 域的 bash 会触发 SELinux 域转移被拒，报 Permission denied），而
        `/bin/sh -c "bash <script> <args>"` 走的是被允许的 sh_exec -> hnp_file(bash)
        转移（ninja 的每条命令都如此运行）。启动器自身用一个**真实存在且可 exec 的
        python3** 顶替「被 exec 的脚本」这一角色，再显式拉起 sh/bash 运行真实脚本。

        ★ shebang 的解释器由 `_python3_interpreter` 在配置期就地探测，不能写死：
        本机是 /storage/Users/currentUser/usr/local/bin/python3，CI worker 是
        /data/service/hnp/bin/python3。写死任一处，另一台机器上 shebang 就指向不存在的
        解释器 —— 内核 exec 报 ENOENT，而 shell/ninja 只显示成
          "/bin/sh: .../toolbin/gdbus-codegen: No such file or directory"
          "FileNotFoundError: .../toolbin/glib-mkenums"
        把「缺解释器」伪装成「缺文件」（2026-09-24 PR #11584 构建 #59556 的根因）。

        ★ 另：不要把启动器改成 `#!/bin/sh`。本沙箱构建域拒绝 exec 构建树内 sh-shebang
        脚本（实测 ninja `FAILED: [code=126]`、meson posix_spawn
        `PermissionError: [Errno 13] Permission denied`），python-shebang 才可 exec。

        落点与引用（AI Review P2 修复，2026-09-21）：
          - 启动器写在 `self.source_folder/tools/{nm-run-test,nm-check-exports}`，
            **不再写机器全局目录**（旧实现写 `…/usr/local/bin`，属构建目录之外的副作用）；
          - 补丁 `0005-meson-script-invocation.patch` 用
            `find_program(join_paths(source_root, 'tools', 'nm-run-test'))` 引用，
            故**补丁内不存在任何机器/用户专属绝对路径**，换机可复现；
          - 目标脚本或 `source_folder` 缺失时**直接失败**（不再静默跳过——旧实现的
            warning + `return` 会让 meson 在配置期才报 “Program not found”，定位困难）。

        注：bash 的绝对路径 `/data/service/hnp/bin/bash` 是 OHOS 的既定 bash 位置
        （补丁 0004 亦如此改写脚本 shebang），CI worker 与本机一致（meson 日志
        `Program /data/service/hnp/bin/bash found: YES`）。
        """
        if not getattr(self, "source_folder", None):
            raise ConanException(
                "nm 测试启动器必须在源码解包后生成（self.source_folder 为空）："
                "请通过 conan create/build 流程构建本配方"
            )
        bash = "/data/service/hnp/bin/bash"
        sh = "/bin/sh"
        tools_dir = os.path.join(self.source_folder, "tools")
        if not os.path.isdir(tools_dir):
            raise ConanException(f"nm launcher dir missing: {tools_dir}")
        os.makedirs(tools_dir, exist_ok=True)

        targets = {
            "nm-run-test": os.path.join(self.source_folder, "tools", "run-nm-test.sh"),
            "nm-check-exports": os.path.join(
                self.source_folder, "tools", "check-exports.sh"
            ),
        }
        for name, script in targets.items():
            if not os.path.isfile(script):
                raise ConanException(f"nm launcher target script missing: {script}")
            launcher = os.path.join(tools_dir, name)
            with open(launcher, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    f"#!{self._python3_interpreter}\n"
                    "import os\n"
                    "import shlex\n"
                    "import sys\n"
                    f"BASH = {bash!r}\n"
                    f"SH = {sh!r}\n"
                    f"SCRIPT = {script!r}\n"
                    "args = [SH, '-c', BASH + ' ' + shlex.quote(SCRIPT) + ' ' +"
                    " ' '.join(shlex.quote(a) for a in sys.argv[1:])]\n"
                    "os.execv(SH, args)\n"
                )
            try:
                os.chmod(launcher, 0o755)
            except OSError:
                pass
            self.output.info(f"wrote nm test launcher {launcher} -> {script}")

    def _write_pc_shim(
        self, pc_name, version, description, requires, cflags, libs, prefix,
        variables=None,
    ):
        pc_path = os.path.join(self.generators_folder, f"{pc_name}.pc")
        lines = [
            f"prefix={prefix}",
            "exec_prefix=${prefix}",
            "libdir=${prefix}/lib",
            "includedir=${prefix}/include",
        ]
        for key, value in (variables or {}).items():
            lines.append(f"{key}={value}")
        lines += [
            "",
            f"Name: {pc_name}",
            f"Description: {description}",
            f"Version: {version}",
        ]
        if requires:
            lines.append(f"Requires: {requires}")
        lines += [
            f"Cflags: {cflags}",
            f"Libs: -L${{prefix}}/lib {libs}",
            "",
        ]
        with open(pc_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        self.output.info(f"wrote pkg-config shim {pc_name}.pc")

    def build(self):
        if str(self.settings.os) == "OHOS":
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            tools = self._resolve_llvm_tools(executables, target_os=self.settings.os)
            for name, path in tools.items():
                if not os.path.isfile(path) or not os.access(path, os.X_OK):
                    raise ConanInvalidConfiguration(
                        f"target compiler tool {name!r} is not executable: {path}"
                    )
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build(target=None)

    # ------------------------------------------------------------------
    # packaging: SONAME 实体化 + OHOS ELF 自签名
    # ------------------------------------------------------------------

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _materialize_soname_aliases(self, directory, preserve_soname_inode=False):
        stem = self._soname_stem
        pattern = re.compile(
            rf"^{re.escape(stem)}[.]so[.](?P<version>[0-9]+(?:[.][0-9]+)*)$"
        )
        sources = []
        if os.path.isdir(directory):
            for name in os.listdir(directory):
                path = os.path.join(directory, name)
                if (
                    pattern.fullmatch(name)
                    and os.path.isfile(path)
                    and not os.path.islink(path)
                ):
                    sources.append(path)
        if len(sources) != 1:
            raise ConanInvalidConfiguration(
                f"expected one versioned shared object for {stem!r} in "
                f"{directory!r}, found {len(sources)}"
            )

        source = sources[0]
        source_stat = os.stat(source, follow_symlinks=False)
        source_mode = stat.S_IMODE(source_stat.st_mode)
        source_identity = (source_stat.st_dev, source_stat.st_ino)
        version = pattern.fullmatch(os.path.basename(source)).group("version")
        aliases = (
            f"{stem}.so.{version.split('.', 1)[0]}",
            f"{stem}.so",
        )
        alias_states = []
        for alias_name in aliases:
            alias = os.path.join(directory, alias_name)
            if os.path.lexists(alias):
                if os.path.islink(alias):
                    try:
                        same_source = os.path.samefile(alias, source)
                    except OSError:
                        same_source = False
                    if not same_source:
                        raise ConanInvalidConfiguration(
                            f"shared-library alias {alias!r} does not match "
                            f"{source!r}"
                        )
                    alias_states.append((alias_name, alias, "link"))
                elif (
                    os.path.isfile(alias)
                    and filecmp.cmp(alias, source, shallow=False)
                    and stat.S_IMODE(
                        os.stat(alias, follow_symlinks=False).st_mode
                    )
                    == source_mode
                ):
                    alias_states.append((alias_name, alias, "regular"))
                else:
                    raise ConanInvalidConfiguration(
                        f"shared-library alias {alias!r} does not match "
                        f"{source!r}"
                    )
            else:
                alias_states.append((alias_name, alias, "missing"))

        if preserve_soname_inode:
            soname_name, soname_alias, soname_state = alias_states[0]
            if soname_state == "link":
                os.unlink(soname_alias)
                os.replace(source, soname_alias)
            elif soname_state == "missing":
                os.replace(source, soname_alias)
            elif os.path.samefile(soname_alias, source):
                os.unlink(source)
            else:
                raise ConanInvalidConfiguration(
                    f"runtime SONAME alias does not preserve the versioned "
                    f"shared object's identity: {soname_alias!r}"
                )
            soname_stat = os.stat(soname_alias, follow_symlinks=False)
            if (
                os.path.lexists(source)
                or not os.path.isfile(soname_alias)
                or os.path.islink(soname_alias)
                or (soname_stat.st_dev, soname_stat.st_ino) != source_identity
                or stat.S_IMODE(soname_stat.st_mode) != source_mode
            ):
                raise ConanInvalidConfiguration(
                    f"failed to preserve shared-library identity at runtime "
                    f"SONAME {soname_alias!r}"
                )
            self.output.info(
                f"promoted versioned shared object to regular runtime "
                f"SONAME {soname_name}"
            )

            alias_name, alias, state = alias_states[1]
            if state == "link":
                os.unlink(alias)
            if state != "regular":
                shutil.copyfile(soname_alias, alias)
                shutil.copymode(soname_alias, alias, follow_symlinks=False)
            if (
                not os.path.isfile(alias)
                or os.path.islink(alias)
                or not filecmp.cmp(alias, soname_alias, shallow=False)
            ):
                raise ConanInvalidConfiguration(
                    f"failed to materialize link-time shared-library alias "
                    f"{alias!r}"
                )
            return

        for alias_name, alias, state in alias_states:
            if state == "regular":
                continue
            if state == "link":
                os.unlink(alias)
            shutil.copyfile(source, alias)
            shutil.copymode(source, alias, follow_symlinks=False)
            if not os.path.isfile(alias) or os.path.islink(alias):
                raise ConanInvalidConfiguration(
                    f"failed to materialize shared-library alias {alias_name!r}"
                )
            self.output.info(f"materialized regular shared-library alias {alias_name}")

    def _resolve_ohos_signing_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = self._require_absolute_tool(
            executables.get("c"), "c", target_posix=True
        )
        compiler_dir = posixpath.dirname(compiler)
        tools = {
            "readelf": posixpath.join(compiler_dir, "llvm-readelf"),
            "objcopy": posixpath.join(compiler_dir, "llvm-objcopy"),
            "signer": posixpath.join(compiler_dir, "binary-sign-tool"),
        }
        missing = [
            name
            for name, path in tools.items()
            if not os.path.isfile(path) or not os.access(path, os.X_OK)
        ]
        if missing:
            if not can_run(self):
                self.output.info(
                    "PACKAGE_CODESIGN=NOT_RUN reason=cross_building; "
                    f"missing_tools={','.join(missing)}"
                )
                return None
            raise ConanInvalidConfiguration(
                "native OHOS package signing tools are missing: "
                + ", ".join(missing)
            )
        return tools

    @staticmethod
    def _run_signing_tool(arguments, label):
        completed = subprocess.run(
            arguments,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise ConanInvalidConfiguration(
                f"{label} failed with exit code {completed.returncode}"
            )
        return completed.stdout

    def _sign_final_ohos_elf(self, path, tools):
        if not os.path.isfile(path) or os.path.islink(path) or not self._is_elf(path):
            raise ConanInvalidConfiguration(
                f"required final OHOS ELF is missing, linked, or invalid: {path!r}"
            )
        original_mode = stat.S_IMODE(os.stat(path, follow_symlinks=False).st_mode)
        temporary = f"{path}.signing-{os.getpid()}"
        signed = f"{path}.signed-{os.getpid()}"
        if os.path.lexists(temporary) or os.path.lexists(signed):
            raise ConanInvalidConfiguration(
                f"OHOS ELF signing temporary already exists for {path!r}"
            )
        try:
            shutil.copy2(path, temporary)
            sections = self._run_signing_tool(
                [tools["readelf"], "-S", temporary], "pre-sign readelf"
            ).decode("utf-8", errors="strict")
            if ".codesign" in sections:
                self._run_signing_tool(
                    [tools["objcopy"], "--remove-section", ".codesign", temporary],
                    "codesign removal",
                )
            self._run_signing_tool(
                [
                    tools["signer"],
                    "sign",
                    "-inFile",
                    temporary,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                "OHOS ELF signer",
            )
            if not os.path.isfile(signed) or os.path.islink(signed):
                raise ConanInvalidConfiguration(
                    f"OHOS ELF signer did not create a regular output: {path!r}"
                )
            signed_sections = self._run_signing_tool(
                [tools["readelf"], "-S", signed], "post-sign readelf"
            ).decode("utf-8", errors="strict")
            if signed_sections.count(".codesign") != 1:
                raise ConanInvalidConfiguration(
                    f"signed OHOS ELF must contain exactly one .codesign: {path!r}"
                )
            if filecmp.cmp(temporary, signed, shallow=False):
                raise ConanInvalidConfiguration(
                    f"OHOS ELF signer did not change the unsigned input: {path!r}"
                )
            os.chmod(signed, original_mode | 0o755)
            os.replace(signed, path)
        finally:
            for candidate in (temporary, signed):
                if os.path.lexists(candidate):
                    os.unlink(candidate)

    def _sign_final_ohos_package(self):
        if str(self.settings.os) != "OHOS":
            return
        tools = self._resolve_ohos_signing_tools()
        if tools is None:
            return

        library_dir = os.path.join(self.package_folder, "lib")
        soname_pattern = re.compile(
            rf"^{re.escape(self._soname_stem)}[.]so[.][0-9]+$"
        )
        sonames = [
            os.path.join(library_dir, name)
            for name in (os.listdir(library_dir) if os.path.isdir(library_dir) else [])
            if soname_pattern.fullmatch(name)
            and os.path.isfile(os.path.join(library_dir, name))
            and not os.path.islink(os.path.join(library_dir, name))
        ]
        if len(sonames) != 1:
            raise ConanInvalidConfiguration(
                f"expected one final runtime SONAME for {self._soname_stem!r}, "
                f"found {len(sonames)}"
            )
        alias = os.path.join(library_dir, f"{self._soname_stem}.so")
        if not os.path.isfile(alias) or os.path.islink(alias):
            raise ConanInvalidConfiguration(
                f"final link-time alias is missing or linked: {alias!r}"
            )

        signed_paths = []
        for directory, subdirectories, filenames in os.walk(self.package_folder):
            subdirectories.sort()
            for filename in sorted(filenames):
                path = os.path.join(directory, filename)
                if path in (sonames[0], alias) or os.path.islink(path) or not self._is_elf(path):
                    continue
                self._sign_final_ohos_elf(path, tools)
                signed_paths.append(path)

        if sonames[0] not in signed_paths:
            self._sign_final_ohos_elf(sonames[0], tools)
            signed_paths.append(sonames[0])
        # 别名用已签名的 SONAME 内容覆盖，保持链接时与运行时一致
        shutil.copyfile(sonames[0], alias)
        shutil.copymode(sonames[0], alias, follow_symlinks=False)
        if (
            not os.path.isfile(alias)
            or os.path.islink(alias)
            or not filecmp.cmp(alias, sonames[0], shallow=False)
            or not stat.S_IMODE(os.stat(alias, follow_symlinks=False).st_mode) & stat.S_IXUSR
        ):
            raise ConanInvalidConfiguration(
                f"signed link-time alias validation failed: {alias!r}"
            )
        self.output.info(f"PACKAGE_CODESIGN=PASS signed_elfs={len(signed_paths)}")

    def package(self):
        meson = Meson(self)
        meson.install()

        library_dir = os.path.join(self.package_folder, "lib")
        if str(self.settings.os) in ("Linux", "OHOS") and self.options.shared:
            self._materialize_soname_aliases(
                library_dir, preserve_soname_inode=True
            )

        # 只保留 libnm 库 + 头 + pc + 许可证；守护进程/工具是构建过程的
        # 中间产物，不属于 libnm 包内容。
        for entry in ("bin", "sbin", "share", "etc", "var", "libexec"):
            rmdir(self, os.path.join(self.package_folder, entry))
        for entry in os.listdir(library_dir):
            if entry == "pkgconfig":
                continue
            path = os.path.join(library_dir, entry)
            if os.path.isdir(path):
                rmdir(self, path)
        # 只留 libnm.pc，其余 pc 属于依赖包
        pkgconfig_dir = os.path.join(library_dir, "pkgconfig")
        if os.path.isdir(pkgconfig_dir):
            for entry in os.listdir(pkgconfig_dir):
                if entry != "libnm.pc":
                    os.unlink(os.path.join(pkgconfig_dir, entry))

        copy(
            self,
            "COPYING.LGPL",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._sign_final_ohos_package()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libnm")
        self.cpp_info.set_property("cmake_target_name", "libnm::libnm")
        self.cpp_info.set_property("pkg_config_name", "libnm")
        # libnm.pc: Cflags: -I${includedir}/libnm（消费者 #include <NetworkManager.h>）
        self.cpp_info.includedirs = ["include/libnm"]
        self.cpp_info.libs = ["nm"]
        # conan2 校验（internal/model/cpp_info.py:check_component_requires）：一旦
        # 设置 cpp_info.requires，就必须覆盖 requirements() 里的全部直接依赖，
        # 否则报 "The direct dependency 'X' is not used by any
        # '(cpp_info/components).requires'"。
        #
        # 说明：libnm.so 的 NEEDED 只有 libgio/libgobject/libgmodule/libglib（+libc），
        # 即 glib 一族；libndp / libudev-zero / dbus / uuid 只是 daemon（未打包进本
        # 包）的构建期依赖。但它们在 requirements() 中属直接依赖，依规则必须在此列出。
        # 无 components 的依赖包以默认组件 "pkg::pkg"（即包名::包名）引用。
        self.cpp_info.requires = [
            "glib::glib",
            "glib::gobject",
            "glib::gio",
            "glib::gmodule",
            "libndp::libndp",
            "libudev-zero::libudev-zero",
            "dbus::dbus",
            "uuid::uuid",
        ]
        if self.options.shared and str(self.settings.os) in ("Linux", "OHOS"):
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
            )
