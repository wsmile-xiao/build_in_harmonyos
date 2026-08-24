# abuild-sudo

Alpine `abuild`（Alpine build tools）项目中的 setuid 提权辅助工具。允许
`abuild` 组成员以受限方式执行白名单命令（`adduser`/`addgroup`/`apk`），
用于在构建 Alpine 软件包时进行受控的权限提升。

## 功能概述

- 校验调用者属于 `abuild` 组（或为 root）
- 按 `argv[0]`（`abuild-adduser`/`abuild-addgroup`/`abuild-apk`）分发到白名单命令
- 拒绝危险选项（`--allow-untrusted`、`--keys-dir`）
- 校验通过后 `setuid(0)` + `setgid(0)` 并 `execv` 目标命令

## OHOS 适配

- 本包安装 `bin/abuild-sudo` 并创建 `abuild-adduser`/`abuild-addgroup`/`abuild-apk`
  符号链接（程序按 argv[0] 中的子命令名分发）；setuid 位不保留（OHOS 无此语义）
- 上游测试套件（`tests/`，ATF/kyua 框架，10 个测试程序 111 个用例）依赖
  `kyua` + `atf-sh`，OHOS 缺失；配方用内置 `atf-shim.sh`（与 abuild 3.17.0.1
  同方案，真机已验证）直接运行各 `tests/*_test` 程序，详见版本目录
  notes.md 与 test_package/MANIFEST.yml

## 依赖关系

- 编译依赖：openssl（abuild-tar，测试套件用）、zlib（abuild-gzsplit，测试套件用）；
  abuild-sudo 二进制本身仅依赖 libc
- 运行依赖：`abuild` 组存在

## 参考资料

- 上游仓库：https://gitlab.alpinelinux.org/alpine/abuild/
- 版本目录：`archives/a/abuild-sudo/3.18.0_rc3/`
