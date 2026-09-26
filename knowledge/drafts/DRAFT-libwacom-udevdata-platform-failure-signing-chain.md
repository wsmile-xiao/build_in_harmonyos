# E6407：udev 形态平台失败论证+.so 签名链

## 错误特征

udev hwdb 不可用（OHOS 无 udev 守护）+HMDFS 上 .so dlopen 失败（签名缺失）。

## 解法

1. **平台失败论证**（PR 正文记录）：数据库查询 API 无设备环境返回空集=合法语义，消费者断言空集+error code
2. **签名链**：llvm-objcopy 去旧签名→binary-sign-tool 自签→dlopen 恢复（libgudev/glib 先例集大成）

## 实证

PR #12570 libwacom 2.13.0 CI passed。
