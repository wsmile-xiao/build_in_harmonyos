import os

from conan import ConanFile
from conan.errors import ConanException


class DhSysuserTestConan(ConanFile):
    """test_package for script/application packages — runs test.sh with the package bin dir.

    OHOS 无 perl 运行时，脚本无法直接执行；此处对包产物做存在性 + 内容断言
    （L1e：CI 会先删除包 bin/ 再重跑本测试，断言必须读取包内产物以保证破坏后失败）。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        dep = self.dependencies["dh-sysuser"]
        candidates = []
        if dep.cpp_info.bindirs:
            candidates += [os.path.join(dep.package_folder, d) for d in dep.cpp_info.bindirs]
        candidates.append(os.path.join(dep.package_folder, "bin"))
        bin_dir = next((p for p in candidates if os.path.isdir(p)), None)
        if bin_dir is None:
            raise ConanException(
                f"dh-sysuser package has no bin/ directory under {dep.package_folder}; "
                "package() may have failed to install scripts"
            )
        self.run(f'{bash} test.sh "{bin_dir}"', env="conanrun")