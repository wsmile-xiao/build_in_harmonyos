#!/usr/bin/env python3
"""test_package — kamailio-kemix 6.0.6（Kamailio 经典 Makefile 构建体系）消费者测试。

真实加载产物：dlopen(kemix.so) → dlsym(exports) → mod_register → KEMI 函数表校验 →
真实调用 → dlclose；另有 check_kemix.py 做产物结构断言（纯 Python ELF 解析）。
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


class KamailioKemixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _c_compiler(self):
        """定位 e2e 用例的 C 编译器。

        构建/CI harness 会把 CC 导出为裸名字（本机实测 CC=clang），而 test() 内
        subprocess 继承的是 conan 进程环境，不保证 PATH 里有 OHOS SDK bin。
        故按「profile conf（绝对路径）→ OHOS SDK 兜底 → CC/cc/gcc（which 解析）」
        顺序选取，全部不可用才报错。
        """
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

    def test(self):
        # R34 实质验证：对打包产物 kemix.so 做真实检查
        # （ELF 架构 / 动态依赖 / 模块描述符与 KEMI 注册入口符号 / 许可证文件）
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "kemix.so")
        assert os.path.isfile(module), f"kemix.so not found at {module}"
        self.output.info(f"kemix.so found: {module}")

        checker = os.path.join(self.source_folder, "check_kemix.py")
        env = Environment()
        env.define("KEMIX_MODULE", module)
        env.define("KEMIX_PACKAGE_FOLDER", package_folder)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')

        # rule12 鸿蒙特有端到端消费者用例：真实走通
        # dlopen(kemix.so) -> dlsym(exports) -> dlsym(mod_register) -> 调用注册入口
        # -> 观察 sr_kemi_modules_add 收到的 KEMI 函数表 -> 真实调用其中一个函数指针
        # （模拟 kamailio core 的 loadmodule + KEMI 注册消费路径），而非仅产物结构断言。
        # 编译器由 _c_compiler() 解析（不依赖裸 CC）。
        #
        # kemix 是 core 插件（引用 get_debug_level / sr_kemi_xval_null / SIP 解析器等
        # core 符号），而 OHOS/musl 的加载器不做惰性绑定——dlopen 时全部未定义符号都要
        # 解析完，故必须把 kamailio_core_stub.c（最小 core 符号层）一并编译进测试可执行
        # 文件，并用 -Wl,--export-dynamic 导出其符号供 dlopen 解析。
        e2e_src = os.path.join(self.source_folder, "test_kemix_e2e.c")
        stub_src = os.path.join(self.source_folder, "kamailio_core_stub.c")
        # 编译产物写入 build/ 子目录：test_package 的 build_folder 即本目录，
        # 直接落在此处会留下未被 .gitignore 覆盖的 ELF（R19 预编译二进制）。
        # 仓库 .gitignore 已忽略任意层级的 build/，故统一落到该子目录。
        e2e_dir = os.path.join(self.build_folder, "build")
        os.makedirs(e2e_dir, exist_ok=True)
        e2e_bin = os.path.join(e2e_dir, "test_kemix_e2e")
        cc = self._c_compiler()
        self.output.info(f"e2e compiler: {cc}")
        cmd = [cc, "-std=c11", e2e_src, stub_src, "-o", e2e_bin,
               "-I", self.source_folder, "-Wl,--export-dynamic", "-ldl"]
        subprocess.run(cmd, check=True)

        # 运行时库搜索路径：模块目录（kemix.so 无第三方依赖，仅需 libc，由系统提供）
        lib_dirs = []
        for cand in (os.path.join(package_folder, "lib"),
                     os.path.join(package_folder, "lib", "kamailio", "modules")):
            if cand and os.path.isdir(cand) and cand not in lib_dirs:
                lib_dirs.append(cand)
        self.output.info(f"e2e LD_LIBRARY_PATH entries: {lib_dirs}")

        e2e_env = Environment()
        e2e_env.define("KEMIX_MODULE", module)
        for lib_dir in lib_dirs:
            e2e_env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        with e2e_env.vars(self).apply():
            self.run(f'"{e2e_bin}" "{module}"')
