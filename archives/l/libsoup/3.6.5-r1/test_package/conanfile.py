# test_package/conanfile.py — libsoup 3.6.5 consumer test (R34)
"""L1 test:
1. 编译并运行 test.cpp（链接 libsoup-3.0，真实调用
   soup_version_string() 验证库可用）。
"""
import os

from conan import ConanFile


class LibsoupTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式 requires（test() 需用依赖包路径组装 LD_LIBRARY_PATH）
        self.requires("glib/2.84.0")

    def build(self):
        # TMPDIR 注入（鸿蒙安全框架拦 clang 创建临时文件）
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cxx = ccs.get("cpp") or "clang++"
        src = os.path.join(self.source_folder, "test.cpp")
        out = os.path.join(self.build_folder, "test_libsoup")
        pkg = self.dependencies["libsoup"].package_folder
        glib_pkg = self.dependencies["glib"].package_folder
        self.run(
            f"{cxx} {src} -o {out} -std=c++17 "
            f"-I{pkg}/include/libsoup-3.0 -I{glib_pkg}/include/glib-2.0 "
            f"-I{glib_pkg}/lib/glib-2.0/include "
            f"-L{pkg}/lib -L{glib_pkg}/lib -lsoup-3.0 -lglib-2.0 -lgobject-2.0")

    def test(self):
        exe = os.path.join(self.build_folder, "test_libsoup")
        pkg = self.dependencies["libsoup"].package_folder
        glib_pkg = self.dependencies["glib"].package_folder
        # LD_LIBRARY_PATH 收集 libsoup 及其所有依赖包 lib 目录
        # （libsoup-3.0.so.0 加载需 glib/nghttp2/libpsl/sqlite3/zlib 等）
        _lib_dirs = [os.path.join(pkg, "lib"), os.path.join(glib_pkg, "lib")]
        for _dep in self.dependencies.values():
            _dp = _dep.package_folder
            if _dp:
                _dl = os.path.join(_dp, "lib")
                if os.path.isdir(_dl) and _dl not in _lib_dirs:
                    _lib_dirs.append(_dl)
        ld_path = os.pathsep.join(_lib_dirs)
        # libidn2（libpsl 的依赖，传递依赖不在 self.dependencies 直接可见）
        import glob as _glob
        for _idn in _glob.glob(
                "/storage/Users/currentUser/.conan2/p/libidn*/p/lib"):
            if os.path.isdir(_idn) and _idn not in _lib_dirs:
                _lib_dirs.append(_idn)
        ld_path = os.pathsep.join(_lib_dirs)
        # test_libsoup 用 clang++ 编译，NEEDED 含 libc++_shared.so——
        # 加 SDK llvm lib（从 clang realpath 推导，同 bart/avisynthplus 先例）
        import subprocess as _sp
        try:
            _clang = ccs.get("cpp") or "clang++"
            _real = _sp.run(
                ["realpath", _clang], capture_output=True, text=True)
            _llvm_lib = os.path.join(
                os.path.dirname(os.path.dirname(_real.stdout.strip())),
                "lib", "aarch64-linux-ohos")
            if os.path.isdir(_llvm_lib):
                ld_path += os.pathsep + _llvm_lib
        except Exception:
            pass
        _old = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = (
            ld_path + (os.pathsep + _old if _old else ""))
        # 不带 env="conanrun"（conanrun 环境会重置 LD_LIBRARY_PATH）
        self.run(exe)
