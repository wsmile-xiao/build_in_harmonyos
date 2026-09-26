# test_package/conanfile.py — globus-gsi-openssl-error 4.4 consumer test
"""L1 test: 编译并链接 libglobus_openssl_error（include globus_error_openssl.h），
验证头文件 + 库可被消费者正常使用。
"""
import os

from conan import ConanFile


class GlobusGsiOpensslErrorTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 直接声明 openssl：test 图中 openssl 边的 traits 为 run=False，
        # 会被整体 skip（package_folder=None）拿不到 include/lib 路径；
        # 直接 require 使其成为本 test 的直接依赖而参与解析。
        # 版本与主配方 R27 钉版一致（漂移时会显式冲突报错）。
        self.requires("openssl/3.5.6")

    def build(self):
        # TMPDIR 注入（鸿蒙安全框架拦 clang 创建临时文件）
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test_package.c")
        out = os.path.join(self.build_folder, "test_globus_gsi_openssl_error")
        _inc, _ld = [], []
        for _d in self.dependencies.values():
            _pf = _d.package_folder
            if not _pf:
                continue
            _inc.append(f"-I{os.path.join(_pf, 'include')}")
            _libdir = os.path.join(_pf, "lib")
            if os.path.isdir(_libdir):
                _ld.append(f"-L{_libdir}")
        self.run(
            f"{cc} {src} -o {out} {' '.join(_inc)} {' '.join(_ld)} "
            f"-lglobus_openssl_error -lglobus_common -lssl -lcrypto")

    def test(self):
        exe = os.path.join(self.build_folder, "test_globus_gsi_openssl_error")
        # LD_LIBRARY_PATH 注入运行时 .so 目录（test 二进制链接的
        # libglobus_openssl_error.so.0/libglobus_common.so.0/libcrypto.so.3
        # 不在 loader 默认搜索路径——同 globus-callout 4.3 test 先例）
        _libs = []
        for _d in self.dependencies.values():
            if not _d.package_folder:
                continue
            _lp = os.path.join(_d.package_folder, "lib")
            if os.path.isdir(_lp) and _lp not in _libs:
                _libs.append(_lp)
        self.run(f'LD_LIBRARY_PATH="{os.pathsep.join(_libs)}" {exe}')
