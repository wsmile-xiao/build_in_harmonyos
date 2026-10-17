# DRAFT-9685-bsc-ghc-toolchain-source-contract - 宿主语言工具链阻塞时的源码契约与消费者门控

> **Contributor**: gcw_6YxinkyD | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-12
> **Source event**: bsc 2026.01（Bluespec Compiler），issue 待补，PR #9685

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、正式文档、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 适用场景

适用于满足以下全部条件的组件：

- 上游是"宿主语言工具链型"应用——源码主体是 Haskell/OCaml/Rust 旧版等
  **非 CI 自带工具链**的语言实现（本例：bsc 编译器核心约 500k 行 Haskell，
  需 GHC 7.10.3–9.12 + 5 个 Hackage 包 + libgmp）；
- 目标 OHOS 主机为纯 musl：官方预编译工具链全部 glibc 动态链接（缺
  `/lib/ld-linux-aarch64.so.1`），无法运行（E105/E172）；
- 上游**没有 linux-arm64 二进制**，use-binary-release 回退路径也不存在
  （与 pandoc 的差异：pandoc 有官方 arm64 二进制可用）；
- 下游仍需要从 Conan 包取得可审计、机器可消费的上游构建契约。

## 问题模型

工具链型应用不能像普通 C/C++ 库那样"补几个头文件桩交叉编译通过"：没有
GHC 就没有任何可编译单元。两类常见误报：

1. 构建层伪造：把 `build()` 留空却宣称适配成功；
2. 测试层伪造：test_package 打印 SKIP 退出 0，把"未验证"记录为"通过"。

另一类隐患是"装饰性契约"：把上游文档拷进包里只做**存在性 grep**，包内容
无法支撑下游任何真实决策。

正确边界：承认构建阻塞，导出 pinned 源码契约，并用**消费者用例**证明契约
机器可消费（parse + decide，不是定长字符串匹配）。

## 推荐方法

### 1. 双路径都实证阻塞后再定性

源码路径（工具链不可运行）与二进制路径（无 linux-arm64 产物）都要留
证据（官方 bindist 列表、release 资产列表），不能只查其一。

### 2. 契约文件选"下游会用的"，不是"顺手拷的"

bsc 导出：COPYING/LICENSE.txt/LICENSES/（许可审计）、INSTALL.md（工具链
版本范围）、src/Makefile（GHC_PKGS 依赖清单）、platform.mk（架构支持
矩阵）、release/ReleaseNotes.adoc（版本标识）、GNUmakefile/platform.sh
（构建入口）。全部是小文本文件，不打包 200MB 源码树。

### 3. 两层 fail-closed 验证

- 契约层（check_source.sh）：真实 grep 断言契约要素；缺失契约 exit 2、
  断言失败 exit 1；
- 消费者层（test_consumer.py）：模拟下游工具链门控脚本**只凭包内容**做
  决策——从 INSTALL.md 解析全部 "A through B" 推导有效支持区间（floor 取
  最大/ceiling 取最小）并门控候选版本；从 src/Makefile 解析 GHC_PKGS 生成
  置备清单；查询 platform.mk 确认架构被识别。决策错误即失败。

### 4. 证据分层，不许折算

- 上游可执行自动化测试：`0/4530（0%，未执行）`，有据（套件需已构建的
  bsc；testsuite/*.bsv 计数）；
- 源码契约：4/4；
- 消费者门控用例：3/3；
- 编译器功能验证：0/N 未执行。

任何一层都不能被表述为另一层"通过"。

### 5. 留出解锁路径并验证边界事实

记录候选解锁实验（GHC 9.10.1 起 aarch64-alpine3_18 musl bindist 在支持
范围内；需 ELF 签名 + libgmp/libffi 依赖 + 资源评估），并把消费者门控的
一个断言对准它（9.10.1 必须被接受）——解锁后同一契约立即复用。

## 与已有知识的差异

- `DRAFT-acpi_call-kbuild-source-contract-6499`：内核 ABI 阻塞（Kbuild 模块
  缺内核 build tree），契约对象是加固后的模块源码本身；本条是**宿主语言
  工具链**阻塞，契约对象是上游构建元数据（版本范围/依赖清单/架构矩阵），
  且新增"消费者 parse+decide 用例"这一层——装饰性文本过存在性检查，但只有
  真契约能产出一致门控决策。
- pandoc 的 use-binary-release：上游有官方 arm64 二进制可用；本条明确
  上游无 linux-arm64 二进制时该路径不可用，防止盲目套用。

## 禁止做法

- 不要在工具链缺失时把 build() 留空还说"编译完成"。
- 不要把存在性 grep 当作消费者验证；不要用定长字符串匹配冒充 parse+decide。
- 不要把上游 0/N 未执行写成 100%，或用契约通过折算功能通过。
- 不要把 GHC aarch64-alpine musl bindist 写成"已可用"——它只是候选，
  未在 OHOS 上验证。
- 不要修改正式知识图谱、索引或预占正式 E 编号。

## 已验证示例

bsc 2026.01：OHOS 真机（frp 设备，隔离 CONAN_HOME）`conan create` RC=0，
包内契约打包完整（含 LICENSES/ 全部 vendored 许可）；check_source.sh
4/4 真机 PASS；test_consumer.py 3/3（GHC 门控 9.10.1/9.6.4 接受、7.10.2
拒绝；GHC_PKGS 恰为 5 包；platform.mk 认识 aarch64）。上游 4530 例未执行。

复现入口：

```sh
CI_PACKAGES="archives/b/bsc/2026.01" zsh ci/conan/build_and_test.sh
```

## 证据来源

- `archives/b/bsc/2026.01/conanfile.py`
- `archives/b/bsc/2026.01/test_package/check_source.sh`
- `archives/b/bsc/2026.01/test_package/test_consumer.py`
- `archives/b/bsc/2026.01/test_package/MANIFEST.yml`
- `archives/b/bsc/2026.01/notes.md`（真机验证记录、双路径阻塞证据）
- GitCode PR #9685
