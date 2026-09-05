# passwdqc

密码和密码短语强度检查及策略执行工具集。

## OHOS 适配

- 构建系统：GNU Makefile
- 编译器：由 Conan profile 注入
- OHOS 构建产物：`libpasswdqc`、`pwqgen`、`pwqcheck`、`pwqfilter`
- `pam_passwdqc.so` 未构建，因为 OHOS 不提供 Linux-PAM 运行时

## 参考

- 官网：https://www.openwall.com/passwdqc/
