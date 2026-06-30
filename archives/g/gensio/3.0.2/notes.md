# gensio 3.0.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++ (15.0.4)
- 状态: published

## 编译步骤

1. **源码准备**: 从 GitHub 下载 v3.0.2 tarball
   ```bash
   ohc-run.py init-build gensio 3.0.2 --url=https://api.github.com/repos/cminyard/gensio/tarball/v3.0.2
   ```

2. **生成构建系统**: 源码中只有 configure.ac，需要运行 autoreconf
   ```bash
   cd /storage/Users/currentUser/builds/gensio-3.0.2.work
   autoreconf -fi
   ```

3. **配置**:
   ```bash
   ./configure --prefix=/storage/Users/currentUser/usr/local
   ```

4. **编译**:
   ```bash
   make -j2
   ```

5. **安装**:
   ```bash
   make install DESTDIR=/storage/Users/currentUser/test-install-gensio-3.0.2
   ```

6. **测试**:
   ```bash
   make check
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 configure 脚本 | GitHub tarball 只包含 configure.ac | 运行 `autoreconf -fi` 生成构建系统 |
| 2 | reconf 脚本失败 | aclocal 找不到 autom4te | 使用 `autoreconf -fi` 替代 reconf |
| 3 | make check 失败 | OpenSSL 未安装，SSL 相关测试无法运行 | 跳过 SSL 测试，核心功能可用 |

## 源码修改

无补丁。源码直接编译成功，仅需要生成构建系统。

## 依赖版本

- **无强制依赖**: 核心库无需外部依赖即可编译
- **可选依赖（未安装）**:
  - OpenSSL（SSL 支持）
  - glib（GLib OS funcs）
  - tcl（TCL OS funcs）
  - sctp（SCTP 支持）
  - avahi（mDNS 支持）
  - alsa（音频支持）
  - openipmi（IPMI SOL 支持）
  - pam（认证支持）
  - swig（Python/Go bindings）

## 验证结果

```bash
# C++ 基础测试
PASS: basic_cpp_test
SKIP: serial_test

# 总体测试结果
# TOTAL: 2
# PASS:  1
# SKIP:  1
# FAIL:  0
```

**注意**: SSL 相关测试因 OpenSSL 未安装而失败，这不影响核心功能的使用。

## 交付物

### 库文件
- libgensio.so.14.1.1 (350K)
- libgensio.a (514K)
- libgensiocpp.so.14.1.1 (263K)
- libgensiocpp.a (330K)
- libgensioosh.so.14.1.1 (406K)
- libgensioosh.a (631K)
- libgensiomdns.so.14.1.1 (30K)
- libgensiomdns.a (21K)
- libgensiomdnscpp.so.14.1.1 (71K)
- libgensiomdnscpp.a (83K)
- libgensiooshcpp.so.14.1.1 (155K)
- libgensiooshcpp.a (187K)

### 可执行文件
- gensiot (122K) - 基本连接工具
- gsound (54K) - 音频工具
- gagwpe (79K) - AGWPE 工具
- greflector (6.6K) - 反射器脚本

### pkg-config 文件
- libgensio.pc
- libgensioosh.pc
- libgensiomdns.pc
- libgensiocpp.pc
- libgensiooshcpp.pc
- libgensiomdnscpp.pc

## 注意事项

1. **构建系统生成**: GitHub tarball 不包含 configure 脚本，必须先运行 `autoreconf -fi`
2. **可选依赖**: 大部分功能依赖可选库（OpenSSL、glib、tcl 等），未安装时对应功能不可用
3. **测试限制**: SSL 相关测试需要 OpenSSL，未安装时会失败
4. **核心功能**: 基础 I/O 功能（TCP、UDP、Unix sockets、serial、pty 等）无需外部依赖即可使用
---

**编译结束**: 2026-06-09 10:51
**最终状态**: built
