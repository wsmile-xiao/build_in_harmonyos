#!/usr/bin/env python3
"""test_package — zzuf 0.15 消费者验证

R34: test 必须实质调用被测包（禁止空壳）。zzuf 是 LD_PRELOAD 模糊工具，
消费者验证 = 编译真实受害者程序，用安装的 zzuf 二进制驱动并断言：
1. zzuf 二进制存在且可执行（--help 退出码 0）
2. 确定性：同 seed/ratio 两次 fuzz 输出 md5 一致（可复现实验）
3. 拦截链路：zzuf 驱动 victim 读文件与直接 stdin fuzz 的 md5 一致
   （libzzuf.so 注入子进程真实生效）
"""
import hashlib
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class ZzufTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["zzuf"].package_folder
        zzuf_bin = os.path.join(package_folder, "bin", "zzuf")
        assert os.path.isfile(zzuf_bin), f"zzuf binary not found: {zzuf_bin}"

        if not can_run(self):
            with open(zzuf_bin, "rb") as binary:
                assert binary.read(4) == b"\x7fELF", "zzuf is not an ELF binary"
            self.output.info(f"zzuf ELF binary exists: {zzuf_bin}")
            return

        work = os.path.join(self.build_folder, "tp")
        os.makedirs(work, exist_ok=True)
        data = os.path.join(work, "data.bin")
        with open(data, "wb") as f:
            f.write(bytes(range(256)) * 4)  # 1024 字节确定性输入

        # 1. --help 可执行
        self.run(f'"{zzuf_bin}" --help > /dev/null', env="conanrun")

        # 2. 编译真实受害者程序（test.c: 迷你 cat）
        cc = shutil.which("clang") or "cc"
        victim = os.path.join(work, "victim")
        self.run(
            f'"{cc}" -O1 -o "{victim}" '
            f'"{os.path.join(self.recipe_folder, "test.c")}"'
        )
        assert os.path.isfile(victim), "victim compile failed"

        def run_zzuf(seed, ratio, extra):
            out = os.path.join(work, f"out-{seed}-{ratio}-{extra}.bin")
            if extra == "direct":
                cmd = f'"{zzuf_bin}" -m -s {seed} -r {ratio} < "{data}"'
            elif extra == "victim":
                # victim 从 stdin 读取：需 -i (ZZUF_STDIN) 才被 libzzuf 拦截
                cmd = (
                    f'"{zzuf_bin}" -i -m -s {seed} -r {ratio} '
                    f'"{victim}" < "{data}"'
                )
            elif extra == "cat":
                cmd = f'"{zzuf_bin}" -m -s {seed} -r {ratio} cat "{data}"'
            # shell 重定向捕获输出（conan self.run 的 stdout 参数需文件对象）
            self.run(f'{cmd} > "{out}"', env="conanrun")
            with open(out) as f:
                return f.read().strip()

        # 2. 确定性：同 seed 两次 md5 一致
        h1 = run_zzuf(42, 0.01, "victim")
        h2 = run_zzuf(42, 0.01, "victim")
        assert h1 and h1 == h2, f"zzuf not deterministic: {h1} != {h2}"
        self.output.info(f"deterministic fuzz md5: {h1}")

        # 3. 拦截链路：direct / victim / cat 三种读路径 md5 一致
        hd = run_zzuf(7, 0.001, "direct")
        hv = run_zzuf(7, 0.001, "victim")
        hc = run_zzuf(7, 0.001, "cat")
        assert hd and hd == hv == hc, f"preload mismatch: {hd} / {hv} / {hc}"
        self.output.info(f"child preload interception ok: {hc}")

        self.output.info("zzuf 0.15 consumer validation PASSED")