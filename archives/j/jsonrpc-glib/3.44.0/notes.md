# jsonrpc-glib 3.44.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **依赖编译（特殊处理）**：
   - libpcre2 10.42: 使用CMake替代autotools（因HMDFS临时文件限制E091）
   - glib 2.88.0: 预编译包安装
   - gio 2.88.0: 预编译包安装（依赖libpcre2、libffi）
   - json-glib 1.6.6: 预编译包安装

2. **主软件编译**：
   ```bash
   meson setup builddir --prefix=$HOME/usr/local \
     -Dwith_introspection=false \
     -Dwith_vapi=false \
     -Denable_tests=false
   ninja
   ninja install DESTDIR=$TEST_PREFIX
   ```

3. **质量门禁验证**：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py verify-build jsonrpc-glib 3.44.0
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libpcre2 autotools失败 | HMDFS临时文件创建限制（E091） | 使用CMake替代autotools编译libpcre2 10.42 |
| 2 | gobject-introspection依赖缺失 | 可选依赖无预编译包 | 通过meson选项禁用：-Dwith_introspection=false |
| 3 | meson make步骤失败 | meson使用ninja而非make | 手动执行ninja编译 |

## 特殊处理

### libpcre2依赖编译
- **问题**: HMDFS autotools临时文件创建限制
- **方案**: 使用CMake替代autotools编译libpcre2 10.42
- **原因**: config.status无法创建临时文件（E091）
- **记录**: 主编批准的特殊方案（平台限制）

### 依赖链
1. libpcre2 10.42 (CMake手动编译，启用PIC)
2. glib 2.88.0 (预编译包)
3. gio 2.88.0 (预编译包)
4. json-glib 1.6.6 (预编译包)
5. jsonrpc-glib 3.44.0 (meson编译)

## 源码修改

无补丁文件（meson配置禁用可选功能，无源码修改）

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libpcre2-8 | 10.42 | CMake手动编译 |
| glib-2.0 | 2.88.0 | 预编译包 |
| gio-2.0 | 2.88.0 | 预编译包 |
| json-glib-1.0 | 1.6.6 | 预编译包 |
| libffi | 3.4.4 | 预编译包 |

## 验证结果

```bash
pkg-config --modversion jsonrpc-glib-1.0
# 输出: 3.44.0

ls -lh ~/usr/local/lib/libjsonrpc-glib-1.0.so.1.4400.0
# 输出: -rwxr-x--- 1 ... 5.2M 2026-05-29 12:28
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libjsonrpc-glib-1.0.so.1.4400.0 | 5.2M | 共享库（动态链接） |
| jsonrpc-glib-1.0.pc | 0.5K | pkg-config文件 |
| include/jsonrpc-glib-1.0/*.h | 9个文件 | 头文件 |
| jsonrpc-glib-3.44.0-release.tar.gz | 5.3M | 预编译包 |

## 注意事项

1. **HMDFS平台限制**：autotools构建系统无法创建临时文件，需使用CMake或手动指定系统类型
2. **可选依赖处理**：gobject-introspection功能已禁用（-Dwith_introspection=false）
3. **知识提取**：创建E091知识条目（HMDFS autotools临时文件限制）

## 知识提取

- E091: HMDFS autotools临时文件创建限制
  - 影响：所有使用GNU autotools的软件
  - 方案：使用CMake替代或手动修改config.guess
  - 平台：HarmonyOS HMDFS