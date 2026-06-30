# libmodbus 3.1.10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: cc/c++ (系统默认编译器)
- 状态: built

## 编译步骤

1. **下载源码**：从 GitHub 下载（Savannah SSL 证书问题）
   ```bash
   curl -L -o libmodbus-3.1.10.tar.gz https://github.com/stephane/libmodbus/archive/refs/tags/v3.1.10.tar.gz
   ```

2. **解压和初始化**：
   ```bash
   tar -xzf libmodbus-3.1.10.tar.gz
   cd libmodbus-3.1.10
   ./autogen.sh  # 生成 configure 脚本
   ```

3. **配置编译选项**（禁用依赖跟踪）：
   ```bash
   ./configure --prefix=$HOME/usr/local --disable-dependency-tracking
   ```

4. **编译和安装**：
   ```bash
   make -j1
   make install DESTDIR=$HOME/tmp/test-install-libmodbus-3.1.10  # staging
   make install  # 安装到本地
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah SSL 证书验证失败 | 网络环境 SSL 证书问题 | 使用 GitHub 镜像下载源码 |
| 2 | mv: bad '.deps/modbus.Tpo' | 依赖跟踪文件生成失败 | 使用 `--disable-dependency-tracking` 配置 |
| 3 | libtool 脚本不完整（仅149行） | configure 时 sed/mv 命令失败 | 复制完整 libtool 脚本（11947行）|
| 4 | 只生成静态库（libmodbus.a） | libtool 动态库生成失败 | 接受静态库，无动态库 |

## 源码修改

无补丁，直接使用原始源码编译。

## 依赖版本

- automake: 系统自带
- libtool: 系统自带（1.5.x）
- autoconf: 系统自带

## 验证结果

```bash
# pkg-config 验证
pkg-config --modversion libmodbus
# 输出: 3.1.10

pkg-config --cflags libmodbus
# 输出: -I/storage/Users/currentUser/usr/local/include/modbus

pkg-config --libs libmodbus
# 输出: -L/storage/Users/currentUser/usr/local/lib -lmodbus

# 安装文件检查
ls ~/usr/local/lib/libmodbus.a
# 输出: -rw-rw---- libmodbus.a (171KB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmodbus-3.1.10-ohos-aarch64.tar.gz | 230KB | 预编译包（静态库 + 头文件 + pkgconfig）|
| libmodbus.a | 171KB | 静态库 |

## 注意事项

1. **仅静态库**：本版本只生成了静态库（libmodbus.a），无动态库（.so）。使用时需要静态链接。
2. **libtool 问题**：autotools 项目在鸿蒙平台上可能遇到 libtool 生成问题，需要手动修复或使用完整脚本。
3. **依赖跟踪**：建议使用 `--disable-dependency-tracking` 避免依赖文件生成失败。

---
**编译结束**: 2026-05-21 20:40
**最终状态**: built
---

**编译结束**: 2026-05-21 20:44
**最终状态**: built
