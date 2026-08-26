# authselect — OHOS 适配概述

authselect 是 Linux 系统认证和身份源选择工具，替代 authconfig。
上游 https://github.com/authselect/authselect。

## 版本

- 1.7.1（第 1 个适配目标版本）

## 适配策略

标准 Autotools C 项目。依赖 popt/libselinux/glibc，测试使用 cmocka + pytest。
本地适配完成后需执行 `conan create` 和 consumer 验证。