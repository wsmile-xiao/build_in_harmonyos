import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            deps = {str(d.ref.name): d.package_folder
                    for d in self.dependencies.values()}
            # 传递依赖库目录（ucommon 静态链 gnutls/nettle 等）
            extra = [deps[name] + "/lib" for name in deps
                     if name not in ("ccscript", "ucommon")]
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_ccscript.py")
            args = " ".join(f'"{p}"' for p in extra)
            self.run(
                f'{sys.executable} "{test_script}" '
                f'"{deps["ccscript"]}" "{deps["ucommon"]}" {args}',
                env="conanrun")
