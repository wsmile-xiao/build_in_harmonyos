# libselinux

## 简介

libselinux 提供 SELinux 安全上下文的管理接口，包括：
- 安全上下文获取/设置（getfilecon/setfilecon 等）
- SELinux 策略查询（compute_av、getenforce 等）
- SELinux 文件标签解析（selabel_* 后端）
- 策略加载与转储（load_policy）

## OHOS 适配

- 构建系统：纯 Makefile（无 autotools/CMake/meson）
- 依赖：libsepol 3.10（同一 monorepo 标签）、pcre2（libpcre2-8）
- 编译器：clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态：built