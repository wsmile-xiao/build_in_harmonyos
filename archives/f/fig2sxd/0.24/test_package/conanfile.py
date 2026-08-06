#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.build import can_run


class Fig2sxdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _check_binary_exists(self):
        """检查 fig2sxd 二进制是否已安装到 package 中"""
        binary = os.path.join(self.dependencies["fig2sxd"].package_folder, "usr", "bin", "fig2sxd")
        if os.path.exists(binary):
            self.output.info(f"fig2sxd binary found: {binary}")
            return True
        self.output.error(f"fig2sxd binary not found at {binary}")
        return False

    def test(self):
        # 始终检查二进制产物是否存在
        binary_ok = self._check_binary_exists()
        if not binary_ok:
            raise Exception("fig2sxd binary not found in package")

        if can_run(self):
            # 调用独立测试脚本 test.sh：用上游 examples/smalltext.fig 验证
            # 转换功能（fig2sxd 输出 .sxd 为 zip 格式，文件头应为 PK）
            fig2sxd_bin = os.path.join(self.dependencies["fig2sxd"].package_folder, "usr", "bin", "fig2sxd")
            fig_file = os.path.join(self.source_folder, "src", "smalltext.fig")
            out_file = os.path.join(self.build_folder, "out.sxd")
            test_sh = os.path.join(self.source_folder, "test.sh")
            self.run(f'sh "{test_sh}" "{fig2sxd_bin}" "{fig_file}" "{out_file}"')
            self.output.info("fig2sxd conversion verified successfully (sxd zip header OK)")
        else:
            # 交叉编译场景：无法运行二进制，但已检查产物存在
            self.output.info("Cross-building: skipping runtime tests, binary existence verified")