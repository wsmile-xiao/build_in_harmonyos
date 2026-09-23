#!/usr/bin/env python3
"""Conan recipe — nift (nifty-site-manager / nsm) 3.0.3 (纯 Makefile 构建).

nift 是 C++ 编写的跨平台静态网站生成器，自包含项目：内嵌 Lua-5.3/LuaJIT、
exprtk、rapidjson、hashtk，无任何外部 conan 依赖。
构建产物为命令行可执行文件 nift 与 nsm（nsm 是原名，nift 是同二进制的拷贝）。

构建要点（探索阶段实测验证）：
- Makefile 无 configure 脚本；`detected_OS` 取自 `uname`，在本 OHOS 环境
  返回 HarmonyOS → 走通用 *nix 分支。
- 顶层 Makefile BUNDLED 分支默认编译内嵌 LuaJIT；显式传 `LUA_VERSION=5.3`
  走内嵌 Lua-5.3 的 `generic` 目标，规避 LuaJIT 子构建在 OHOS 上的额外适配成本。
- Lua-5.3/src 子 Makefile 硬编码 `CC= gcc -std=gnu99`；把 CC/CXX 放最外层
  make 命令行（经 MAKEFLAGS 传播到子 make）即可覆盖（R33：编译器必须来自
  profile conf tools.build:compiler_executables，不裸用 ${CC} 等 shell 变量）。
- 上游 `make install` 会对二进制执行 `chmod 755`；本机 HMDFS 对部分 inode
  拒绝 chmod（E046 平台限制）导致 install 目标中断。配方 package() 改为直接
  copy nsm/nift 到包内 bin/（与上游 install 语义等价：仅把两个可执行文件放入
  bin/），不依赖 chmod，CI/本地均稳健。
- 上游无 make check / test 目标、无 tests/ 目录；功能验证在 test_package
  中以真实调用 nift/nsm 的 11 项消费者断言代替（R34）。
- 环境覆盖（可选）：exprtk 单头库在 -O3/-O2 下 clang 峰值内存很高；在内存
  受限的构建机上可设 NIFT_OPT=-O0/-O1 显著降压，用 NIFT_JOBS 调并行度。
  默认不设 CXXFLAGS（沿用上游 Makefile 的 -O3 与平台宏），仅在 NIFT_OPT 显式
  给出时整体覆盖 CXXFLAGS（须自带全部必要宏；仅作用于 nsm 自身 TU，Lua 子
  构建用其自有 CFLAGS 不受影响）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NiftConan(ConanFile):
    name = "nift"
    version = "3.0.3"
    description = "Nift (aka nifty-site-manager / nsm) - fast cross-platform static website generator"
    license = "MIT"
    homepage = "https://github.com/nifty-site-manager/nsm"
    url = "https://github.com/nifty-site-manager/nsm"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33/R49: 编译器必须来自 profile conf tools.build:compiler_executables
        # （ci/conan/profiles/ohos-aarch64 注入 /data/service/hnp/bin/clang[++]）。
        # conf 缺失时显式失败而非回退裸编译器名（裸名可能静默编译出非 OHOS 目标）。
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c")
        cxx = comp_execs.get("cpp")
        if not cc or not cxx:
            raise ConanInvalidConfiguration(
                "nift build 需要 profile [conf] tools.build:compiler_executables 提供 c/cpp "
                "（参考 ci/conan/profiles/ohos-aarch64）"
            )
        # 并行度默认按 CPU 数取 min(8)；NIFT_JOBS 可显式覆盖（内存受限机用 -j1/-j2）。
        jobs = os.cpu_count() or 2
        if jobs > 8:
            jobs = 8
        jobs_env = os.environ.get("NIFT_JOBS")
        if jobs_env:
            jobs = max(1, int(jobs_env))
        # 优化级别：默认不覆盖（沿用上游 Makefile 内嵌 -O3 与 -D 宏）。
        # NIFT_OPT 显式给出时整体覆盖 CXXFLAGS（命令行的 CXXFLAGS 会覆盖 Makefile
        # 的 CXXFLAGS+=，故须自带全部必要宏）。
        opt = os.environ.get("NIFT_OPT")
        make_target = f"make -C {self.source_folder} CC={cc} CXX={cxx} LUA_VERSION=5.3 -j{jobs}"
        if opt:
            cxxflags = (f"-std=c++11 {opt} -Dexprtk_disable_caseinsensitivity "
                        "-D__BUNDLED__ -D__LUA_VERSION_5_3__")
            make_target = (
                f"make -C {self.source_folder} CC={cc} CXX={cxx} "
                f"CXXFLAGS=\"{cxxflags}\" LUA_VERSION=5.3 -j{jobs}"
            )
        # 顶层 all -> bundled-msg make-lua nsm；LUA_VERSION=5.3 使 make-lua 走
        # Lua-5.3 的 generic 目标；CC/CXX 命令行变量经 MAKEFLAGS 传播到子 make。
        self.run(make_target)

    def package(self):
        # 上游 install 目标 = chmod 755 + mv nift/nsm 到 ${DESTDIR}${PREFIX}/bin。
        # 这里做等价物：把构建产物 nsm/nift 拷入包内 bin/（copy 而非 mv，保留源
        # 文件以便复现），不依赖 chmod（HMDFS E046）。文件模式继承构建产物
        # （owner 可执行），消费者同用户运行无碍。
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for exe in ("nsm", "nift"):
            src = os.path.join(self.source_folder, exe)
            if not os.path.isfile(src):
                raise ConanInvalidConfiguration(f"构建产物缺失: {src}")
            shutil.copy2(src, os.path.join(bindir, exe))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
