import os
import shutil

from conan import ConanFile


class HickleTestConan(ConanFile):
    """hickle test_package — 包完整性 + 可选功能往返测试.

    两级验证：
      1) 包完整性（硬断言）：hickle/__version__.py 存在且 __version__ == "5.0.3"，
         hickle/hickle.py 存在。移走产物即失败（过 L1e 破坏性反向验证）。
      2) 功能往返（可选）：h5py+numpy 可用时做 dump/load 往返；缺失则 SKIP，
         不阻断 CI（OHOS 上 numpy 可用，h5py 待 HDF5 部署）。
    """
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        hickle_pkg = self.dependencies["hickle"]
        site_packages = os.path.join(
            str(hickle_pkg.package_folder), "lib", "python3.12", "site-packages")
        self.output.info("hickle site-packages: " + site_packages)
        py = shutil.which("python3") or "python3"
        # test_type=explicit 下 test() 的工作目录是 self.build_folder，
        # 而 test.py 位于 self.source_folder（test_package 源码目录），
        # 故需构造绝对路径传入 python3，避免 "No such file or directory"。
        test_script = os.path.join(self.source_folder, "test.py")
        # L0h: self.run 内不使用 ${CC}/${CFLAGS} 等 shell 变量
        self.run('HICKLE_SITE_PACKAGES="{sp}" {py} "{ts}"'.format(
            sp=site_packages, py=py, ts=test_script))
