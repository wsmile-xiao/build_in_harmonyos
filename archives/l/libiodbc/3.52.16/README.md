# libiodbc 3.52.16 — HarmonyOS 预编译包

> iODBC（Independent Open Database Connectivity）是一个开源的 ODBC 驱动管理器实现，
> 提供 ODBC 2.x 和 3.x 标准 API，用于在应用程序和数据库驱动之间建立统一接口层。

## 基本信息

| 属性 | 值 |
|------|-----|
| 软件名称 | libiodbc |
| 版本 | 3.52.16 |
| 构建系统 | autotools |
| 目标平台 | aarch64-unknown-linux-ohos (HarmonyOS) |
| 编译器 | clang 15.0.4 |
| 许可证 | LGPL-2.1+ / BSD-2-Clause |
| 状态 | 已发布 (published) |

## 源码

- **下载地址**: https://github.com/openlink/iODBC/archive/refs/tags/v3.52.16.tar.gz
- **SHA256**: `a0cf0375b462f98c0081c2ceae5ef78276003e57cdf1eb86bd04508fb62a0660`

## 构建步骤

```bash
# 1. 源码不含 configure 脚本，需先 autoreconf
autoreconf -fi

# 2. 配置（禁用静态库）
./configure --prefix=$DEFAULT_PREFIX --disable-static

# 3. 编译
make -j1

# 4. 安装（DESTDIR 模式）
make install DESTDIR=$TEST_PREFIX

# 5. 安装（正式）
make install
```

## 补丁说明

本版本应用了以下补丁：

| 补丁文件 | 类型 | 说明 |
|----------|------|------|
| `0001-INSTALL.patch` | autoreconf 自动生成 | autoreconf 更新的 INSTALL 文件（非功能性） |
| `0002-admin-mkinstalldirs.patch` | autoreconf 自动生成 | autoreconf 更新的 mkinstalldirs 脚本（非功能性） |
| `0003-samples-Makefile.am.patch` | **功能性补丁** | 移除 iodbctest/iodbctestw 的 `-static` LDFLAGS，解决 libtool convenience 库静态链接 undefined symbol 问题 |

**核心补丁说明**: iODBC 使用 libtool convenience 库 (`noinst_LTLIBRARIES`) 作为内部子库。这些 convenience 库的对象文件不会合并到父库的 `.a` 静态归档中，导致 `-static` 链接时出现 undefined symbol 错误。补丁移除样本程序的 `-static` LDFLAGS，配合 `--disable-static` 使用动态链接。

## 安装产物

### 共享库

| 文件 | 大小 | 说明 |
|------|------|------|
| libiodbc.so.2.1.31 | 356KB | ODBC 驱动管理器核心库 |
| libiodbcinst.so.2.1.31 | 104KB | ODBC 驱动安装管理器库 |

### 可执行文件

| 文件 | 说明 |
|------|------|
| iodbc-config | 编译配置查询工具 |
| iodbctest | ODBC 连接测试工具（⚠️ musl 限制无法直接运行） |
| iodbctestw | ODBC 连接测试工具（Unicode 版，⚠️ 同上） |

### 头文件（11个）

- `isql.h`, `isqlext.h`, `isqltypes.h` — ODBC 2.x 接口
- `sql.h`, `sqlext.h`, `sqlucode.h`, `sqltypes.h` — ODBC 3.x 接口
- `odbcinst.h`, `iodbcunix.h`, `iodbcinst.h`, `iodbcext.h` — iODBC 平台特有接口

### pkg-config

- `lib/pkgconfig/libiodbc.pc`

## 使用方法

### 编译链接

```bash
# 使用 iodbc-config
clang myapp.c $(iodbc-config --cflags) $(iodbc-config --libs) -o myapp

# 使用 pkg-config
clang myapp.c $(pkg-config --cflags libiodbc) $(pkg-config --libs libiodbc) -o myapp
```

### 版本确认

```bash
iodbc-config --version   # → 3.52.16
pkg-config --modversion libiodbc  # → 3.52.16
```

## 已知限制

1. **iodbctest 无法直接运行**: HarmonyOS 的 musl 动态链接器不支持直接执行依赖共享库的二进制文件，这是平台限制而非 iODBC 问题。其他通过 `-liodbc -liodbcinst` 链接的应用程序不受影响。

2. **源码缺少 configure 脚本**: GitHub tarball 不包含 autotools 生成的文件，构建前必须先运行 `autoreconf -fi`。

3. **G0 clean-verify 失败**: 当前 clean-verify 脚本不支持 `pre_configure` bootstrap（autoreconf）步骤，导致自动验证无法通过。人工构建验证已通过。

## 依赖关系

- **无特殊依赖**: iODBC 是独立的 ODBC 驱动管理器，共享库仅依赖 libc.so
- **可选依赖**: GTK+（用于 iodbcadm 图形管理工具，本构建未启用）

## 预编译包

| 包文件 | 大小 | 说明 |
|--------|------|------|
| libiodbc-3.52.16-ohos-aarch64.tar.gz | 2.3MB | 完整预编译包 |
| libiodbc-3.52.16-ohos-aarch64-debug.tar.gz | 430KB | 调试符号包 |