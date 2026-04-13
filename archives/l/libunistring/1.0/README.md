# GNU libunistring 1.0 在 OpenHarmony 上的编译指南

## 概述

本文档记录了 GNU libunistring 1.0 在 OpenHarmony/HarmonyOS 系统上的编译过程、关键修改点和测试结果。libunistring 是一个提供 Unicode 字符串处理功能的 C 库，被 boxes 等软件依赖。

### 编译结果

| 项目 | 结果 |
|------|------|
| 软件版本 | GNU libunistring 1.0 |
| 目标平台 | aarch64-unknown-linux-ohos |
| 编译器 | clang (系统自带) |
| 安装位置 | vendor/libunistring-1.0/ohos-install |
| 静态库大小 | 5.3 MB (libunistring.a) |
| 动态库大小 | 2.9 MB (libunistring.so.2.2.0) |
| 编译日期 | 2026-04-13 |

## 软件信息

| 项目 | 信息 |
|------|------|
| 软件名称 | GNU libunistring |
| 版本 | 1.0 |
| 官方网站 | https://www.gnu.org/software/libunistring/ |
| 下载地址 | https://ftp.gnu.org/gnu/libunistring/libunistring-1.0.tar.gz |
| 许可证 | LGPL v3+ (库), GPL v3+ (程序) |
| 描述 | Unicode 字符串处理库，提供 Unicode 字符串函数 |

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
curl -L -O https://ftp.gnu.org/gnu/libunistring/libunistring-1.0.tar.gz
tar -xzf libunistring-1.0.tar.gz
cd libunistring-1.0
```

### 2. 更新 config.guess/config.sub

libunistring 1.0 内嵌的 config.guess (2021-11-30 版) 不支持 HarmonyOS，需要更新：

```bash
# 下载 GNU config 最新版本
export SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem
curl -L -o build-aux/config.guess 'https://git.savannah.gnu.org/cgit/config.git/plain/config.guess'
curl -L -o build-aux/config.sub 'https://git.savannah.gnu.org/cgit/config.git/plain/config.sub'
chmod +x build-aux/config.guess build-aux/config.sub
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

```sh
# 在 OS 列表中添加 ohos*
| android* \
| ohos* \
| aof* \
```

### 4. 配置

```bash
# 创建 config.cache 解决 socklen_t 问题
cat > config.cache << 'EOF'
gl_cv_header_netinet_in_h=yes
gl_cv_type_socklen_t=yes
ac_cv_type_socklen_t=yes
EOF

# 配置
./configure \
    --enable-static \
    --prefix=$PWD/ohos-install \
    --cache-file=config.cache
```

**配置选项说明**：

| 选项 | 说明 |
|------|------|
| `--enable-static` | 构建静态库（推荐） |
| `--prefix=$PWD/ohos-install` | 安装到本地目录 |
| `--cache-file=config.cache` | 使用预设检测结果 |

### 5. 编译安装

```bash
make -j$(nproc)
make install
```

### 6. 验证

```bash
ls -la $PWD/ohos-install/lib/
# 应显示: libunistring.a, libunistring.so.2.2.0

# 检查头文件
ls -la $PWD/ohos-install/include/
# 应显示: unitypes.h, unistring.h, uniconv.h 等
```

## 补丁说明

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `build-aux/config.guess` | 添加 HarmonyOS 系统识别 |
| `build-aux/config.sub` | 添加 ohos-linux 和 ohos* 支持 |
| `config.cache` | 预置 socklen_t 等检测结果 |

### 关键修改详解

#### config.guess - 系统识别

**问题背景**：
- 原版 config.guess 无法识别 HarmonyOS（`uname -s` 返回 `HarmonyOS`）
- 需要生成正确的三元组：`aarch64-unknown-linux-ohos`

**技术原理**：
- HarmonyOS 基于 Linux 内核，使用 musl libc
- 系统识别需要将 `HarmonyOS` 映射到 `linux-ohos`

**解决方案**：
```sh
case $UNAME_SYSTEM in
HarmonyOS)
    echo "$UNAME_MACHINE"-unknown-linux-ohos
    exit ;;
Linux|GNU|GNU/*)
    # ... 原有逻辑
```

#### config.sub - 目标验证

**问题背景**：
- config.sub 需要验证三元组合法性
- 原版不接受 `linux-ohos` 作为有效 OS

**解决方案**：
1. 添加 `ohos-linux` 分支处理
2. 在 OS 列表中添加 `ohos*`

#### config.cache - 检测结果预置

**问题背景**：
- configure 检测 socklen_t 类型时失败
- 原因：HarmonyOS SDK 的类型定义机制与检测逻辑冲突

**技术原理**：
- `socklen_t` 在 musl libc 中通过 `sys/socket.h` 定义
- configure 的检测脚本尝试创建临时文件检测类型存在性
- HarmonyOS 环境下临时目录权限导致检测失败

**解决方案**：
```bash
# 创建 config.cache 预置检测结果
gl_cv_type_socklen_t=yes
ac_cv_type_socklen_t=yes
```

## 遇到的问题

### 问题 1：config.guess 无法识别 HarmonyOS

**现象**：
```
checking build system type... cannot guess build type; you must specify one
configure: error: cannot guess build type
```

**原因**：
- libunistring 1.0 内嵌的 config.guess 版本过旧 (2021-11-30)
- 最新 GNU config 版本 (2025-07-10) 仍不包含 HarmonyOS 识别

**解决方案**：
- 手动在 config.guess 中添加 HarmonyOS case 分支
- 在 config.sub 中添加 ohos-linux 和 ohos* 支持

### 问题 2：socklen_t 类型缺失

**现象**：
```
checking for socklen_t equivalent... configure: error: Cannot find a type to use in place of socklen_t
```

**原因**：
- HarmonyOS SDK 使用 musl libc 风格的头文件
- configure 检测逻辑尝试创建临时文件失败（权限问题）

**解决方案**：
- 创建 config.cache 预置检测结果
- 使用 `--cache-file=config.cache` 参数

### 问题 3：locale 检测耗时过长

**现象**：
- configure 在检测 locale 时卡住（如 "checking for a traditional french locale"）

**原因**：
- HarmonyOS 环境缺少标准 locale 数据
- configure 尝试遍历各种 locale 组合进行检测

**解决方案**：
- 使用 config.cache 预置 locale 相关检测结果
- 或等待 configure 自然超时后继续

## 编译产物

### 静态库

| 库文件 | 大小 | 说明 |
|--------|------|------|
| `libunistring.a` | 5.3 MB | 静态链接库 |

### 动态库

| 库文件 | 大小 | 说明 |
|--------|------|------|
| `libunistring.so.2.2.0` | 2.9 MB | 动态链接库 |
| `libunistring.so` | symlink | 指向 libunistring.so.2.2.0 |
| `libunistring.so.2` | symlink | 指向 libunistring.so.2.2.0 |

### 头文件

| 头文件 | 说明 |
|--------|------|
| `unitypes.h` | Unicode 类型定义 |
| `unistring.h` | Unicode 字符串函数 |
| `uniconv.h` | Unicode 转换函数 |
| `unistdio.h` | Unicode I/O 函数 |

## 测试结果

由于作为依赖库编译，未执行完整测试套件。

### 基本验证

| 测试项 | 结果 |
|--------|------|
| 静态库编译 | ✅ 通过 |
| 动态库编译 | ✅ 通过 |
| 头文件安装 | ✅ 通过 |
| 与 boxes 链接 | ✅ 通过 |

## 注意事项

1. **必须更新 config.guess/config.sub**：原版不支持 HarmonyOS
2. **推荐使用静态库**：避免运行时库路径问题
3. **config.cache 是必要的**：解决 socklen_t 等检测问题
4. **作为依赖编译**：通常不需要独立安装到系统

## 经验总结

1. **E007 错误模式**：config.guess 不识别系统时，需手动添加 HarmonyOS 分支
2. **E072 错误模式**：config.sub 三元组验证失败时，需添加 ohos-linux 支持
3. **检测缓存策略**：对于 HarmonyOS 特有的检测失败，使用 config.cache 预置结果是最有效的解决方案
4. **依赖库编译流程**：作为 boxes 等软件的依赖，可在 vendor 目录下编译，避免污染系统环境

## 参考资料

- GNU libunistring 官方文档: https://www.gnu.org/software/libunistring/manual/
- GNU FTP: https://ftp.gnu.org/gnu/libunistring/
- GNU Config: https://git.savannah.gnu.org/cgit/config.git/
- OpenHarmony 编译知识库: `build_in_harmonyos/SKILL.md`
- 相关错误模式: `build_in_harmonyos/knowledge/graph/E007.kv`, `E072.kv`
- boxes 编译记录: `build_in_harmonyos/archives/b/boxes/2.3.1/README.md`