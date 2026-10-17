import os
from conan import ConanFile


class IrqbalanceTestConan(ConanFile):
    """CLI 工具包验证：真的把 irqbalance 跑起来，而不是只检查文件存在。

    irqbalance 是 application 包（无库/CMake target 可链接），消费者验证直接
    执行安装后的二进制并核验版本输出（R34 实质测试）。
    注意：上游 --version 分支退出码为 1（irqbalance.c: version(); exit(1)），
    故用管道 grep 校验输出，不把上游退出语义当失败。
    """
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["irqbalance"]
        bindir = dep.package_folder
        cands = [os.path.join(bindir, "bin", "irqbalance"),
                 os.path.join(bindir, "sbin", "irqbalance"),
                 os.path.join(bindir, "irqbalance")]
        exe = next((p for p in cands if os.path.isfile(p)), None)
        if exe is None:
            raise Exception("irqbalance 可执行文件未安装到 package（%s）" % bindir)
        # 执行真实测试源 test.sh（与 MANIFEST.yml 声明一致），
        # conanrun 环境提供 glib 的 LD_LIBRARY_PATH
        self.run('sh "%s" "%s"' % (
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sh"),
            exe), env="conanrun")
        self.output.info("[ok] irqbalance 真实执行并输出版本号 1.9.4")