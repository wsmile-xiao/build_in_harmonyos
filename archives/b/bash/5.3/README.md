# GNU Bash 5.3 在 OpenHarmony 上的编译指南

## 概述

本文档记录了 GNU Bash 5.3 在 OpenHarmony/HarmonyOS 系统上的编译过程、关键修改点和测试结果。

### 编译结果

| 项目 | 结果 |
|------|------|
| 软件版本 | GNU bash 5.3.0(1)-release |
| 目标平台 | aarch64-unknown-linux-ohos |
| 编译器 | clang (系统自带) |
| 安装位置 | `$HOME/usr/local/bin/bash` |
| 文件大小 | ~3.7 MB |
| 编译日期 | 2026-03-17 |

## 软件信息

| 项目 | 信息 |
|------|------|
| 软件名称 | GNU Bash |
| 版本 | 5.3 |
| 官方网站 | https://www.gnu.org/software/bash/ |
| 下载地址 | https://ftp.gnu.org/gnu/bash/bash-5.3.tar.gz |
| 许可证 | GPL v3 |

## 鸿蒙环境

| 项目 | 信息 |
|------|------|
| 系统版本 | OpenHarmony |
| 编译器 | clang (系统自带) |
| 构建系统 | Autotools |

## 编译步骤

### 1. 下载源码

```bash
cd $HOME/tmp
curl -L -O https://ftp.gnu.org/gnu/bash/bash-5.3.tar.gz
tar -xzf bash-5.3.tar.gz
cd bash-5.3
```

### 2. 应用补丁

```bash
# 应用补丁（补丁文件位于本归档目录下）
patch -p1 < 0001-port-for-ohos.patch
```

### 3. 配置（本地构建）

**简化配置**：系统环境已自动设置编译器，只需最简配置：

```bash
./configure \
    --prefix=$HOME/usr/local \
    --without-bash-malloc
```

**配置选项说明**：

| 选项 | 说明 |
|------|------|
| `--prefix=$HOME/usr/local` | 安装位置 |
| `--without-bash-malloc` | 禁用 bash 内置内存分配器（避免与 musl libc 不兼容）|

**注意事项**：
- 系统环境已自动设置 `CC=clang`, `AR=llvm-ar` 等
- `config.guess` 会自动检测系统为 `aarch64-unknown-linux-ohos`
- 无需手动指定 `--host`、`CFLAGS`、`LDFLAGS` 等参数

### 4. 编译安装

```bash
make -j$(nproc)
make install
```

### 5. 验证

```bash
$HOME/usr/local/bin/bash --version
# 输出: GNU bash, version 5.3.0(1)-release (aarch64-unknown-linux-ohos)
```

## 补丁说明

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `support/config.guess` | 添加 HarmonyOS 系统识别和 `__OHOS__` 宏检测 |
| `support/config.sub` | 添加 `ohos-linux` 目标系统支持 |

### 关键修改详解

#### config.guess - 系统识别

**问题背景**：
- 原版 `config.guess` 无法识别 HarmonyOS 系统（`uname -s` 返回 `HarmonyOS`）
- 需要生成正确的三元组：`aarch64-unknown-linux-ohos`

**技术原理**：
- `config.guess` 脚本用于检测当前系统的架构和操作系统
- 生成的三元组格式：`<架构>-<厂商>-<操作系统>`
- HarmonyOS 使用 musl libc，需要与 Android 类似的特殊处理

**解决方案**：

1. **添加 `__OHOS__` 宏检测**（检测 C 库类型）：
```c
#if defined(__ANDROID__)
LIBC=android
#elif defined(__OHOS__)
LIBC=ohos
#else
// ... 原有检测逻辑
```

2. **添加 HarmonyOS 系统识别**：
```sh
*:HarmonyOS:*:*)
    GUESS=$UNAME_MACHINE-unknown-linux-ohos
    ;;
```

**影响**：
- 当在 HarmonyOS 系统上运行时，自动生成正确的三元组
- 编译系统能正确识别目标平台

#### config.sub - 目标系统验证

**问题背景**：
- `config.sub` 无法识别 `linux-ohos` 目标
- 需要将 `ohos-linux` 三元组解析为正确的系统配置

**技术原理**：
- `config.sub` 用于验证和规范化三元组
- 将三元组分解为：CPU、厂商、操作系统等组件
- 需要将 `ohos` 识别为有效的操作系统标识

**解决方案**：

```sh
ohos-linux)
    basic_machine=$field1-unknown
    basic_os=linux-ohos
    ;;
```

**影响**：
- 支持以 `--host=aarch64-linux-ohos` 方式配置
- 编译系统能正确解析目标平台参数

### 与其他项目对比

| 项目 | 构建系统 | 平台标识 | 预定义宏 |
|------|----------|----------|----------|
| Bash 5.3 | Autotools | `aarch64-unknown-linux-ohos` | 无（通过三元组识别）|
| OpenSSL 1.1.1w | 自定义 Perl | `openharmony-aarch64` | `__OHOS__` |
| libffi 3.4.4 | Autotools | `aarch64-unknown-linux-ohos` | 无 |

**关键差异**：
- Bash 与 libffi 使用相同的三元组格式
- OpenSSL 使用不同的目标名称格式
- 三者都依赖 `__OHOS__` 宏进行系统检测

## 遇到的问题

### 问题 1：系统无法识别

**现象**：
```
checking build system type... Invalid configuration `aarch64-unknown-linux-ohos': machine `aarch64-unknown-linux-ohos' not recognized
```

**原因**：
- 原版 `config.guess` 和 `config.sub` 不支持 HarmonyOS

**解决方案**：
- 应用补丁修改 `config.guess` 和 `config.sub`
- 添加 HarmonyOS 系统识别逻辑

### 问题 2：内存分配器不兼容

**现象**：
- 编译成功但运行时可能出现内存问题

**原因**：
- Bash 内置的内存分配器可能与 HarmonyOS 的 musl libc 不兼容

**解决方案**：
- 使用 `--without-bash-malloc` 配置选项
- 使用系统内存分配器

## 测试结果

### 基本功能测试

| 测试项 | 结果 |
|--------|------|
| 版本显示 | ✅ 通过 |
| echo 输出 | ✅ 通过 |
| for 循环 | ✅ 通过 |
| 算术运算 | ✅ 通过 |
| 数组操作 | ✅ 通过 |
| 命令替换 | ✅ 通过 |
| 管道操作 | ✅ 通过 |
| 条件判断 | ✅ 通过 |
| 函数定义 | ✅ 通过 |

### 测试命令

```bash
# 基本输出
bash -c 'echo "Hello from bash 5.3"'
# 输出: Hello from bash 5.3

# 循环测试
bash -c 'for i in 1 2 3; do echo "Loop $i"; done'
# 输出: Loop 1, Loop 2, Loop 3

# 算术运算
bash -c 'echo "Test: $((2+3))"'
# 输出: Test: 5

# 数组操作
bash -c 'arr=(a b c); echo ${arr[@]}'
# 输出: a b c

# 命令替换
bash -c 'echo "Current dir: $(pwd)"'

# 条件判断
bash -c 'if [ 1 -eq 1 ]; then echo "equal"; fi'
# 输出: equal

# 管道操作
bash -c 'echo "hello world" | tr "a-z" "A-Z"'
# 输出: HELLO WORLD

# 函数定义
bash -c 'f() { echo "function: $1"; }; f test'
# 输出: function: test
```

## 注意事项

1. **必须应用补丁**：编译前需要先应用 `0001-port-for-ohos.patch`
2. **禁用内置内存分配器**：使用 `--without-bash-malloc` 选项
3. **依赖库**：需要 ncursesw（已安装在 `$HOME/usr/local`）
4. **首次运行**：鸿蒙系统首次执行新编译的二进制会弹窗确认

## 参考资料

- GNU Bash 官方文档: https://www.gnu.org/software/bash/manual/
- GNU FTP: https://ftp.gnu.org/gnu/bash/
- OpenHarmony 编译知识库: `build_in_harmonyos/SKILL.md`
- 相关项目参考: `build_in_harmonyos/l/libffi/3.4.4/README.md`