#!/usr/bin/env python3
"""test_package — atlas-ecmwf 0.46.0 consumer test (R34).

L1 test:
1. 编译并运行 test.cpp（链接 libatlas，真实调用
   atlas::Library::instance().version() 验证库可用）。
"""
import os

from conan import ConanFile


class AtlasEcmwfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式 requires（test() 需用依赖包路径组装 LD_LIBRARY_PATH）
        self.requires("eckit/2.0.7")

    def build(self):
        # TMPDIR 注入（鸿蒙安全框架拦 clang 创建临时文件）
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cxx = ccs.get("cpp") or "clang++"
        src = os.path.join(self.source_folder, "test.cpp")
        out = os.path.join(self.build_folder, "test_atlas")
        pkg = self.dependencies["atlas-ecmwf"].package_folder
        eckit_pkg = self.dependencies["eckit"].package_folder
        self.run(
            f"{cxx} {src} -o {out} -std=c++17 "
            f"-I{pkg}/include -I{eckit_pkg}/include "
            f"-L{pkg}/lib -L{eckit_pkg}/lib -latlas")

    def test(self):
        exe = os.path.join(self.build_folder, "test_atlas")
        # 运行时需找到 libatlas 及其所有依赖（libatlas.so 的 NEEDED 是
        # 相对路径 ../../lib/libatlas_io.so——cd 到包 lib 目录使相对路径
        # 从 cwd 解析；libatlas 依赖 libomp.so（OpenMP，SDK llvm lib）与
        # libaec/libzip 等）
        pkg = self.dependencies["atlas-ecmwf"].package_folder
        eckit_pkg = self.dependencies["eckit"].package_folder
        _lib_dirs = [os.path.join(pkg, "lib"), os.path.join(eckit_pkg, "lib")]
        for _dep in self.dependencies.values():
            _dp = _dep.package_folder
            if _dp:
                _dl = os.path.join(_dp, "lib")
                if os.path.isdir(_dl) and _dl not in _lib_dirs:
                    _lib_dirs.append(_dl)
        # SDK llvm lib（libomp.so/libc++_shared.so）——用 Python
        # os.path.realpath 推导 clang 真实目录（不能依赖外部 realpath
        # 命令：CI worker 的原始 PATH 不含其所在目录，异常被吞后 SDK
        # lib 从未加入 LD_LIBRARY_PATH——libsoup 同款教训）
        _llvm_root = os.path.dirname(
            os.path.dirname(os.path.realpath("/data/service/hnp/bin/clang")))
        # libomp.so 在 llvm/lib/aarch64-linux-ohos/（triplet 子目录），
        # 不在 llvm/lib/ 直接下面——两个目录都加入
        for _sub in ("lib", os.path.join("lib", "aarch64-linux-ohos")):
            _ll = os.path.join(_llvm_root, _sub)
            if os.path.isdir(_ll) and _ll not in _lib_dirs:
                _lib_dirs.append(_ll)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(_lib_dirs)
        # cd 到包 lib 目录（相对 NEEDED ../../lib/ 从 cwd 解析——
        # package() 已 patchelf 修复为 SONAME，此处兜底）
        os.chdir(os.path.join(pkg, "lib"))
        # LD_LIBRARY_PATH 命令行前缀（self.run 默认 conanrun 环境会重置
        # os.environ 注入——同 build() 修复，命令行前缀确保 libomp/
        # 依赖库路径对 test 子进程生效）
        self.run(
            f'LD_LIBRARY_PATH="{os.pathsep.join(_lib_dirs)}" {exe}')
