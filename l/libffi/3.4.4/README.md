# libffi for OpenHarmony (HarmonyOS)

本修改为 libffi 添加了 OpenHarmony（鸿蒙系统）支持，通过修改 autotools 的配置脚本，让 libffi 能够识别鸿蒙系统并正确配置编译参数。

## 代码准备

- 下载代码使用官方代码下载
  ```bash
  wget https://ghfast.top/https://github.com/libffi/libffi/releases/download/v3.4.4/libffi-3.4.4.tar.gz
  tar -xzf libffi-3.4.4.tar.gz
  cd libffi-3.4.4
  ```

  或使用 git clone
  ```bash
  git clone -b v3.4.4 https://github.com/libffi/libffi.git
  cd libffi
  ```

- 应用修改的补丁
  ```bash
  patch -p1 < 0001-port-for-ohos.patch
  ```

## 修改内容介绍（0001-port-for-ohos.patch 补丁内容）

### 1. 修改 config.guess - 系统检测

在 `config.guess` 中添加了 HarmonyOS 系统的识别逻辑：

```bash
*:HarmonyOS:*)
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
```

**功能说明：**
- 检测 `uname -s` 返回 `HarmonyOS`
- 将架构名称标准化（aarch64、arm、x86_64、i686）
- 生成三元组格式：`${MACHINE}-unknown-linux-ohos`
- 使用 `linux-ohos` 作为操作系统名称，让 libffi 把鸿蒙当作 Linux 兼容系统

### 2. 修改 config.sub - 平台验证

在 `config.sub` 中添加了 `ohos` 操作系统的支持：

```bash
# 在操作系统匹配中添加 linux-ohos*
case $maybe_os in
    nto-qnx* | linux-* | linux-ohos* | uclinux-uclibc* \
    ...

# 在系统类型列表中添加 ohos*
case $os in
    gnu* | android* | ohos* | bsd* | mach* | minix* | genix* | ultrix* | irix* \
    ...

# 在内核-操作系统匹配中添加 linux-ohos*
case $kernel-$os in
    linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \
    | linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )
        ;;
```

**功能说明：**
- 让 configure 接受 `linux-ohos` 作为有效操作系统
- 让 libffi 的构建系统识别 `ohos` 系统类型
- 确保 `linux-ohos` 三元组能够通过验证

## 使用方法

### 方法1：使用环境变量别名（推荐）✨

如果已在 `~/.zshrc`` 中配置了环境变量和别名：

```bash
configure
make
make install
```

### 方法2：手动指定参数

```bash
./configure --prefix=$HOME/usr/local
make
make install
```

### 方法3：指定三元组

```bash
./configure --host=aarch64-unknown-linux-ohos --prefix=$HOME/usr/local
make
make install
```

## 编译环境要求

### 必需工具
- GCC/Clang 编译器
- Make
- autotools（autoconf, automake, libtool）
- LLVM 工具链（llvm-ar, llvm-ranlib, llvm-nm, llvm-strip）

通过应用市场下载 DevBox 安装以上工具链。

### 环境变量

鸿蒙系统修改 `~/.zshrc` 或对应的解释器配置文件，文件内容如下：

```bash
export DEFAULT_PREFIX=$HOME/usr/local

export PATH=$PATH:$HOME/npm/bin:$HOME/.local/bin:$DEFAULT_PREFIX/bin
export LIBRARY_PATH=$DEFAULT_PREFIX/lib:$LIBRARY_PATH
export LD_LIBRARY_PATH=$DEFAULT_PREFIX/lib:$LD_LIBRARY_PATH

export C_INCLUDE_PATH=$DEFAULT_PREFIX/include:$C_INCLUDE_PATH
export CPLUS_INCLUDE_PATH=$DEFAULT_PREFIX/include:$CPLUS_INCLUDE_PATH

alias configure='./configure --prefix=$DEFAULT_PREFIX'
alias cmake='cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX'
alias Configure='./Configure --prefix=$DEFAULT_PREFIX'

export AS="llvm-as"
export CC="clang"
export CC_FOR_BUILD="clang"
export CXX="clang++"
export LD="ld.lld"
export STRIP="llvm-strip"
export RANLIB="llvm-ranlib"
export OBJDUMP="llvm-objdump"
export OBJCOPY="llvm-objcopy"
export NM="llvm-nm"
export AR="llvm-ar"
```

## 支持的功能

### ✅ 已支持
- FFI（Foreign Function Interface）核心功能
- 多架构支持（aarch64, arm, x86_64, i686）
- 动态库和静态库编译
- C 语言接口
- 闭包（closures）支持

### ⚠️ 注意事项
- libffi 3.4.4 不包含 `FFI_VERSION_STRING` 和 `FFI_VERSION` 宏（3.5.0+ 才有）
- Java Raw API 已弃用（ffi_java_raw_*）

## 故障排除

### 问题1：config.guess 权限问题
```bash
chmod +x config.guess config.sub
```

### 问题2：检测不到 HarmonyOS
```bash
# 检查系统信息
uname -s
uname -m
uname -r

# 手动指定三元
./configure --host=aarch64-unknown-linux-ohos
```

### 问题3：链接错误
```bash
export LDFLAGS="-L$HOME/usr/local/lib -Wl,-rpath,$HOME/usr/local/lib $LDFLAGS"
```

### 问题4：找不到头文件
```bash
export CPPFLAGS="-I$HOME/usr/local/include $CPPFLAGS"
```

## 文件清单

```
libffi-3.4.4/
├── config.guess      # 修改：添加 HarmonyOS 检测
└── config.sub        # 修改：添加 ohos 操作系统支持
```

## 技术细节

### 三元组格式

libffi 使用 autotools 的标准三元组格式：
```
<架构>-<厂商>-<操作系统>
```

对于鸿蒙系统，我们使用：
```
aarch64-unknown-linux-ohos
arm-unknown-linux-ohos
x86_64-unknown-linux-ohos
i686-unknown-linux-ohos
```

**为什么使用 `linux-ohos`？**
- `linux` 表示兼容 Linux ABI
- `ohos` 表示 OpenHarmony 系统变体
- 这样可以让 libffi 复用 Linux 的代码路径，同时保持系统标识

### 架构映射

| uname -m 输出 | 标准架构 | 三元组 |
|--------------|---------|--------|
| aarch64 | aarch64 | aarch64-unknown-linux-ohos |
| arm64 | aarch64 | aarch64-unknown-linux-ohos |
| armv7l | arm | arm-unknown-linux-ohos |
| armv8l | arm | arm-unknown-linux-ohos |
| x86_64 | x86_64 | x86_64-unknown-linux-ohos |
| amd64 | x86_64 | x86_64-unknown-linux-ohos |
| i686 | i686 | i686-unknown-linux-ohos |
| i386 | i686 | i686-unknown-linux-ohos |

### 与 OpenSSL 适配的差异

| 方面 | OpenSSL (1.1.1w) | libffi (3.4.4) |
|------|------------------|----------------|
| **构建系统** | 自定义的 Perl Configure | autotools (configure) |
| **配置文件** | Configurations/*.conf | config.guess, config.sub |
| **平台检测** | 修改 Configure 脚本 | 修改 config.guess |
| **三元组** | openharmony-aarch64 | aarch64-unknown-linux-ohos |
| **预定义宏** | __OHOS__ | 无（通过三元组识别） |
| **自动检测** | Perl 代码 | Shell 脚本 |
| **配置方式** | 目标名称 | 三元组 |

**关键差异：**
1. **构建系统不同**：OpenSSL 使用自定义的 Perl Configure 脚本，libffi 使用标准的 autotools
2. **配置方式不同**：OpenSSL 通过目标名称（openharmony-aarch64），libffi 通过三元组（aarch64-unknown-linux-ohos）
3. **检测方式不同**：OpenSSL 在 Configure 脚本中检测，libffi 在 config.guess 中检测
4. **平台标识不同**：OpenSSL 使用 `__OHOS__` 宏，libffi 使用 `linux-ohos` 三元组

## 验证编译结果

```bash
# 检查安装的文件
ls -lh $HOME/usr/local/lib/libffi*
ls -lh $HOME/usr/local/include/ffi*

# 检查 pkg-config
cat $HOME/usr/local/lib/pkgconfig/libffi.pc

# 编译测试程序
cat > test_libffi.c << 'EOF'
#include <stdio.h>
#include <ffi.h>

int main() {
    printf("libffi default ABI: %d\n", FFI_DEFAULT_ABI);
    printf("sizeof(ffi_cif): %zu\n", sizeof(ffi_cif));
    return 0;
}
EOF

clang -I$HOME/usr/local/include -L$HOME/usr/local/lib \
    -Wl,-rpath,$HOME/usr/local/lib test_libffi.c -lffi -o test_libffi
./test_libffi
```

## 参考资料

- libffi 官方文档：https://github.com/libffi/libffi
- OpenHarmony 官方网站：https://www.openharmony.cn/
- HarmonyOS 开发者文档：https://developer.huawei.com/consumer/cn/doc/
- Harmony PC 开发者社区：https://harmonypc.csdn.net/content
- OpenHarmony PC Developer gitcode社区：https://gitcode.com/OpenHarmonyPCDeveloper

## 许可证

本修改遵循 libffi 原有许可证。
