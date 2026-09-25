# libgcrypt20

## 简介
GnuPG 通用密码库运行时包（与上游 libgcrypt 1.12.2 同源，SONAME 为 libgcrypt.so.20），提供对称加密、哈希、MAC、KDF、MPI 与 S 表达式等基础密码原语。

## OHOS 适配
- 构建系统: autotools
- 详见各版本 notes.md 获取适配详情
- 复用同源 libgcrypt 1.12.2 已验证的 4 个补丁：libgpg-error 基线对齐、HMDFS shell 包装、config.guess/sub 识别 HarmonyOS

## 依赖
- `libgpg-error/1.55`

## 功能验证
- 构建阶段执行完整上游 `make check`，并输出 HMBS_UPSTREAM_TEST_RESULT 标记。
- Conan `test_package` 通过 15 个独立命令验证安装后的版本、摘要、MAC、对称加密、KDF、MPI、S 表达式和随机数公开 API，并输出 HMBS_TEST_PACKAGE_RESULT 标记。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 1.12.2 | built | 与 libgcrypt 1.12.2 同源；待真机预检与正式 CI 发布 |

## 参考
- https://gnupg.org/software/libgcrypt/
