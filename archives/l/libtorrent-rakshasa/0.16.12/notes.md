# libtorrent-rakshasa 0.16.12 适配笔记

## 编译环境

- **系统**: HarmonyOS (OpenHarmony) PC aarch64
- **编译器**: clang (OHOS native)
- **构建系统**: autotools (configure + make)
- **C++标准**: C++17 (AX_CXX_COMPILE_STDCXX(17, noext, mandatory))
- **日期**: 2026-08-30

## 依赖

### 运行时依赖
- **curl/8.15.0** — configure.ac 中 PKG_CHECK_MODULES([LIBCURL], [libcurl]) 为必需依赖
- **openssl/3.5.6.1** — TORRENT_CHECK_OPENSSL 检测 OpenSSL
- **zlib/1.3.1.1** — PKG_CHECK_MODULES([ZLIB], [zlib]) 为必需依赖

### 测试依赖
- **cppunit/1.15.1** — test_requires，仅用于 make check

### 构建工具依赖 (build_requirements)
- **automake/1.18** — GitHub tag 归档不含预生成的 configure 脚本
- **libtool/2.5.4** — autoreconf 需要 libtoolize
- **m4/1.4.19** — autotools 宏处理器

## Conan 配方

基于同仓库中已验证的 `libtorrent/0.16.17` 配方适配：
- 包名改为 `libtorrent-rakshasa`（避免与 arvidn 的 libtorrent 冲突）
- C++标准从 C++20 降为 C++17（configure.ac 差异）
- 仅保留 pkg.m4 补丁（0.16.17 的 4 个补丁为版本特有问题）
- 移除 `--enable-pthread-setstacksize`（0.16.12 configure.ac 无此选项）
- 保留所有 OHOS 特定适配代码：
  - autoreconf 环境设置（ACLOCAL/AUTOMAKE/LIBTOOLIZE 环境变量）
  - configure 编译器包装器（conftest 签名）
  - umask 077 → 022 修复（HMDFS 兼容）
  - TESTS_ENVIRONMENT 覆盖（HMDFS libtool shebang 问题）

## 历史编译步骤 (2026-05-21 手动编译)

1. 下载源码（使用 curl -k 跳过 SSL 验证）
2. 运行 `autoreconf -ivf` 生成 configure 脚本
3. 复制 pkg.m4 到 scripts 目录
4. 设置 PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig
5. 运行 configure: `./configure --prefix=$DEFAULT_PREFIX`
6. 编译: `make -j2`
7. 安装: `make install DESTDIR=$TEST_PREFIX`

## 问题与方案

### 问题1: SSL 证书验证失败
- **原因**: GitHub HTTPS 连接证书验证失败
- **解决方案**: 使用 `curl -k` 手动下载源码

### 问题2: configure 脚本不存在
- **原因**: Git 克隆的源码缺少预生成的 configure
- **解决方案**: 运行 `autoreconf -ivf` 生成；Conan 配方使用 tool_requires(automake/libtool/m4)

### 问题3: PKG_CHECK_MODULES 宏未展开
- **原因**: pkg.m4 文件不在正确位置
- **解决方案**: 通过补丁 0001-scripts-pkg.m4.patch 将 pkg.m4 添加到 scripts/ 目录

### 问题4: pkg-config 找不到依赖库
- **原因**: PKG_CONFIG_PATH 未设置
- **解决方案**: Conan 配方使用 PkgConfigDeps 生成器自动管理

## 交付物

- 静态库: libtorrent.a
- 动态库: libtorrent.so
- 头文件: torrent/*.h
- pkg-config: libtorrent.pc

## 验证

```bash
pkg-config --modversion libtorrent
# 输出: 0.16.12
```

## 与 0.16.17 的差异

| 项目 | 0.16.12 | 0.16.17 |
|------|---------|---------|
| C++标准 | C++17 | C++20 |
| 补丁 | pkg.m4 (1个) | clang15/libcxx15/cppunit/writable-test (4个) |
| configure选项 | 无 --enable-pthread-setstacksize | 有 --enable-pthread-setstacksize |
| 包名 | libtorrent-rakshasa | libtorrent |
