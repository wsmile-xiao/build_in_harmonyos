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