# Dhrystone 2.1 验证报告

日期：2026-09-12。分支：feat/dhrystone-2.1，基线 upstream/main a675263b91。

## 结果与边界

| 验证 | 实际环境 | 结果 |
|---|---|---|
| Conan create、source 下载/校验/补丁重放 | Windows，Conan 2.29.1，SDK 26.0.0，Clang 15.0.4 | OHOS AArch64、x86_64 两种构建通过 |
| Conan 消费者运行测试 | WSL Ubuntu，GCC 13.3，Conan 2.29.1 | 12 通过，1 鸿蒙专用项跳过 |
| 最终安装程序运行测试 | HarmonyOS 6.0.0.48(SP31DEVC00E47R1P3)，Linux 5.10.210，x86_64 | 13/13 通过，0 失败，0 跳过 |
| 本地 W3 CI | WSL，仓库原始 setup.sh + build_and_test.sh，显式 Linux profile | exit 0；L0/L1/L2/L5 通过；L4 仅原版 strcpy 上下文告警 |
| ConanVerifier | WSL，显式 Linux profile | 返回 PASS；包 ID 定位失败导致部分产物门禁跳过，已另行验证实际产物 |
| 实际 OHOS ELF | AArch64、x86_64 | PIE、NX、完整 RELRO，架构及 musl interpreter 正确 |
| 独立代码审查 | 源码、补丁、Conan 配方、日志、二进制 | 2 项问题已修复，复审无剩余实质问题 |

仅有 x86_64 虚拟机；**未执行 AArch64 真机运行测试或远端 CI**。W3 的 Linux
运行结果用于本地流程验证，不能冒充原生 OHOS worker CI。鸿蒙运行结果来自真实
HDC 连接的 HarmonyOS 虚拟机，使用同一 test_package/test_dhrystone.py，非宿主模拟。

## 上游测试清点

Netlib dhry-c 的 SHA256：
`038a7e9169787125c3451a6c941f3aca5db2d2f3863871afcdce154ef17f4e3e`。
8 个成员：RATIONALE、README_C、VARIATIONS、dhry.h、dhry_1.c、dhry_2.c、
dhry_c.dif、submit.frm。没有 Makefile/CMakeLists、tests 目录或自动化测试框架，
注册用例数为 0。原程序会打印参考变量值，但不自动判定成功/失败。
补充测试独立统计为 12 项 CLI 集成测试 + 1 项鸿蒙专项测试。

## 新增用例

| 方法 | 检查 |
|---|---|
| test_version / test_help / test_unknown_option | 版本、帮助及错误选项退出状态 |
| test_one_iteration / test_multiple_iterations / test_whitespace_input | 1、10000、17 次运行的全部标量、数组、记录、字符串参考值和 64 位指针相等性 |
| test_zero_rejected / test_negative_rejected | 非正迭代数拒绝 |
| test_junk_rejected | 非数字、尾部垃圾、多数字、127 字节合法前缀掩盖尾部垃圾 |
| test_overflow_rejected / test_eof_rejected | 整数上限/超长整数/空输入拒绝 |
| test_measured_rate | 自动提高迭代数达到至少两秒的用户 CPU 时间，速率为正且有限，最终状态仍正确 |
| test_ohos_loader_and_sandbox | SDK 的 __OHOS__ 编译条件、64 位 time_t、真实动态加载器、times/sysconf/进程 CPU 时钟、musl interpreter；从含空格和中文的可写临时目录运行安装程序 |

最终虚拟机运行：160000000 次，26143790 Dhrystones/s，13 项耗时 11.630 秒。
这个数据仅证明有效计时分支执行；虚拟机成绩不代表 HarmonyOS PC 真机性能。
鸿蒙探针输出：`OHOS_RUNTIME_OK ticks=100 libc=/lib/ld-musl-x86_64.so.1 time_t=8`。

## 测试有效性与基准语义

- 改动前测试实际检出零次迭代被接受和指针输出截断，2/2 失败；修复后通过。
- 独立审查提出的超长合法前缀在鸿蒙产物上复现失败，增加完整行长度检查后通过。
- W3 L1e 隐藏实际包内 bin/ 后，Conan 消费者测试失败；恢复后正常。
- 测量循环与官方源码逐字相同，片段 SHA256：
  `7a1e2eb5c2ecc40ce635d76b7da7a1d995101fb962ff48144a97adafa2a014af`。
- 遵循 RATIONALE 禁用普通函数内联、LTO、unity build；两种 OHOS 反汇编均确认
  Proc_1→Proc_3、Proc_6→Func_3、Func_2→Func_1 的调用仍存在。
- L4 对 strcpy 的告警来自基准固定字符串操作及补丁上下文，不改写这些测量操作。

## 最终产物哈希

| 目标 | 包 ID | 安装程序 SHA256 |
|---|---|---|
| OHOS x86_64 | 7a04d520acd845b96f805ffbcc51fac5b17a209e | 3c59beb470a705edb1fcf5626e9febe4c97721c370b55c33d821358ccd002c4c |
| OHOS AArch64 | 6b129b068851896169fae42d399fa922d239ce8a | d8c6a82322077320820bfb5d53df3e95efa60ce948d85eca4da0e6a6d40b960b |

设备上 sha256sum 与 x86_64 安装程序一致。产物均保存在本地任务的 Conan 缓存中，
未把二进制或上游压缩包混入配方归档。

## 复现

原生 HarmonyOS worker（具有仓库要求的 Clang/Conan/Python/CMake）：

```sh
conan create archives/d/dhrystone/2.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
CI_PACKAGES=archives/d/dhrystone/2.1 zsh ci/conan/build_and_test.sh
```

本机交叉配置及日志根目录：
`C:/Users/ASUS/Desktop/build_in_harmonyos/tmp/dhrystone-2.1`。
profiles/ 中保留 ohos-armv8、ohos-x86_64、windows-build 和 linux-ci。
设置 CONAN_HOME 为该目录的 conan-windows，然后运行：

```powershell
conan create archives/d/dhrystone/2.1 -pr:h=<任务目录>/profiles/ohos-armv8 -pr:b=<任务目录>/profiles/windows-build --no-remote
conan create archives/d/dhrystone/2.1 -pr:h=<任务目录>/profiles/ohos-x86_64 -pr:b=<任务目录>/profiles/windows-build --no-remote
```

实际设备文件位于 `/data/local/tmp/dhrystone-2.1-codex/run/`。设置
`DHRYSTONE_TEST_OHOS=1`，运行 test_dhrystone.py，传入 --hdc、--binary
设备安装路径、--elf-file 本地相同 ELF、--probe 设备 test_ohos_runtime 路径。
本地 W3 复现入口为任务目录 run_local_ci.py；它调用原始 FinishPipeline W3 方法，
不修改基础设施，不跳过门禁。JUNK_PR_DIFF 为本次完整 Dhrystone 变更生成的真实 diff。

## 证据与框架限制

提交前清理了构建缓存、补丁备份和重复 PR 草稿，保留本报告及全部配方、补丁和测试。
原始日志和状态文件保存在上述本地任务目录的 submission-evidence/，不随归档提交。
其中 W3 结果为 w3-local-ci.log，`.ci-result.json` 由官方方法生成，
含日志 SHA256。ConanVerifier 原始输出为 conan-verify-report.md；其
G4/L2/L4/L5 的跳过不能算执行证据。实际 ELF 属性、产物哈希和反汇编证据在
本地任务目录 artifact-verification.json、elf-*.log、disassembly-*.log。
其它日志：conan-ohos-armv8.log、conan-ohos-x86_64.log、harmonyos-runtime.log、
red-tests.log、truncated-input-red.log。

额外框架测试：Linux tests/test_smoke.py 为 15/15；tests/test_v1221.py 为
15 通过、2 失败，失败是未受本包修改的共享生成 catalog.tsv 分类数量断言
（headeronly≥100、copy≥300）。Windows smoke 的锁测试不支持该宿主环境，
相同测试在 Linux 通过。知识图谱校验通过，保留 169 条既有词表/编号等警告。
未修改框架、共享索引或此前的 detox/cpp-gsl/cpp-httplib/cpipe/libxext 内容。
