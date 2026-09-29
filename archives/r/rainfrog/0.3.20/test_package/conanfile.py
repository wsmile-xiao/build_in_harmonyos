import os

from conan import ConanFile
from conan.tools.build import can_run


class RainfrogTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_rainfrog.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("not runnable on this host — skipping runtime test")
            return

        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_rainfrog.sh")

        # 必须用 self.run(...)，不能用 subprocess.run(...)：
        # CI 门禁 L0d 对 test_package/conanfile.py 做静态检查——
        #   grep -q "self\.run" 否则判 "stub_test_method" 并拦截整个构建
        # （L0_RESULT=fail，实测 CI #63090）。self.run 同时会应用 conanrun 运行期
        # 环境（本 test_package 已声明 generators = "VirtualRunEnv"），
        # 而非零返回码会直接抛错，等价于原先的手工 returncode 判断。
        self.run(f'sh "{script}" "{pkg_folder}"', env="conanrun")
