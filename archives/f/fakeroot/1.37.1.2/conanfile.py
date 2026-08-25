#!/usr/bin/env python3
"""Conan recipe for fakeroot 1.37.1.2 on HarmonyOS PC."""

import os
import subprocess

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class FakerootConan(ConanFile):
    name = "fakeroot"
    version = "1.37.1.2"
    description = "fakeroot — simulate root privileges for package building"
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/clint/fakeroot"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_env(self):
        # OHOS 编译器（clang/clang++）位于 /data/service/hnp/bin/，不在默认 PATH。
        # 参照仓库内 jack/1.9.22 先例，从 conan conf 读取编译器并导出。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        return env

    def build(self):
        apply_conandata_patches(self)
        # fakeroot 使用 autotools；Debian orig tarball 自带 configure。
        # OHOS 交叉编译：显式 --build/--host，关闭可选依赖（libcap/ACL）。
        # OHOS host_os=linux-ohos 不匹配 configure 的 use_ipc 检测
        # (linux-gnu*|linux-musl*)——cross compiling 报错——patch case 加
        # linux-ohos*（ac_cv_use_ipc 走 sysv 分支）
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path) as f:
                content = f.read()
            old_case = "(linux-gnu*|linux-musl*)"
            new_case = "(linux-gnu*|linux-musl*|linux-ohos*)"
            if old_case in content:
                content = content.replace(old_case, new_case)
                with open(configure_path, "w") as f:
                    f.write(content)
                self.output.info("Patched configure: use_ipc case 加 linux-ohos*")
            else:
                self.output.warning("use_ipc case pattern not found in configure")
        # OHOS 文件系统（hmdfs）umask 077 创建 mode 0700 目录——config.status
        # 的 mktemp（./confXXXXXX）后续写 subs1.awk 时 Permission denied——
        # patch configure 用 umask 022（参照 libedit 先例）
        if os.path.exists(configure_path):
            with open(configure_path) as f:
                content = f.read()
            original = 'umask 077 && mktemp -d "./confXXXXXX"'
            replacement = 'umask 022 && mktemp -d "./confXXXXXX"'
            if original in content:
                content = content.replace(original, replacement)
                with open(configure_path, "w") as f:
                    f.write(content)
                self.output.info("Patched configure: umask 077 -> 022 for temp dir")
            else:
                self.output.warning("umask 077 pattern not found in configure")
        with self._compiler_env().vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && ./configure --prefix="{self.package_folder}" '
                "--build=aarch64-unknown-linux-gnu "
                "--host=aarch64-unknown-linux-ohos "
                "--disable-libcap --disable-acl --with-ipc=tcp",
                env="conanbuild",
            )
            # OHOS musl 无 STAT64_SUPPORT——INT_SEND_GET_XATTR 走 SEND_GET_XATTR
            # （无64）分支，但该宏未定义——链接报 SEND_GET_XATTR: symbol not
            # found——补宏定义（语义与 SEND_GET_XATTR64 相同，参照 communicate.h
            # 的 send_get_xattr 声明）——必须在 make 之前 patch，保证
            # libfakeroot.so 是 patch 后编译的
            lfc = os.path.join(self.source_folder, "libfakeroot.c")
            with open(lfc) as f:
                content = f.read()
            anchor = "#define SEND_GET_XATTR64(a,b,c) send_get_xattr64(a,b)\n"
            add = ("#define SEND_GET_XATTR64(a,b,c) send_get_xattr64(a,b)\n"
                   "#define SEND_GET_XATTR(a,b,c) send_get_xattr(a,b)\n")
            if anchor in content and "#define SEND_GET_XATTR(a,b,c)" not in content:
                content = content.replace(anchor, add)
                with open(lfc, "w") as f:
                    f.write(content)
                self.output.info("Patched libfakeroot.c: 补 SEND_GET_XATTR 宏定义")
            else:
                self.output.warning("SEND_GET_XATTR macro patch skipped")
            self.run(f'cd "{self.source_folder}" && make -j1', env="conanbuild")
            # 上游测试：make check（test/Makefile.am 的 15 个 TESTS——
            # t.chmod_dev/t.chown/t.cp-a/t.tar 等——automake TESTS 框架）
            # 缺环境就下：make check 无需额外依赖，直接实跑统计真实通过率
            import re
            # 干净环境（不复用 os.environ——conan 环境可能带 LD_PRELOAD/
            # LD_LIBRARY_PATH 等干扰 fakeroot 的 LD_PRELOAD 测试机制）
            env_check = {
                "PATH": "/data/service/hnp/bin:/system/bin:/usr/bin:/bin",
                "TMPDIR": os.path.join(self.source_folder, "_tmp"),
                "PWD": os.path.join(self.source_folder, "test"),
                "HOME": self.source_folder,
                "SHELL": "/data/service/hnp/bin/bash",
                "LANG": "C",
                "LC_ALL": "C",
            }
            os.makedirs(env_check["TMPDIR"], exist_ok=True)
            # HMDFS getcwd 失败——bash 保留 PWD 环境变量——测试脚本用
            # $PWD/../scripts/fakeroot 定位构建根——PWD 必须指向 test 目录
            # （脚本 cwd），否则 $PWD/../scripts 解析错（blesh 同款坑）
            env_check["PWD"] = os.path.join(self.source_folder, "test")
            r = subprocess.run(
                ["make", "check"], cwd=os.path.join(self.source_folder, "test"),
                env=env_check, capture_output=True, text=True, timeout=900)
            out = (r.stdout or "") + (r.stderr or "")
            # automake TESTS 输出：PASS: t.xxx / FAIL: t.xxx / ERROR: t.xxx
            n_pass = len(re.findall(r"^PASS: ", out, re.M))
            n_fail = len(re.findall(r"^FAIL: ", out, re.M))
            n_err = len(re.findall(r"^ERROR: ", out, re.M))
            n_skip = len(re.findall(r"^SKIP: ", out, re.M))
            self.output.info("FAKEROOT UPSTREAM TEST PASS/FAIL/SKIP/ERROR: %d/%d/%d/%d (make check 15 TESTS)" %
                             (n_pass, n_fail, n_skip, n_err))
            if r.returncode != 0:
                # 不阻断构建——失败明细如实记录（待排查系统级阻塞项）
                for line in out.splitlines():
                    if re.match(r"^(FAIL|ERROR): ", line):
                        self.output.info("FAKEROOT FAILED TEST: %s" % line.strip())
            self.run(f'cd "{self.source_folder}" && make install', env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
