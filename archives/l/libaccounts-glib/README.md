# libaccounts-glib

## 软件简介

libaccounts-glib 是 accounts-sso（Single Sign-On）项目的核心组件，提供了用于管理在线账户信息的 GLib/GObject 库。该库实现了统一的账户管理框架，允许应用程序安全地存储和访问用户的在线账户凭据。

**核心功能**：
- 账户信息的安全存储和管理
- 多服务提供商支持（Google、Facebook、Twitter 等）
- D-Bus 接口实现跨进程通信
- 基于 GLib/GObject 的 C API
- 支持账户同步、备份和恢复

**项目地址**：https://gitlab.com/accounts-sso/libaccounts-glib

## 主要特性

1. **账户管理**
   - 创建、删除、修改账户
   - 支持账户服务和类型定义
   - 账户提供者注册和管理

2. **安全存储**
   - 集成系统密钥环（可选）
   - 支持账户凭据加密存储
   - 服务类型和应用程序权限管理

3. **D-Bus 接口**
   - 提供账户管理器 D-Bus 服务
   - 支持多进程并发访问
   - 完整的 XML Schema 定义

4. **多语言支持**
   - GObject Introspection 支持（可选）
   - Python 绑定（通过 PyGObject）

## 编译信息

**版本**: 1.27
**编译日期**: 2026-05-29
**构建系统**: Meson
**编译器**: Clang 15.0.4
**目标平台**: OpenHarmony ARM64

### 编译配置

```bash
# 依赖预编译包
- glib 2.88.0
- libxml2 2.11.9
- sqlite3 3.49.1
- check 0.15.2 (测试依赖)

# 环境变量
export CC=/storage/Users/currentUser/usr/local/bin/clang
export CXX=/storage/Users/currentUser/usr/local/bin/clang++
export AR=/storage/Users/currentUser/usr/local/bin/llvm-ar
export RANLIB=/storage/Users/currentUser/usr/local/bin/llvm-ranlib
export STRIP=/storage/Users/currentUser/usr/local/bin/llvm-strip
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig

# 配置
meson setup builddir --prefix=/storage/Users/currentUser/usr/local

# 编译
ninja -C builddir

# 安装
meson install -C builddir
```

### 平台适配说明

1. **禁用功能**（平台限制）：
   - GObject Introspection（gobject-introspection 未预装）
   - 文档生成（gtkdoc-scan 未预装）
   - 命令行工具（libintl 链接问题）

2. **已知问题**：
   - `/tmp` 只读导致测试套件部分失败（E002 平台限制）
   - libintl 链接问题（需要使用静态库 libintl.a）

## 依赖

### 运行时依赖

- **glib** 2.88.0 - GLib 核心库
- **libxml2** 2.11.9 - XML 解析库
- **sqlite3** 3.49.1 - 数据库引擎（账户存储）

### 编译时依赖

- **meson** 1.6.1 - 构建系统
- **ninja** 1.12.1 - 构建工具
- **pkg-config** 0.29.2 - 依赖管理
- **check** 0.15.2 - 单元测试框架（可选）

## 安装使用

### 预编译包安装

```bash
# 通过 cmd-pkgs 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | \
  sh -s -- libaccounts-glib 1.27
```

### 验证安装

```bash
# 检查库文件
ls -lh ~/usr/local/lib/libaccounts-glib.so*

# 检查头文件
ls ~/usr/local/include/libaccounts-glib/

# 检查 pkg-config
pkg-config --modversion libaccounts-glib
```

### 使用示例

```c
#include <libaccounts-glib/accounts-glib.h>

int main() {
    AgManager *manager = ag_manager_new();
    GList *accounts = ag_manager_list(manager);

    // 遍历账户
    for (GList *l = accounts; l != NULL; l = l->next) {
        AgAccount *account = AG_ACCOUNT(l->data);
        g_print("Account: %s\n", ag_account_get_display_name(account));
    }

    g_list_free(accounts);
    g_object_unref(manager);
    return 0;
}
```

编译：
```bash
clang -o myapp myapp.c $(pkg-config --cflags --libs libaccounts-glib)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `libaccounts-glib.so.1.27` | ~11 MB | 动态库（未 strip） |
| `libaccounts-glib.so` → `libaccounts-glib.so.0` | - | 软链接 |
| `libaccounts-glib.pc` | - | pkg-config 文件 |
| `ag-*.h` | - | 12 个头文件 |
| `accounts-*.its` | - | gettext ITS 文件 |
| `accounts-*.dtd` | - | XML Schema 文件 |

## 质量门禁

| 门禁 | 状态 | 说明 |
|------|------|------|
| G0 干净构建 | ✅ PASS | 补丁自包含，可重现构建 |
| G1 二进制完整性 | ✅ PASS | 库文件完整，符号表正确 |
| G2 功能可用性 | ⚠️ PARTIAL | 核心库可用，工具未编译 |
| G3 可移植性 | ✅ PASS | ELF 已签名，RPATH 正确 |
| G4 档案完整性 | ✅ PASS | manifest.yaml、README.md、notes.md 齐全 |

## 已知限制

1. **命令行工具未编译**
   - ag-backup 和 ag-tool 因 libintl 链接问题暂未编译
   - 核心库功能完整，不影响应用程序使用

2. **测试套件部分失败**
   - `/tmp` 只读导致 check 库无法创建临时文件
   - 这是 OpenHarmony 平台已知限制（E002）

3. **GObject Introspection 缺失**
   - gobject-introspection-1.0 未预装
   - Python 绑定不可用

## 维护信息

- **补丁版本**: 3 个平台适配补丁
  - `0001-docs-meson.build.patch` - 禁用文档生成
  - `0002-libaccounts-glib-meson.build.patch` - 使 gobject-introspection 可选
  - `0003-tools-meson.build.patch` - 禁用工具编译

- **编译状态**: built
- **预编译包**: libaccounts-glib-1.27-ohos-aarch64.tar.gz

## 参考资料

- [GitLab 项目主页](https://gitlab.com/accounts-sso/libaccounts-glib)
- [API 文档](https://accounts-sso.gitlab.io/libaccounts-glib/)
- [Accounts-SSO 项目](https://gitlab.com/accounts-sso)