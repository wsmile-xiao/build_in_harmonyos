# Dhrystone 2.1 适配记录

源码采用 Netlib 的原始 dhry-c shar 文件，SHA256 为
038a7e9169787125c3451a6c941f3aca5db2d2f3863871afcdce154ef17f4e3e。
运行时仅依赖系统 libc，不需要第三方 Conan 依赖；W0 预检通过。

上游文件共 8 个：RATIONALE、README_C、VARIATIONS、dhry.h、dhry_1.c、
dhry_2.c、dhry_c.dif、submit.frm。没有构建脚本、tests 目录或自动化测试框架。
dhry_1.c 在每次基准运行后打印参考值供人工检查，消费者测试把这些值转换为断言。
上游独立单元测试 0、集成测试 0、注册测试 0；不把补充用例算作上游测试。

保留计时循环内的所有语句和计算，以及两个独立编译单元，关闭 LTO、普通函数
内联和 CMake unity build，遵守 RATIONALE 的 separate compilation/no procedure
merging 规则；保留上游允许的标准字符串函数优化。
计时使用原有 times() 用户 CPU 时间，以 sysconf(_SC_CLK_TCK) 获取刻度并保持
至少 2 秒的有效测量门槛；短运行仅检查正确性，不宣称有效性能成绩。
现代化函数声明、标准库头文件和返回类型，指针输出改为 %p。
迭代次数从 stdin 读取，拒绝非正整数及超过 INT_MAX-10 的值，防止数组计数溢出。
拒绝填满 127 字节缓冲区的过长输入，防止合法前缀掩盖截断后的非法内容。
增加 --version/--help 以支持仓库 smoke test，不改变正常 stdin 使用方式。

init-build 的双轨提取仅识别 tar/zip 和现代构建文件，不支持本次官方 shar；
按 R14 使用手动入口建立原始/工作源码目录。配方只提取固定 8 个 shar 成员，
不执行下载内容中的 shell 命令。补丁由 refresh-patch --auto 生成。

上游未提供单独 LICENSE 或明确 SPDX 许可标识，因此标记 LicenseRef-Dhrystone，
保留作者原始说明及源码头部，不冒充 MIT/BSD 授权。

## 最终验证

- Windows SDK 26.0.0 / Clang 15.0.4 / Conan 2.29.1：AArch64 和 x86_64
  `conan create` 均通过；`test_package` 验证 ELF 架构及 musl interpreter。
- WSL Ubuntu / GCC 13.3 / Conan 2.29.1：从官方源码构建并运行 12 项通用
  消费者测试；鸿蒙专用项在 Linux 明确跳过。
- HarmonyOS 6.0.0.48(SP31DEVC00E47R1P3) x86_64 虚拟机：实际运行最终
  Conan 包，13/13 通过、0 跳过；未将此结果冒充 AArch64 实机验证。
- 仓库 `FinishPipeline.step35_local_ci()` 执行 setup.sh + build_and_test.sh
  通过，包含 L1e 缺少产物时消费者测试失败的反向检查。
- CI 显示 L4 warn：补丁上下文包含原版基准的 strcpy。它们复制固定字符串到
  31 字节数组，长度可界定且是测量负载的一部分；保留这些操作。另行对两种最终
  OHOS ELF 检查，均为 PIE、NX、完整 RELRO。
- 原始测量循环逐字一致；两种 OHOS 反汇编均保留 Proc_1→Proc_3、Proc_6→Func_3、
  Func_2→Func_1。独立审查发现的截断输入和内联问题均已修复并复验。

## 本地框架限制

`finish` 整体流程默认面向配备原生工具链的 OHOS worker。本地虚拟机没有
Python/Conan/Clang，采用 Windows SDK 交叉编译 + HDC 实测，并在 WSL 运行原始
W3 门禁和 ConanVerifier；不修改共享 ci/scripts/profile，也不伪造 CI 结果。
W3 通过仓库已有 JUNK_PR_DIFF 参数读取本次包的完整 diff，避免旧 origin/main
基线把无关软件变更算入当前包。profile 位于仓库外的本地任务目录。

ConanVerifier 已运行并返回 PASS，但其包 ID 提取未识别含小数点版本的引用，
导致 G4/L2/L4/L5 部分跳过；报告保留原始输出，另有 W3 实际产物检查、HDC
--version 和双架构 ELF/哈希核验补足，不能把跳过解释成已执行。

额外的 Linux 框架冒烟测试 15/15 通过；test_v1221.py 为 15 通过、2 失败，
失败仅为共享生成索引 catalog.tsv 的 headeronly/copy 分类数量断言。
未修改共享索引或框架文件。这两项不是 Dhrystone 包的失败。

完整测试证据和复现命令见 reports/test-report.md。状态为 built，未上传制品或创建 PR。
