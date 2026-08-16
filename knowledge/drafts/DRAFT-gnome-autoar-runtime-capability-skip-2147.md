# DRAFT-gnome-autoar-runtime-capability-skip-2147 - 运行时能力驱动的最小测试跳过

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-16
> **Source event**: gnome-autoar 0.4.5, issue #2147, PR #5323

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 适用场景

上游测试依赖某项运行时能力，但该能力不是简单的操作系统名称属性，而可能由沙箱策略、
挂载点、依赖库构建选项或设备配置决定。例如：

- 文件系统是否允许在当前测试目录创建符号链接；
- 归档依赖是否编译了加密 backend；
- 某个可选 codec、协议或硬件 backend 是否可用。

这类测试既不能按 `__OHOS__` 等平台宏整体关闭，也不能把已经确认的能力缺失等同于被测库
逻辑失败。正确边界是先触达目标能力，再依据结构化且精确的错误决定是否跳过当前用例。

## 问题模型

能力受限测试有三类常见误改：

1. 按平台名提前 skip，目标操作从未执行；
2. 任意 error 都转成 skip，把真正回归吞掉；
3. 在异步回调或同步操作完成前检查 error，判断时机错误。

gnome-autoar 0.4.5 同时暴露了两个不同来源的能力边界。两个符号链接用例在 HarmonyOS PC
应用沙箱内收到 `G_IO_ERROR_PERMISSION_DENIED`；两个加密解压用例从当前发布的
`libarchive/3.8.7` 收到精确的 `Decryption is unsupported`。前者是运行目录/沙箱能力，
后者是依赖构建特性，不能用同一个平台条件粗略概括。

## 推荐方法

### 1. 保留测试注册与原始断言

不要删除测试，也不要减少 Meson/GLib 注册项。能力可用时必须继续运行原有业务断言；能力
不可用时只跳过直接依赖该能力的单个测试。

### 2. 文件系统能力使用独立最小探针

在测试拥有的临时目录创建最小对象，调用与目标用例相同的 API。仅接受能明确表示能力
缺失的结构化 error domain/code，例如 `G_IO_ERROR_NOT_SUPPORTED` 或
`G_IO_ERROR_PERMISSION_DENIED`。成功后清理探针对象并继续原测试；其他错误立即失败。

探针不能写固定系统路径，也不能修改共享设备状态。探针目录创建或清理失败同样属于测试
基础错误，不能转换为 skip。

### 3. 依赖 backend 能力先执行目标流程

加密、codec 或协议能力应由实际目标操作证明。gnome-autoar 先运行原解密流程，只有在
错误 domain 与消息都吻合已确认的 libarchive 能力错误时才 `g_test_skip`；错误为空时继续
原断言，其他错误保持失败。

判断必须位于正确的完成点。同步 API 可在返回后检查回调结果；异步 API 必须等待完成或
错误回调，不能在启动函数刚返回时读取尚未稳定的状态。

### 4. 分层报告结果

报告至少区分注册总数、实际通过、失败和能力跳过，并记录目标环境、依赖版本、能力错误和
独立探针结果。`skip` 不是 `pass`，也不能用“适配后通过率 100%”掩盖未执行项。

## 与已有知识的差异

- E018 记录符号链接创建失败及替代方向，但没有定义如何保留并适配上游测试。
- E224 说明能力门控优于平台名门控，重点是 signal-stack 资源生命周期。
- E230 要求运行时测试真正触达目标操作，并精确匹配受限 transport 的错误，重点是传输库
  的编译矩阵与回环事务。

本草稿补充的是上游测试移植中的统一闭环：同时处理“运行环境能力”和“依赖构建特性”，
规定探针/目标操作、完成时序、精确错误、原断言保留及 pass/skip 分层统计。

## 禁止做法

- 不要用平台宏或平台字符串提前跳过整类测试。
- 不要把任意 `error != NULL` 作为 skip 条件。
- 不要在目标操作、同步返回或异步完成前判断能力。
- 不要删除上游测试注册项或把 skip 计为 pass。
- 不要修改依赖库能力来掩盖缺失；依赖能力适配应拆成独立任务。

## 已验证示例

gnome-autoar 0.4.5 保留 22 个上游 GLib 测试注册项。真机运行结果为 18 pass、0 fail、
4 capability skip：两个符号链接用例仅在真实创建探针返回明确 GIO 能力错误时 skip，两个
加密用例仅在原解密流程返回 `Decryption is unsupported` 时 skip。Conan consumer 额外
执行真实 ZIP 创建流程并通过。

最终 shadow CI：
`codex-gnome-autoar-gnome-autoar-0.4.5-2147-infra-path-r22-20260816-122207-5462`，
exit code 0；生产 CI #26007 的 Conan test_package、L0、L1 及全部构建 step 通过。

复现入口：

```sh
CI_PACKAGES="archives/g/gnome-autoar/0.4.5" zsh ci/conan/build_and_test.sh
```

## 证据来源

- `archives/g/gnome-autoar/0.4.5/patches/0002-skip-unavailable-ohos-tests.patch`
- `archives/g/gnome-autoar/0.4.5/notes.md`
- `archives/g/gnome-autoar/0.4.5/reports/path-b-candidate.md`
- AtomGit/GitCode PR #5323，生产 CI #26007
