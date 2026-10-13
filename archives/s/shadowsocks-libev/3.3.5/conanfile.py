#!/usr/bin/env python3
"""Conan recipe — shadowsocks-libev 3.3.5 (autotools, ohos-aarch64).

shadowsocks-libev 是 Shadowsocks 协议的 C 实现（libev 事件循环），产出
ss-local / ss-server / ss-tunnel / ss-manager / ss-redir 五个可执行文件、
libshadowsocks-libev 静态库与 shadowsocks-libev.pc。

构建系统说明（为什么是「手写 Autotools 调用」而不是 Autotools(self)）：
- 上游工程是 autotools，但 **不提供 `check` 目标**：Makefile.am 里既没有
  TESTS/check_PROGRAMS，也没有 tests 子目录参与构建，故没有可用的
  `Autotools(self).make(target="check")`。
- 上游的自动化测试是 tests/test.sh + tests/test.py，靠「起
  ss-server/ss-local/ss-tunnel 三进程 + curl 经 SOCKS5 访问外网 +
  dig 经 ss-tunnel 解析」来验证；它**硬依赖公网可达**（默认
  http://www.google.com/ 与 8.8.8.8:53），在离线的 CI/真机环境必然失败。
  因此本配方不把 test.py 当作可执行门禁，而是在 test_package 里实现
  **等价的离线回环消费者用例**（详见 conandata.yml 与 test_package/）。

R40（源码归档选择）：GitHub 的 tag *源码* 归档里 libcork/libipset/libbloom
三个子模块目录为空且没有生成的 configure，必须联网 clone + autoreconf；
官方 release 资产内嵌三个子模块并自带 configure，可离线复现 —— 本配方用后者。
子模块在 release 资产里由上游自带的 Makefile.am 包装（纯 automake 静态
libtool 库，路径为 $(top_srcdir)/libcork 等），**不会**去调用子模块自己的
CMakeLists.txt，故构建时无需 CMake。

R33：编译器一律由 AutotoolsToolchain 的 conanbuild env 提供
（CC / CFLAGS / LDFLAGS 等由 conan 注入），本文件的 self.run() 调用里
不出现裸的 shell 编译器变量展开。注：原文此处曾以示例形式写出该变量名，
会被 CI 的 L0h 门禁（正则匹配 "self.run(" 同行出现的 shell 变量展开）判为
违规——门禁按文本匹配、不区分代码与注释，故此处改为不含该模式的表述。

mbedtls 依赖（本配方唯一的非平凡点，详见 conandata.yml 的 vendor 段）：
shadowsocks-libev 3.3.5 硬依赖 mbedtls **v2/v3** 的经典 cipher/md API，
而 OHOS 制品仓只发布了 mbedtls/4.1.0（已改 TF-PSA-Crypto，移除
mbedtls/cipher.h 等头）。故按仓库既有先例（bzrtp/5.3.105、librist/2.0.18、
lib60870/2.4.0）在 source() 内 vendoring mbedtls 2.28.10 源码，并在 build()
里用同一个 Conan 工具链文件把它子构建成私有静态库，再通过
--with-mbedtls=<私有 prefix> 喂给上游 configure。私有依赖**不安装进本包**，
也不作为 conan requirement，消费者不需要它。
"""
import glob
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

VENDOR_MBEDTLS = "vendor/mbedtls-2.28.10"
# OHOS netfilter 兼容头（相对 recipe 目录），见 _install_netfilter_shim
NETFILTER_SHIM_DIR = "patches/ohos-netfilter-shim"


class ShadowsocksLibevConan(ConanFile):
    name = "shadowsocks-libev"
    version = "3.3.5"
    description = ("A lightweight secured SOCKS5 proxy based on Shadowsocks "
                   "protocol (libev implementation)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/shadowsocks/shadowsocks-libev"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_cares": [True, False],
    }
    default_options = {
        "shared": False,
        # ss-tunnel / ss-server 的远端域名解析走 c-ares（异步 DNS）。
        # 上游 configure 在缺少 ares 时可回退 getaddrinfo（resolv.c 内分支），
        # 但 ss-tunnel 的 -L 语义依赖异步解析，故默认开启。
        "with_cares": True,
    }

    def export_sources(self):
        export_conandata_patches(self)
        # OHOS netfilter 兼容 shim（见 _install_netfilter_shim）
        copy(self, "*", src=os.path.join(self.recipe_folder, NETFILTER_SHIM_DIR),
             dst=os.path.join(self.export_sources_folder, NETFILTER_SHIM_DIR))

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):  # R32
            raise ConanInvalidConfiguration(
                f"shadowsocks-libev supports Linux and OHOS targets, "
                f"got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # pcre 为 configure 硬依赖（TS_CHECK_PCRE 失败即 AC_MSG_ERROR）。
        self.requires("pcre/8.45")
        self.requires("libev/4.33")
        self.requires("libsodium/1.0.22")
        if self.options.with_cares:
            self.requires("c-ares/1.34.6")
        # 注意：mbedtls **不是** conan requirement —— 见 conandata.yml 与
        # _build_private_mbedtls()，它是本配方私有 vendoring 的子构建。

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(self, **self.conan_data["vendor"]["mbedtls"], strip_root=True,
            destination=os.path.join(self.source_folder, VENDOR_MBEDTLS))

    # ── E007：内置 GNU config.sub / config.guess 不认识 OHOS ───────────────
    def _patch_gnu_triplet_for_ohos(self):
        """让上游内置的 GNU config.sub 与 config.guess 认识 OHOS/HarmonyOS（E007）。

        有两个**互相独立**的三元组识别失败点，都必须处理：

        (1) config.sub —— 交叉构建（--host=aarch64-linux-ohos）时：
                checking host system type... Invalid configuration
                `aarch64-linux-ohos': system `ohos' not recognized
                configure: error: .../auto/config.sub aarch64-linux-ohos failed
            上游内置的是 2018/2020 年的 config.sub，kernel-OS 白名单里没有
            ohos。凡含 ohos 的 target 一律规范化成
            <machine>-unknown-linux-ohos 并直接 exit 0。

        (2) config.guess —— **在真机/CI 上原生构建时**：
                uname -m = aarch64
                uname -s = HarmonyOS
                configure: error: cannot guess build type; you must specify one
            真机跑的是 HarmonyOS，`uname -s` 返回 `HarmonyOS`（不是 `Linux`）。
            2018 版 config.guess 的探测表里既没有 HarmonyOS/OHOS 这个 system
            名，也不认这套组合，于是直接
            "unable to guess system type" —— 而 CI 是**原生**构建，
            AutotoolsToolchain 不会传 --build，configure 只能自己猜 build
            type，猜不出来就报 "cannot guess build type"。
            注意：这个失败**只在真机口径暴露**，本地 WSL 交叉构建
            （ohos-aarch64-run，--build=x86_64-linux-gnu 由 conan 显式提供）
            永远不会走到 config.guess 的这条分支。

        两个补丁都采用「shebang 之后插入与版本无关的 fast-path」的做法，
        不去逐版本改那张易碎的 machine/OS 校验表。幂等：按 marker 跳过。

        注：Conan 2 禁止在 source() 里访问 self.settings，故本方法在 build()
        阶段对 source_folder 就地执行（只改源树里的这两个脚本，不改配方）。
        """
        sub_marker = "OHOS fast-path (shadowsocks-libev OHOS port, E007)"
        sub_snippet = (
            "\n# OHOS fast-path (shadowsocks-libev OHOS port, E007):\n"
            "# 内置 config.sub 早于 OHOS，先于下方按版本校验的表格把 ohos\n"
            "# 三元组规范化，避免 'system `ohos' not recognized'。\n"
            'case "$1" in\n'
            "  *ohos*)\n"
            '    _ohos_machine=`echo "$1" | cut -d- -f1`\n'
            '    case "$_ohos_machine" in\n'
            "      aarch64|arm64) _ohos_machine=aarch64 ;;\n"
            "      arm*) _ohos_machine=arm ;;\n"
            "      x86_64|amd64) _ohos_machine=x86_64 ;;\n"
            "      i?86) _ohos_machine=i686 ;;\n"
            "    esac\n"
            '    echo "${_ohos_machine}-unknown-linux-ohos"\n'
            "    exit 0\n"
            "    ;;\n"
            "esac\n"
        )

        guess_marker = ("OHOS/HarmonyOS fast-path "
                        "(shadowsocks-libev OHOS port, E007)")
        guess_snippet = (
            "\n# OHOS/HarmonyOS fast-path (shadowsocks-libev OHOS port, E007):\n"
            "# 真机 uname -s 返回 'HarmonyOS'，2018 版 config.guess 不认识，\n"
            "# 会 'unable to guess system type'，进而 configure 报\n"
            "# 'cannot guess build type; you must specify one'。\n"
            "# 在正规探测表之前先给出规范三元组。\n"
            'case "`(uname -s) 2>/dev/null`" in\n'
            "  HarmonyOS|OHOS|harmonyos|ohos)\n"
            '    _ohos_m=`(uname -m) 2>/dev/null`\n'
            '    case "$_ohos_m" in\n'
            "      aarch64|arm64) echo aarch64-unknown-linux-ohos ;;\n"
            "      arm*)          echo arm-unknown-linux-ohos ;;\n"
            "      x86_64|amd64)  echo x86_64-unknown-linux-ohos ;;\n"
            '      *)             echo "${_ohos_m}-unknown-linux-ohos" ;;\n'
            "    esac\n"
            "    exit 0\n"
            "    ;;\n"
            "esac\n"
        )

        targets = {
            "config.sub": (sub_marker, sub_snippet),
            "config.guess": (guess_marker, guess_snippet),
        }
        counts = {name: 0 for name in targets}
        for dirpath, _dirnames, filenames in os.walk(self.source_folder):
            for name in filenames:
                spec = targets.get(name)
                if spec is None:
                    continue
                marker, snippet = spec
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="replace", newline="") as handle:
                        content = handle.read()
                except OSError:
                    continue
                if marker in content:
                    continue
                lines = content.splitlines(keepends=True)
                if lines and lines[0].startswith("#!"):
                    lines.insert(1, snippet)
                    new_content = "".join(lines)
                else:
                    new_content = snippet + content
                try:
                    with open(path, "w", encoding="utf-8", newline="") as handle:
                        handle.write(new_content)
                    counts[name] += 1
                except OSError:
                    continue
        self.output.info(
            "shadowsocks-libev OHOS triplet patch: "
            f"config.sub={counts['config.sub']} "
            f"config.guess={counts['config.guess']}")

    # ── E011：HMDFS + umask 077 导致 config.status 无法建立临时目录 ─────────
    def _patch_autoconf_umask_for_hmdfs(self):
        """把 configure 里的 `umask 077` 改成 `umask 022`（E011）。

        失败现场（CI #65921，真机原生构建，configure 走到最后一步）：
            configure: creating ./config.status
            ./config.status: line 822: ./confnDjInI/subs1.awk: Permission denied
            config.status: error: could not setup config files machinery

        根因：autoconf 生成的 config.status 用
            (umask 077 && mktemp -d)  或类似形态
        建立 ./confXXXXXX 临时目录（意图是 0700，只有自己能进）。但在
        OHOS 的 HMDFS 上，目录会被强制继承 setgid 位，实际权限变成
        drwx--S--- —— 连属主自己都写不进去，于是写 subs1.awk / subs1.sed
        时直接 Permission denied，config.status 中止。

        改成 umask 022 后目录权限为 drwxr-xr-x，可正常写入。config.status
        本身是 configure 模板生成的，所以只改 configure 即可覆盖两者。

        这是本仓库已知的通用问题（E011），已有大量先例：
        archives/x/xqilla、x/xcursorgen、x/xcb-util-renderutil、
        x/xapian-bindings、x/xz 等均以「configure 内 umask 077 → 022」
        处理，不改上游业务源码。

        幂等：按内容是否仍含 `umask 077` 判断；顺带确保 configure 可执行
        （改写后保留原 mode 并补齐 x 位）。
        """
        if str(self.settings.os) != "OHOS":
            return
        roots = set()
        for base in (getattr(self, "source_folder", None),
                     getattr(self, "build_folder", None)):
            if base and os.path.isdir(str(base)):
                roots.add(str(base))
        if not roots:
            return
        fixed = 0
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    if name != "configure":
                        continue
                    path = os.path.join(dirpath, name)
                    try:
                        st = os.stat(path)
                    except OSError:
                        continue
                    try:
                        with open(path, "r", encoding="utf-8",
                                  errors="replace", newline="") as handle:
                            content = handle.read()
                    except OSError:
                        continue
                    if "umask 077" not in content:
                        continue
                    new_content = content.replace("umask 077", "umask 022")
                    try:
                        with open(path, "w", encoding="utf-8",
                                  newline="") as handle:
                            handle.write(new_content)
                    except OSError:
                        continue
                    try:
                        os.chmod(path, st.st_mode | stat.S_IXUSR
                                 | stat.S_IXGRP | stat.S_IXOTH)
                    except OSError:
                        pass
                    fixed += 1
        self.output.info(
            f"shadowsocks-libev OHOS autoconf umask patch (E011): "
            f"configure={fixed}")

    # ── OHOS netfilter 头兼容 ─────────────────────────────────────────────
    def _netfilter_shim_candidates(self):
        """shim 目录的候选基路径（generate() 与 _install_netfilter_shim() 共用）。

        两处必须用**同一套**解析逻辑：曾经 generate() 只看 source_folder 且
        找不到就静默跳过，而 _install_netfilter_shim() 有三级回落并在找不到时
        raise。回落到 export_sources_folder/recipe_folder 时，build() 能过而
        generate() 悄悄不加 -I，真机编译会以误导性错误失败（P2-3）。
        """
        return [
            self.source_folder,
            getattr(self, "export_sources_folder", None),
            self.recipe_folder,
        ]

    def _resolve_netfilter_shim(self):
        """返回 shim 目录的绝对路径；找不到返回 None（由调用方决定报错语义）。"""
        for base in self._netfilter_shim_candidates():
            if not base:
                continue
            probe = os.path.join(base, NETFILTER_SHIM_DIR)
            if os.path.isdir(probe):
                return probe
        return None

    def _install_netfilter_shim(self):
        """补上真机 SDK 缺失的 netfilter UAPI 头，并把它们加进 CPPFLAGS。

        失败现场（CI #65884，真机原生构建 configure 阶段）：
            checking for net/if.h... yes
            checking for linux/if.h... no
            configure: error: Missing netfilter headers

        根因：configure.ac 的 `case $host in *-linux*)` 分支（因为我们的
        config.guess fast-path 产出 aarch64-unknown-linux-ohos，匹配
        *-linux*）会强制检查
            linux/if.h  linux/netfilter_ipv4.h
            linux/netfilter_ipv6/ip6_tables.h
        三者缺一即 AC_MSG_ERROR。这三个是**内核 UAPI 头**，OHOS 真机的
        系统 include 不提供（本仓库其它配方在 nftables/haproxy/hashrat 上
        也反复踩到 OHOS UAPI 头缺失/冲突，是同一类问题）。

        为什么本地不报错：WSL 侧的 OHOS SDK sysroot 里恰好带了这几个
        Linux 内核头副本，所以本地交叉构建一路绿；只有真机口径缺失。

        做法（与仓库既有先例一致的「补头」而非「改上游源码」）：
          1) 把 patches/ohos-netfilter-shim/ 下的兼容头拷进 source_folder，
             用 -I 让它们优先于系统头被找到；
          2) 兼容头只提供上游真正用到的最小内容（redir.c 只用到
             SO_ORIGINAL_DST / IP6T_SO_ORIGINAL_DST，以及转发 net/if.h
             拿到 struct ifreq），不复制整份内核头，避免本仓库其它配方
             遇到的 sockaddr_storage / __packed 之类重定义冲突。

        实测等价性（同一套 flags 编译 src/redir.c）：
            加上 shim（模拟真机无 netfilter 头）  -> rc=0
            不加 shim（用本地真头）              -> rc=0
        即 shim 是这些头的完全替代，不改变任何编译语义。
        幂等：重复调用按目录是否已存在跳过。
        """
        # 查找顺序：export_sources 的内容会被 conan 展开到 source_folder；
        # 本地直接跑（未 export）时回落到 recipe_folder。
        # 注意 build() 阶段 self.recipe_folder 指向**导出目录**，那里只有
        # conanfile.py/conandata.yml，不含 patches/，故不能作为首选。
        candidates = self._netfilter_shim_candidates()
        shim_dst = None
        for base in candidates:
            if not base:
                continue
            probe = os.path.join(base, NETFILTER_SHIM_DIR)
            if os.path.isdir(probe):
                shim_dst = probe
                break
        if shim_dst is None:
            raise ConanException(
                f"netfilter shim ({NETFILTER_SHIM_DIR}) not found under any of "
                f"{candidates}; check export_sources()")
        if not os.path.isdir(os.path.join(shim_dst, "linux")):
            raise ConanException(
                f"netfilter shim at {shim_dst} lacks linux/ subtree")
        sockaddr_h = os.path.join(shim_dst, "ohos_sockaddr_compat.h")
        if not os.path.isfile(sockaddr_h):
            raise ConanException(
                f"sockaddr_storage compat header missing at {sockaddr_h}")
        self._netfilter_shim_include = shim_dst.replace("\\", "/")
        self.output.info(
            f"OHOS netfilter shim installed: {self._netfilter_shim_include}")

    # ── 私有 mbedtls 子构建 ────────────────────────────────────────────────
    def _build_private_mbedtls(self):
        """把 vendoring 的 mbedtls 2.28.10 用同一套工具链编译成私有静态库。

        返回安装前缀（供 --with-mbedtls= 使用）。私有前缀位于 build 目录下，
        不进入本包 package_folder，也不构成 conan requirement。
        """
        src = os.path.join(self.source_folder, VENDOR_MBEDTLS)
        for marker in ("CMakeLists.txt", "include/mbedtls/cipher.h"):
            if not os.path.isfile(os.path.join(src, marker)):
                raise ConanException(
                    f"vendored mbedtls incomplete, missing {marker} under {src}")
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            # AutotoolsToolchain 只产出 conanbuild 环境脚本，不产出 CMake 工具链
            # 文件；私有 mbedtls 是 CMake 工程，这里显式再生成一份 CMakeToolchain
            # （与仓库内 bzrtp/5.3.105 内嵌 mbedtls 的做法一致）。
            from conan.tools.cmake import CMakeToolchain
            ctc = CMakeToolchain(self)
            ctc.variables["BUILD_SHARED_LIBS"] = False
            ctc.generate()
        if not os.path.isfile(toolchain):
            raise ConanException(f"conan_toolchain.cmake missing at {toolchain}")

        build_dir = os.path.join(self.build_folder, "vendor-mbedtls-build")
        prefix = os.path.join(self.build_folder, "vendor-mbedtls-install")
        shutil.rmtree(build_dir, ignore_errors=True)
        os.makedirs(build_dir, exist_ok=True)
        os.makedirs(prefix, exist_ok=True)

        cmake = self._cmake_executable()
        # -DMBEDTLS_FATAL_WARNINGS=OFF：2.28.10 在 clang 15 下有若干告警，
        #   上游 CMake 默认把告警当错误（-Werror），会中断构建。
        # -DCMAKE_POLICY_VERSION_MINIMUM=3.5：mbedtls 2.28.10 声明
        #   cmake_minimum_required(VERSION 2.8.12)，而 CI/真机 CMake 4.x 已
        #   移除 <3.5 兼容。本地 WSL 的 cmake 3.28 不会报错，故必须在真机
        #   口径（CMake 4.x）下验证——见 notes.md 问题表 #9。
        # 关闭 programs/tests：只要三个静态库。
        self.run(
            f'"{cmake}" -S "{src}" -B "{build_dir}" '
            f'-DCMAKE_TOOLCHAIN_FILE="{toolchain}" '
            f'-DCMAKE_BUILD_TYPE=Release '
            f'-DCMAKE_INSTALL_PREFIX="{prefix}" '
            f'-DCMAKE_POSITION_INDEPENDENT_CODE=ON '
            f'-DUSE_SHARED_MBEDTLS_LIBRARY=OFF '
            f'-DUSE_STATIC_MBEDTLS_LIBRARY=ON '
            f'-DENABLE_PROGRAMS=OFF -DENABLE_TESTING=OFF '
            f'-DMBEDTLS_FATAL_WARNINGS=OFF '
            # mbedtls 2.28.10 的 CMakeLists.txt 写的是
            # cmake_minimum_required(VERSION 2.8.12)；CI/真机的 CMake 4.x
            # 已移除对 <3.5 的兼容（"Compatibility with CMake < 3.5 has been
            # removed"），不加此参数会直接配置失败。
            # 这是 CMake 官方迁移开关（不改上游源码），仓库内已有大量先例：
            # archives/x/xerces、archives/x/xxhash、archives/x/xtl、
            # archives/x/xenium 均以 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 处理。
            f'-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
            env="conanbuild")
        # 遵循 profile 的 tools.build:jobs（P3-6：原为写死 -j1，约 200 个 .c
        # 串行编译，CI 上耗时显著；未读配置也与仓库其它配方不一致）。
        # 未设置时退回 1，保持与旧行为一致的最小并发保证。
        jobs = self.conf.get("tools.build:jobs", default=1, check_type=int)
        self.run(f'"{cmake}" --build "{build_dir}" --config Release -j{jobs}',
                 env="conanbuild")
        self.run(f'"{cmake}" --install "{build_dir}" --config Release',
                 env="conanbuild")

        for lib in ("libmbedcrypto.a", "libmbedtls.a", "libmbedx509.a"):
            found = (os.path.join(prefix, "lib", lib)
                     if os.path.isfile(os.path.join(prefix, "lib", lib))
                     else os.path.join(prefix, "lib64", lib))
            if not os.path.isfile(found):
                raise ConanException(
                    f"private mbedtls install missing {lib} under {prefix}")
        if not os.path.isfile(os.path.join(prefix, "include", "mbedtls", "cipher.h")):
            raise ConanException(
                f"private mbedtls install missing include/mbedtls/cipher.h "
                f"under {prefix}")
        self.output.info(f"private mbedtls/2.28.10 installed under {prefix}")
        return prefix

    def _cmake_executable(self):
        configured = self.conf.get("tools.cmake:cmake_program")
        if configured and os.path.isfile(str(configured)):
            return str(configured)
        found = shutil.which("cmake")
        if not found:
            raise ConanException("cmake executable not found (PATH lookup failed)")
        return found

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 真机 SDK 缺 netfilter UAPI 头：把 shim 目录加到编译命令最前面，
        # 让 configure 的头检查（AC_CHECK_HEADERS 走 CFLAGS/CC）与后续编译
        # 都优先命中它（见 _install_netfilter_shim）。
        # 注意：AutotoolsToolchain 2.29 只有 extra_cflags/extra_cxxflags/
        # extra_ldflags/extra_defines，**没有 extra_cppflags**
        # （CPPFLAGS 只由 self.defines 拼装，见 autotoolstoolchain.py:305）。
        # configure 的 header 探测用 C 编译器，故 CFLAGS 是正确且足够的注入点；
        # 为稳妥起见 C++ 侧也一并注入。
        # 仅在 OHOS 上注入 shim：非 OHOS 目标（Linux）行为必须完全不变 ——
        # shim 目录只含裁剪版 netfilter/socket UAPI 头，注入到 Linux 目标会把
        # 它置于真实内核 UAPI 头之前（P2-4：原实现只给 -include 加了 OS 守卫，
        # 紧邻的 -I 却没有，与注释承诺不符）。
        if str(self.settings.os) == "OHOS":
            shim_path = self._resolve_netfilter_shim()
            # P2-3：不得静默跳过。build() 阶段必然需要 shim，这里找不到就直接
            # 报错，否则会退化成"build 能过、generate 少加 -I"的不一致契约。
            if shim_path is None:
                raise ConanException(
                    "OHOS 目标需要 netfilter shim，但在 "
                    f"{self._netfilter_shim_candidates()} 下均未找到 "
                    f"{NETFILTER_SHIM_DIR}（检查 export_sources()）")
            shim_include = shim_path.replace("\\", "/")
            tc.extra_cflags.insert(0, f"-I{shim_include}")
            tc.extra_cxxflags.insert(0, f"-I{shim_include}")
            # sockaddr_storage 重复定义（真机 sys/socket.h vs linux/socket.h）：
            # 用 -include 在一切之前预先置上 <linux/socket.h> 的 include guard。
            compat_h = f"{shim_include}/ohos_sockaddr_compat.h"
            tc.extra_cflags.insert(0, f"-include {compat_h}")
            tc.extra_cxxflags.insert(0, f"-include {compat_h}")
        # 上游 configure.ac 用 TS_CHECK_PCRE 的 --with-pcre=DIR 形态探测 pcre：
        # 该分支只认 <DIR>/include/pcre.h 与 <DIR>/lib，不接受 pkg-config，
        # 因此把 Conan 依赖的 prefix 显式喂给 --with-pcre。
        pcre_dir = self.dependencies["pcre"].package_folder.replace("\\", "/")
        tc.configure_args.append(f"--with-pcre={pcre_dir}")
        # 同上的 --with-<dep>=DIR 形态：ss_SODIUM / ss_CARES 也只加
        # -I$DIR/include 与 -L$DIR/lib，不做 pkg-config 探测。
        sodium_dir = self.dependencies["libsodium"].package_folder.replace("\\", "/")
        tc.configure_args.append(f"--with-sodium={sodium_dir}")
        if self.options.with_cares:
            cares_dir = self.dependencies["c-ares"].package_folder.replace("\\", "/")
            tc.configure_args.append(f"--with-cares={cares_dir}")
        # libev 只有 --with-ev=DIR（无 -include/-lib 变体），configure.ac 里
        # 同时加 -I$DIR/include 与 -L$DIR/lib，然后用 AC_CHECK_LIB([ev], ...)
        # 探测 libev.a。
        ev_dir = self.dependencies["libev"].package_folder.replace("\\", "/")
        tc.configure_args.append(f"--with-ev={ev_dir}")
        # mbedtls 的路径在 build() 里算出（私有子构建），此处只占位，
        # 实际参数由 _ss_build_configure_args 在 build() 中补齐 —— 见 build()。
        # 文档需要 asciidoc/xmlto，CI 与真机均不保证存在 -> 关闭。
        tc.configure_args.append("--disable-documentation")
        # 上游默认 --disable-system-shared-lib，即用源码包内嵌的
        # libcork/libipset/libbloom 一起静态构建（release 资产已内嵌）。
        # 保持该默认：libcork/libipset 在 ohpcd 远程没有对应 Conan 包。
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        if not self.options.with_cares:
            tc.configure_args.append("--disable-cares")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._patch_gnu_triplet_for_ohos()
            self._install_netfilter_shim()
            self._patch_autoconf_umask_for_hmdfs()
        # HMBS 平台诊断（与仓库内其它 autotools 配方口径一致）：
        #  - [readonly_tmp] OHOS /tmp 不可写。configure 的 conftest 与
        #    libtool 会用 mktemp，务必把 TMPDIR/TMP/TEMP 指向可写目录。
        #  - [missing_build_tool] 真机 make 位于 /data/service/hnp/bin/make，
        #    不保证在子进程 PATH 上；Autotools 走 profile 的 buildenv。
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

        mbedtls_prefix = self._build_private_mbedtls()

        autotools = Autotools(self)
        # 私有 mbedtls 前缀只能在 build() 里确定（子构建产物），
        # 故在 configure() 调用点上作为额外参数补入。
        autotools.configure(args=[f"--with-mbedtls={mbedtls_prefix}"])
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        # 上游通过 libtool 安装出的 .la 文件会写死构建期绝对路径，
        # 消费者无需也不应携带它们。
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "shadowsocks-libev")
        self.cpp_info.libs = ["shadowsocks-libev"]
        # 上游 libshadowsocks-libev 是 libtool 静态库，其对象引用了
        # libcork/libipset/libbloom 的符号；这三个库在上游是
        # noinst_LTLIBRARIES（不单独安装），故其对象已并入 libshadowsocks-libev.a。
        # 消费者仍需链接 ev/sodium/pcre/cares 与数学库。
        self.cpp_info.requires = ["pcre::pcre", "libev::libev", "libsodium::libsodium"]
        if self.options.with_cares:
            self.cpp_info.requires.append("c-ares::c-ares")
        self.cpp_info.system_libs = ["m", "pthread"]

        bindir = os.path.join(self.package_folder, "bin")
        self.output.info(f"shadowsocks-libev binaries: {bindir}")
        self.buildenv_info.define_path("SHADOWSOCKS_LIBEV_BINDIR", bindir)
        self.runenv_info.define_path("SHADOWSOCKS_LIBEV_BINDIR", bindir)
