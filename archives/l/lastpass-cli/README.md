# lastpass-cli

LastPass 命令行界面工具，用于在终端中管理 LastPass 密码库。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.6.1 | built | 2026-06-03 |

## 依赖

- libxml2 (≥ 2.9)
- openssl (≥ 1.1)
- libcurl (≥ 7.0)

## 说明

lastpass-cli 是 LastPass 的官方命令行客户端，支持登录、同步、增删改查密码等操作。
在 OpenHarmony 上因 CMake 平台检测问题，使用手动编译方式构建。