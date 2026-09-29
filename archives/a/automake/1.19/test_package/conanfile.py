import os
from conan import ConanFile


class TestPkg(ConanFile):
    """工具包的验证：**真的把工具跑起来**，而不是检查文件存在。

    这两个包的意义在于让消费方的 autoreconf 能用，所以除了 --version，
    还要验证 aclocal 能找到宏（ACLOCAL_PATH 接对了）。
    """
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def generate(self):
        # conan 2 不会为 test_package 自动生成 conanbuild 环境，
        # 而 test() 里 env="conanbuild" 依赖它注入 tool_requires 的
        # bin 目录（PATH）与 package_info 声明的 ACLOCAL_PATH/PERL5LIB。
        # 1.18 时代能过是因为运行环境 PATH 里恰有系统 aclocal，不可依赖。
        from conan.tools.env import VirtualBuildEnv
        VirtualBuildEnv(self).generate()

    def test(self):
        # 四断言独立在 test.sh（CI L0c 要求 test_package/ 有非 conanfile.py
        # 的测试源文件）；test() 经 self.source_folder 绝对路径驱动：
        # 真机 OHOS 内核策略禁止 shebang 直接执行（execve 脚本一律 EACCES），
        # 且 sh 的命令名查找会逐个 execve 探测 PATH 候选（conan 任务创建的
        # 脚本带 noexec 标签、探测直接被内核吞掉），必须显式给绝对路径让
        # sh 直接打开文件读入。该写法在允许 shebang 的环境（CI/Linux）下同样成立。
        # 依赖集里按 tested_reference_str 全串索引会 KeyError（conan 2 真机实测：
        # 包在依赖集里、但键的形式不同），先直取、失败就按包名匹配。
        try:
            dep = self.dependencies[self.tested_reference_str]
        except KeyError:
            dep = next(d for d in self.dependencies.values() if d.ref.name == "automake")
        bindir = os.path.join(dep.package_folder, "bin")
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run('sh "%s" "%s"' % (test_sh, bindir), env="conanbuild")
        # 鸿蒙特有测试：完整消费者端到端用例（aclocal→automake→configure
        # →make→make check→make install→运行产物），驱动逻辑见 test_e2e.sh。
        test_e2e = os.path.join(self.source_folder, "test_e2e.sh")
        self.run('sh "%s" "%s"' % (test_e2e, bindir), env="conanbuild")
