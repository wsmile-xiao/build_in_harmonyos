# DRAFT-m1ddc-apple-ddc-transport-boundary - Apple 私有 DDC/CI 传输层缺失时的 CLI 合约保留

> **Contributor**: codex | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-28
> **Source event**: m1ddc 1.0.0.1, upstream waydabber/m1ddc v1.0.0, PR #7051

## 知识类型与提升边界

本条目是路径 B/B 类知识库扩展候选，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote 或已获 B 类认定；是否提升及最终分类由知识库维护者和评审决定。

## 适用场景

适用于同时满足以下条件的硬件控制 CLI：

- 上游生产 backend 依赖 macOS、Apple Silicon 或其他平台私有框架；
- 命令解析、帮助文本、参数表或能力码表可从真实硬件 transport 中拆出来；
- HarmonyOS 普通单包 CI 无稳定公共 API 或设备权限可执行真实硬件副作用；
- 上游没有测试套件，必须由 test_package 建立最小但诚实的行为证据。

m1ddc 的上游 `m1ddc.m` 把 DDC/CI 命令行前端、VCP 码表和 Apple 私有
`IOAVService` I2C DDC transport 写在一个 Objective-C 文件中。OHOS clang 首个阻塞点是
`module 'Darwin' not found`，但真正的移植边界是缺少 Apple 私有显示器传输层，而不是
简单补一个头文件。

## 问题模型

这类库有三种容易误判的处理方式：

1. 整包标记 unsupported 或删除二进制，只证明编译失败被绕开；
2. 为 `set/get/chg` 返回 0，伪造用户脚本最关心的硬件副作用；
3. 临时引入 Linux DDC 栈、访问 `/dev/i2c` 或其他真实设备节点，把依赖和设备状态混进单包 PR。

更稳的边界是区分“可移植 CLI 合约”和“目标平台暂缺的硬件 transport”。前者应该继续构建、
安装和测试；后者必须诚实失败，并且在测试报告中与上游测试缺失分层记录。

## 推荐方法

### 1. 在源码边界拆分私有 transport

用平台 guard 保留上游 Apple 实现，例如 `#ifdef __APPLE__` 内保持原始 Darwin/Foundation/IOKit
导入和 IOAVService 调用。非 Apple 分支使用标准 C 实现命令行前端，不导入私有框架，不访问
真实设备。

### 2. 保留用户可见 CLI 合约

可移植分支应复刻上游帮助文本、命令动词、参数校验和 VCP 码表。这样即使真实 DDC transport
不可用，包仍能证明安装的命令行界面与上游一致，下游脚本也能得到稳定错误。

### 3. 对真实硬件请求诚实失败

`display list`、`set`、`get`、`max`、`chg` 等会触发 DDC 传输的路径不能假装成功。m1ddc 的
可移植分支在无 Apple IOAVService 时返回 "Could not find a suitable external display."，
与上游找不到外接显示器的语义一致。

### 4. test_package 覆盖可执行文件和失败语义

上游没有 `--version`，`--help` 也不是 0 返回；测试不应强套版本/帮助模板。更合适的是：

- 运行无参数命令，确认输出 DDC/CI 用法文本和关键能力名；
- 确认 `set/get` 命令动词仍在 CLI 中暴露；
- 执行真实命令如 `m1ddc set luminance 5`，确认无 transport 环境下给出 no-display 失败信息。

这不是硬件功能通过证明，而是已安装 CLI 在目标环境中的最小诚实行为证明。

### 5. 上游测试缺失单独审计

如果官方归档只含源码、Makefile、README 和 LICENSE，应在 MANIFEST 和测试输出中声明
`discovered=0/executed=0`，不要把 test_package 冒烟测试写成上游测试通过率。

## 与已有知识的差异

- `DRAFT-seatd-noop-backend-validation-2146` 复用上游正式 noop backend 验证 seat-management
  公共 API；m1ddc 没有上游 noop backend，且生产路径是 Apple 私有 IOAVService。
- `DRAFT-gnome-autoar-runtime-capability-skip-2147` 处理上游测试中的运行时能力 skip；m1ddc
  上游无测试，本条目补的是 CLI 合约保留和 test_package 证据边界。
- `E321-draft-qbootctl-a-b-slot-mock-backend` 处理可注入 mock backend 的设备 CLI；m1ddc 的
  单文件 Apple 私有 transport 没有稳定公共注入点，因此采用前端拆分和诚实失败。

## 禁止做法

- 不要删除二进制、交付空包，或把整包 unsupported 写成适配通过。
- 不要让 `set/get/chg` 在没有真实 DDC transport 时返回假成功。
- 不要把 no-display 冒烟测试写成真实硬件 DDC/CI 功能已通过。
- 不要把未适配的 ddcutil、libdrm、`/dev/i2c` 访问混入同一个库 PR。
- 不要按平台名跳过所有测试；应测试可移植 CLI，跳过或分离真实设备能力。

## 已验证示例

m1ddc 1.0.0.1 基于上游 v1.0.0。配方应用
`archives/m/m1ddc/1.0.0.1/patches/0001-portable-nonapple.patch`，将 Apple 原版实现保留在
`__APPLE__` 分支，非 Apple 分支以标准 C 复刻 CLI 和 VCP 码表。HarmonyOS aarch64 真机
shadow/PR CI 使用下方单包命令验证，`test_package` 覆盖 6 个冒烟检查；L2 对版本/帮助探测
可标记 skip，因为上游命令没有 `--version` 或 0 返回的 `--help`。

复现入口：

```sh
CI_PACKAGES="archives/m/m1ddc/1.0.0.1" zsh ci/conan/build_and_test.sh
```

证据记录：

- AtomGit PR: `https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/7051`
- 具体 shadow/PR CI run id 随分支 HEAD 更新，记录在 PR 正文或评论中；本草稿只保留稳定复现入口。

## 证据来源

- `archives/m/m1ddc/1.0.0.1/conanfile.py`
- `archives/m/m1ddc/1.0.0.1/conandata.yml`
- `archives/m/m1ddc/1.0.0.1/patches/0001-portable-nonapple.patch`
- `archives/m/m1ddc/1.0.0.1/test_package/test.sh`
- `archives/m/m1ddc/1.0.0.1/test_package/MANIFEST.yml`
- `archives/m/m1ddc/1.0.0.1/notes.md`
