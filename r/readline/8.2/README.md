# readline for OpenHarmony (HarmonyOS)

本修改为 readline 添加了 OpenHarmony（鸿蒙系统）支持，通过修改 autotools 的配置脚本，让 readline 能够识别鸿蒙系统并正确配置编译参数。

## 代码准备

- 下载代码使用官方代码下载
  \`\`\`bash
  wget https://ftp.gnu.org/gnu/readline/readline-8.2.tar.gz
  tar -xzf readline-8.2.tar.gz
  cd readline-8.2
  \`\`\`

  或使用 git clone
  \`\`\`bash
  git clone -b readline-8.2 https://github.com/readline/readline.git
  cd readline
  \`\`\`

- 应用修改的补丁
  \`\`\`bash
  patch -p1 < 0001-port-for-ohos.patch
  \`\`\`

## 修改内容介绍（0001-port-for-ohos.patch 补丁内容）

### 1. 修改 support/config.guess - 系统检测

在 \`support/config.guess\` 中添加了 HarmonyOS 系统的识别逻辑：

\`\`\`bash
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
\`\`\`

**功能说明：**
- 检测 \`uname -s\` 返回 \`HarmonyOS\`
- 将架构名称标准化（aarch64、arm、x86_64、i686）
- 生成三元组格式：\`\`\`${MACHINE}-unknown-linux-ohos\`\`
- 使用 \`linux-ohos\` 作为操作系统名称，让 readline 把鸿蒙当作 Linux 兼与其他系统兼容系统

### 2. 修改 support/config.sub - 平台验证

在 \`support/config.sub\` 中添加了 \`ohos\` 操作系统的支持：

**在操作系统匹配中添加 linux-ohos*：**
\`\`\`bash
case $maybe_os in
	nto-qnx* | linux-* | linux-ohos* | uclinux-uclibc* \
\`\`\`

**在系统类型列表中添加 ohos*：**
\`\`\`bash
case $os in
	gnu* | android* | ohos* | bsd* | mach* | minix* | genix* | ultrix* | irix* \
\`\`\`

**在内核-操作系统匹配中添加 linux-ohos*：**
\`\`\`bash
case $kernel-$os in
	linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \
		   | linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )
	\`\`\`

**功能说明：**
- 让 configure 接受 \`linux-ohos\` 作为有效操作系统
- 让 readline 的构建系统识别 \`ohos\` 系统类型
- 确保`linux-ohos\` 三元组能够通过验证

## 使用方法

### 方法1：自动检测（推荐）✨

如果已在 \`~/.zshrc\`\` 中配置了环境变量和别名：

\`\`\`bash
configure
make
make install
\`\`\`

### 方法2：手动指定参数

\`\`\`bash
./configure --prefix=\$HOME/usr/local
make
make install
\`\`\`

### 方法3：指定三元组

\`\`\`bash
./configure --host=aarch64-unknown-linux-ohos --prefix=\$HOME/usr/local
make
make install
\`\`\`

## 编译环境要求

### 必需工具
- GCC/Clang 编译器
- Make
- autotools（autoconf, automake, libtool）
- LLVM 工具链（llvm-ar, llvm-ranlib, llvm-nm, llvm-strip）

通过应用市场下载 DevBox 安装以上工具链。

### 环境变量

鸿蒙系统修改\`~/.zshrc\`\` 或对应的解释器配置文件，文件内容如下； 这套环境变量中\`DEFAULT_PREFIX\`指定了安装的目录, 在alias的\`configure\`,\`cmake\`,\`Configure\`中默认指定，这部分可以忽略，若需要指定目录的这部分，需要提前执行\`\`mkdir -p $DEFAULT_PREFIX\`, 避免install过程中出现目录不存在等问题

\`\`\`bash
export DEFAULT_PREFIX=\$HOME/usr/local

export PATH=\$PATH:\$HOME/npm/bin:\$HOME/.local/bin:\$DEFAULT_PREFIX/bin
export LIBRARY_PATH=\$DEFAULT_PREFIX/lib:\$LIBRARY_PATH
export LD_LIBRARY_PATH=\$DEFAULT_PREFIX/lib:\$LD_LIBRARY_PATH

export C_INCLUDE_PATH=\$DEFAULT_PREFIX/include:\$C_INCLUDE_PATH
export CPLUS_INCLUDE_PATH=\$DEFAULT_PREFIX/include:\$CPLUS_INCLUDE_PATH

alias configure='./configure --prefix=\$DEFAULT_PREFIX'
alias cmake='cmake -DCMAKE_INSTALL_PREFIX=\$DEFAULT_PREFIX'
alias Configure='./Configure --prefix=\$DEFAULT_PREFIX'

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
\`\`\`

### 可选环境变量

\`\`\`bash
# 自定义安装路径
PREFIX=/opt/readline

# 运行测试
RUN_TESTS=1
\`\`\`

## 支持的功能

### ✅ 已支持
- FFI（Foreign Function Interface）核心功能
- 多架构支持（aarch64, arm, x86_64, i686）
- 动态库和静态库编译
- C 语言接口
- 闭包（closures）支持

### ⚠️ 注意事项
- readline 依赖 ncurses 库，需要先安装 ncurses
- termcap 库需要先安装 ncurses

## 故障排除

### 问题1：config.guess 权限问题
\`\`\`bash
chmod +x support/config.guess support/config.sub
\`\`\`

### 问题2：检测不到 HarmonyOS
\`\`\`bash
# 检查系统信息
uname -s
uname -m
uname -r

# 手动指定三元组
./configure --host=aarch64-unknown-linux-ohos
\`\`\`

### 问题3：链接错误
\`\`\`bash
export LDFLAGS="-L$HOME/usr/local/lib -Wl,-rpath,$HOME/usr/local/lib $LDFLAGS"
\`\`\`

### 问题4：找不到头文件
\`\`\`bash
export CPPFLAGS="-I$HOME/usr/local/include $CPPFLAGS"
\`\`\`

## 文件清单

\`\`\`\`bash
readline-8.2/
├── support/config.guess      # 修改：添加 HarmonyOS 检测
└── support/config.sub        # 修改：添加 ohos 操作系统支持
\`\`\`

## 技术细节

### 三元组格式

readline 使用 autotools 的标准三元组格式：
\`\`\`\`
<架构>-<厂商>-<操作系统>
\`\`\`

对于鸿蒙系统，我们使用：
\`\`\`\`
aarch64-unknown-linux-ohos
arm-unknown-linux-ohos
x86_64-unknown-linux-ohos
i686-unknown-linux-ohos
\`\`\`

**为什么使用 \`linux-ohos\`？**
- \`linux\` 表示兼容 Linux ABI
- \`ohos\` 表示 OpenHarmony 系统变体
- 这样可以让 readline 复用 Linux 的代码路径，同时保持系统标识

### 架构映射

| uname -m 输出 | 标准架构 | 三元组 |
|--------------|--------------|---------------------|
| aarch64 | aarch64 | aarch64-unknown-linux-ohos |
| arm64 | aarch64 | aarch64-unknown-linux-ohos |
| armv7l/armv8l | arm | arm-unknown-linux-ohos |
| x86_64 | x86_64 | x86_64-unknown-linux-ohos |
| amd64 | x86_64 | x86_64-unknown-linux-ohos |
| i?86 | i686 | i686-unknown-linux-ohos |
|\`\`

### 与其他平台对比

| 方面 | OpenSSL | libffi |
|------|---------|--------|
| **构建系统** | 自定义 Perl Configure | autotools (configure) |
| **配置文件** | Configurations/*.conf | config.guess, config.sub |
| **平台检测** | 修改 Configure 脚本 | 修改 config.guess |
| **三元组** | openharmony-aarch64 | aarch64-unknown-linux-ohos |
| **预定义宏** | __OHOS__ | 无（通过三元组识别） |
| **自动检测** | Perl 代码 | Shell 脚本 |
| **配置方式** | 目标名称 | 三元组 |
|\`\`

**关键差异：**
1. **构建系统不同**：readline 使用 autotools，libffi 使用 autotools
2. **配置方式不同**：readline 通过三元组识别，libffi 也通过三元组识别
3. **平台标识不同**：readline 使用 \`linux-ohos\` 三元组，libffi 也使用 \`linux-ohos\` 三元组
4. **自动检测方式相同**：都在 config.guess 中用 Shell 脚本检测
\`\`

## 验证编译结果

\`\`\`bash
# 检查安装的文件
ls -lh \$HOME/usr/local/lib/libreadline*
ls -lh \$HOME/usr/local/lib/libhistory*
\`\`\`

\`\`\`bash
# 检查 pkg-config
cat \$HOME/usr/local/lib/pkgconfig/readline.pc
\`\`\`

\`\`\`bash
# 编译测试程序
cat > test_readline.c << 'EOF'
#include <stdio.h>
#include <readline/readline.h>
#include <readline/history.h>

int main() {
    printf("readline version: %s\n", rl_library_version);
    printf("History version: %s\n", history_get_version());
    return 0;
}
\`\`\`\`

# 使用静态库编译
clang -I\$HOME/usr/local/include -L\$HOME/usr/local/lib test_readline.c \
    \$HOME/usr/local/lib/lib/libreadline.a -o test_readline
./test_readline
\`\`\`

预期输出：
\`\`\`bash
readline version: 8.2
History version: 8.2
\`\`\`

## 参考资料

- readline 官方文档：https://tiswww.cwru.edu/php/chet/readline/rltop.html
- readline GitHub 仓库：https://github.com/readline/readline
- OpenHarmony 官方网站：https://www.openharmony.cn/
- Harmony PC 开发者社区：https://harmonypc.csdn.net/content
- OpenHarmony PC Developer gitcode社区：https://gitcode.com/OpenHarmonyPCDeveloper

## 许可证

本修改遵循 readline 原有许可证。
