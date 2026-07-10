# keychain

## 简介

keychain 是一个 SSH/GPG key agent 管理器，由 Daniel Robbins 开发。它作为 ssh-agent 和 gpg-agent 的前端，在用户登录时自动加载 SSH 密钥，并在多个终端会话之间共享 agent。支持 Bourne shell、csh/tcsh 和 fish。

## OHOS 适配

- keychain 使用 plain Makefile 构建系统（无 configure 脚本）
- 构建需要 Perl（pod2man/pod2text 生成 man page 和脚本）
- 无标准 `make install` 目标，conanfile.py 手动安装 bin/man/completions
- conanfile.py 包含 R32 平台兼容检查（`settings.os in ["Linux", "OHOS"]`）
- source() 方法含 SSL fallback：GitHub SSL 不可用时回退到本地归档 tarball

## 依赖

- Perl 5.x（pod2man, pod2text）
- make
- 运行时需要 ssh-agent 和/或 gpg-agent

## 功能验证

```bash
keychain --version
keychain --help
bash -n $(which keychain)  # 语法检查
```

## 参考

- 源码: https://github.com/danielrobbins/keychain
- Wiki: https://www.funtoo.org/Funtoo:Keychain
