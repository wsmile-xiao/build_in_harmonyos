#!/usr/bin/env python3
"""test_package for worklog 2.1 — 执行被测包真实产出的 OHOS 二进制做功能断言。

设计要点
--------
* R34 / CI L1e：先无条件断言 bin/worklog 存在且为 ELF 可执行文件。
  当 CI 把 bin/ 整体移走后本断言必然失败 → 反向验证通过（证明测试真实
  依赖被测包，而非 echo/print 空壳）。该断言不受 can_run() 影响。
* 当构建/宿主同 profile（CI 与本地均如此，can_run() 为 True）时，进一步
  真实执行二进制：7 项功能断言（含 2 项鸿蒙特有），见 run_tests.sh。
* 跨编译且不可运行的宿主上，退化为产物静态校验（仍为真实断言，非空壳）。
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class WorklogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 无需编译消费者：worklog 是纯 CLI 工具，不导出库/头文件。
        # 上游 Makefile 仅有 all/install/clean/dist，无 `make check` 目标，
        # 因此上游官方测试不存在（见 MANIFEST.yml 清点说明）。
        pass

    def test(self):
        pkg = self.dependencies["worklog"].package_folder
        bin_path = os.path.join(pkg, "bin", "worklog")
        man_page = os.path.join(pkg, "share", "man", "man1", "worklog.1.gz")

        # ---- R34 / L1e：无条件产物断言（不依赖 can_run）----
        if not os.path.isfile(bin_path):
            raise ConanException(f"worklog binary missing from package: {bin_path}")
        mode = os.stat(bin_path).st_mode
        if not mode & stat.S_IXUSR:
            raise ConanException(f"worklog binary is not executable: {bin_path}")
        with open(bin_path, "rb") as fh:
            if fh.read(4) != b"\x7fELF":
                raise ConanException(f"worklog binary is not an ELF: {bin_path}")
        self.output.info(f"artifact OK: {bin_path}")

        if not os.path.isfile(man_page):
            raise ConanException(f"worklog man page missing from package: {man_page}")
        self.output.info(f"man page OK: {man_page}")

        if not can_run(self):
            self.output.warning("host cannot execute OHOS binaries; static checks only")
            return

        # ---- 真实执行 7 项功能断言 ----
        script = os.path.join(self.source_folder, "run_tests.sh")
        example = os.path.join(self.source_folder, "projects.example")
        for required in (script, example):
            if not os.path.isfile(required):
                raise ConanException(f"test source missing: {required}")
        self.run(f'sh "{script}" "{bin_path}" "{self.source_folder}"')
