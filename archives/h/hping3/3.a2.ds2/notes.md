# 适配笔记 — hping3 3.a2.ds2（网络测试工具）

## 2026-07-31 适配

### 库信息
- **软件**: hping3 (antirez)
- **版本**: 3.a2.ds2
- **构建系统**: 自定义 configure + Makefile
- **许可证**: GPL-2.0-only
- **上游**: http://www.hping.org/ / https://github.com/antirez/hping
- **功能**: 网络测试工具，支持 TCP/UDP/ICMP 自定义报文、端口扫描

### 构建说明
- 使用 Debian 官方 orig.tar.gz 源码包（版本号含 ds2 表示 Debian 源版本）
- 自定义 configure 脚本（非标准 autotools），`--no-tcl` 禁用 TCL 绑定
- 默认禁用 libpcap（可选特性）
- 上游 install 目标硬编码 `/usr/sbin/`，不适用 DESTDIR，手动打包二进制

### 依赖
- **运行时**: 零外部依赖
- **构建时**: make + cc

### 上游测试
- 上游 Makefile.in 中**无 test/check 目标**，无测试框架

### test_package 测试
- `test_hping3.c`：验证 `hping3 --version`、`--help`、版本输出（3 个断言）
- `_check_binary_exists()`：交叉编译时验证二进制安装正确

### 本地验证记录
| 检查项 | 结果 |
|--------|------|
| conan export | ✅ 成功 |
| SHA256 | ✅ |
| configure + make（OHOS aarch64） | ✅ 编译成功 |
| test_package（--version/--help/版本输出） | ✅ 3/3 通过 |
| 核心收发路径 | ⚠️ 未运行验证（本机无原始套接字能力，且默认禁用 libpcap） |
