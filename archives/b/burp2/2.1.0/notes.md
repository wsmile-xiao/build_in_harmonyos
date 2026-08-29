# burp2 2.1.0 适配笔记

## 上游信息
- 上游项目: grke/burp (Backup and Restore Program)
- 版本: 2.1.0 (2017-01-01 发布)
- 许可证: AGPL-3.0-only (附带 OpenSSL 连接例外)
- 构建系统: Autotools (configure.ac + Makefile.am)
- 官方源码: https://github.com/grke/burp/archive/refs/tags/2.1.0.tar.gz
- SHA256: 5e1ca79a57e50ed2092eb1319e97b9484e0a2e2e4ed9e098ab9dd2476ab0af19

## 适配内容
### 构建适配
1. 源码 tarball 不含 configure 脚本，需 bootstrap (autoreconf -ivf)
2. 使用 LT_INIT(libtool)，需 libtoolize
3. config.sub 需要 aarch64-*-ohos 三元组支持，已通过 patches/0001-ohos-config-sub.patch 解决
4. 使用 conan tool_requires: autoconf/2.72, automake/1.18, libtool/2.5.4, perl/5.42.2
5. 使用 AutotoolsToolchain 自动注入依赖的头文件和库路径

### 依赖
- 必需: openssl/3.5.6, zlib/1.3.1, librsync/2.3.4, uthash/2.3.0
- 可选: ncurses/6.5 (状态监控), check/0.15.2 (单元测试框架)
- 测试依赖: check/0.15.2, pkgconf/3.0.5

### 测试
- 上游测试: make check → runner (Check 框架单元测试)
- 测试目录: utest/ (~50 个测试文件), test/ (集成测试脚本)
- 消费者测试: test_package 运行 burp -v 验证版本输出

### 注意事项
- GitCode 镜像返回 HTML 错误页，官方 GitHub URL 为唯一可靠源码源
- 本机为 HarmonyOS PC (aarch64 HongMeng Kernel)，utest 可本地运行
- 包类型: application (可执行文件: sbin/burp, bin/vss_strip, sbin/burp_ca)
---

**编译结束**: 2026-08-28 11:29
**最终状态**: built
