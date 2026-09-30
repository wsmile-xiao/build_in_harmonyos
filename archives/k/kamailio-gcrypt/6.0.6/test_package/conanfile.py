#!/usr/bin/env python3
"""test_package — kamailio-gcrypt 6.0.6（Kamailio 经典 Makefile 构建体系）消费者测试。

真实加载产物：dlopen(gcrypt.so) → dlsym(exports) → 校验模块描述符与 cfg 命令表 →
dlsym(mod_register) → 观察 core 侧 sr_kemi_modules_add() 收到的 KEMI 函数表 →
dlsym(aes128_*) → **AES-128-CBC 已知答案（KAT）实测**（openssl 独立复算的向量）→
dlclose；另有 check_gcrypt_module.py 做产物结构/依赖闭包断言（纯 Python ELF 解析）。
"""

import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


# OHOS SDK clang：与 ci/conan/profiles/ohos-aarch64 的
# tools.build:compiler_executables 一致，作为 conf 读不到时的兜底绝对路径。
OHOS_SDK_CLANG = "/data/service/hnp/bin/clang"


class KamailioGcryptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _c_compiler(self):
        """定位 e2e 用例的 C 编译器（profile conf → OHOS SDK 兜底 → CC/cc/gcc）。"""
        exes = {}
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:  # conf 跨上下文不可读时退化为路径探测
            pass
        tried = []
        for cand in (exes.get("c"), OHOS_SDK_CLANG, os.environ.get("CC"),
                     "clang", "cc", "gcc"):
            if not cand:
                continue
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
            found = shutil.which(cand)
            if found:
                return found
            tried.append(cand)
        raise ConanException(f"e2e: no usable C compiler (tried: {', '.join(tried)})")

    def _writable_tmpdir(self):
        """返回一个可写的临时目录供编译器放置中间文件。

        必须显式提供：鸿蒙目标机 /tmp 只读，若沿用环境里的 TMPDIR，clang 会直接
        `unable to make temporary file: No such file or directory` 而编译失败。
        优先沿用仍可写的既有 TMPDIR，否则退到 build 目录下的 tmp/。
        """
        cand = os.environ.get("TMPDIR")
        if cand and os.path.isdir(cand) and os.access(cand, os.W_OK):
            return cand
        fallback = os.path.join(self.build_folder, "build", "tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def test(self):
        # R34 实质验证：对打包产物 gcrypt.so 做真实检查
        # （ELF 身份 / 模块描述符与 cfg 命令表 / DT_NEEDED 闭包 / 无 RPATH / 许可证）
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "gcrypt.so")
        assert os.path.isfile(module), f"gcrypt.so not found at {module}"
        self.output.info(f"gcrypt.so found: {module}")

        # 动态依赖包（libgcrypt / libgpg-error）产物目录：既供 check 脚本做
        # 「未定义符号是否被依赖包提供」的闭包核验，也供 e2e 运行时定位 .so
        libgcrypt_pkg = self.dependencies["libgcrypt"].package_folder
        libgpg_error_pkg = self.dependencies["libgpg-error"].package_folder

        checker = os.path.join(self.source_folder, "check_gcrypt_module.py")
        env = Environment()
        env.define("KAMAILIO_GCRYPT_MODULE", module)
        env.define("KAMAILIO_GCRYPT_PACKAGE_FOLDER", package_folder)
        env.define("LIBGCRYPT_PACKAGE_FOLDER", libgcrypt_pkg)
        env.define("LIBGPG_ERROR_PACKAGE_FOLDER", libgpg_error_pkg)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')

        # rule12 鸿蒙特有端到端消费者用例：真实走通
        # dlopen(gcrypt.so) → dlsym(exports) 校验模块契约与 cfg 命令表
        # → dlsym(mod_register) 调用并观察 sr_kemi_modules_add 收到的 KEMI 表
        # → dlsym(aes128_*) 做 AES-128-CBC 已知答案（KAT）实测 → dlclose。
        # 编译器由 _c_compiler() 解析（不依赖裸 CC）。
        #
        # gcrypt.so 是 core 插件（引用 sr_kemi_modules_add / fixup_spve2_pvar / dprint 等
        # core 符号），而 OHOS/musl 加载器不做惰性绑定——dlopen 时全部未定义符号都要
        # 解析完，故把 kamailio_core_stub.c（最小 core 符号层）一并编译进测试可执行文件，
        # 并用 -Wl,--export-dynamic 导出符号供 dlopen 解析。
        e2e_src = os.path.join(self.source_folder, "test_gcrypt_e2e.c")
        stub_src = os.path.join(self.source_folder, "kamailio_core_stub.c")
        # 编译产物写入 build/ 子目录（仓库 .gitignore 已忽略任意层级 build/），
        # 避免在 test_package 目录留下未被忽略的 ELF（R19 预编译二进制）
        e2e_dir = os.path.join(self.build_folder, "build")
        os.makedirs(e2e_dir, exist_ok=True)
        e2e_bin = os.path.join(e2e_dir, "test_gcrypt_e2e")
        # 运行时库搜索路径：模块目录 + conan 依赖包 lib（libgcrypt/libgpg-error 非
        # 系统同名库，OHOS sysroot/目标机 /lib 均无，由 conan 依赖链提供运行时 .so）
        lib_dirs = []
        for cand in (os.path.join(package_folder, "lib"),
                     os.path.join(package_folder, "lib", "kamailio", "modules"),
                     os.path.join(libgcrypt_pkg, "lib"),
                     os.path.join(libgpg_error_pkg, "lib")):
            if cand and os.path.isdir(cand) and cand not in lib_dirs:
                lib_dirs.append(cand)
        self.output.info(f"e2e LD_LIBRARY_PATH entries: {lib_dirs}")

        cc = self._c_compiler()
        self.output.info(f"e2e compiler: {cc}")

        # 编译与运行共用同一环境：LD_LIBRARY_PATH 供运行时解析 libgcrypt/libgpg-error，
        # TMPDIR 供编译器放置中间文件（鸿蒙 /tmp 只读，缺 TMPDIR 时 clang 直接报
        # "unable to make temporary file"）。
        e2e_env = Environment()
        e2e_env.define("KAMAILIO_GCRYPT_MODULE", module)
        e2e_env.define("TMPDIR", self._writable_tmpdir())
        for lib_dir in lib_dirs:
            e2e_env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        with e2e_env.vars(self).apply():
            cmd = [cc, "-std=c11", e2e_src, stub_src, "-o", e2e_bin,
                   "-I", self.source_folder, "-Wl,--export-dynamic", "-ldl"]
            subprocess.run(cmd, check=True)
            self.run(f'"{e2e_bin}" "{module}"')
