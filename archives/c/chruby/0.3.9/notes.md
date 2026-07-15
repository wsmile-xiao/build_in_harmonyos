# chruby 0.3.9 适配笔记

## 编译过程

chruby 是纯 shell 工具，无 C 代码，无 configure 脚本。

### 编译步骤
1. 下载源码 tarball（从 GitHub，gh.idayer.com 镜像 SSL 问题）
2. 解压到 ~/tmp/builds/chruby-0.3.9/
3. DESTDIR 模式 staging: `make install PREFIX=$TEST_PREFIX/$DEFAULT_PREFIX`
4. 本地安装: `make install PREFIX=$DEFAULT_PREFIX`
5. 验证: chruby-exec --version → chruby version 0.3.9

### 特殊说明
- chruby 的 Makefile 不支持标准 DESTDIR 模式（PREFIX?=$(DESTDIR)/usr/local）
- 使用 `PREFIX=$TEST_PREFIX/$DEFAULT_PREFIX` 替代 DESTDIR staging
- 无 ELF 二进制文件，所有文件为 shell 脚本

### SSL 问题
- gh.idayer.com 镜像 SSL 证书验证失败，改用 GitHub 直连下载
- 需 `curl -kL` 跳过 SSL 验证

### 测试
- chruby 测试套件需要 Ruby 安装，跳过
---

**编译结束**: 2026-07-15 15:28
**最终状态**: built
