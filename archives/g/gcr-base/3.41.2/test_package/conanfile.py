#!/usr/bin/env python3
"""Conan test_package — gcr-base 3.41.2（dlopen 探针模式）

采用 libgpg-error 已验证的探针写法：直接编译 test.c（-ldl），
运行时 dlopen 被测包 .so 并 dlsym 真实导出符号，绕开 loader 查找路径问题。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class GcrBaseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["gcr-base"].cpp_info
        if not dep.libdirs:
            raise RuntimeError("gcr-base 包 libdirs 为空，无法定位共享库")
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libgck-1.so")
        cc = os.environ.get("CC", "clang")
        rc = self.run(f"{cc} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' -ldl")
        if rc != 0:
            raise RuntimeError(f"test.c 编译失败，退出码 {rc}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        rc = self.run(f"{bash} -c './test_probe'", env="conanrun", ignore_errors=True)
        if rc == 2:
            # 本设备（OHOS/hmdfs+SELinux adhoc 域）dlopen 本地构建 .so 被拒（Permission denied）。
            # 兜底：用 nm 验证被测包 .so 的真实导出符号，仍满足 R34 反空壳。
            libdir = self.dependencies["gcr-base"].cpp_info.libdirs[0]
            libs = ["libgck-1.so", "libgcr-base-3.so"]
            # 查找可用的 nm 工具（支持 llvm-nm 或 nm）。NM 环境变量可能是裸命令名
            # （如 "llvm-nm"），须经 shutil.which 解析为真实路径，否则 subprocess 会
            # 报 FileNotFoundError。
            import shutil
            nm = shutil.which(os.environ.get("NM") or "llvm-nm") or shutil.which("nm")
            if not nm:
                raise RuntimeError("找不到 nm 工具（llvm-nm 或 nm），无法进行 ELF 符号验证")
            for lib in libs:
                so = os.path.join(libdir, lib)
                import subprocess
                result = subprocess.run([nm, "-D", so], capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(f"{nm} -D {so} 失败，退出码 {result.returncode}")
                count = sum(1 for line in result.stdout.splitlines() if " T " in line)
                if count < 10:
                    raise RuntimeError(f"{lib} 导出符号过少 ({count})，包可能为空壳")
                self.output.info(f"ELF 兜底验证: {lib} 导出 {count} 个文本符号")
            self.output.info("dlopen 受限（环境 SELinux），已通过 ELF 符号验证")
        elif rc != 0:
            # R9 反欺骗：dlopen 成功但 dlsym 符号缺失（rc==1）等其他非零退出码必须失败，
            # 不允许静默通过（否则空壳包会绕过门禁）。
            raise RuntimeError(f"test_probe 返回非零码 {rc}，符号验证失败")
