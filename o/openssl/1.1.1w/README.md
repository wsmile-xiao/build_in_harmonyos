# OpenSSL for OpenHarmony (HarmonyOS)

本修改为 OpenSSL 添加了 OpenHarmony（鸿蒙系统）支持，实现了**自动平台检测**，用户可以直接运行 `./Configure`，无需手动指定目标。

## 代码准备
- 下载代码使用官方代码下载
	```bash
	git clone -b OpenSSL_1_1_1w https://github.com/openssl/openssl.git
	```

	网络有问题则推荐使用国内镜像站
	```bash
	git clone -b OpenSSL_1_1_1w git@gitcode.com:GitHub_Trending/ope/openssl.git
	```
- 应用修改的补丁
	```
	cd openssl
	git apply 0001-support-build-in-harmonyos.patch
	```

## 修改内容介绍（0001-support-build-in-harmonyos.patch 补丁内容）

### 1. 新增配置文件

#### Configurations/15-openharmony.conf
OpenHarmony 平台配置文件，定义了以下目标架构：
- `openharmony` - 基础配置（32位）
- `openharmony-aarch64` - 64位 ARM
- `openharmony-arm` - 32位 ARM
- `openharmony-x86_64` - 64位 x86
- `openharmony-x86` - 32位 x86
- `openharmony-riscv64` - RISC-V 64位

使用官方标准的预处理器宏 `__OHOS__`。

### 2. 修改 Configure 脚本

在 Configure 脚本中添加了**自动平台检测**逻辑：

```perl
# 当目标不在目标表中时，自动检测是否为 OpenHarmony 系统
if (!$table{$target}) {
    # 检测系统信息
    my $sysname = `uname -s 2>/dev/null`;
    my $machine = `uname -m 2>/dev/null`;
    my $kernel = `uname -r 2>/dev/null`;
    
    # 检查是否为 OpenHarmony 系统
    if ($sysname =~ m/harmonyos|openharmony/i || 
        $kernel =~ m/harmonyos|openharmony/i) {
        # 自动映射到对应的 openharmony-* 目标
        print "Auto-detected OpenHarmony system, using target: $target\n";
    }
}
```

**检测方式：**
1. 通过 `uname -s` 检测系统名称（HarmonyOS/OpenHarmony）
2. 通过 `uname -m` 检测机器架构（aarch64/arm/x86_64等）
3. 通过 `uname -r` 检测内核版本（备用检测方式）

## 使用方法

### 方法1：自动检测（推荐）✨

在 OpenHarmony 系统上，直接运行 `./Configure`，无需指定目标：

```bash
./Configure
make
make install
```

Configure 脚本会自动检测到 OpenHarmony 系统并选择合适的目标架构，输出类似：
```
Auto-detected OpenHarmony system, using target: openharmony-aarch64
```

### 方法2：直接指定目标

如果需要指定特定架构：

```bash
# ARM64
./Configure openharmony-aarch64

# ARM32
./Configure openharmony-arm

# x86_64
./Configure openharmony-x86_64

# RISC-V
./Configure openharmony-riscv64

make
make install
```

## 编译环境要求

### 必需工具
- Perl 5.10+ (需要 Text::Template 模块，OpenSSL 自带)
- Clang/Clang++ 编译器
- Make
- LLVM 工具链（llvm-ar, llvm-ranlib, llvm-nm, llvm-strip）
通过应用市场下载DevBox安装以上工具链

### 环境变量

鸿蒙系统修改~/.zshrc 或对应的解释器配置文件，文件内容如下; 这套环境变量中`DEFAULT_PREFIX`指定了安装的目录, 在alias的`configure`,`cmake`,`Configure`中默认指定，这部分可以忽略，若需要指定目录的这部分，需要提前执行`mkdir -p $DEFAULT_PREFIX`, 避免install过程中出现目录不存在等问题

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

### 可选环境变量

```bash
# 自定义安装路径
PREFIX=/opt/openssl

# 运行测试
RUN_TESTS=1
```

## 支持的功能

### ✅ 已支持
- 核心加密算法（AES, DES, 3DES等）
- 哈希函数（SHA1, SHA256, SHA512, MD5等）
- 公钥加密（RSA, ECDSA, ECDH等）
- 对称加密
- 多线程支持（pthread）
- 动态链接（dlopen）

### ⚠️ 可能需要适配
- 某些系统调用（syslog, getrandom等）
- 硬件加速（需要根据具体平台适配）

## 故障排除

### 问题1：找不到 perl
```bash
export PATH=/data/service/hnp/bin:$PATH
```

### 问题2：Configure 权限问题
```bash
chmod +x Configure
```

### 问题3：找不到系统头文件
```bash
export CPPFLAGS="-I/path/to/sysroot/usr/include $CPPFLAGS"
```

### 问题4：链接错误
```bash
export LDFLAGS="-L/path/to/sdk/lib $LDFLAGS"
```

### 问题5：自动检测失败

如果自动检测失败，可以手动指定目标：

```bash
# 查看当前系统信息
uname -s
uname -m

# 手动指定目标
./Configure openharmony-aarch64
```

## 文件清单

```
openssl/
├── Configure                              # 修改：添加自动检测
└── Configurations/
    └── 15-openharmony.conf               # 新增：OpenHarmony 配置
```

## 技术细节

### 预处理器宏
- `__OHOS__` - OpenHarmony 系统标识（官方标准）
- `_REENTRANT` - 线程安全支持

### 目标架构映射

| 系统检测 | 架构检测 | OpenSSL 目标 |
|---------|---------|--------------|
| HarmonyOS/OpenHarmony | aarch64 | openharmony-aarch64 |
| HarmonyOS/OpenHarmony | armv7l/armv8l | openharmony-arm |
| HarmonyOS/OpenHarmony | x86_64 | openharmony-x86_64 |
| HarmonyOS/OpenHarmony | x86 | openharmony-x86 |
| HarmonyOS/OpenHarmony | riscv64 | openharmony-riscv64 |

### 自动检测逻辑

1. 用户运行 `./Configure`（不带参数）
2. Configure 尝试查找目标，但未找到（因为用户没指定）
3. 触发自动检测逻辑：
   - 检测系统名称（`uname -s`）
   - 检测内核版本（`uname -r`）
   - 如果匹配 "harmonyos" 或 "openharmony"（不区分大小写）
   - 检测机器架构（`uname -m`）
   - 映射到对应的 `openharmony-*` 目标
4. 继续正常的配置流程

## 为什么使用 __OHOS__ 而不是 __HARMONYOS__？

1. **官方标准** - `__OHOS__` 是 OpenHarmony 官方定义的宏
2. **广泛支持** - OpenHarmony 生态系统中广泛使用
3. **统一性** - HarmonyOS 作为 OpenHarmony 的发行版，应遵循上游标准
4. **兼容性** - Clang 编译器已预定义 `__OHOS__` 宏

## 参考资料

- OpenSSL 官方文档：https://www.openssl.org/docs/
- OpenHarmony 官方网站：https://www.openharmony.cn/
- HarmonyOS 开发者文档：https://developer.huawei.com/consumer/cn/doc/
- Harmony PC 开发者社区：https://harmonypc.csdn.net/content
- OpenHarmony PC Developer gitcode社区：https://gitcode.com/OpenHarmonyPCDeveloper
## 许可证

本修改遵循 OpenSSL 原有许可证（Apache 2.0 License）。
