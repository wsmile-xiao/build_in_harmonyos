"""Conan test_package — combine 0.4.0

R34：test_package 必须真实调用被测包。combine 是纯命令行工具
（package_type = application；包内没有 .a/.so —— src/Makefile.am 只有
bin_PROGRAMS = combine，lib/ 的 libdf.a 是 noinst_LIBRARIES），
所以消费者测试以**使用者身份直接运行打包出来的 combine 二进制**，
对"退出码 + 输出"做双断言，而不是只 include / 只链接 / 只打印。

测试源文件 = test.sh（由下面的 test() 在 conanrun 环境里真实执行）。
计数口径：按 test.sh 的「7 个编号节」计 7 项断言 —— 第 7 节本身含 7a/7b 两项反向
检查，所以**检查项是 8、断言数是 7**；同一口径同步在 test.sh 的 echo 文案、
test_package/MANIFEST.yml、notes.md 与版本级 manifest.yaml，⛔ 只改一处。
  1) --version 退出码 0 且报告 "combine (combine) 0.4.0"
  2) --help    退出码 0 且给出用法横幅（证明 CLI 解析层真的编进去了）
  3) 字段投影 -D , -o 1,3 -w  ⇒ stdout 逐字节 == "a,c / d,f / g,i"
  4) -t 指定输出文件           ⇒ 文件内容逐字节 == "b / e / h"
  5) 引用文件匹配 d1{1,2,3} ∩ r1{1,3}
     ⇒ stderr 统计 "Number of reference-data matches:  2"（combine 的看家功能）
  6) 不加 -u 时不合并重复键    ⇒ d2(1,1,2) 投影第 1 字段 == "1 / 1 / 2"
  7) 反向节（计 1 项断言，内含 2 项检查）
     7a) 数据文件不存在            ⇒ 非零退出（反向）
     7b) -u 出现在任何 -r 之前     ⇒ 非零退出（反向，用法错误）

期望值由 test.sh 自己写下的输入数据 + `combine --help` 的 documented 语义推出，
不是从构建日志反填的。
"""
import os

from conan import ConanFile


class CombineTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L0c：测试源文件 test.sh 必须存在并被真实执行（7 个编号节的口径与上方同源）
        self.run("sh %s" % os.path.join(self.recipe_folder, "test.sh"),
                 env="conanrun")
