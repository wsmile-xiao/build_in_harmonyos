# duo-unix

Duo Security 双因素认证 Unix 客户端，包含：

- **libduo** — Duo API 客户端库（HTTP over SSL，自带 http_parser）
- **login_duo** — SSH/登录集成命令行工具
- **pam_duo** — PAM 模块（可选，本配方默认不构建）

## 依赖

- OpenSSL（必需，用于 HTTPS/TLS）

## 构建

autotools 项目，GitHub archive 不含 configure 脚本，通过 `tool_requires` automake/libtool 在 build 阶段 autoreconf 自举。
