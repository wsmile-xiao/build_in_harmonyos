# libgcrypt

## 简介
General purpose cryptographic library (GnuPG)

## OHOS 适配
- 构建系统: autotools
- 详见各版本 notes.md 获取适配详情

## 依赖
- `libgpg-error/1.55`

## 功能验证
- 1.12.2 在构建阶段执行完整上游 `make check`。
- Conan `test_package` 通过 15 个独立命令验证安装后的版本、摘要、MAC、
  对称加密、KDF、MPI、S-expression 和随机数公开 API；shared/static 均通过。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 1.12.2 | built | Percona XtraBackup #1088 的前置依赖；待正式 CI 发布 |
| 1.11.0 | built | 历史配方，仅供问题线索参考 |

## 参考
- https://gnupg.org/software/libgcrypt/
