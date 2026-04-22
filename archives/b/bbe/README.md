# bbe for OpenHarmony (HarmonyOS)

本修改为 bbe 添加了 OpenHarmony（鸿蒙系统）支持，通过修改 autotools 的配置脚本，让 bbe 能够识别鸿蒙系统并正确配置编译参数。

## 代码准备

- 下载代码使用官方代码下载
  ```bash
  wget https://download.savannah.gnu.org/releases/bbe/bbe-0.2.2.tar.gz
  tar -xzf bbe-0.2.2.tar.gz
  cd bbe-0.2.2
  ```

- 应用修改的补丁
  ```bash
  patch -p1 < 0002-config-config.guess.patch
  patch -p1 < 0003-config-config.sub.patch
  ```

## 修改内容介绍

### 1. 修改 config/config.guess - 系统检测

在 `config/config.guess` 中添加了 HarmonyOS 系统的识别逻辑：

```bash
aarch64:HarmonyOS:*:*)
    echo aarch64-unknown-linux-ohos
    exit ;;
```

**功能说明：**
- 检测 `uname -s` 返回 `HarmonyOS`
- 生成三元组格式：`aarch64-unknown-linux-ohos`
- 使用 `linux-ohos` 作为操作系统名称，让 bbe 把鸿蒙当作 Linux 兼容系统

同时也添加了其他架构的检测支持：

```bash
aarch64:Linux:*:*)
    echo aarch64-unknown-linux-gnu
    exit ;;
aarch64_be:Linux:*:*)
    echo aarch64_be-unknown-linux-gnu
    exit ;;
```

### 2. 修改 config/config.sub - 平台验证

在 `config/config.sub` 中添加了 `ohos` 操作系统的支持：

```bash
# 在操作系统匹配中添加 linux-ohos*
case $maybe_os in
  nto-qnx* | linux-gnu* | linux-dietlibc | linux-newlib* | linux-uclibc* | linux-ohos* | \
  ...

# 在系统类型列表中添加 -ohos*
case $os in
  ... | -skyos* | -haiku* | -rdos* | -toppers* | -ohos*)
```

**功能说明：**
- 让 configure 接受 `linux-ohos` 作为有效操作系统
- 让 bbe 的构建系统识别 `ohos` 系统类型
- 确保 `linux-ohos` 三元组能够通过验证

## 使用方法

### 方法1：使用环境变量别名（推荐）✨

如果已在 `~/.zshrc` 中配置了环境变量和别名：

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

通过应用市场下载 DevBox 安装以上工具链。

### 环境变量

鸿蒙系统修改 `~/.zshrc` 或对应的解释器配置文件：

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

export CC="clang"
export CXX="clang++"
export LD="ld.lld"
export STRIP="llvm-strip"
export RANLIB="llvm-ranlib"
export NM="llvm-nm"
export AR="llvm-ar"
```

## 支持的功能

### ✅ 已支持
- bbe 核心功能（二进制块编辑）
- 基本命令行工具
- 正则表达式匹配

### ⚠️ 注意事项
- 部分测试可能因平台限制而无法通过
- 测试套件需要 bash 环境支持

## 故障排除

### 问题1：config.guess 权限问题
```bash
chmod +x config/config.guess config/config.sub
```

### 问题2：检测不到 HarmonyOS
```bash
# 检查系统信息
uname -s
uname -m

# 手动指定三元组
./configure --host=aarch64-unknown-linux-ohos
```

### 问题3：链接错误
```bash
export LDFLAGS="-L$HOME/usr/local/lib -Wl,-rpath,$HOME/usr/local/lib $LDFLAGS"
```

## 文件清单

```
bbe-0.2.2/
└── config/
    ├── config.guess      # 修改：添加 HarmonyOS 检测
    └── config.sub        # 修改：添加 ohos 操作系统支持
```

## 技术细节

### 三元组格式

bbe 使用 autotools 的标准三元组格式：
```
<架构>-<厂商>-<操作系统>
```

对于鸿蒙系统，我们使用：
```
aarch64-unknown-linux-ohos
```

**为什么使用 `linux-ohos`？**
- `linux` 表示兼容 Linux ABI
- `ohos` 表示 OpenHarmony 系统变体
- 这样可以让 bbe 复用 Linux 的代码路径，同时保持系统标识

## 验证编译结果

```bash
# 检查安装的文件
ls -lh $HOME/usr/local/bin/bbe

# 运行 bbe 版本检查
bbe --version

# 简单测试
echo "test" > test.txt
bbe -b '0x74657374' -e '0x64617461' test.txt
```

## 参考资料

- bbe 官方网站：https://savannah.gnu.org/projects/bbe/
- OpenHarmony 官方网站：https://www.openharmony.cn/
- HarmonyOS 开发者文档：https://developer.huawei.com/consumer/cn/doc/
- OpenHarmony PC Developer gitcode社区：https://gitcode.com/OpenHarmonyPCDeveloper

## 许可证

本修改遵循 bbe 原有许可证（GPL）。