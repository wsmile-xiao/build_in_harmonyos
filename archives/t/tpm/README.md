# tpm

**tpm** = tiny password manager（`nmeum/tpm`）。一个纯 POSIX shell 脚本实现的命令行密码管理器，兼容 [pass(1)](https://www.passwordstore.org/) 的存储格式（`~/.password-store/*.gpg`），使用 `gpg2` 对称加密存储密码条目。

## 描述

tpm 提供 `tpm insert ENTRY`（写入加密密码）和 `tpm show ENTRY`（解密读取）两个核心子命令，所有密码以 `.gpg` 文件形式存于密码存储目录。脚本本身是 `#!/bin/sh`，无任何编译产物，无 C/C++ 代码。

## 已归档版本

- 1.3.3（2026-07-16，Alpine 参考包 `1.3.3-r4`，Conan 版本取上游 `1.3.3`）

## OHOS 适配要点

- **纯 shell 脚本 + Makefile（install-only）**，无编译过程，无 musl/ABI 风险，`pre_scan`/`engine` 不适用。
- **零源码补丁**：上游 Makefile 原生支持 `PREFIX/BINDIR/MANDIR/DESTDIR`，打包在 Conan 配方层 `package()` 完成。
- **跳过 man page 生成**：Makefile 用 `pod2man`(perl) 生成 `tpm.1`；为避免对 perl 的硬构建期依赖，配方仅安装 `bin/tpm`，man page 可由用户自行从 `README.pod` 生成。
- **构建系统类型**：makefile（`conan-init` 默认误判为 autotools，已在配方层修正）。

## 依赖关系

| 依赖 | 类型 | 鸿蒙制品仓状态 |
|------|------|---------------|
| gpg2 (gnupg) | 运行时（必须） | ⚠️ 未发布（`archives/g/gnupg/2.4.9/` 有手动编译记录但 status=failed，卡 libiconv；无完整 Conan 配方包） |
| pod2man | 构建期（可选，仅生成 man page） | N/A（host 工具，配方已跳过） |
| 编译期库 | — | 无（registry 零依赖） |

> ⚠️ **运行时 gpg 未发布**：tpm 的 insert/show 必须调用 `gpg2`。仓库有 gnupg 2.4.9 手动编译记录但 status=failed（卡 libiconv 运行时链接），无完整 Conan 配方包，等于未发布。因此 tpm 安装后**打包层面成功**（`bin/tpm` 可装可执行），但**真实功能需 gnupg 完整迁移后才有**。这是运行时生态问题，不阻塞打包提交。

## test_package 说明

- 采用 **executable 模板**（工具类），调用安装后的 `tpm` 命令。
- 通过 **mock gpg2 stub**（`test_package/mock_gpg2.sh`，可逆 base64 变换非真加密）驱动 tpm 跑完整 insert→show 数据链路，共 15 条断言：
  - **Group A**（CLI 契约，4 条）：tpm 在 PATH、无参/未知子命令输出 `USAGE: tpm` + 退出码 1
  - **Group B**（核心功能，5 条）：insert 写入正确存储路径且文件不含明文、show 读回的密码与插入一致（完整往返）
  - **Group C**（错误路径，5 条）：show 不存在条目退 1、insert 重复条目退 1、空名走 USAGE
- mock gpg2 仅用于让 gpg2 依赖的 insert/show 代码路径在无 gpg2 的 CI 中可验证；运行时真实功能待 gnupg 完整迁移后用真 gpg2 复验。

## 参考资料

- 上游仓库：https://github.com/nmeum/tpm
- 许可证：GPL-3.0-or-later
- 兼容项目：pass(1) — https://www.passwordstore.org/
- Alpine 包页：https://alpine.pkgs.org/3.24/alpine-community-x86_64/tpm-1.3.3-r4.apk.html
