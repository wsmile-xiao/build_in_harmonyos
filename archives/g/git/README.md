# git

## 简介
Git — 分布式版本控制系统。支持分支、合并、远程协作等完整的版本管理功能。

## OHOS 适配
- 打包时需包含完整的 `share/git-core/templates/` 目录（含 hooks/*.sample、info、description）
- git 2.35+ 引入的 safe.directory 安全特性在 HMDFS 上会触发 dubious ownership 错误
- 需创建 `~/usr/local/etc/gitconfig` 配置 `safe.directory = *`
- shell 脚本因 shebang 限制需通过 `sh` 调用

## 排除与替代
无

## 依赖
- 编译依赖：zlib, openssl, curl, expat, gettext
- 运行依赖：无

## 功能验证
```bash
git --version
git init --tmpdir $TMPDIR/test-repo
git config --global user.name "test"
git config --global user.email "test@test.com"
```

## 参考
- 官方网站：https://git-scm.com/
- 源码：https://mirrors.edge.kernel.org/pub/software/scm/git/
