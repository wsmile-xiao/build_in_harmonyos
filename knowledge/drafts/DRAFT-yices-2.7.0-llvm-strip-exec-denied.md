# llvm-strip 产物被 OHOS 执行策略拒绝（execve EACCES）

> 配套 kv：DRAFT-yices-2.7.0-llvm-strip-exec-denied.kv（结构化字段见 kv）

## 现象

yices 2.7.0 的 `make dist/install` 内置 `$(STRIP)=llvm-strip`（configure 默认探测），
其 dist/bin 下全部二进制在 OHOS 设备上 execve 返回 EACCES（shell 报 Permission denied），
L2 smoke test 与 CLI test_package 无法执行。

## 实证（2026-09-20 真机对照实验）

| 实验 | 结果 |
|---|---|
| hello-world 原件执行 | ✅ rc=7 |
| 同文件 llvm-strip 后执行 | ❌ rc=126 Permission denied |
| llvm-strip 产物的 cp 字节拷贝/改名 | ❌ 同样被拒（内容/布局相关，非文件名/目录） |
| 同 objects 用 clang 重链（不 strip） | ✅ "Yices 2.7.0" 正常输出 |
| 权限位/SELinux 标签/xattr 对比 | 与可执行原件完全一致 |

## 修法（配方层）

`make` 与 `make install` 命令行传 `STRIP=true` 覆盖变量，strip 变 no-op，
二进制不 strip 交付。

## 注意区分

- 与 E046（hmdfs chmod 权限位不生效）机制不同：本条是 strip 后 ELF 被拒，权限位完全正常
- 与 R7 安全弹窗不同：无弹窗，直接拒绝
