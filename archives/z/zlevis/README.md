# zlevis

**ZFS root-pool TPM2 自动解密工具（Clevis 的 POSIX shell 精简实现）**

## 简介

zlevis 是 [Clevis](https://github.com/latchset/clevis) 的精简分支，以 POSIX shell 重写，
用于在开机时借助 TPM2.0 芯片自动解密 ZFS root-pool。上游通过 Meson 安装
`zlevis` / `zlevis-encrypt` / `zlevis-decrypt` 三个 shell 脚本，无编译产物。

## OHOS 适配要点

- 纯 POSIX shell 脚本工具，无编译步骤：conanfile.py `build()` 为空，
  `package()` 将 3 个脚本 copy 到 `bin/` 并 chmod 0755（参照 acme.sh 先例）。
- 脚本运行时依赖外部命令 `zfs` / `jose` / `tpm2-tools`（TPM2 硬件相关），
  消费方需自备这些命令，不参与 conan 依赖链。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| zfs | - | 运行时外部命令（zpool/zfs 管理） |
| jose | - | 运行时外部命令（JWE 编解码） |
| tpm2-tools | 4~5 | 运行时外部命令（TPM2 操作） |

## 功能验证

```bash
# 各脚本 --summary 输出（上游 meson test 3 用例同款）
zlevis --summary         # A tool that enables automatic decryption of ZFS rpools with TPM2
zlevis-encrypt --summary # Encrypts using a TPM2.0 chip binding policy
zlevis-decrypt --summary # Decrypts a JWE using a TPM2.0 chip
```

## 编译状态

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 2.2 | built | meson (纯脚本安装) | 2026-09-16 |

## 参考

- **上游仓库**: https://git.ampel.dev/ampel/zlevis
- **Alpine 打包**: community/zlevis (2.2-r0)
- **许可证**: GPL-3.0-only