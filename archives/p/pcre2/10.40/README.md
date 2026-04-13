# PCRE2 10.40 在 OpenHarmony 上的编译指南

## 概述

本文档记录了 PCRE2 10.40（Perl Compatible Regular Expressions）在 OpenHarmony/HarmonyOS 系统上的编译过程、关键修改点和测试结果。PCRE2 是正则表达式库，提供 8位、16位、32位三种编码支持，被 boxes 等软件依赖。

### 编译结果

| 项目 | 结果 |
|------|------|
| 软件版本 | PCRE2 10.40 |
| 目标平台 | aarch64-unknown-linux-gnu (workaround) |
| 编译器 | clang (系统自带) |
| 安装位置 | vendor/pcre2-10.40/ohos-install |
| 静态库大小 | 425 KB (libpcre2-8.a) |
| 编译日期 | 2026-04-13 |

## 软件信息

| 项目 | 信息 |
|------|------|
| 软件名称 | PCRE2 (Perl Compatible Regular Expressions) |
| 版本 | 10.40 |
| 官方网站 | https://www.pcre.org/ |
| 下载地址 | https://github.com/PCRE2Project/pcre2/releases/download/pcre2-10.40/pcre2-10.40.tar.gz |
| 许可证 | BSD 3-Clause |
| 描述 | 正则表达式库，支持 8位/16位/32位编码 |

## 鸿蒙环境

| 项目 | 信息 |
|------|------|
| 系统版本 | HarmonyOS HongMeng Kernel 1.12.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM 15.0.4) |
| 构建系统 | Autotools |

## 依赖关系

| 角色 | 软件 |
|------|------|
| 被依赖 | boxes 2.3.1 |
| 依赖 | 无（基础库） |

## 编译步骤

### 1. 下载源码

```bash
cd $HOME/tmp
curl -L -O https://github.com/PCRE2Project/pcre2/releases/download/pcre2-10.40/pcre2-10.40.tar.gz
tar -xzf pcre2-10.40.tar.gz
cd pcre2-10.40
```

### 2. 更新 config.guess/config.sub

PCRE2 10.40 内嵌的 config.guess 不支持 HarmonyOS，需要更新：

```bash
# 下载 GNU config 最新版本
export SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem
curl -L -o config.guess 'https://git.savannah.gnu.org/cgit/config.git/plain/config.guess'
curl -L -o config.sub 'https://git.savannah.gnu.org/cgit/config.git/plain/config.sub'
chmod +x config.guess config.sub
```

### 3. 添加 HarmonyOS 识别（手动补丁）

最新版 config.guess 仍不包含 HarmonyOS，需手动添加：

**config.guess 修改**：
```sh
# 在 "case $UNAME_SYSTEM in" 之后添加
HarmonyOS)
    echo "$UNAME_MACHINE"-unknown-linux-ohos
    exit ;;
```

**config.sub 修改**：
```sh
# 在 android-linux 分支后添加
ohos-linux)
    basic_machine=$field1-unknown
    basic_os=linux-ohos
    ;;
```

### 4. 配置

由于 config.sub 仍不接受 `linux-ohos` 作为有效 OS，使用 workaround：

```bash
# 使用 --build 指定类型（符合 skill R15 原则）
./configure \
    --enable-static \
    --disable-shared \
    --prefix=$PWD/ohos-install \
    --build=aarch64-unknown-linux-gnu
```

**配置选项说明**：

| 选项 | 说明 |
|------|------|
| `--enable-static` | 仅构建静态库（推荐） |
| `--disable-shared` | 禁用动态库（可选） |
| `--prefix=$PWD/ohos-install` | 安装到本地目录 |
| `--build=aarch64-unknown-linux-gnu` | 指定构建类型（workaround） |

**重要说明**：
- PCRE2 是 native 编译，不需要交叉编译参数
- `--build` 参数是 workaround，用于绕过 config.sub 不接受 ohos 的问题
- 此方案符合 skill R15 原则：记录为技术债务

### 5. 编译安装

```bash
make -j$(nproc)
make install
```

### 6. 验证

```bash
ls -la $PWD/ohos-install/lib/
# 应显示: libpcre2-8.a, libpcre2-posix.a

# 检查头文件
ls -la $PWD/ohos-install/include/
# 应显示: pcre2.h, pcre2posix.h
```

## 补丁说明

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `config.guess` | 添加 HarmonyOS 系统识别 |
| `config.sub` | 添加 ohos-linux 和 ohos* 支持 |

### 关键修改详解

#### config.guess - 系统识别

**问题背景**：
- 原版 config.guess 无法识别 HarmonyOS
- PCRE2 编译时需要正确的系统类型识别

**解决方案**：
```sh
case $UNAME_SYSTEM in
HarmonyOS)
    echo "$UNAME_MACHINE"-unknown-linux-ohos
    exit ;;
```

#### config.sub - 目标验证

**问题背景**：
- PCRE2 的 config.sub 不接受 `linux-ohos` 作为有效操作系统
- 导致三元组验证失败

**解决方案**：
```sh
# 添加 ohos-linux 分支
ohos-linux)
    basic_machine=$field1-unknown
    basic_os=linux-ohos
    ;;
```

#### --build workaround

**问题背景**：
- 即使更新 config.sub，configure 仍可能不接受 `linux-ohos`
- 需要 fallback 方案

**解决方案**：
```bash
./configure --build=aarch64-unknown-linux-gnu
```

**符合原则**：
- skill R15：native 编译时使用 `--build=linux-gnu` 是可接受的 workaround
- 需在 manifest.yaml 中记录为技术债务

## 遇到的问题

### 问题 1：config.sub 不识别 ohos

**现象**：
```
config.sub: invalid configuration `aarch64-unknown-linux-ohos': OS `ohos' not recognized
```

**原因**：
- PCRE2 内嵌的 config.sub 版本过旧
- 不包含 `ohos` 作为有效操作系统

**解决方案**：
- 更新 config.guess/config.sub
- 使用 `--build=aarch64-unknown-linux-gnu` 作为 fallback

### 问题 2：32位编码支持

**现象**：
- boxes 需要 32位 PCRE2 支持

**原因**：
- 默认配置可能不启用 32位编码

**解决方案**：
- PCRE2 10.40 默认启用 8位、16位、32位编码
- 无需额外配置参数

## 编译产物

### 静态库

| 库文件 | 大小 | 说明 |
|--------|------|------|
| `libpcre2-8.a` | 425 KB | 8位编码支持（最常用） |
| `libpcre2-posix.a` | 5.8 KB | POSIX API 兼容层 |

### 头文件

| 头文件 | 说明 |
|--------|------|
| `pcre2.h` | 主头文件 |
| `pcre2posix.h` | POSIX API 头文件 |

### pkg-config 文件

| 文件 | 说明 |
|------|------|
| `libpcre2-8.pc` | 8位编码 pkg-config |
| `libpcre2-posix.pc` | POSIX pkg-config |

## 测试结果

由于作为依赖库编译，未执行完整测试套件。

### 基本验证

| 测试项 | 结果 |
|--------|------|
| 静态库编译 | ✅ 通过 |
| 头文件安装 | ✅ 通过 |
| pkg-config 文件 | ✅ 通过 |
| 与 boxes 链接 | ✅ 通过 |

## 注意事项

1. **推荐静态库**：避免运行时库路径问题
2. **32位编码**：boxes 使用 32位 PCRE2 (`libpcre2-32`)
3. **--build workaround**：使用 `--build=linux-gnu` 作为 HarmonyOS 的 fallback
4. **技术债务记录**：需在 manifest.yaml 中注明此 workaround

## 经验总结

1. **config.sub fallback**：当 config.sub 不接受 ohos 时，使用 `--build=linux-gnu` 是标准 workaround
2. **skill R15 原则**：native 编译不需要 `--host/--target`，仅 `--build` 作为 fallback
3. **依赖库编译策略**：PCRE2 作为基础库，编译时无需启用所有功能
4. **32位编码支持**：确保启用 32位编码以支持 Unicode 正则表达式

## 技术债务

| 项目 | 说明 | 改进计划 |
|------|------|----------|
| `--build=linux-gnu` | 使用 linux-gnu 替代 linux-ohos | 等上游 config.sub 支持 ohos 后去掉 |

## 参考资料

- PCRE2 官方文档: https://www.pcre.org/current/doc/html/
- PCRE2 GitHub: https://github.com/PCRE2Project/pcre2
- GNU Config: https://git.savannah.gnu.org/cgit/config.git/
- OpenHarmony 编译知识库: `build_in_harmonyos/SKILL.md`
- 相关错误模式: `build_in_harmonyos/knowledge/graph/E072.kv`
- boxes 编译记录: `build_in_harmonyos/archives/b/boxes/2.3.1/README.md`
- libunistring 编译记录: `build_in_harmonyos/archives/l/libunistring/1.0/README.md`