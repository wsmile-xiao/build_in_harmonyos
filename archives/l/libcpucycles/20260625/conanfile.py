#!/usr/bin/env python3
# libcpucycles 20260625 Conan 2 recipe (HarmonyOS PC / OHOS aarch64)
#
# 上游构建系统：./configure（python3 脚本）+ scripts-build/ + Makefile
#   - ./configure 生成 build/<arch>/ 构建树（Makefile、compilers、options 等）
#   - make          -> cd build && make
#   - make install  -> scripts-build/install（内部用 tempfile.mkdtemp(dir=<install-dir>)）
#   - configure 探测全部是 compile-only（try-*.c 用 $CC 试编译，不运行 target 二进制）
#
# 上游产物（build/<arch>/package/）：
#   - include/cpucycles.h + lib/libcpucycles.a + lib/libcpucycles.so.1
#   - bin/cpucycles-info（信息工具）、man 页
#
# OHOS 适配要点：
#   1. 工具链注入：上游 configure 不读取任何环境变量（源码中无 getenv），
#      CC/CFLAGS/AR/RANLIB 环境变量注入全部无效；编译器唯一来源是源码树的
#      compilers/default（每行 = 命令 + flags，逐行以 --version 探测，首个
#      可用者的整行被写入生成的脚本）。故 build() 先把 profile 通过
#      tools.build:compiler_executables.c 配置的 OHOS clang 前置到该文件
#      （仅修改构建缓存中的源码副本），上游原有候选行保留作 fallback。
#   2. 不绕过 make install：因 scripts-build/install 的 tempfile 临时目录创建在
#      setgid 目标目录（OHOS hmfs 挂载语义）内部，会因 umask 077 + setgid 位
#      导致 PermissionError；因此 recipe 改为直接收集 build/<arch>/package/ 产物
#      （上游 install 本身只是 copy2 + rename，无编译动作，语义等价）。
#   3. 后端选择 100% 在运行时由 cpucycles_init() 完成（sigsetjmp 捕获 SIGILL 等
#      逐个实测），保留完整 runtime backend selection，不做构建期硬编码。
#
# 上游无正式测试套件（无 test/、无 CI、无 make check/test 目标）；消费者验证
# 由本包 test_package/ 承担（API 契约测试）。

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get


class LibcpucyclesConan(ConanFile):
    name = "libcpucycles"
    version = "20260625"
    description = "libcpucycles: a fast library for counting CPU cycles"
    topics = ("cpucycles", "cycle-counter", "benchmark", "rdtsc")
    url = "https://atomgit.com/csc-harmonyos-porter/archives"
    homepage = "https://cpucycles.cr.yp.to"
    license = "Unlicense"
    # 上游 make 同时产出 libcpucycles.a 与 libcpucycles.so.1（sharedlib 脚本
    # 无条件执行），shared=True/False 均有真实产物支撑，故为通用 library
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    exports_sources = "patches/*"

    def source(self):
        # strip_root: tarball 解压出 libcpucycles-20260625/ 子目录，剥离后
        # 源码直接位于 source_folder，./configure 才能以 cwd=source_folder 运行
        get(self, strip_root=True, **self.conan_data["sources"][self.version][0])
        # 零 patch：上游 20260625 在 OHOS 上无需任何源码修改

    # 与上游 compilers/default 中 clang 行完全一致的 flags（OHOS clang wrapper
    # 已自带 --sysroot/--target 等参数，无需另行传递）
    _CC_FLAGS = "-Wall -fPIC -fwrapv -Qunused-arguments -O -fvisibility=hidden"

    def _cc(self):
        # 编译器只取 tools.build:compiler_executables["c"]（Conan 2 标准 conf，
        # 由 profile 注入），解析为真实可执行文件路径并校验；任一步失败都
        # fail closed——绝不静默回落到 PATH 中的裸 clang/gcc（即本缺陷根源）。
        conf = self.conf.get("tools.build:compiler_executables")
        cc = conf.get("c") if conf else None
        if not cc:
            raise ConanException(
                "tools.build:compiler_executables.c is not configured; refusing to "
                "let upstream configure pick an arbitrary compiler from PATH"
            )
        # 相对命令（如 "clang"）解析为 PATH 中的真实路径；绝对路径原样保留，
        # 但同样要求存在且可执行
        resolved = shutil.which(cc)
        if not resolved or not os.path.isfile(resolved):
            raise ConanException(
                f"configured C compiler '{cc}' does not resolve to an executable file"
            )
        return resolved

    def _prepend_configured_compiler(self):
        # 上游 configure 的编译器唯一来源是源码树 compilers/default：每行
        # “<命令> <flags…>”，逐行以 --version 探测，首个成功者的整行（含
        # flags）被写入 build/<arch>/scripts/ 的 compiledefault/sharedlib/
        # staticlib 等脚本。这里把配置的 OHOS clang 按同一格式前置到 build()
        # 使用的源码副本，上游原有候选行原样保留作 fallback；只改 Conan 构建
        # 缓存中的副本，上游 tarball 与仓库归档均不受影响。
        cc = self._cc()
        line = f"{cc} {self._CC_FLAGS}"
        path = os.path.join(self.source_folder, "compilers", "default")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if content.startswith(line + "\n"):
            return  # 已前置（重复 build 时幂等）
        with open(path, "w", encoding="utf-8") as f:
            f.write(line + "\n" + content)

    def generate(self):
        pass

    def build(self):
        # 生成 build/<arch>/ 树。上游 configure 自动探测 arch=arm64（从配置的
        # clang -dumpmachine 得到 aarch64-unknown-linux-ohos → arm64）。
        # 探测全部 compile-only，不运行 target 二进制，交叉安全。
        # 注意：configure 不读取环境变量，CC/CFLAGS/AR/RANLIB 注入无效，工具链
        # 必须通过 compilers/default 前置注入（见 _prepend_configured_compiler）。
        self._prepend_configured_compiler()
        self.run(
            f"./configure --prefix={self.package_folder}",
            cwd=self.source_folder,
        )
        self.run("make", cwd=self.source_folder)

    def package(self):
        # 上游 install（scripts-build/install）在 OHOS 上会失败：
        # tempfile.TemporaryDirectory(dir=<prefix>/lib) 创建在 setgid 目录里，
        # umask 077 + setgid → tmp 目录 mode 0700 属主另一个 uid → EACCES。
        # 故直接从 build/<arch>/package/ 收集（install 本身无编译动作）。
        pkg = os.path.join(self.source_folder, "build", "arm64", "package")
        lib_dst = os.path.join(self.package_folder, "lib")
        copy(self, "cpucycles.h", os.path.join(pkg, "include"), os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "libcpucycles.so*", os.path.join(pkg, "lib"), lib_dst)
        else:
            copy(self, "libcpucycles.a", os.path.join(pkg, "lib"), lib_dst)
        # cpucycles-info 是上游信息工具（非测试），可执行文件不进入 package
        # （上游把它安装到 bin/，这里按仓库惯例只保留 lib+include）
        pass

    def package_info(self):
        self.cpp_info.libs = ["cpucycles"]
