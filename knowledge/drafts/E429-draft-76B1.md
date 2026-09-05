# E429 — OHOS 内核 fdinfo flags 无方向位（pipe/pty 端点类测试数据缺口）

## 错误特征
lsof 等 fd 消费工具的 pipe/pty 端点配对类测试恒 FAIL：
```
FAIL: pipe-endpoint
FAIL: pipe-no-close-endpoint
FAIL: pty-endpoint
```
手工检查 fdinfo：
```
cat /proc/<pid>/fdinfo/<fd>
# flags:  02u        ← 期望 01u(写端)/00u(读端) 方向位配对，实际恒为 02u
```
lsof 输出中管道端点缺少 `3r`/`4w` 方向配对显示。

## 触发条件
- 构建系统: 任意（与构建无关，纯运行时数据源问题）
- 阶段: make check / runtime
- 平台: OHOS（HongMeng 内核）
- 任何依赖 `/proc/<pid>/fdinfo/<fd>` 的 `flags:` 字段方向位（O_RDONLY=00/O_WRONLY=01）推断 fd 角色的工具或测试

## 根因分析
Linux 内核在 fdinfo 的 flags 字段上报带方向位的打开标志（00u 读 / 01u 写 / 02u 读写），
上游工具据此推断管道端点角色。OHOS（HongMeng）内核对 pipe/pty fd 统一上报
`02u`（O_RDWR），不提供方向位——数据源在内核侧，用户态补丁无法修复。
属于平台级数据缺口，而非移植缺陷；不应作为移植质量问题上报。

## 解决方案

### 推荐方案
1. 测试归类为平台 FAIL（kernel data gap），在 PR/测试报告中给出归因说明，不阻塞合入
2. 需要端点角色信息的功能降级：无法区分方向时按双向处理（lsof 显示行为可接受的退化）
3. 若测试框架支持，将此类用例在 OHOS 平台的期望结果标记为 known-failure

### 禁止做法
- ❌ 试图用用户态补丁伪造方向位（数据源不在用户态）
- ❌ 为通过测试修改上游断言逻辑（违反测试保真原则）
- ❌ 将其归类为移植缺陷反复排查用户态代码

## 验证
```bash
# 观察内核上报
cat /proc/$$/fdinfo/* | grep flags
# OHOS 上 pipe fd 恒为 flags: 02u，无 00u/01u 区分
```

## 关联条目
- 相关: E051（未实现 syscall SIGSYS，同为内核级平台缺口）、E008/E076（fstat 栈块上报差异，同"内核数据源与 Linux 不一致"模式）
