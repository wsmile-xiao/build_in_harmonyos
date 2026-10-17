# test_package/conanfile.py — Vol 1.5.4 consumer test
"""L1 test: 编译并链接 libVol，验证头文件可 include。"""
import os

from conan import ConanFile


class VolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        cxx = ccs.get("cpp") or "clang++"
        src = os.path.join(self.source_folder, "test_vol.cpp")
        out = os.path.join(self.build_folder, "test_vol")
        pkg = self.dependencies["vol"].package_folder
        cu = self.dependencies["coinutils"].package_folder
        osi = self.dependencies["coin-or"].package_folder
        self.run(
            f"{cxx} {src} -o {out} -std=c++11 "
            f"-I{pkg}/include -I{pkg}/include/coin "
            f"-I{cu}/include/coin -I{osi}/include/coin "
            f"-L{pkg}/lib -L{cu}/lib -L{osi}/lib "
            f"-lVol -lOsi -lCoinUtils -lm"
        )

    def test(self):
        self.run(os.path.join(self.build_folder, "test_vol"))
