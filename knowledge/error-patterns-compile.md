# 🔨 错误模式：编译与构建类 (E021-E048)

> **父文档**: [error-patterns.md](./error-patterns.md)
> **类别**: 配置系统 / 编译器 / 链接器 / 打包 / 依赖管理
> **适用阶段**: Phase 2 核心编译

---

## 错误模式列表

## E021: BUILDEXEEXT 异常

### 错误特征

```
BUILDEXE=.exe
BUILDPYTHON= python3.9.exe   # 应该是 python3.9
```

### 根因

configure 脚本通过检测文件系统是否大小写不敏感来设置 `BUILDEXEEXT`：

```bash
# 典型检测逻辑
mkdir conftestdir
if test -d conftestdir; then
    BUILDEXEEXT=.exe  # 认为大小写不敏感
fi
```

HarmonyOS 的文件系统在某些边界检测中可能误判。

### 影响范围

| 软件 | 影响 |
|------|------|
| Python | 生成 `python3.9.exe` 而非 `python3.9` |
| 其他 autotools 项目 | 可执行文件名附加 `.exe` 后缀 |

### 解决方案

在 `configure.ac` 中为 HarmonyOS 跳过此检测：

```bash
# 或在 configure 后手动修正
sed -i 's/BUILDEXEEXT=.exe/BUILDEXEEXT=/' Makefile
```

---

## E022: POSIX 信号量差异

### 错误特征

```
sem_unlink(name) -> FileNotFoundError: [Errno 2] No such file or directory
```

### 根因

HarmonyOS 的 POSIX 信号量实现与 Linux 有差异：

| 系统 | 信号量文件位置 | sem_unlink 行为 |
|------|---------------|-----------------|
| Linux | `/dev/shm/sem.xxx` | 正常 |
| HarmonyOS | 可能有不同路径 | 可能找不到文件 |

### 影响程度

| 影响类型 | 说明 |
|----------|------|
| ⚠️ 警告级别 | 不影响测试结果，仅清理阶段警告 |
| ✅ 功能正常 | multiprocessing 基本功能可用 |

### 解决方案

```python
# 安全忽略此类警告
try:
    sem_unlink(name)
except FileNotFoundError:
    pass  # HarmonyOS 上可能找不到
```

### 涉及软件

Python 3.9.0（test_socket）

### 跨软件关联

POSIX 信号量差异是鸿蒙 POSIX 兼容性问题的冰山一角。类似的行为差异也存在于
`pthread_cond_timedwait()`（超时时间解析差异），详见
[harmonyos-specifics.md §16](harmonyos-specifics.md#16-pthread_cond_timedwait-行为差异)。

---

## E023: locale 支持不完整

### 错误特征

```
test_strcoll_with_diacritic ... FAIL
test_complex_formatting ... FAIL
```

### 根因

HarmonyOS 的 locale 支持不如 Linux 完整：

```bash
# 检查可用 locale
locale -a
# 可能缺少 en_US.UTF-8 等常用 locale
```

### 受影响测试

| 测试 | 依赖 | 影响 |
|------|------|------|
| test_locale | locale 数据 | ⚠️ 部分失败 |
| test_c_locale_coercion | locale 环境变量 | ⚠️ 部分失败 |

### 解决方案

```bash
# 跳过 locale 相关测试
python3.9 -m test -x test_locale test_c_locale_coercion

# 使用默认 locale
export LC_ALL=C
```

---

## E024: Unix Domain Socket 受限

### 错误特征

```
socket.bind(address) -> PermissionError: [Errno 1] Operation not permitted
```

### 根因

HarmonyOS 的 SELinux 策略限制 Unix domain socket 的 `bind()` 操作。

### 受影响功能

| 功能 | 说明 |
|------|------|
| multiprocessing.Listener | 进程间通信 |
| socket.AF_UNIX | Unix socket |

### 解决方案

```python
# 不使用 Unix socket，改用 TCP socket
# listener = multiprocessing.connection.Listener('/tmp/socket')  # 失败
listener = multiprocessing.connection.Listener(('localhost', 0))  # 成功
```

---

## E025: CAN socket 宏未定义

### 错误特征

```
error: use of undeclared identifier 'CAN_RAW_FD_FRAMES'
error: use of undeclared identifier 'CAN_RAW_JOIN_FILTERS'
```

### 根因

configure 检测到这些宏存在，但实际编译时头文件中未定义（HarmonyOS 内核头文件差异）。

### 解决方案

修改 `pyconfig.h` 禁用这些宏：

```bash
sed -i 's/^#define HAVE_LINUX_CAN_RAW_FD_FRAMES 1/\/\* #undef HAVE_LINUX_CAN_RAW_FD_FRAMES \*\//' pyconfig.h
sed -i 's/^#define HAVE_LINUX_CAN_RAW_JOIN_FILTERS 1/\/\* #undef HAVE_LINUX_CAN_RAW_JOIN_FILTERS \*\//' pyconfig.h
```

---

## E026: 线程局部存储(TLS)差异

### 错误特征

```
error: thread-local storage not supported
error: '__thread' is not supported
TLS definition mismatch
```

### 根因

musl 的 TLS（Thread-Local Storage）实现与 glibc 略有差异：

| 特性 | glibc | musl (HarmonyOS) |
|------|-------|------------------|
| `__thread` | ✅ 支持 | ✅ 支持 |
| `_Thread_local` (C11) | ✅ 支持 | ✅ 支持 |
| `thread_local` (C++) | ✅ 支持 | ✅ 支持 |
| glibc TLS 扩展 | ✅ 支持 | ❌ 不支持 |
| 动态 TLS | 完整支持 | 有限支持 |

### 常见问题

1. **使用了 glibc 特有的 TLS 扩展**
```c
// glibc 特有，musl 不支持
__thread int *ptr __attribute__((tls_model("initial-exec")));
```

2. **TLS 模型不兼容**
```c
// 某些 TLS 模型在 musl 上可能有问题
__thread int var __attribute__((tls_model("local-dynamic")));
```

### 解决方案

```bash
# 方案1：使用标准语法
# 使用 __thread 或 _Thread_local
__thread int my_tls_var;
// 或 C11 标准
_Thread_local int my_tls_var;

# 方案2：条件编译
#if defined(__OHOS__) || !defined(__GLIBC__)
  // 使用简单 TLS
  __thread int var;
#else
  // glibc 扩展 TLS
  __thread int var __attribute__((tls_model("initial-exec")));
#endif

# 方案3：检查编译选项
# 确保使用 -pthread 或 -lpthread
export CFLAGS="-pthread $CFLAGS"
```

### 验证 TLS 支持

```bash
# 测试 TLS 编译
cat > test_tls.c << 'EOF'
#include <stdio.h>
#include <pthread.h>

_Thread_local int tls_var = 0;

void* thread_func(void* arg) {
    tls_var = (int)(long)arg;
    printf("Thread %ld: tls_var = %d\n", (long)arg, tls_var);
    return NULL;
}

int main() {
    pthread_t t1, t2;
    pthread_create(&t1, NULL, thread_func, (void*)1);
    pthread_create(&t2, NULL, thread_func, (void*)2);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
EOF

clang -pthread test_tls.c -o test_tls
./test_tls
# 应该看到两个线程各自独立的 tls_var 值
```

---

## E027: libintl_gettext 链接失败

### 错误特征

```
ld.lld: error: undefined symbol: libintl_gettext
ld.lld: error: undefined symbol: libintl_bindtextdomain
```

### 根因

GNU 软件默认启用 NLS（Native Language Support）国际化，依赖 libintl（gettext 库），鸿蒙系统未预装该库。

### 验证命令

```bash
grep -r "LIBINTL\|libintl\|nls" Makefile.am configure.ac
```

### 解决方案

```bash
# 推荐方案：禁用国际化
./configure --disable-nls

# 如确需 gettext 支持，需自行编译安装 libintl
```

### 涉及软件

gdbm 1.23、tar 1.35

---

## E028: 用户编译的共享库与系统库冲突

### 错误特征

```
ncurses 共享库安装后，系统 zsh 崩溃，所有终端不可用
```

### 根因

用户编译的共享库版本（如 libncursesw.so.6.4）覆盖了系统版本但符号链接不完整，导致依赖系统 ncurses 的程序崩溃。

### 验证命令

```bash
ls -la $HOME/usr/local/lib/libncurses*
```

### 解决方案

```bash
# 方案1：只编译静态库（推荐）
./configure --without-shared --prefix=$HOME/usr/local
make && make install

# 方案2：如需共享库，确保符号链接完整
# 检查所有 .so 链接是否正确指向
```

### 涉及软件

ncurses 6.4

---

## E029: bash 内置 malloc 与 musl 不兼容

### 错误特征

```
编译成功但运行时内存异常
```

### 根因

bash 默认使用内置 malloc 实现，与 musl libc 的内存管理不兼容，导致运行时出现内存相关问题。

### 验证命令

```bash
./configure --help | grep bash-malloc
```

### 解决方案

```bash
./configure --without-bash-malloc --prefix=$HOME/usr/local
make && make install
```

### 涉及软件

bash 5.3

---

## E030: 鸿蒙无 32 位兼容层导致 strace 编译失败

### 错误特征

```
configure 阶段 m32 personality 检测失败
```

### 根因

strace 默认启用 m32 personality 支持以追踪 32 位程序，鸿蒙系统没有 32 位兼容层，仅有 aarch64 架构。

### 验证命令

```bash
uname -m  # 仅 aarch64
```

### 解决方案

```bash
./configure --disable-mpers --prefix=$HOME/usr/local
make && make install
```

### 涉及软件

strace 6.19

---

## E031: /proc 文件系统 SELinux 访问限制

### 错误特征

```
htop: Cannot open /proc/stat: Permission denied
```

### 根因

鸿蒙 SELinux 策略限制普通用户访问 /proc 文件系统。

### 验证命令

```bash
cat /proc/stat  # Permission denied
```

### 解决方案

```bash
# 使用 sudo 运行
sudo -E TERM=xterm-256color htop
```

### 涉及软件

htop 3.4.1

---

## E032: _GNU_SOURCE 未定义导致 dirent API 不完整

### 错误特征

```
error: unknown type name 'DIR'
error: call to undeclared function 'opendir'
```

### 根因

musl 需要 `_GNU_SOURCE` 而非 `_BSD_SOURCE` 来暴露完整 dirent API，部分软件使用 `_BSD_SOURCE` 不足以在 musl 下获得完整接口。

### 验证命令

```bash
grep -r "_BSD_SOURCE\|_GNU_SOURCE" 源码
```

### 解决方案

```bash
# 方案1：通过 CFLAGS 添加
export CFLAGS="-D_GNU_SOURCE $CFLAGS"

# 方案2：修改源码中的 _BSD_SOURCE 为 _GNU_SOURCE
sed -i 's/_BSD_SOURCE/_GNU_SOURCE/g' 源文件
```

### 涉及软件

gawk 5.3.0

---

## E033: ncurses 宽字符函数需要 _XOPEN_SOURCE_EXTENDED

### 错误特征

```
error: unknown type name 'cchar_t'
error: call to undeclared function 'setcchar'
```

### 根因

musl 下 ncurses 宽字符接口需要显式定义 `_XOPEN_SOURCE_EXTENDED` 才能暴露 cchar_t 等类型和 setcchar 等函数。

### 验证命令

```bash
grep -r "_XOPEN_SOURCE" 源码
```

### 解决方案

```bash
export CFLAGS="-D_XOPEN_SOURCE_EXTENDED -D_XOPEN_SOURCE=600 $CFLAGS"
```

### 涉及软件

Python 3.9.0（curses 模块）

---

## E034: 系统缺少 CA 证书包

### 错误特征

```
wget: unable to load client CA certificates
SSL 证书验证失败
```

### 根因

鸿蒙系统未预装 ca-certificates 包，缺少 `/etc/ssl/certs/ca-certificates.crt`。

### 验证命令

```bash
ls /etc/ssl/certs/ca-certificates.crt  # 文件不存在
```

### 解决方案

```bash
# 临时方案：跳过证书验证
wget --no-check-certificate https://example.com/file

# 永久方案：安装 CA 证书包
```

### 涉及软件

wget 1.19.1

---

## E035: libtoolize shell 函数加载失败

### 错误特征

```
func_add_hook: inaccessible or not found
func_dirname: command not found
```

### 根因

libtoolize 使用 bash 特有的内嵌 source 加载机制，即使 bash 下也可能因函数加载方式问题而失败。

### 验证命令

```bash
libtoolize --version  # 版本正常但功能受限
```

### 解决方案

```
核心功能 libtool 正常可用，libtoolize 仅在从零创建 autotools 项目时需要。
一般不影响使用已有 autotools 配置的项目构建（此类项目通常自带已生成的配置脚本）。
```

### 涉及软件

libtool 2.4.7

---

## E036: 平台字符串含空格导致构建路径错误

### 错误特征

```
No module named '_sysconfigdata__ohos_aarch64'
构建路径含空格
```

### 根因

`uname -r` 返回 `"HongMeng Kernel 1.11.0"`（含空格），Python 的 `get_platform()` 将其拼入路径，导致模块路径解析失败。

### 验证命令

```bash
python3 -c "import sysconfig; print(sysconfig.get_platform())"
```

### 解决方案

```python
# 修改 sysconfig.py / distutils/util.py
# 跳过 release 字段，使用 "ohos-aarch64" 作为平台标识
```

### 涉及软件

Python 3.9.0

---

## E037: /usr/bin/env 不存在导致 shebang 失败

### 错误特征

```
/usr/bin/env: bad interpreter: No such file or directory
```

### 根因

鸿蒙系统没有 `/usr/bin/env`，部分脚本使用 `#!/usr/bin/env sh` 的 shebang，导致直接执行失败。

### 验证命令

```bash
ls /usr/bin/env  # 文件不存在
```

### 解决方案

```bash
# 批量修复 shebang
sed -i 's|#!/usr/bin/env sh|#!/bin/sh|' file
sed -i 's|#!/usr/bin/env bash|#!/bin/bash|' file

# 安装后检查并修复所有脚本的 shebang
```

### 涉及软件

libtool 2.4.7 及通用

---

## E038: groff 宏文件缺失

### 错误特征

```
man man
# <standard input>:1: warning: macro 'g' not defined (diversion on)
# <standard input>:1: warning: macro 'safe' not defined (diversion on)
# <standard input>:1: warning: macro 'padj' not defined (diversion on)
```

### 根因

groff 1.23.0 相较于旧版本移除了 `g.tmac`（getopt 宏）、`safe.tmac`（安全子集宏）和 `padj.tmac`（段落调整宏）。man-db 的 man_db.conf 中 nroff 定义引用了这些已移除的宏。

| 宏 | 旧版 groff | groff 1.23.0 | man_db.conf 参数 |
|----|-----------|-------------|-----------------|
| g.tmac | ✅ 有 | ❌ 移除 | `-mg` |
| safe.tmac | ✅ 有 | ❌ 移除 | `-msafe` |
| padj.tmac | ✅ 有 | ❌ 移除 | `-mpadj` |
| s.tmac | ✅ 有 | ✅ 有 | `-ms` |
| mandoc.tmac | ✅ 有 | ✅ 有 | `-mandoc` |

### 解决方案

修改 man_db.conf 中的 nroff 定义，移除不兼容的宏参数：

```bash
# man_db.conf 中
# 修改前
DEFINE  nroff  groff -Tutf8 -mg -msafe -mpadj -mandoc

# 修改后（groff 1.23.0 兼容）
DEFINE  nroff  groff -Tutf8 -mandoc
```

### 涉及软件

man-db 2.13.1（搭配系统预装的 groff 1.23.0）

---

## E039: musl iconv 不支持 //IGNORE 后缀

### 错误特征

```
mandb: iconv_open ("UTF-8//IGNORE", "utf-8"): Invalid argument
mandb: iconv_open ("UTF-8//IGNORE", "iso-8859-1"): Invalid argument
```

### 根因

glibc 的 iconv 支持特殊后缀 `//IGNORE`（忽略不可转换字符）和 `//TRANSLIT`（音译不可转换字符），但 musl libc 的 iconv 实现不支持这些 glibc 扩展后缀。

| 特性 | glibc | musl libc (鸿蒙) |
|------|-------|------------------|
| 基本字符集转换 | ✅ | ✅ |
| `//IGNORE` 后缀 | ✅ | ❌ 不支持 |
| `//TRANSLIT` 后缀 | ✅ | ❌ 不支持 |
| `//WCHAR_T` 后缀 | ✅ | ❌ 不支持 |

### 影响范围

man-db 的 `manconv` 工具使用 `iconv_open("UTF-8//IGNORE", ...)` 进行字符编码转换，导致 mandb 的 whatis 解析全部失败。`apropos` 和 `whatis` 命令因此无法搜索手册页描述。**`man` 命令本身的手册页显示不受影响**。

### 解决方案

```c
// musl 兼容方案：去掉 //IGNORE 后缀
#ifdef __OHOS__
  // musl iconv 不支持 //IGNORE，使用标准编码名
  char *to_code = "UTF-8";
#else
  char *to_code = "UTF-8//IGNORE";
#endif
  iconv_t cd = iconv_open(to_code, from_code);
```

### 涉及软件

man-db 2.13.1

---

## E040: MAN_OWNER 空指针解引用段错误

### 错误特征

```
mandb
# (无输出，直接退出)
echo $?  # 139 = SIGSEGV
```

### 根因

man-db 源码中 `lib/security.c` 的 `get_man_owner()` 函数在 HarmonyOS 上找不到 `man` 系统用户时返回 NULL，但调用方（如 `src/mandb.c`）直接解引用返回值 `man_owner->pw_uid` 而未做 NULL 检查，导致段错误。

**问题链**：
```
configure --with-owner=man  (默认行为)
    ↓
config.h: #define MAN_OWNER "man"
    ↓
src/mandb.c 第 891 行（在 #ifdef MAN_OWNER 内）:
    struct passwd *man_owner = get_man_owner();
    // 未检查 NULL
    chown(catpath, man_owner->pw_uid, man_owner->pw_gid);
    //                              ^^^^^^^^^^^^^ 段错误!
```

### 解决方案

**方案 1（推荐）：在 config.h 中取消 MAN_OWNER 定义**

```bash
# 编译后修改 config.h
sed -i 's/^#define MAN_OWNER "man"/\/\* #undef MAN_OWNER \*\//' config.h
make clean && make
```

这是最彻底的方案，让整个权限管理代码路径不被编译，避免所有相关的 NULL 解引用风险。

**方案 2：补丁 security.c 返回 NULL + 调用方加 NULL 检查**

```c
// lib/security.c
struct passwd *man_owner = getpwnam(MAN_OWNER);
if (!man_owner) {
    debug("man user '%s' does not exist, skipping man page ownership", MAN_OWNER);
    return NULL;  // 而非 error(FAIL, ...)
}

// 调用方
struct passwd *man_owner = get_man_owner();
if (man_owner) {
    chown(catpath, man_owner->pw_uid, man_owner->pw_gid);
}
```

方案 2 需要修改多处调用方，不如方案 1 干净。

### 验证命令

```bash
# 检查 config.h 中的 MAN_OWNER 定义
grep MAN_OWNER config.h
# 应看到: /* #undef MAN_OWNER */

# 测试 mandb
mandb -C man_db.conf -c /path/to/man
echo $?  # 应为 0，而非 139
```

### 涉及软件

man-db 2.13.1

---

## E041: automake 版本不匹配触发重生成

### 错误特征

```
configure.ac: error: requires automake >= 1.17, but automake 1.16.5 is installed
# 或
Makefile.am: error: AM_INIT_AUTOMAKE called but too old
```

或者更隐蔽的情况：configure 成功但 make 过程中 autotools 检测到源码时间戳比生成的 Makefile.in 更新，触发重新生成，导致大量错误。

### 根因

某些上游 tarball 中的 `configure` 脚本是用较新版本的 automake 生成的，但 configure.ac 中声明的 automake 版本要求更高。在 VPATH 构建中，如果源码目录的时间戳被 touch 等操作更新，autotools 会尝试重新生成文件。

### 解决方案

**方案 1：使用 /bin/true 绕过 autotools 工具**

```bash
# 强制跳过 autotools 重生成
ACLOCAL="/bin/true" AUTOHEADER="/bin/true" AUTOMAKE="/bin/true" \
  ./configure --prefix=$HOME/usr/local
make -j1
```

这告诉 configure 跳过 aclocal、autoheader 和 automake 的调用。适用于源码中已包含正确生成的 Makefile.in 的情况。

**方案 2：VPATH 构建（推荐，避免时间戳问题）**

```bash
# 将源码放在一个目录，在另一个目录构建
mkdir -p $HOME/man-db-src    # 原始源码（只读）
mkdir -p $HOME/build-man-db  # 构建目录

# 在构建目录中运行 configure
cd $HOME/build-man-db
ACLOCAL="/bin/true" AUTOHEADER="/bin/true" AUTOMAKE="/bin/true" \
  ../man-db-src/configure --prefix=$HOME/usr/local
make -j1
```

VPATH 构建的好处：
1. 不触碰源码目录的时间戳
2. 构建产物与源码分离，方便清理
3. 可以同一份源码用于多个配置的构建

### 涉及软件

man-db 2.13.1

---

## E042: 扩展模块 RPATH 遗漏导致运行时库找不到

### 错误特征

```
import _gdbm  # ImportError
# 或：扩展模块在当前环境能用，但复制到其他机器后失败
```

运行时可能正常也可能失败，取决于 musl 动态链接器是否能通过调用者链的 RPATH 找到依赖库。

### 根因

打包可移植包时，只为主程序和主共享库设置了 RPATH，**遗漏了扩展模块**（`lib-dynload/*.so`）的 RPATH 设置。

扩展模块（如 `_gdbm.so`）如果 NEEDED 外部库（如 `libgdbm.so.6`），musl 动态链接器会沿调用者链搜索 RPATH——这在简单场景下能工作，但不稳健。如果用户系统上恰好有同名库，可能加载错误版本。

### 验证命令

```bash
# 检查扩展模块是否有 RPATH
PATCHELF=/data/service/hnp/bin/patchelf
for so in lib/python3.9/lib-dynload/*.so; do
    rpath=$($PATCHELF --print-rpath "$so" 2>/dev/null)
    if [ -z "$rpath" ]; then
        echo "❌ $(basename $so): RPATH 为空"
    fi
done

# 检查哪些扩展模块 NEEDED 外部库
for so in lib/python3.9/lib-dynload/*.so; do
    needed=$(llvm-readelf -d "$so" 2>/dev/null | grep NEEDED | \
        grep -v 'libc.so\|libm.so\|libdl.so\|libpthread.so\|libpython')
    if [ -n "$needed" ]; then
        echo "⚠️ $(basename $so): $needed"
    fi
done
```

### 解决方案

为扩展模块显式设置 RPATH：

```bash
# 扩展模块在 lib/python3.9/lib-dynload/ 下
# 需要向上找到 lib/ 和 lib/external/
EXT_RPATH='$ORIGIN:$ORIGIN/..:$ORIGIN/../external'

for so in "$PKGDIR/lib/python3.9/lib-dynload/"*.so; do
    $PATCHELF --set-rpath "$EXT_RPATH" "$so"
    # 然后执行签名三步流程
done
```

**RPATH 分级参考**（详见 `packaging.md` §3.2）：

| 文件类型 | 推荐 RPATH |
|----------|-----------|
| bin/ 可执行文件 | `$ORIGIN/../lib:$ORIGIN/../lib/external` |
| lib/libxxx.so 主共享库 | `$ORIGIN:$ORIGIN/external` |
| lib-dynload/*.so 扩展模块 | `$ORIGIN:$ORIGIN/..:$ORIGIN/../external` |
| lib/external/*.so 外部依赖 | `$ORIGIN` |

### 涉及软件

Python 3.9.0 可移植打包（通用经验，适用于所有含 C 扩展的解释型语言）

---

## E043: activate.sh 中 ${BASH_SOURCE} 在 HiShell 不可用

### 错误特征

```
source activate.sh
# 脚本执行但不报错，但环境变量未生效
# PYTHON_DIR 为空，后续的 PATH/LD_LIBRARY_PATH 设置全部指向错误路径
```

### 根因

鸿蒙 HiShell 的 `/bin/sh` 是 **toybox ash**，不支持 bash 特有的 `${BASH_SOURCE}` 变量。
脚本中使用 `$(dirname "${BASH_SOURCE[0]}")` 来获取脚本所在目录，但 `${BASH_SOURCE[0]}` 在 toybox ash 下为空。

### 验证命令

```bash
# 检查当前 shell
echo $SHELL  # /bin/sh
ls -la /bin/sh  # -> toybox

# 测试 BASH_SOURCE
echo "${BASH_SOURCE[0]}"  # 输出为空
```

### 解决方案

使用 POSIX 兼容的方式获取脚本目录：

```bash
# ❌ 不兼容 toybox ash
PYTHON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ✅ 兼容 toybox ash / bash / dash
PYTHON_DIR="$(cd "$(dirname "$0")" && pwd)"
```

**原理**：`$0` 在所有 POSIX shell 中都可用，包含调用脚本时使用的路径。

### 涉及软件

通用（所有为鸿蒙编写 shell 脚本时都需要注意）

---

## E044: 可移植包缺少 PYTHONHOME 导致标准库找不到

### 错误特征

```
python3.9
# Fatal Python error: init_sys_streams: can't initialize sys standard streams
# ModuleNotFoundError: No module named 'encodings'
```

### 根因

Python 使用 `PYTHONHOME` 环境变量定位标准库目录（`lib/python3.x/`）。如果不设置，Python 使用编译时硬编码的路径（如 `$HOME/usr/local`），当可移植包解压到其他位置时找不到标准库。

### 验证命令

```bash
# 检查编译时的前缀
python3.9 -c "import sys; print(sys.prefix, sys.exec_prefix)"
# 如果输出的是编译路径而非包解压路径，说明需要设置 PYTHONHOME
```

### 解决方案

在 activate.sh 中必须设置 `PYTHONHOME`：

```bash
PYTHON_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONHOME="$PYTHON_DIR"   # 必须设置！
export PATH="$PYTHON_DIR/bin:$PATH"
export LD_LIBRARY_PATH="$PYTHON_DIR/lib:$PYTHON_DIR/lib/external${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

**注意**：`PYTHONHOME` 同时影响 `sys.prefix` 和 `sys.exec_prefix`，确保标准库和平台相关文件都能被找到。

### 涉及软件

Python 3.9.0 可移植打包（Python 特有，但同类"解释器需要 HOME 变量"的模式可能也适用于 Perl、Ruby 等）

---

## E045: mmap RWX 被拒（W^X 策略）

### 错误特征

```
# ctypes 回调包装器创建失败
@ctypes.CFUNCTYPE(None, ctypes.c_voidp)
def myfree(ptr):
    pass
# MemoryError

# mmap 直接调用失败
mmap.mmap(-1, size, prot=mmap.PROT_READ|mmap.PROT_WRITE|mmap.PROT_EXEC)
# OSError: [Errno 22] Invalid argument
```

### 根因

HarmonyOS 内核强制 **W^X（Write XOR Execute）** 安全策略，禁止同时可写且可执行的内存映射。这在以下场景中会触发：

1. **ctypes CFUNCTYPE 回调包装器**：libffi 在创建回调 closure 时需要分配 RWX 内存页来存放动态生成的跳转代码
2. **JIT 编译器**（如 PyPy、numba）：需要将运行时生成的机器码写入可执行内存
3. **动态代码生成**：任何需要 mmap RWX 的场景

| 系统 | mmap RWX | ctypes 回调 |
|------|----------|------------|
| Linux | ✅ 允许 | ✅ 正常 |
| HarmonyOS | ❌ Invalid argument | ❌ MemoryError |

### 影响范围

| 影响程度 | 说明 |
|----------|------|
| 🔴 严重 | 所有使用 `@ctypes.CFUNCTYPE` 装饰器的代码都会 MemoryError |
| 🟡 中等 | `ctypes.CFUNCTYPE` 类型创建本身 OK，但包装器创建（传入函数）会失败 |
| 🟢 轻微 | 普通的 ctypes 函数调用（无回调）正常工作 |

### 验证命令

```python
import ctypes, mmap

# 测试 1：CFUNCTYPE 类型创建（应该成功）
t = ctypes.CFUNCTYPE(None, ctypes.c_voidp)
print("Type creation:", "OK")

# 测试 2：包装器创建（应该 MemoryError）
try:
    @t
    def f(ptr): pass
except MemoryError:
    print("Wrapper creation: MemoryError")

# 测试 3：mmap RWX（应该失败）
try:
    buf = mmap.mmap(-1, 4096, prot=mmap.PROT_READ|mmap.PROT_WRITE|mmap.PROT_EXEC)
except OSError as e:
    print(f"mmap RWX: {e}")
```

### 解决方案

**当前无法在 Python 层修复。** 需要在 libffi 层使用 RW→RX 分步映射：

```c
// 正确做法：先分配 RW，写入代码后改为 RX
void *buf = mmap(NULL, size, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANON, -1, 0);
memcpy(buf, code, code_size);
mprotect(buf, size, PROT_READ|PROT_EXEC);  // 去掉 W，加上 X
```

**临时绕过**：对于需要回调的场景，可以使用 `subprocess` 将数据传给外部进程处理，避免在进程内使用 ctypes 回调。

### 涉及软件

- Python 3.9.0（ctypes CFUNCTYPE 回调）
- 任何使用 ctypes 回调的第三方库（cffi、pycurl 等）
- **libffi**（ffi_closure_alloc/ffi_prep_closure_loc 在鸿蒙上返回 NULL）
- 任何依赖 libffi closure 的 C/C++ 软件

---

## E046: chmod() 完全不生效

### 错误特征

```python
import os, stat

os.chmod('/tmp/testfile', 0o000)
mode = os.stat('/tmp/testfile').st_mode
print(oct(stat.S_IMODE(mode)))  # 仍然是 0o660，chmod 未生效

os.access('/tmp/testfile', os.R_OK)  # True，仍然可读
```

### 根因

HarmonyOS 的 SELinux 或 HMDFS 文件系统忽略了 POSIX `chmod()` 调用。`chmod()` 系统调用返回成功（不报错），但文件权限实际上没有改变。

**影响链**：所有依赖 `chmod()` 创建受限权限文件的测试逻辑都会失效。

| 系统 | chmod 行为 | os.access 结果 |
|------|-----------|---------------|
| Linux | ✅ 实际修改权限 | 按 chmod 后的权限检查 |
| HarmonyOS | ❌ 返回成功但不修改 | 仍按原始权限检查 |

### 典型失败模式

```python
# test_httpservers 的测试逻辑
os.chmod(directory, 0o000)       # 期望：目录不可读
response = request('/path')       # 期望：404 Not Found
# 鸿蒙实际：目录仍可读 → 返回 200 OK → 断言失败

# test_argparse 的测试逻辑
os.chmod(file, 0o444)             # 期望：只读
parser.parse_args(['readonly'])    # 期望：ArgumentParserError
# 鸿蒙实际：文件仍可写 → 不报错 → 断言失败
```

### 验证命令

```python
import os, tempfile, stat
tmpf = tempfile.NamedTemporaryFile(delete=False)
tmpf.close()

os.chmod(tmpf.name, 0o000)
print("Before:", oct(stat.S_IMODE(os.stat(tmpf.name).st_mode)))
print("Readable:", os.access(tmpf.name, os.R_OK))
# 鸿蒙输出: Before: 0o660, Readable: True（chmod 无效）

os.unlink(tmpf.name)
```

### 解决方案

**无法在 Python 层修复。** 这是平台限制。

对于测试代码，可以跳过依赖 chmod 的测试：

```python
import os, sys

def skip_if_chmod_broken():
    """HarmonyOS: chmod() 不生效"""
    import tempfile
    tmpf = tempfile.NamedTemporaryFile(delete=False)
    tmpf.close()
    try:
        os.chmod(tmpf.name, 0o000)
        if os.access(tmpf.name, os.R_OK):
            os.unlink(tmpf.name)
            return True  # chmod broken
    except:
        pass
    finally:
        try: os.unlink(tmpf.name)
        except: pass
    return False

if skip_if_chmod_broken():
    raise unittest.SkipTest("chmod() not functional on this platform")
```

### 涉及软件

Python 3.9.0（test_argparse、test_httpservers 等至少 7 个测试）

---

## E047: 文件权限 other-read bit 被额外屏蔽

### 错误特征

```python
# test_dbm_dumb
AssertionError: 440 != 413

# test_uu
AssertionError: 432 != 292
```

### 根因

HarmonyOS 文件系统（HMDFS）在文件创建时会额外清除 "other read" 权限位（0o004），与 umask 设置无关。

| umask 设置 | 期望文件权限 | 实际文件权限 | 差异 |
|-----------|-------------|-------------|------|
| 0o022 | 0o644 | 0o640 | -0o004 |
| 0o002 | 0o664 | 0o660 | -0o004 |
| 0o077 | 0o600 | 0o600 | 无差异 |

**规律**：other-read（0o004）位始终被清除。当 umask 本身就屏蔽了该位时（如 0o077），没有额外影响。

### 验证命令

```python
import os, tempfile, stat

old = os.umask(0o022)
tmpf = tempfile.NamedTemporaryFile(delete=False)
tmpf.write(b'test')
tmpf.close()
mode = stat.S_IMODE(os.stat(tmpf.name).st_mode)
print(f"umask 022: got {oct(mode)}, expected {oct(0o644)}, diff {oct(0o644 - mode)}")
os.unlink(tmpf.name)
os.umask(old)
# 鸿蒙输出: umask 022: got 0o640, expected 0o644, diff 0o004
```

### 解决方案

**无法修复。** 文件系统行为差异。对于测试代码，建议放宽权限断言的容差：

```python
# 修改前
self.assertEqual(actual_mode, expected_mode)

# 修改后：允许 other-read 位差异
if sys.platform.startswith(('ohos', 'harmonyos')):
    expected_mode &= ~0o004  # HarmonyOS 额外清除 other-read
self.assertEqual(actual_mode, expected_mode)
```

### 涉及软件

Python 3.9.0（test_dbm_dumb、test_uu）

---

## E048: UDPLITE 协议不支持

### 错误特征

```python
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDPLITE)
# PermissionError: [Errno 13] Permission denied
```

### 根因

HarmonyOS 内核未启用 UDPLITE（UDP-Lite, RFC 3828）协议支持。UDPLITE 允许部分校验和覆盖，主要用于无线网络环境。

| 系统 | UDPLITE | IPPROTO_UDPLITE 值 |
|------|---------|-------------------|
| Linux | ✅ 支持 | 136 |
| HarmonyOS | ❌ 不支持 | 136（定义存在但内核不支持） |

### 影响范围

| 测试 | 影响 |
|------|------|
| test_socket | 36 个 UDPLITE 相关测试 error，其余 352 个通过 |

Python 的 `socket` 模块中 `IPPROTO_UDPLITE` 常量已定义（因为在头文件中），但内核不实际支持该协议。

### 验证命令

```python
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDPLITE)
    print("UDPLITE: OK")
    s.close()
except PermissionError:
    print("UDPLITE: not supported (PermissionError)")
except OSError as e:
    print(f"UDPLITE: {e}")
```

### 解决方案

**无法修复。** 内核不支持该协议。对于测试代码，跳过 UDPLITE 相关测试：

```python
import socket, sys

def skip_if_no_udplite():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDPLITE)
        s.close()
        return False
    except (PermissionError, OSError):
        return True

if skip_if_no_udplite():
    raise unittest.SkipTest("UDPLITE not supported on this platform")
```

### 涉及软件

Python 3.9.0（test_socket）

---

## E049: 脚本 shebang 硬编码绝对路径导致不可移植

### 错误特征

```bash
#!/data/service/hnp/bin/perl -w
# 或
#!/usr/local/bin/python3
```

脚本在构建机器上能运行，但换一台 perl/python 路径不同的机器就全部失效。

### 根因

构建脚本（如 automake 的 `gen-all.pl`）在生成输出脚本时，将解释器路径硬编码到 shebang 中：

```perl
# gen-all.pl 中的问题代码（修复前）
my $perl_path = '/data/service/hnp/bin/perl';          # ❌ 硬编码平台特定路径
s|^#!.*perl.*|#!$perl_path -w|;                        # ❌ 写死到输出脚本
```

生成的 `bin/automake`、`bin/aclocal` 等脚本第一行变成：
```
#!/data/service/hnp/bin/perl -w    # 仅在当前构建环境有效
```

### 影响范围

| 场景 | 影响 |
|------|------|
| 换机部署 | 解释器路径不同 → 所有脚本无法执行 |
| 多 Perl 版本共存 | 绑定特定版本 → 无法切换 |
| 可移植包分发 | 接收方无该路径 → 包不可用 |
| `env + 参数` | `#!/bin/env perl -w` → env 把 `perl -w` 当文件名查找 |

### 正确做法

使用 `/bin/env` 作为中间层，由 PATH 查找解释器：

```bash
# ✅ 正确的 shebang（可移植）
#!/bin/env perl
#!/bin/env python3
#!/bin/env bash
```

**注意**：`/bin/env` 不支持传递参数给解释器。以下写法是错误的：

```bash
# ❌ 错误：-w 会被 env 当作文件名
#!/bin/env perl -w

# ✅ 正确：用代码内部启用 warnings
#!/bin/env perl
# 脚本体中：
use warnings;    # Perl
# 或 set -o nounset 等  # Shell
```

### 验证命令

```bash
# 检查已安装脚本的 shebang 是否可移植
head -1 $PREFIX/bin/*
# 应看到 #!/bin/env xxx 而非 #!/xxx/path/xxx
```

### 通用规则

> **所有构建系统生成的脚本、以及手动编写的安装/配置脚本，shebang 必须使用 `/bin/env` 格式。**
> 硬编码解释器路径是可移植性头号杀手。

### 涉及软件

automake 1.16.5（gen-all.pl 生成的 automake/aclocal 脚本）
通用（所有生成脚本或编写 shell/perl/python 脚本的场景）

---
*属于 [error-patterns.md](./error-patterns.md) 的模块化子集*
