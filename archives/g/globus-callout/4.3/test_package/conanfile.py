# test_package/conanfile.py — globus-callout 4.3 consumer test
"""L1 test: 编译并链接 libglobus_callout（include globus_callout.h），
验证头文件 + 库可被消费者正常使用。
"""
import os

from conan import ConanFile


class GlobusCalloutTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # TMPDIR 注入（鸿蒙安全框架拦 clang 创建临时文件）
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test_package.c")
        out = os.path.join(self.build_folder, "test_globus_callout")
        pkg = self.dependencies["globus-callout"].package_folder
        gc = self.dependencies["globus-common"].package_folder
        lt = self.dependencies["libtool"].package_folder
        self.run(
            f"{cc} {src} -o {out} -I{pkg}/include -I{gc}/include "
            f"-L{pkg}/lib -L{gc}/lib -L{lt}/lib "
            f"-lglobus_callout -lglobus_common -lltdl")

    def test(self):
        exe = os.path.join(self.build_folder, "test_globus_callout")
        # LD_LIBRARY_PATH 注入运行时 .so 目录（test 二进制链接的
        # libglobus_callout.so.0/libglobus_common.so.0/libltdl.so.7
        # 不在 loader 默认搜索路径——同 libsoup/atlas test 先例）
        _libs = []
        for _dep in ("globus-callout", "globus-common", "libtool"):
            _d = self.dependencies.get(_dep)
            if _d and _d.package_folder:
                _lp = os.path.join(_d.package_folder, "lib")
                if os.path.isdir(_lp) and _lp not in _libs:
                    _libs.append(_lp)
        self.run(f'LD_LIBRARY_PATH="{os.pathsep.join(_libs)}" {exe}')
