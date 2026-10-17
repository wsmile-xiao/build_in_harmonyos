"""test_package/conanfile.py — DRAFT (kbtin 2.3, application 包).

kbtin 不装头/库（只有一个 KBtin 可执行 + 一个数据面 KBtin_help.gz），所以消费者测试的合格形态
只能是"运行被测二进制并断言行为"（AGENTS §10）：驱动脚本用上游语料的逐字输入/输出对做 6 条断言，
退出码决定 test() 成败。同时断言运行期数据面确实随包落地（不是只查文件存在，见下 test() 的第二步）。
"""
import gzip
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy

required_conan_version = ">=1.59.0"


class KbtinTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def export_sources(self):
        # 驱动脚本必须显式导出，否则 cache 里没有 test_package/*.py（同 lbcd 的 copy 写法）
        copy(self, "*.py", src=self.recipe_folder, dst=self.export_sources_folder)

    @property
    def _kbtin(self):
        return os.path.join(self.dependencies["kbtin"].cpp_info.bindirs[0], "KBtin")

    def build(self):
        pass                      # 无被测库可编；行为断言在 test() 里由 Python 驱动

    def test(self):
        if not can_run(self):
            self.output.info("SKIP consumer test: 交叉产物在当前会话不可执行（按 §10 标 SKIP，不记通过）")
            return
        exe = os.path.join(self.recipe_folder, "kbtin_behavior.py")
        if not os.path.isfile(exe):   # 从 cache 跑时脚本在 export_sources_folder
            exe = os.path.join(self.export_sources_folder, "kbtin_behavior.py")
        work = os.path.join(self.build_folder, "behaviour")
        os.makedirs(work, exist_ok=True)
        self.run(f'python3 "{exe}" "{self._kbtin}" "{work}"', env="conanrun")

        # 运行期数据面：KBtin_help.gz 必须随包存在且可解（gzip 解压一次，不是 stat）
        # conan2 里 user_info 不跨包可读（真机逐字：AttributeError: 'ConanFileInterface'
        # object has no attribute 'user_info'）⇒ 改从被测包的 resdirs 定位数据面
        dep = self.dependencies["kbtin"]
        cands = [os.path.join(dep.package_folder, r, "kbtin", "KBtin_help.gz")
                 for r in dep.cpp_info.resdirs]
        cands += [os.path.join(dep.package_folder, r, "KBtin_help.gz")
                  for r in dep.cpp_info.resdirs]
        helpgz = next((c for c in cands if os.path.isfile(c)), "")
        if not helpgz:
            raise ConanInvalidConfiguration(
                f"运行期帮助数据未随包落地，找过：{cands}")
        with gzip.open(helpgz, "rb") as fh:
            body = fh.read()
        if len(body) < 100:
            raise ConanInvalidConfiguration(f"KBtin_help.gz 解出 {len(body)}B，异常小")
        self.output.info(f"KBtin_help.gz 解压 OK: {len(body)}B")
