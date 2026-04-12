# readline for OpenHarmony (HarmonyOS)

本修改为 readline 添加了 OpenHarmony（鸿蒙系统）支持，通过修改 autotools 的配置脚本，让 readline 能够识别鸿蒙系统并正确配置编译参数。

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | readline |
| 版本 | 8.2 |
| 官网 | https://tiswww.cwru.edu/php/chet/readline/rltop.html |
| 源码下载 | https://ftp.gnu.org/gnu/readline/readline-8.2.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 代码准备

- 下载代码使用官方代码下载
  ```bash
  wget https://ftp.gnu.org/gnu/readline/readline-8.2.tar.gz
  tar -xzf readline-8.2.tar.gz
  cd readline-8.2
  ```

  或使用 git clone
  ```bash
  git clone -b readline-8.2 https://github.com/readline/readline.git
  cd readline
  ```

- 应用修改的补丁
  ```bash
  patch -p1 < 0001-port-for-ohos.patch
  ```

## 编译步骤

### 1. 配置

```bash
# ⚠️ 关键：必须设置 CFLAGS="-fPIC"，否则静态库链接到共享库会报错
CFLAGS="-fPIC -O2" ./configure --prefix=$HOME/usr/local --with-curses
```

### 2. 编译

```bash
make -j$(nproc)
```

### 3. 安装

```bash
make install
```

## ⚠️ 关键注意事项：CFLAGS="-fPIC" 必须设置

### 问题现象

如果不设置 `CFLAGS="-fPIC"`，编译 Python 时会报错：

```
ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'rl_prompt'; recompile with -fPIC
>>> defined in /storage/Users/currentUser/usr/local/lib/libreadline.a(readline.o)
```

### 问题根因

readline 的 configure 脚本对静态库和共享库使用不同的编译选项：

| 变量 | 用途 | 是否自动加 -fPIC |
|------|------|-----------------|
| `CFLAGS` | 静态库 (`libreadline.a`) | ❌ **不会自动加** |
| `SHOBJ_CFLAGS` | 共享库 (`libreadline.so`) | ✅ 自动加 `-fPIC` |

在鸿蒙系统上：
- musl libc 默认使用 **BIND_NOW**（符号立即解析）
- 当静态库被链接到共享库（Python `.so`）时，静态库也必须使用 `-fPIC`

### 解决方案

```bash
# ✅ 正确方式：在 configure 命令前设置 CFLAGS
CFLAGS="-fPIC -O2" ./configure --prefix=$HOME/usr/local --with-curses

# ❌ 错误方式：不设置 CFLAGS
./configure --prefix=$HOME/usr/local  # 静态库无 -fPIC，链接 Python 报错
```

### 为什么 export CFLAGS 可能无效？

1. **没有 export**：
   ```bash
   # ❌ 错误：只在当前 shell 生效，configure 是子进程
   CFLAGS="-fPIC -O2"
   ./configure
   
   # ✅ 正确：export 后子进程可继承
   export CFLAGS="-fPIC -O2"
   ./configure
   ```

2. **直接在命令行设置更可靠**：
   ```bash
   # ✅ 推荐：直接在 configure 前设置，最可靠
   CFLAGS="-fPIC -O2" ./configure --prefix=$HOME/usr/local --with-curses
   ```

## 编译结果

安装后会生成以下文件：

```
$HOME/usr/local/
├── lib/
│   ├── libreadline.a      # 静态库（带 -fPIC）
│   ├── libreadline.so     -> libreadline.so.8
│   ├── libreadline.so.8   -> libreadline.so.8.2
│   ├── libreadline.so.8.2 # 动态库
│   ├── libhistory.a       # 历史库静态库（带 -fPIC）
│   ├── libhistory.so      -> libhistory.so.8
│   ├── libhistory.so.8    -> libhistory.so.8.2
│   └── libhistory.so.8.2  # 历史库动态库
├── include/
│   └── readline/
│       ├── readline.h
│       ├── history.h
│       └── ...
└── lib/pkgconfig/
    ├── readline.pc
    └── history.pc
```

## 依赖关系

### 依赖

- **ncurses**：终端库，readline 依赖 ncurses 进行终端操作

### 被依赖

以下软件依赖 readline：
- Python（交互式命令行）
- Bash
- GDB
- 以及许多需要命令行编辑的程序

## 修改内容介绍（0001-port-for-ohos.patch 补丁内容）

### 1. 修改 support/config.guess - 系统检测

在 `support/config.guess` 中添加了 HarmonyOS 系统的识别逻辑：

```bash
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
```

**功能说明：**
- 检测 `uname -s` 返回 `HarmonyOS`
- 将架构名称标准化（aarch64、arm、x86_64、i686）
- 生成三元组格式：`${MACHINE}-unknown-linux-ohos`
- 使用 `linux-ohos` 作为操作系统名称，让 readline 把鸿蒙当作 Linux 兼容系统

### 2. 修改 support/config.sub - 平台验证

在 `support/config.sub` 中添加了 `ohos` 操作系统的支持：

**在操作系统匹配中添加 linux-ohos*：**
```bash
case $maybe_os in
    nto-qnx* | linux-* | linux-ohos* | uclinux-uclibc* \
```

**在系统类型列表中添加 ohos*：**
```bash
case $os in
    gnu* | android* | ohos* | bsd* | mach* | minix* | genix* | ultrix* | irix* \
```

**在内核-操作系统匹配中添加 linux-ohos*：**
```bash
case $kernel-$os in
    linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \
           | linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )
```

## 常见问题

### Q: 编译时找不到 ncurses

确保 ncurses 已安装，并且头文件在正确位置：

```bash
# 检查 ncurses 安装
ls -la $HOME/usr/local/lib/libncursesw*
ls -la $HOME/usr/local/include/curses.h

# 如果 curses.h 在 ncursesw/ 子目录，创建软链接
cd $HOME/usr/local/include
ln -sf ncursesw/curses.h curses.h
```

### Q: 运行时找不到 libreadline.so

确保库路径在搜索路径中：

```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
```

### Q: Python 编译报错 "recompile with -fPIC"

重新编译 readline，确保设置 `CFLAGS="-fPIC -O2"`：

```bash
cd readline-8.2
make clean
CFLAGS="-fPIC -O2" ./configure --prefix=$HOME/usr/local --with-curses
make -j$(nproc)
make install
```

## 验证编译结果

```bash
# 检查安装的文件
ls -lh $HOME/usr/local/lib/libreadline*
ls -lh $HOME/usr/local/lib/libhistory*

# 检查静态库是否带 -fPIC（应该能正常链接到共享库）
cd $HOME/tmp
cat > test_readline.c << 'EOF'
#include <stdio.h>
extern char *rl_prompt;
int main() {
    printf("test\n");
    return 0;
}
EOF

clang -shared -fPIC -o test_readline.so test_readline.c \
    -L$HOME/usr/local/lib -lreadline -lncursesw
echo "链接结果: $?"

rm -f test_readline.c test_readline.so
```

## 参考资料

- readline 官方文档：https://tiswww.cwru.edu/php/chet/readline/rltop.html
- readline GitHub 仓库：https://github.com/readline/readline
- OpenHarmony 官方网站：https://www.openharmony.cn/

## 许可证

本修改遵循 readline 原有许可证（GPL v3）。