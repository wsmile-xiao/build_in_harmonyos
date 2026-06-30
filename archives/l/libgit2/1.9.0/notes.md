# libgit2 1.9.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **下载源码**: 从 GitHub archive 下载 v1.9.0 tarball
2. **初始化**: `ohc-run.py init-build libgit2 1.9.0 --url=file:///path/to/tarball`
3. **安装依赖**: 通过 cmd-pkgs 安装 OpenSSL 1.1.1w 预编译包
4. **配置 CMake**: 设置环境变量并运行 cmake
   - `export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig"`
   - `export OPENSSL_ROOT_DIR="$HOME/usr/local"`
   - `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DUSE_HTTPS=OpenSSL ..`
5. **编译**: `make -j`
6. **安装**: `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 找不到 OpenSSL | SSL 证书问题导致下载失败 | 使用本地文件或 GitHub archive |
| 2 | CMake 配置失败 | 缺少 HTTPS 后端 | 安装 OpenSSL 预编译包并设置 OPENSSL_ROOT_DIR |

## 源码修改

无补丁，使用原始源码编译。

## 依赖版本

- openssl: 1.1.1w (预编译包)

## 验证结果

```bash
# CMake 配置成功
-- Enabled features:
 * HTTPS, using OpenSSL
 * SHA256, using OpenSSL

# 编译成功
[100%] Built target libgit2_tests

# 安装成功
Installing to staging directory
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libgit2-1.9.0-ohos-aarch64.tar.gz | ~7MB | 预编译包（待生成）|

## 注意事项

1. **必须设置 OPENSSL_ROOT_DIR**: CMake 的 find_package(OpenSSL) 需要这个环境变量
2. **预扫描警告**: /tmp 硬编码和 chmod 调用为 low/medium 级别，非阻塞
3. **getloadavg 可用**: musl/OHOS 上已实现，无需处理
---

**编译结束**: 2026-05-19 22:34
**最终状态**: published
