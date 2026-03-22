# Autotools 修改模式

本文档详细介绍如何修改 Autotools 构建系统的配置文件以支持 HarmonyOS。

## 1. 核心文件

| 文件 | 作用 | 修改必要性 |
|------|------|------------|
| `config.guess` | 自动检测系统类型 | ⭐⭐⭐ 必须 |
| `config.sub` | 验证系统三元组 | ⭐⭐⭐ 必须 |
| `configure.ac` | 生成 configure 脚本 | ⭐ 可选 |
| `Makefile.am` | 生成 Makefile | ⭐ 可选 |

## 2. config.guess 修改

### 2.1 修改位置一：LIBC 检测

在 `__ANDROID__` 检测后添加 `__OHOS__` 检测：

```bash
# 原代码
#if defined(__ANDROID__)
LIBC=android
#else
#include <features.h>
...

# 修改后
#if defined(__ANDROID__)
LIBC=android
#elif defined(__OHOS__)
LIBC=ohos
#else
#include <features.h>
...
```

**作用**：让脚本知道当前使用的是 HarmonyOS 的 C 库（基于 musl）。

### 2.2 修改位置二：系统识别

在主 `case` 语句开头添加 HarmonyOS 识别：

```bash
# 在 case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in 后添加
case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in
    *:HarmonyOS:*:*)
        case "$UNAME_MACHINE" in
            aarch64|arm64)
                MACHINE=aarch64
                ;;
            armv7*|armv8*)
                MACHINE=arm
                ;;
            x86_64|amd64)
                MACHINE=x86_64
                ;;
            i?86)
                MACHINE=i686
                ;;
            *)
                MACHINE="$UNAME_MACHINE"
                ;;
        esac
        GUESS=${MACHINE}-unknown-linux-ohos
        ;;
    *:NetBSD:*:*)
        ...
```

### 2.3 完整补丁示例

```diff
--- a/config.guess
+++ b/config.guess
@@ -150,6 +150,10 @@ Linux|GNU|GNU/*)
 #if defined(__ANDROID__)
 LIBC=android
+#elif defined(__OHOS__)
+LIBC=ohos
 #else
 #include <features.h>
 #ifdef __GNU_LIBRARY__
@@ -200,6 +204,30 @@ case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in
        # Note: NetBSD "libc.so" will be matched by the "libc.*" pattern.
        LIBC=gnu
        ;;
+    *:HarmonyOS:*:*)
+       case "$UNAME_MACHINE" in
+           aarch64|arm64)
+               MACHINE=aarch64
+               ;;
+           armv7*|armv8*)
+               MACHINE=arm
+               ;;
+           x86_64|amd64)
+               MACHINE=x86_64
+               ;;
+           i?86)
+               MACHINE=i686
+               ;;
+           *)
+               MACHINE="$UNAME_MACHINE"
+               ;;
+       esac
+       GUESS=${MACHINE}-unknown-linux-ohos
+       ;;
 esac
```

## 3. config.sub 修改

### 3.1 添加 ohos-linux 支持

在 `android-linux` 处理后添加 `ohos-linux` 支持：

```bash
# 原代码
android-linux)
    basic_machine=$field1-unknown
    basic_os=linux-android
    ;;

# 添加后
android-linux)
    basic_machine=$field1-unknown
    basic_os=linux-android
    ;;
ohos-linux)
    basic_machine=$field1-unknown
    basic_os=linux-ohos
    ;;
```

### 3.2 添加 ohos 操作系统类型

在操作系统列表中添加 `ohos`：

```bash
# 在 case $os 中添加
case $os in
    gnu* | android* | ohos* | bsd* | mach* | minix* | genix* | ultrix* | irix* \
    ...
```

### 3.3 添加 linux-ohos 内核支持

```bash
case $kernel-$os in
    linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \
    | linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )
        ;;
```

## 4. 三元组格式

### 4.1 标准格式

```
<架构>-<厂商>-<操作系统>
```

### 4.2 HarmonyOS 三元组

| 架构 | 三元组 |
|------|--------|
| ARM64 | `aarch64-unknown-linux-ohos` |
| ARM32 | `arm-unknown-linux-ohos` |
| x86_64 | `x86_64-unknown-linux-ohos` |
| i686 | `i686-unknown-linux-ohos` |

### 4.3 为什么使用 linux-ohos

- `linux`：表示兼容 Linux ABI
- `ohos`：表示 OpenHarmony 系统变体
- 这样可以让软件复用 Linux 的代码路径，同时保持系统标识

## 5. 验证修改

### 5.1 验证 config.guess

```bash
# 应用补丁后
./config.guess
# 应输出: aarch64-unknown-linux-ohos

# 检查修改内容
grep -n "__OHOS__" config.guess
grep -n "HarmonyOS" config.guess
```

### 5.2 验证 config.sub

```bash
# 测试三元组验证
./config.sub aarch64-linux-ohos
# 应输出: aarch64-unknown-linux-ohos

./config.sub aarch64-ohos-linux
# 应输出: aarch64-unknown-linux-ohos
```

### 5.3 完整测试

```bash
# 在源码目录
./configure --prefix=$HOME/usr/local
# 应该看到: checking build system type... aarch64-unknown-linux-ohos

# 检查 config.log
grep "build-aarch64-unknown-linux-ohos" config.log
```

## 6. 参考项目

以下项目已完成 HarmonyOS 适配，可作为参考：

| 软件 | 补丁路径 |
|------|----------|
| libffi 3.4.4 | `archives/l/libffi/3.4.4/patches/0001-port-for-ohos.patch` |
| bash 5.3 | `archives/b/bash/5.3/patches/0001-port-for-ohos.patch` |
| automake 1.16.5 | `archives/a/automake/1.16.5/patches/0001-port-for-ohos.patch` |
| libtool 2.4.7 | `archives/l/libtool/2.4.7/patches/0001-port-for-ohos.patch` |
| coreutils 9.10 | `archives/c/coreutils/9.10/patches/0001-add-harmonyos-support.patch` |

## 7. 快速适配脚本

```bash
#!/bin/bash
# autotools-harmonyos-quickfix.sh - 快速适配 Autotools 项目

# 检查文件是否存在
check_file() {
    if [ ! -f "$1" ]; then
        echo "警告: $1 不存在"
        return 1
    fi
    return 0
}

# 修改 config.guess
fix_config_guess() {
    local file="config.guess"
    check_file "$file" || return
    
    # 检查是否已修改
    if grep -q "__OHOS__" "$file"; then
        echo "config.guess 已包含 HarmonyOS 支持"
        return
    fi
    
    echo "正在修改 config.guess..."
    
    # 添加 LIBC 检测
    sed -i '/#if defined(__ANDROID__)/a #elif defined(__OHOS__)\nLIBC=ohos' "$file"
    
    # 添加系统识别
    # 注意：这需要更复杂的 sed 操作，建议使用补丁文件
    echo "请手动添加 HarmonyOS 系统识别代码或应用补丁"
}

# 修改 config.sub
fix_config_sub() {
    local file="config.sub"
    check_file "$file" || return
    
    # 检查是否已修改
    if grep -q "ohos-linux" "$file"; then
        echo "config.sub 已包含 HarmonyOS 支持"
        return
    fi
    
    echo "正在修改 config.sub..."
    
    # 添加 ohos-linux 支持
    sed -i '/android-linux)/a \    ohos-linux)\n\tbasic_machine=$field1-unknown\n\tbasic_os=linux-ohos\n\t;;' "$file"
}

# 主函数
main() {
    echo "=== Autotools HarmonyOS 快速适配 ==="
    
    fix_config_guess
    fix_config_sub
    
    echo ""
    echo "建议：使用完整补丁文件进行更准确的修改"
}

main "$@"
```

---

## 8. OpenSSL vs libffi 适配对比

OpenSSL 和 libffi 代表了两种典型的构建系统适配方式。

### 8.1 对比总览

| 方面 | OpenSSL (1.1.1w) | libffi (3.4.4) |
|------|------------------|----------------|
| **构建系统** | 自定义 Perl Configure | Autotools (configure) |
| **配置文件** | `Configurations/15-openharmony.conf` | `config.guess`, `config.sub` |
| **平台检测位置** | Configure 脚本 | config.guess 脚本 |
| **检测方式** | Perl 代码 | Shell 脚本 |
| **目标标识** | `openharmony-aarch64` | `aarch64-unknown-linux-ohos` |
| **预定义宏** | `__OHOS__` | 无（通过三元组识别） |
| **配置方式** | 目标名称 | 三元组 |
| **继承关系** | `linux-generic32.0` | 自动继承 Linux |
| **修改文件数** | 2 个 | 2 个 |
| **补丁大小** | ~2KB | ~1.5KB |

### 8.2 OpenSSL 适配方式

**添加配置文件** `Configurations/15-openharmony.conf`：

```perl
my %targets = (
    "openharmony" => {
        inherit_from     => [ "linux-generic32.0" ],
        template         => 1,
        cflags           => add("-D__OHOS__"),
        thread_scheme    => "pthreads",
        dso_scheme       => "dlfcn",
        shared_target    => "linux-shared",
    },
    "openharmony-aarch64" => {
        inherit_from     => [ "openharmony", "linux-aarch64" ],
    },
);
```

**修改 Configure 脚本添加自动检测**：

```perl
# 检测 HarmonyOS
if (!$table{$target}) {
    my $sysname = `uname -s 2>/dev/null`;
    if ($sysname =~ m/harmonyos|openharmony/i) {
        $target = "openharmony-" . `uname -m`;
    }
}
```

### 8.3 libffi 适配方式

**修改 config.guess**：

```bash
# 位置1：LIBC 检测
#if defined(__ANDROID__)
LIBC=android
#elif defined(__OHOS__)
LIBC=ohos
#else

# 位置2：系统识别
*:HarmonyOS:*:*)
    case "$UNAME_MACHINE" in
        aarch64|arm64) MACHINE=aarch64 ;;
        armv7*|armv8*) MACHINE=arm ;;
        x86_64|amd64)  MACHINE=x86_64 ;;
        *)             MACHINE="$UNAME_MACHINE" ;;
    esac
    GUESS=${MACHINE}-unknown-linux-ohos
    ;;
```

**修改 config.sub**：

```bash
ohos-linux)
    basic_machine=$field1-unknown
    basic_os=linux-ohos
    ;;
```

### 8.4 关键差异总结

| 差异点 | OpenSSL | libffi |
|--------|---------|--------|
| 构建系统不同 | 自定义 Perl Configure | 标准 autotools |
| 配置方式不同 | 目标名称（openharmony-aarch64） | 三元组（aarch64-unknown-linux-ohos） |
| 检测方式不同 | Configure 脚本中 Perl 检测 | config.guess 中 Shell 检测 |
| 平台标识不同 | `__OHOS__` 宏 | `linux-ohos` 三元组 |
| 文件位置不同 | 新建配置文件 | 修改现有文件 |

### 8.5 选择建议

| 场景 | 推荐方式 |
|------|----------|
| Autotools 项目 | 使用 libffi 模式（修改 config.guess/config.sub） |
| 自定义构建系统 | 参考 OpenSSL 模式（添加配置文件） |
| CMake 项目 | 添加平台检测逻辑 |

---

## 9. 常见问题

### 9.1 configure 后子目录 Makefile 包含乱码

**现象**：`top_srcdir` 变量值异常。

**原因**：toybox expr 不支持复合正则表达式。

**解决**：

```bash
# 安装 GNU coreutils
export PATH=$HOME/usr/local/bin:$PATH

# 或手动修复
for dir in */; do
    if [ -f "$dir/Makefile" ]; then
        perl -pi -e 's/^top_srcdir\s*=.*/top_srcdir\t= ..\/' "$dir/Makefile"
    fi
done
```

### 9.2 无法识别 HarmonyOS 系统

**现象**：
```
configure: error: cannot guess build type
```

**解决**：检查 config.guess 补丁是否正确应用。

```bash
grep -n "HarmonyOS" config.guess
grep -n "__OHOS__" config.guess
```

### 9.3 三元组验证失败

**现象**：
```
configure: error: invalid triplet aarch64-unknown-linux-ohos
```

**解决**：检查 config.sub 是否添加了 ohos-linux 支持。

```bash
grep -n "ohos-linux" config.sub
```

---

*文档版本: 1.1*  
*最后更新: 2024-03-22*