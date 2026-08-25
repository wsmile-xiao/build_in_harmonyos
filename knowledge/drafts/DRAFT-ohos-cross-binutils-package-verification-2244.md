# DRAFT-ohos-cross-binutils-package-verification-2244 - 交叉 Binutils 包验证

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-18
> **Source event**: avr-binutils 2.43.1, issue #2244

## 知识类型与提升边界

本条目是路径 B 知识库扩展候选，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote 或已获 B 类认定；是否提升及最终分类由知识库维护者和赛事评审决定。

新增点仅是交叉命令行工具包的“双架构语义 + 包所有权”验证闭环。OHOS triplet、HMDFS
脚本执行、configure 临时目录权限、Info 文档回退和 ELF 签名均为既有适配方法，不在本条目
中重复申报。

## 适用场景

本方法适用于同时满足以下条件的交叉工具包：

- 工具程序本身是 HarmonyOS 宿主原生可执行文件；
- 工具输出为 MCU 或其他非宿主架构对象、ELF 或固件格式；
- 目标程序没有可用模拟器，不能在宿主真机直接执行；
- 真机、构建镜像或其他依赖可能提供同名交叉命令；
- 需要证明下游使用的是当前 Conan 包，而不是系统工具或构建残留。

普通 OHOS 原生库仍应采用编译、链接和运行消费者程序的测试方式。已经能完整执行目标程序的
模拟器环境，也应继续增加动态行为测试，本方法不能替代它。

## 问题模型

交叉 Binutils 横跨两个架构边界：`avr-as`、`avr-ld` 等程序运行在 OHOS/AArch64，输出却是
AVR 对象和 ELF。由此产生三个独立问题：

1. 程序能否作为 OHOS 宿主工具启动；
2. 多个工具能否协同产生正确的目标架构产物；
3. 被执行的命令是否确实来自当前 Conan 包。

只运行 `--version` 只能回答第一个问题的一部分。把目标 ELF 直接放到 OHOS 上执行会得到
预期的架构错误，无法证明产物损坏或正确。若命令来自 `PATH`，系统中已有的 `avr-as` 还可能
掩盖空包、漏打包或错误的 `package_info()`。

## 推荐方法

### 1. 从 package_folder 解析绝对工具路径

消费者测试应从 Conan 依赖对象取得 `package_folder`，构造 `bin/avr-*` 的绝对路径。先对
交付命令执行版本检查，但不把版本检查计为完整功能测试。命令清单与 `commands.json` 和 L2
验证保持一致。

### 2. 构建一个真实目标产物链

使用最小但非空的目标汇编源，经包内 `avr-as` 生成对象，再由包内 `avr-ld` 针对具体 MCU
链接。随后由 `avr-objcopy` 生成 Intel HEX 等实际交付格式。这样可验证汇编器、链接器和
格式转换工具之间的兼容性，而不是孤立地探测二进制存在。

### 3. 静态验证目标语义

目标 ELF 不在 OHOS 上运行。由包内 `avr-objdump`、`avr-readelf`、`avr-nm` 和 `avr-size`
验证：

- 文件格式和机器架构确为目标架构；
- 入口、应用符号及必要段存在；
- 对象、ELF 和 HEX 均非空；
- 工具读取彼此生成的文件时没有格式错误。

这些断言证明“工具在宿主运行并正确生成目标产物”，但不宣称固件已经在 MCU 上执行。

### 4. 用破坏性负向测试证明包所有权

Shadow CI 在成功消费者测试后，暂时移除 Conan 包的 `bin`/`lib` 内容并重跑测试。第二次必须
失败；若仍成功，说明测试可能使用系统工具、构建残留或未声明路径。完成后由 CI 缓存隔离或
重新创建包恢复环境。

若环境不允许修改缓存，可将包复制到隔离目录并执行等价负向测试，但必须保留命令绝对路径和
删除后失败的证据。

## 与已有知识的差异

- E077 处理安装后 ELF 重签；本条目只使用已签名宿主工具，不把签名方法申报为新知识。
- E087 处理 HMDFS shell 脚本显式解释；包装器可复用它，但它不是本条验证闭环的新增点。
- E272 处理 DejaGNU/Expect、`/bin/stty` 和 `tmpfile()` 在 OHOS 上的上游 testsuite 迁移；
  本条目处理 Conan 消费者层的包所有权与目标产物语义，两者可以叠加，不能互相冒充。
- E311 处理 Conan source-folder 隔离，不覆盖交叉命令来源或双架构断言。

## 禁止做法

- 不要只用 `--version` 或文件存在性代表完整功能通过。
- 不要依赖 `PATH`、`which` 或真机预装的同名交叉工具。
- 不要在没有模拟器时尝试在 OHOS 上执行目标 ELF。
- 不要把 DejaGNU 未运行写成上游测试通过；应分别统计已运行的官方子集和未运行矩阵。
- 不要把通用签名、HMDFS 权限或 triplet 修复重复申报为本条目的创新点。

## avr-binutils 2.43.1 验证证据

真机单包 Shadow CI
`codex-avr-binutils-shadow-ci-r5-2244-20260817-134800-3191` 已通过 G0、L0、L1、L2 和 L5：

- 6 项无需 DejaGNU 的官方 libiberty 检查通过；
- 16 个打包命令的版本检查通过；
- ATmega328P 汇编、链接、AVR ELF 静态检查和 Intel HEX 生成通过；
- 删除包 `bin`/`lib` 后的破坏性负向测试按预期失败，所有权门禁通过；
- 完整 DejaGNU target matrix 因配置远端未发布 `runtest` 而未执行，未计为 PASS。

验证使用配方提交 `025ba666fdac38d42d5feefa534388111a3b22ca`，Shadow 提交
`66a185f1b5dfc310b5a6ba52b891201a9c70a88a`。

复现入口：

```sh
CI_PACKAGES="archives/a/avr-binutils/2.43.1" zsh ci/conan/build_and_test.sh
```
