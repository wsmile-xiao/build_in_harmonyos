import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        info = self.dependencies["ivar"].cpp_info
        # R34/L1e：显式校验包内产物路径存在，防止 CI 破坏性负测试 fallback
        # 到系统 ivar 误判为真测试。
        bindir = info.bindirs[0] if info.bindirs else ""
        if not bindir or not os.path.isdir(bindir):
            raise ConanException(f"ivar package bin dir missing: {bindir}")
        ivar = os.path.join(bindir, "ivar")
        if not os.path.isfile(ivar):
            raise ConanException(f"ivar binary missing in package: {ivar}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验包内产物存在")
            return
        info = self.dependencies["ivar"].cpp_info
        bindir = info.bindirs[0]
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_ivar.sh")
        # R33：被测二进制取自包路径并显式传入，禁止 PATH 撞车系统 ivar。
        # ivar 二进制 NEEDED libdeflate.so.0（libdeflate 包仅共享库形态）
        # → 显式前置依赖 libdirs（防御性注入，真机第 2 轮实测 conanbuild
        # 环境无依赖 lib 目录）
        runpaths = []
        for ref, dep in self.dependencies.host.items():
            if ref.ref.name == "ivar":  # Conan 2：键是 Requirement，name 在 ref.ref 上
                continue
            runpaths.extend(dep.cpp_info.libdirs)
        self.run(
            f'LD_LIBRARY_PATH="{":".join(runpaths)}:$LD_LIBRARY_PATH" '
            f'{bash} "{script}" "{bindir}/ivar"',
            env="conanrun")
