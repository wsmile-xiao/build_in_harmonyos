# 构建系统识别与适配策略

## 1. 构建系统类型

| 构建系统 | 识别特征 | 配置文件 | 适配方式 | 示例软件 |
|---------|---------|---------|---------|---------|
| **Autotools** | 存在 `configure` 脚本 | `configure.ac`, `Makefile.am` | 修改 `config.guess`, `config.sub` | libffi, bash, coreutils |
| **CMake** | 存在 `CMakeLists.txt` | `CMakeLists.txt`, `*.cmake` | 添加平台检测 | zlib |
| **自定义 Perl** | 存在 `Configure` (大写) | `Configurations/*.conf` | 添加配置文件 | OpenSSL |
| **Meson** | 存在 `meson.build` | `meson.build` | 添加平台检测 | systemd |
| **Makefile** | 存在 `Makefile` | `Makefile`, `*.mk` | 直接修改 | bzip2 |
| **QMake** | 存在 `.pro` 文件 | `*.pro` | 修改 .pro 文件 | Qt 项目 |

## 2. 构建系统识别命令

```bash
# 检测脚本
check_build_system() {
    if [ -f "configure" ] && [ -x "configure" ]; then
        echo "Autotools"
    elif [ -f "CMakeLists.txt" ]; then
        echo "CMake"
    elif [ -f "Configure" ] && [ -x "Configure" ]; then
        echo "Custom-Perl"
    elif [ -f "meson.build" ]; then
        echo "Meson"
    elif [ -f "Makefile" ] || ls *.mk 1>/dev/null 2>&1; then
        echo "Makefile"
    else
        echo "Unknown"
    fi
}
```

## 3. Autotools 适配

### 3.0 核心原则：不欺骗构建系统

> **重要原则**：永远不要通过伪造三元组（如 `--build=aarch64-unknown-linux-gnu`）来欺骗 configure。
> 
> 这种做法虽然可能暂时解决问题，但会导致：
> 1. 构建系统对平台特性的错误判断
> 2. 缺失正确的平台特定代码路径
> 3. 编译产物可能与预期不符
> 4. 无法复用补丁和经验

**正确做法**：为 HarmonyOS 添加正式的三元组支持：
1. 修改 `config.guess` 添加 HarmonyOS 识别
2. 修改 `config.sub` 添加 `linux-ohos` 支持
3. 如有必要，修改 `configure.ac` 添加平台分支

**三元组格式**：`{架构}-{厂商}-{操作系统}`
- 标准格式：`aarch64-unknown-linux-ohos`
- 表示：ARM64 架构，未知厂商，基于 Linux 的 HarmonyOS

### 3.1 修改 config.guess

在两个位置添加代码：

**位置 1：LIBC 检测**
```bash
#if defined(__ANDROID__)
LIBC=android
#elif defined(__OHOS__)
LIBC=ohos
#else
```

**位置 2：系统识别**
```bash
case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in
    *:HarmonyOS:*:*)
        GUESS=$UNAME_MACHINE-unknown-linux-ohos
        ;;
    # ... 其他系统
```

### 3.2 修改 config.sub

添加 `ohos-linux` 支持：

```bash
android-linux)
    basic_machine=$field1-unknown
    basic_os=linux-android
    ;;
ohos-linux)
    basic_machine=$field1-unknown
    basic_os=linux-ohos
    ;;
```

### 3.3 编译命令

```bash
# 本地构建（最简配置）
./configure --prefix=$HOME/usr/local
make -j$(nproc)
make install
```

## 4. CMake 适配

### 4.1 平台检测

在 `CMakeLists.txt` 中添加：

```cmake
# 检测 HarmonyOS
if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OpenHarmony")
    set(OHOS TRUE)
    add_definitions(-D__OHOS__)
endif()
```

### 4.2 编译命令

```bash
cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
      -DCMAKE_C_COMPILER=clang \
      -DCMAKE_CXX_COMPILER=clang++ \
      ..
make -j$(nproc)
make install
```

## 5. 自定义 Perl Configure（OpenSSL 风格）

### 5.1 添加配置文件

创建 `Configurations/15-openharmony.conf`：

```perl
my %targets = (
    "openharmony" => {
        inherit_from     => [ "linux-generic32.0" ],
        template         => 1,
        cflags           => add("-D__OHOS__"),
        cppflags         => add("-D__OHOS__"),
        cxxflags         => add("-D__OHOS__"),
        thread_scheme    => "pthreads",
        dso_scheme       => "dlfcn",
        shared_target    => "linux-shared",
        shared_cflag     => "-fPIC",
    },
    "openharmony-aarch64" => {
        inherit_from     => [ "openharmony", "linux-aarch64" ],
    },
);
```

### 5.2 修改 Configure 脚本

添加自动检测逻辑：

```perl
# 检测 HarmonyOS
if ($target eq "" && -x "/system/bin/getprop") {
    my $sysname = `uname -s 2>/dev/null`;
    if ($sysname =~ m/harmonyos|openharmony/i) {
        $target = "openharmony-" . `uname -m`;
    }
}
```

### 5.3 编译命令

```bash
# OpenSSL 编译
./Configure --prefix=$HOME/usr/local \
            --openssldir=$HOME/usr/local/ssl \
            no-asm \
            openharmony-aarch64

make -j$(nproc)
make install
```

## 6. Makefile 直接修改

对于简单的 Makefile 项目，直接修改：

```makefile
# 添加编译器设置
CC = clang
AR = llvm-ar
RANLIB = llvm-ranlib

# 添加编译标志
CFLAGS += -fPIC -D__OHOS__

# 添加安装前缀
PREFIX ?= $(HOME)/usr/local
```

## 7. 构建系统对比

| 方面 | Autotools | CMake | Custom-Perl |
|------|-----------|-------|-------------|
| 学习曲线 | 中等 | 较高 | 低（OpenSSL 特有） |
| 平台检测 | config.guess | CMAKE_SYSTEM_NAME | Configure 脚本 |
| 三元组支持 | ✅ 原生 | ❌ 需手动 | ❌ 使用目标名 |
| 交叉编译 | ✅ 优秀 | ✅ 优秀 | ⚠️ 需配置 |
| 鸿蒙适配难度 | 中等 | 简单 | 中等 |

## 8. 常见问题

### 问题1：configure 检测到错误的三元组

**解决**：手动指定
```bash
./configure --host=aarch64-unknown-linux-ohos
```

### 问题2：CMake 找不到编译器

**解决**：显式指定
```bash
cmake -DCMAKE_C_COMPILER=clang \
      -DCMAKE_CXX_COMPILER=clang++
```

### 问题3：OpenSSL Configure 无法识别系统

**解决**：直接指定目标
```bash
./Configure openharmony-aarch64
```

## 9. 测试原则

### 9.1 必须执行官方测试套件

> **核心原则**：编译完成后，必须执行官方测试套件，不能跳过。

**原因**：
1. 验证编译产物的正确性
2. 发现潜在的兼容性问题
3. 为后续用户提供可靠的参考

**测试命令**：

| 构建系统 | 测试命令 |
|----------|----------|
| Autotools | `make check` |
| CMake | `ctest` 或 `make test` |
| Makefile | `make test`（如有） |
| 自定义 | 查看项目文档 |

### 9.2 测试结果分类

测试失败时，需要区分两类问题：

| 类型 | 特征 | 示例 |
|------|------|------|
| **编译问题** | 功能本身不工作 | 链接错误、段错误、输出错误 |
| **环境兼容性问题** | 功能正常但测试框架不兼容 | BusyBox 缺少选项、PTY 不可用 |

**处理方式**：
- 编译问题：必须修复后重新编译
- 环境兼容性问题：在 manifest.yaml 和测试报告中记录，标记为"不影响核心功能"

### 9.3 测试报告模板

```markdown
# XXX 测试报告

## 测试结果汇总

| 测试项 | 结果 |
|--------|------|
| test1 | ✅ PASS |
| test2 | ❌ FAIL |

## 失败分析

### test2

**失败原因**: ...

**影响范围**: ...

## 结论

兼容性评级: 高/中/低
```

### 9.4 manifest.yaml 测试结果字段

```yaml
test_results:
  type: official  # official | manual | skipped
  total: 6
  passed: 5
  failed: 1
  note: |
    详细说明测试结果和失败原因
```

## 10. 特殊构建场景

### 10.1 automake 鸡生蛋问题

**问题**：编译 automake 自身时，make 过程需要调用尚未构建好的 automake 来重新生成 Makefile.in 文件，形成循环依赖。

**现象**：
- config.status 执行后 Makefile 中存在未替换的变量（如 `@am_AUTOCONF@`）
- make check 触发重新生成导致失败

**解决方案**：
1. 使用 automake 自带的 `gen-all.pl` 脚本手动生成所有模板文件
2. 手动 sed 修补残留变量（如 `@am_AUTOCONF@` → `autoconf`）
3. 手动 cp 安装到正确目录

### 10.2 无 32 位兼容层的软件

**问题**：部分软件（如 strace）默认启用 32 位兼容支持（m32 personality），在纯 aarch64 鸿蒙系统上无法编译。

**解决方案**：
```bash
# strace
./configure --disable-mpers

# 其他类似的软件，检查 configure --help 中是否有 32 位相关选项
./configure --help | grep -i "32\|m32\|multi\|personality"
```

**适用软件**：strace 6.19