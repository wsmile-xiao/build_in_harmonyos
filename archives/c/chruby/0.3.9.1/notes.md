# chruby 0.3.9.1 适配笔记

## 版本说明
- 上游版本: 0.3.9
- 包版本: 0.3.9.1（R37: 制品仓已有 0.3.9，递增后缀）
- 源码未变，仅包版本号递增

## 编译过程

chruby 是纯 shell 工具，无 C 代码，无 configure 脚本。

### 编译步骤
1. 下载源码 tarball（从 GitHub，通过 gh-proxy.com 镜像）
2. 解压到 ~/tmp/builds/chruby-0.3.9/
3. staging: `make install PREFIX=$staging`
4. 本地安装: `make install PREFIX=$DEFAULT_PREFIX`
5. 验证: chruby-exec --version → chruby version 0.3.9

### 特殊说明
- chruby 的 Makefile 不支持标准 DESTDIR 模式（PREFIX?=$(DESTDIR)/usr/local）
- 使用 `PREFIX=$staging` 替代 DESTDIR staging
- 无 ELF 二进制文件，所有文件为 shell 脚本
- chruby-exec --version 报告上游版本 0.3.9（非包版本 0.3.9.1）

### 测试
- chruby 测试套件需要 Ruby 安装，跳过
- test_package smoke test: chruby-exec --version 和 --help 均通过

---

**编译结束**: 2026-07-15
**最终状态**: built
