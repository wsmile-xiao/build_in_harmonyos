# words-fr 2.1 适配笔记

## 上游测试清点（R51）

上游源为 GNU Aspell French dictionary 0.50-3。已检查官方归档解压后的 45 个常规文件、README、configure、Makefile.pre 和文件名清单：

- tests/ 目录：0
- 上游测试程序或测试目标：0
- 注册的 ctest/pytest 测试：0
- README/configure/Makefile.pre 中测试目标检索结果：无；configure 中出现的 test 仅是 shell 条件表达式

因此不存在可运行的上游测试命令（上游测试总数 0）。移植验证由 test_package/ 中的数据消费者、HarmonyOS/AArch64 C++ 消费者及 Conan CI 完成；测试范围见 test_package/MANIFEST.yml，运行结果详见本节。

## 实现范围

使用上游默认 fr-60 词表，仅解码 fr-40-only.cwl 和 fr-60-only.cwl；不包含可选 fr-80 或 Swiss 词表。上游 fr.dat 声明 iso8859-1，配方将词条严格按 ISO-8859-1 解码为 Unicode，剥离 / 后的 Aspell 词形标志，去重并按仓库词典键排序，输出 UTF-8。当前数据源生成 629,569 个词条。

数据包不含可执行文件或库，Conan package ID 按架构清除；通过 WORDS_FR_FILE 提供安装后词表路径，并带上游 Copyright 与 COPYING。

## 验证结果

- Windows 开发环境配方单元测试：python -B -m unittest discover -s archives/w/words-fr/2.1/tests -v，16/16 通过。
- 真机目标：HarmonyOS 6.0，HongMeng Kernel 1.12.0，aarch64；Python 3.12.9；Conan 2.29.1；clang 15.0.4。
- 真机 Conan：以 OHOS/armv8 profile 执行 conan create 和 test_package。生成架构无关包 ID da39a3ee5e6b4b0d3255bfef95601890afd80709；Python 消费者 19 项断言通过，Python 缺失路径通过，C++ HarmonyOS/AArch64 消费者报告 WORDS_FR_HARMONY_OK entries=629569 machine=aarch64，C++ 缺失路径通过。消费者场景 4/4 通过。
- ConanVerifier：G1 配方完整性以及 G2 构建、G3 系统库隔离、G4 制品检查均通过。
- AArch64 本地 W3 CI：finish 工作流调用 ci/conan/setup.sh 与 ci/conan/build_and_test.sh。L0、L1、L4 通过；L2 因包不含可执行程序跳过；L5 因包不含 bin/lib 制品给出非阻塞 warn；W3 总体通过。
- 上游未提供测试套件；上游测试总数为 0。

## 收尾门禁说明

AArch64 finish 已生成成功的 W3 结果，但完整 finish 后续未全绿：G0 clean-verify 找不到该 Conan 数据包对应的构建上下文 tarball；W5 检出仓库既有 2,435 个待审知识草稿；submit readiness 要求 staging 标记和 release/debug tarball 目录。该包是 architecture-independent Conan 数据包，不产出 release/debug 二进制 tarball；这些收尾要求没有被伪造为已满足。graph validate 本身通过。用户未要求创建 PR。
