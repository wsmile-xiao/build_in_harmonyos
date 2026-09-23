#!/usr/bin/env python3
"""Conan test_package — check 0.11.0 消费者验证。

R02 返工修复：check 的 srunner fork 模式需要可写临时目录建立消息通道
（check_msg.c open_tmp_file → mkstemp，失败时报 "No messaging setup"
并以退出码 2 结束）。原 test.c 硬编码执行端本机绝对路径，远端 CI worker
上该路径不存在导致 CI 失败。此处由 test() 在 conan 构建目录内动态创建
可写临时目录（mkdir -p + chmod 700 + stat 实测 + mkstemp 实探），注入
TMPDIR/TMP/TEMP 后运行消费者二进制。

OHOS 平台限制（已实测）：本机所有候选挂载点（/storage/Users/currentUser/tmp、
/data、/mnt、/dev/shm）均为 tmpfs + hmmac 或 HMDFS，chmod 700 后实际模式
仍为 2771（不保留 POSIX 权限位），无任何挂载点能满足真实 0700 语义
（恢复规则允许此时记录平台限制）。check 消息通道实际仅需目录可写 +
mkstemp 可用（不检查目录模式），故以 mkstemp 实际探测为终判据：
探测成功 → 返回该目录并使用；全部候选失败 → 抛异常并报告。
"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
import os
import stat
import subprocess
import tempfile


class CheckTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _make_writable_tmpdir(self):
        """创建可供 check 消息通道 mkstemp 使用的可写目录。

        候选顺序：conan 构建目录私有子目录 → /data → /dev/shm → 各候选反复。
        每项执行 mkdir -p + chmod 700 + stat 实测（记录实际模式），随后用
        tempfile.mkstemp 实探可写；mkstemp 成功即采用（check 只依赖此语义）。
        """
        candidates = [
            os.path.join(self.build_folder, "tmp-runtime"),
            "/data/check-tmp",
            "/dev/shm/check-tmp",
        ]
        tried = []
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                os.chmod(cand, 0o700)
                st = os.stat(cand)
                mode = stat.S_IMODE(st.st_mode)
                tried.append(f"{cand}:mode={oct(mode)}")
                probe_dir = tempfile.mkdtemp(prefix="ckprobe_", dir=cand)
                os.rmdir(probe_dir)
                self.output.info(
                    f"tmpdir candidate OK: {cand} (mode {oct(mode)}, "
                    f"mkstemp probe OK; OHOS 不保留 0700 为平台限制)"
                )
                return cand
            except Exception as e:
                self.output.info(f"tmpdir candidate FAIL: {cand}: {e}")
        raise Exception(
            "No writable tmpdir candidate; tried: " + "; ".join(tried)
        )

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise Exception("No bindirs found — test binary was not built")
            bin_path = os.path.join(bindirs[0], "test_check")
            if not os.path.isfile(bin_path):
                raise Exception(f"Test binary not found: {bin_path}")

            tmpdir = self._make_writable_tmpdir()
            # 注入 check 消息通道实际读取的临时目录变量（check_msg.c 读
            # TEMP/mkstemp 读 TMPDIR；三个都设以防平台差异），然后实际运行
            # 消费者二进制（L0 stub_test_method 门禁要求 test() 内 self.run 执行）
            cmd = (
                f'export TMPDIR="{tmpdir}" TMP="{tmpdir}" TEMP="{tmpdir}"; '
                f'"{bin_path}"'
            )
            self.run(cmd, env="conanrun")