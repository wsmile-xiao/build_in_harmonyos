# pam-pgsql

pam-pgsql 是一个 PAM（Pluggable Authentication Module）模块，使用 PostgreSQL 数据库进行用户认证。

## 功能概述

- 支持 PostgreSQL 数据库用户认证
- 可用于系统登录、SSH 等场景的 PAM 认证
- 支持密码和分组查询

## OHOS 适配

- **构建系统**: autotools (configure + make)
- **主要补丁**: pam_pgsql.c 源码平台适配修复
- **依赖**: PostgreSQL (libpq), libgcrypt

## 依赖关系

- PostgreSQL12 (12.22)
- libgcrypt (1.11.0)

## 参考资料

- 官网: https://github.com/pam-pgsql/pam-pgsql