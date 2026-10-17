#!/usr/bin/env python3
"""Conan recipe — dnsperf 2.15.1（DNS 性能测试工具）.

dnsperf / resperf 是 DNS-OARC 维护的 DNS 延迟与吞吐量测试工具
（原 Nominum/Akamai，2019 年起由 DNS-OARC 维护）。
构建系统：GNU Autotools。
平台：OHOS aarch64 / Linux。
依赖：openssl（TLS）、concurrencykit（无锁并发）、libnghttp2（DoH）、
json-c（datafile JSON 输出）；ldns（dynamic update）为可选依赖且 remote
无对应包，configure 对其优雅降级（自动禁用 dynamic update 支持）。

HMDFS 适配说明：profile 的 CONFIG_SHELL 指向的 bash 在 HMDFS 深路径下
getcwd 失败、/tmp 可能只读，因此 build() 不使用 Conan Autotools helper，
而是把源码复制到独立构建目录后用 /bin/sh 脚本完成 configure/make/
make install。CC、CFLAGS、依赖 include/lib 路径全部从 conan conf 与
依赖包推导，无硬编码。
"""

import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class DnsperfConan(ConanFile):
    name = "dnsperf"
    version = "2.15.1"
    description = "DNS performance testing tools (dnsperf, resperf)"
    license = "Apache-2.0"
    homepage = "https://www.dns-oarc.net/tools/dnsperf/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("dnsperf supports POSIX platforms")

    def requirements(self):
        # run=True：openssl 未声明 package_type、concurrencykit 的 shared
        # 选项默认关闭，conan 会推导 run=False，导致测试图跳过其二进制包、
        # VirtualRunEnv 生成的 LD_LIBRARY_PATH 缺少其 lib 目录，dnsperf/
        # resperf 二进制运行时找不到 libssl/libcrypto/libck
        self.requires(
            "openssl/3.5.6",
            transitive_headers=True,
            transitive_libs=True,
            run=True,
        )
        self.requires(
            "concurrencykit/0.7.2",
            transitive_headers=True,
            transitive_libs=True,
            run=True,
        )
        self.requires(
            "libnghttp2/1.70.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "json-c/0.18",
            transitive_headers=True,
            transitive_libs=True,
        )

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self)

    def _gnu_triplet(self):
        machine = {
            "armv8": "aarch64",
            "armv7": "arm",
            "x86_64": "x86_64",
            "x86": "i686",
        }.get(str(self.settings.arch), str(self.settings.arch))
        return f"{machine}-unknown-linux-ohos"

    def _cc(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", check_type=dict
        )
        cc = executables.get("c") if executables else None
        if not cc:
            raise ConanException(
                "tools.build:compiler_executables must be set in the profile"
            )
        return cc

    def _module_flags(self):
        # configure.ac 通过 PKG_CHECK_MODULES 查询 libssl/libcrypto/ck/
        # libnghttp2/json-c 模块；依赖包的 .pc 文件按 conan 包名生成，与
        # configure 查询的模块名并不一一对应（如 openssl.pc 无法满足 libssl
        # 模块查询）。pkg-config 宏优先使用已导出的 <prefix>_CFLAGS/_LIBS
        # 环境变量，因此按模块名直接注入。
        openssl = self.dependencies["openssl"].package_folder
        ck = self.dependencies["concurrencykit"].package_folder
        nghttp2 = self.dependencies["libnghttp2"].package_folder
        json_c = self.dependencies["json-c"].package_folder
        return {
            "libssl": (openssl, ["ssl"]),
            "libcrypto": (openssl, ["crypto"]),
            "ck": (ck, ["ck"]),
            "libnghttp2": (nghttp2, ["nghttp2"]),
            "json_c": (json_c, ["json-c"]),
        }

    def _dep_flags(self):
        # 复刻 AutotoolsDeps 提供的编译/链接搜索路径（均取自依赖包）
        inc_flags, lib_flags = [], []
        for dep in self.dependencies.values():
            for d in dep.cpp_info.includedirs:
                inc_flags.append(f"-I{os.path.join(dep.package_folder, d)}")
            for d in dep.cpp_info.libdirs:
                lib_flags.append(f"-L{os.path.join(dep.package_folder, d)}")
        return inc_flags, lib_flags

    def build(self):
        apply_conandata_patches(self)

        cc = self._cc()
        inc_flags, lib_flags = self._dep_flags()

        cflags = {
            "Release": "-O3",
            "Debug": "-g",
            "RelWithDebInfo": "-O2 -g",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "")
        cppflags = " ".join(inc_flags)
        if str(self.settings.build_type) == "Release":
            cppflags = f"-DNDEBUG {cppflags}"

        configure_args = [
            "./configure",
            "--prefix=/",
            "'--bindir=${prefix}/bin'",
            "'--sbindir=${prefix}/bin'",
            "'--libdir=${prefix}/lib'",
            "'--includedir=${prefix}/include'",
            "'--oldincludedir=${prefix}/include'",
        ]
        if str(self.settings.os) == "OHOS":
            if not cross_building(self):
                # 原生 OHOS 环境无法运行 config.guess（HMDFS 只读 tmp），
                # 显式给出三元组；config.sub 已由 0001 补丁支持 linux-ohos
                triplet = self._gnu_triplet()
                configure_args += [f"--build={triplet}", f"--host={triplet}"]
            else:
                configure_args += [f"--host={self._gnu_triplet()}"]

        # 独立构建目录：TMPDIR 优先（HMDFS 深路径在 /bin/sh 下可用），
        # 未设置时退回 conan 构建目录（保证只读 /tmp 环境也能构建）
        build_dir = tempfile.mkdtemp(
            prefix="dnsperf-",
            dir=os.environ.get("TMPDIR") or self.build_folder,
        )
        shutil.copytree(
            self.source_folder, build_dir, symlinks=True, dirs_exist_ok=True
        )

        lines = [
            "#!/bin/sh",
            "set -e",
            f'cd "{build_dir}"',
            f'export CC="{cc}"',
            # 避免 profile CONFIG_SHELL 指向的 bash 触发 HMDFS getcwd 缺陷
            'export CONFIG_SHELL="/bin/sh"',
            'export SHELL="/bin/sh"',
            f'export PATH="{os.path.dirname(cc)}:$PATH"',
            f'export CFLAGS="{cflags}"',
            f'export CPPFLAGS="{cppflags}"',
            f'export LDFLAGS="{" ".join(lib_flags)}"',
            # 不导出 LIBS：conftest 若链接依赖共享库，运行时加载器无法在
            # 默认路径找到 conan cache 中的 .so（加载失败导致 configure
            # 报 "cannot run C compiled programs"）。最终二进制的链接由
            # Makefile 中 configure 替换的模块变量（$(libssl_LIBS) 等）完成。
        ]
        for prefix, (folder, libs) in self._module_flags().items():
            include = os.path.join(folder, "include")
            lib = os.path.join(folder, "lib")
            lines.append(f'export {prefix}_CFLAGS="-I{include}"')
            libs_flags = " ".join([f"-L{lib}"] + [f"-l{n}" for n in libs])
            lines.append(f'export {prefix}_LIBS="{libs_flags}"')
        lines.append(" ".join(configure_args))
        lines.append("make -j1")
        lines.append(f'make install DESTDIR="{self.package_folder}"')

        script = os.path.join(build_dir, "_build.sh")
        with open(script, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(script, 0o755)
        subprocess.check_call(["/bin/sh", script], cwd=build_dir)

    def package(self):
        # 构建脚本已完成 make install DESTDIR=package_folder
        pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
