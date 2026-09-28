# safecat 1.13-git20170317.185e8bf 适配笔记

## 变更

- 修正 Debian 源包 SHA256，确保 Conan 下载校验与上游文件一致。
- OHOS LLVM lld 会报告 `byte_copy`、`str_len` 重复符号；配方在源码准备阶段从 `safecat` 目标的直接对象列表移除这两个已由 `str.a` 提供的对象。
- 默认 `make` 目标会调用发行环境中的 `nroff`，而目标 PC 环境没有该工具；配方改为显式构建 `safecat maildir`。
- HMDFS 对 HiShell 用户创建硬链接返回 `EPERM`。在该特定错误（`EPERM`/`EOPNOTSUPP`）下，使用同文件系统 `rename()` 完成原子提交；其他错误仍按原始失败路径处理。

## 真机验证

设备：HarmonyOS PC aarch64，独立 HiShell（uid 20020084），OHOS Clang 15，Conan 2.29.1，profile 为 `os=OHOS`、`os.version=6.0`、`arch=armv8`、`libc++`。

- `conan create`：通过（返回码 0）。
- `test_package`：通过，`safecat smoke: 6 assertions passed`（6/6）。
- 验证日志：`/storage/Users/currentUser/ohpc-incoming/verify-two-safecat-fixed3-20260924/safecat/conan-create.log`。

本报告记录的是该 OHOS 真机 Conan 验证。官方 CI 和维护者审核尚未完成。

## 路径判断

按路径 A 提交；HMDFS 硬链接限制及回退仅作为本版本适配说明，不宣称其构成路径 B 知识库贡献。
