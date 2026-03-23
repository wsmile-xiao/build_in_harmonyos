# 鸿蒙编译常见错误模式库

本文档记录在鸿蒙系统编译软件时常见的错误模式及其解决方案。

## 错误模式索引

| 编号 | 错误类型 | 关键词 | 严重程度 |
|------|----------|--------|----------|
| [E001](#e001-找不到编译器) | 工具链 | cc: command not found | 🔴 阻塞 |
| [E002](#e002-临时目录不可写) | 环境 | cannot create temporary directory | 🔴 阻塞 |
| [E003](#e003-找不到-pthread) | 链接 | undefined reference to pthread | 🟡 中等 |
| [E004](#e004-符号找不到-musl-bind_now) | 链接 | symbol not found | 🔴 阻塞 |
| [E005](#e005-静态库链接共享库失败) | 编译 | recompile with -fPIC | 🟡 中等 |
| [E006](#e006-openssl-bad_signature) | SSL | BAD_SIGNATURE | 🔴 阻塞 |
| [E007](#e007-configguess-无法识别系统) | 配置 | cannot guess build type | 🟡 中等 |
| [E008](#e008-fstat-返回-eacces) | 系统调用 | Permission denied | 🟡 中等 |
| [E009](#e009-selinux-域转换限制) | SELinux | exit code 1, 无输出 | 🔴 阻塞 |
| [E010](#e010-toybox-兼容性问题) | 工具 | sed/expr 异常 | 🟡 中等 |
| [E011](#e011-__ohos__-未定义) | 编译 | __OHOS__ is not defined | 🟡 中等 |
| [E012](#e012-找不到-llvm-ar) | 工具链 | ar: command not found | 🔴 阻塞 |
| [E013](#e013-动态链接错误) | 链接 | undefined reference to dlopen | 🟡 中等 |
| [E014](#e014-系统调用不可用) | 系统调用 | undefined reference to syslog | 🟡 中等 |
| [E015](#e015-找不到头文件) | 编译 | sys/socket.h: No such file | 🟡 中等 |
| [E016](#e016-汇编代码错误) | 编译 | assembler error: unknown instruction | 🟡 中等 |
| [E017](#e017-github-下载慢) | 网络 | wget: connect: Operation timed out | 🟡 中等 |
| [E018](#e018-软链接创建失败) | SELinux | cannot create symbolic link | 🟡 中等 |
| [E019](#e019-库加载失败) | 运行时 | error while loading shared libraries | 🔴 阻塞 |
| [E020](#e020-musl-file-结构差异) | 兼容性 | incomplete definition of type FILE | 🟡 中等 |
| [E021](#e021-buildexeext-异常) | 配置 | BUILDEXEEXT=.exe | 🟡 中等 |
| [E022](#e022-posix-信号量差异) | 系统调用 | sem_unlink: No such file | 🟢 轻微 |
| [E023](#e023-locale-支持不完整) | 系统 | locale test FAIL | 🟢 轻微 |
| [E024](#e024-unix-domain-socket-受限) | 系统 | socket.bind: Operation not permitted | 🟡 中等 |
| [E025](#e025-can-socket-宏未定义) | 编译 | CAN_RAW_FD_FRAMES undeclared | 🟡 中等 |
| [E026](#e026-线程局部存储tls-差异) | 兼容性 | thread-local storage error | 🟡 中等 |

---

## E001: 找不到编译器

### 错误特征

```
configure: error: C compiler cannot create executables
cc: command not found
```

### 根因

PATH 中没有 `cc` 软链接，只有 `clang`。

### 解决方案

```bash
# 创建软链接
sudo ln -sf /data/service/hnp/bin/clang /usr/local/bin/cc
sudo ln -sf /data/service/hnp/bin/clang++ /usr/local/bin/c++

# 或设置环境变量
export CC=clang
export CXX=clang++
```

---

## E002: 临时目录不可写

### 错误特征

```
configure: error: cannot create a temporary directory in /tmp
```

### 根因

鸿蒙系统的 `/tmp` 是只读的（erofs 挂载）。

### 解决方案

```bash
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR
```

---

## E003: 找不到 pthread

### 错误特征

```
undefined reference to 'pthread_create'
```

### 根因

未链接 pthread 库。

### 解决方案

```bash
# 方案1：添加 -pthread
export CFLAGS="-pthread $CFLAGS"

# 方案2：添加 -lpthread
export LDFLAGS="-lpthread $LDFLAGS"
```

---

## E004: 符号找不到（musl BIND_NOW）

### 错误特征

```
ImportError: symbol not found: _PyType_Name
undefined symbol: xxx
```

### 根因

musl 默认启用 BIND_NOW，扩展模块需要在加载时解析所有符号。

**问题链**：
```
musl 默认启用 BIND_NOW 标志
    ↓
dlopen() 加载 .so 时要求所有符号必须可解析
    ↓
扩展模块的 NEEDED 只有 libc.so（无 libpython）
    ↓
Python API 符号无法解析 → ImportError
```

### 验证命令

```bash
# 查看扩展模块动态段
llvm-readelf -d module.so | grep -E "NEEDED|BIND"

# 错误输出:
#   NEEDED: libc.so           # 只有 libc
#   FLAGS: BIND_NOW           # musl 默认

# 正确输出:
#   NEEDED: libpython3.9.so.1.0   # 有 libpython
#   NEEDED: libc.so
```

### 解决方案

修改 `LDSHARED`，添加主库链接：

```makefile
# 修改前
LDSHARED= $(CC) -shared $(PY_LDFLAGS)

# 修改后
LDSHARED= $(CC) -shared $(PY_LDFLAGS) -L. -lpython$(LDVERSION)
```

**⚠️ 循环依赖陷阱**：`BLDSHARED`（构建 libpython.so）不能包含 `-lpython`，否则会循环依赖。

**适用范围**：Python、Perl、Ruby 等插件系统。

---

## E005: 静态库链接共享库失败

### 错误特征

```
relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'xxx'; recompile with -fPIC
```

### 根因

静态库编译时未使用 `-fPIC`，当链接到共享库时会报错。

### 解决方案

```bash
# 重新编译静态库，添加 -fPIC
export CFLAGS="-fPIC -O2"
./configure --prefix=$HOME/usr/local
make clean && make && make install

# 临时方案：移除静态库，使用共享库
mv $HOME/usr/local/lib/libxxx.a $HOME/usr/local/lib/libxxx.a.bak
```

---

## E006: OpenSSL BAD_SIGNATURE

### 错误特征

```
ssl.SSLError: [SSL: BAD_SIGNATURE] bad signature
RSA_verify_PKCS1_PSS_mgf1:last octet invalid
tls_process_cert_verify:bad signature
```

### 根因

OpenSSL 的 ARM64 汇编优化代码在 RSA-PSS 签名验证时有 bug。

### 排查

```bash
# 测试 OpenSSL 连接
openssl s_client -connect pypi.org:443 </dev/null
# 看到: RSA_verify_PKCS1_PSS_mgf1:last octet invalid

# 检查编译配置
openssl version -f
# 看到: OPENSSL_BN_ASM_MONT SHA1_ASM ... (表示启用了汇编优化)
```

### 解决方案

使用 `no-asm` 禁用汇编优化：

```bash
./Configure --prefix=$HOME/usr/local --openssldir=$HOME/usr/local/ssl no-asm
make && make install
```

**影响**：性能略慢 10-20%，但稳定性大幅提升。

---

## E007: config.guess 无法识别系统

### 错误特征

```
configure: error: cannot guess build type
checking build system type... Invalid configuration
```

### 根因

`config.guess` 未添加 HarmonyOS 系统检测。

### 解决方案

修改 `config.guess` 添加检测：

```bash
# 位置1：LIBC 检测
#if defined(__ANDROID__)
LIBC=android
#elif defined(__OHOS__)
LIBC=ohos
#else

# 位置2：系统识别
case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in
    *:HarmonyOS:*:*)
        GUESS=$UNAME_MACHINE-unknown-linux-ohos
        ;;
```

**详细指南**：`knowledge/autotools-patterns.md`

---

## E008: fstat 返回 EACCES

### 错误特征

```
cat: standard output: Permission denied
fstat(STDOUT_FILENO) failed: errno=13, Permission denied
```

### 根因

鸿蒙系统限制对管道/终端/套接字的 `fstat()` 调用。

| 文件描述符类型 | fstat() 结果 | write() 结果 |
|---------------|-------------|--------------|
| 普通文件 | ✅ 成功 | ✅ 成功 |
| 管道 | ❌ EACCES | ✅ 成功 |
| 终端 | ❌ EACCES | ✅ 成功 |
| 套接字 | ❌ EACCES | ✅ 成功 |

### 解决方案

```c
#ifdef __OHOS__
static inline int
ohos_fstat_compat (int fd, struct stat *st)
{
  if (fstat (fd, st) == 0)
    return 0;
  if (errno == EACCES || errno == EPERM)
    {
      memset (st, 0, sizeof (*st));
      st->st_blksize = 4096;
      st->st_mode = S_IFIFO;
      return 0;
    }
  return -1;
}
#define OHOS_FSTAT(fd, st) ohos_fstat_compat ((fd), (st))
#else
#define OHOS_FSTAT(fd, st) fstat ((fd), (st))
#endif
```

**参考补丁**：`archives/c/coreutils/9.10/patches/0002-fix-fstat-for-harmonyos.patch`

---

## E009: SELinux 域转换限制

### 错误特征

```python
import subprocess
subprocess.run(['clang', '--version'])  # returncode: 1, 无输出
os.system("clang --version")            # exit code: 1
```

### 根因

SELinux 域转换：`hishell_hap:s0` → `adhoc_bin:s0`，后者无法执行 `hnp_file` 类型的 SDK 工具。

```
Shell 进程 (hishell_hap:s0)
    │
    └─ 执行用户二进制（如 Python）
        │
        └─ 域转换为 adhoc_bin:s0
            │
            └─ 无法执行 hnp_file 类型文件（SDK 工具）
```

### 解决方案

使用管道语法绕过：

```python
# 失败
os.system("clang --version")  # exit code: 1

# 成功
os.system("clang --version | cat")  # exit code: 0
os.system("clang --version 2>&1 | cat")  # 推荐
```

**原理**：管道强制 shell 创建有权限的子进程。

---

## E010: toybox 兼容性问题

### 错误特征

```
# Makefile 中出现乱码
# sed 进程卡住
# config.status 生成的 Makefile 异常
```

### 根因

toybox 的 sed/expr 对复杂脚本支持不完整：
- 不支持复杂的多行命令块 `{...}`
- 不支持分支命令 `:label` 和 `b`、`t` 跳转
- `expr` 不支持复合正则表达式 `\|` 操作符

### 排查

```bash
# 对比测试
expr X"ncurses/Makefile" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
# toybox 输出: 乱码
# GNU expr 输出: ncurses
```

### 解决方案

编译安装 GNU 工具：

```bash
# GNU coreutils (包含 expr)
# 参考: archives/c/coreutils/9.10/

# GNU sed
# 参考: archives/s/sed/4.9/

export PATH=$HOME/usr/local/bin:$PATH
```

---

## E011: __OHOS__ 未定义

### 错误特征

```
error: '__OHOS__' is not defined
```

### 根因

代码中使用了 `__OHOS__` 宏，但编译器未定义。

### 验证

```bash
clang -dM -E - < /dev/null | grep OHOS
# 应该看到:
# #define __OHOS__ 1
# #define __OHOS_FAMILY__ 1
```

### 解决方案

```bash
# 方案1：手动添加
export CFLAGS="-D__OHOS__ $CFLAGS"

# 方案2：检查 clang 版本（旧版本可能未定义）
clang --version
```

---

## E012: 找不到 llvm-ar

### 错误特征

```
ar: command not found
ar: invalid option -- 'T'
```

### 根因

使用了 GNU ar 而非 LLVM ar。鸿蒙使用 LLVM 工具链。

### 解决方案

```bash
export AR=llvm-ar
export RANLIB=llvm-ranlib
export NM=llvm-nm
export STRIP=llvm-strip
```

---

## E013: 动态链接错误

### 错误特征

```
undefined reference to 'dlopen'
undefined reference to 'dlsym'
```

### 根因

未链接 dl 库。

### 解决方案

```bash
# 方案1：添加 -ldl
export LDFLAGS="-ldl $LDFLAGS"

# 方案2：在 configure 中设置
./configure ... LDFLAGS="-ldl"
```

---

## E014: 系统调用不可用

### 错误特征

```
undefined reference to 'syslog'
undefined reference to 'getrandom'
```

### 根因

鸿蒙系统不支持某些系统调用。

### 解决方案

```bash
# 方案1：禁用相关功能
export CFLAGS="-DNO_SYSLOG $CFLAGS"

# 方案2：提供替代实现
# 参考具体软件的 README.md
```

---

## E015: 找不到头文件

### 错误特征

```
fatal error: sys/socket.h: No such file
fatal error: netinet/in.h: No such file
```

### 根因

未指定系统头文件路径。

### 解决方案

```bash
# 添加头文件路径
export CPPFLAGS="-I$HOME/usr/local/include $CPPFLAGS"
export C_INCLUDE_PATH=$HOME/usr/local/include:$C_INCLUDE_PATH

# 交叉编译时指定 sysroot
export CFLAGS="--sysroot=$SYSROOT $CFLAGS"
```

---

## E016: 汇编代码错误

### 错误特征

```
assembler error: unknown instruction
Error: selected processor does not support ARM mode
```

### 根因

汇编代码与架构不匹配。

### 解决方案

```bash
# 方案1：禁用汇编优化
./configure ... --disable-asm
# 或 OpenSSL
./Configure ... no-asm

# 方案2：检查目标架构
./configure --host=aarch64-linux-ohos
```

---

## E017: GitHub 下载慢

### 错误特征

```
wget: connect: Operation timed out
curl: (28) Connection timed out
```

### 根因

GitHub 国内访问网络不稳定。

### 解决方案

```bash
# 方案1：使用国内镜像
# gitcode.cn / gitee.com 镜像

# 方案2：使用加速链接
wget https://ghfast.top/https://github.com/xxx/xxx.tar.gz

# 方案3：使用代理
export https_proxy=http://proxy:port
```

---

## E018: 软链接创建失败

### 错误特征

```
ln: cannot create symbolic link 'xxx': Permission denied
ln -sf 创建带随机后缀的乱码文件
软链接存在但执行时报 "No such file or directory"
```

### 根因

SELinux 策略限制用户进程创建和访问软链接。

### 诊断步骤

```bash
# 1. 检查软链接是否存在
ls -la /path/to/link

# 2. 检查软链接目标
readlink /path/to/link

# 3. 测试软链接是否可执行
/path/to/link --version
```

### 解决方案

**方案1：创建 wrapper 脚本（推荐）**

```bash
# 创建 wrapper 脚本
cat > $HOME/usr/local/bin/cc << 'EOF'
#!/bin/sh
exec /data/service/hnp/bin/clang "$@"
EOF
chmod +x $HOME/usr/local/bin/cc
```

**方案2：使用 cp 复制文件**

```bash
# 复制真实可执行文件
cp $(readlink -f /path/to/target) /path/to/link
```

### 软链接处理标准流程

```bash
# 1. 尝试创建软链接
ln -sf /source/file /path/to/link

# 2. 验证软链接是否可用
if [ -L /path/to/link ] && /path/to/link --version >/dev/null 2>&1; then
    echo "✅ 软链接可用"
else
    echo "❌ 软链接不可用，使用规避方式"
    
    # 使用 wrapper 脚本
    cat > /path/to/link << EOF
#!/bin/sh
exec /source/file "\$@"
EOF
    chmod +x /path/to/link
fi
```

---

## E019: 库加载失败

### 错误特征

```
error while loading shared libraries: libxxx.so: cannot open shared object file
```

### 根因

动态链接器找不到共享库。

### 解决方案

```bash
# 方案1：设置 LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH

# 方案2：编译时使用 rpath
export LDFLAGS="-Wl,-rpath,$HOME/usr/local/lib $LDFLAGS"

# 方案3：检查库文件是否存在
ls -la $HOME/usr/local/lib/libxxx.so*
llvm-readelf -d /path/to/binary | grep NEEDED
```

---

## E020: musl FILE 结构差异

### 错误特征

```
error: incomplete definition of type 'struct _IO_FILE'
error: '_IO_read_ptr' undeclared
```

### 根因

musl 的 FILE 是不透明类型，无法访问内部字段。

| 系统 | FILE 结构 |
|------|-----------|
| glibc | 可访问 `_IO_read_ptr` 等字段 |
| musl | 不透明类型，内部结构不可访问 |

### 解决方案

```c
#if defined(__OHOS__) || (defined(__linux__) && !defined(__GLIBC__))
  // musl 兼容代码
  // 使用公开 API 或安全回退
  return 0;  // 安全回退
#endif
```

**参考实现**：`archives/c/coreutils/9.10/`

---

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

## 错误诊断流程

```
错误发生
    │
    ├─► 收集错误信息
    │       - 完整错误输出
    │       - 编译日志
    │       - 环境变量
    │
    ├─► 分析错误类型
    │       │
    │       ├─► 编译错误 → 检查编译器/标志/头文件
    │       ├─► 链接错误 → 检查库依赖
    │       ├─► 运行时错误 → 检查系统限制
    │       └─► 配置错误 → 检查构建系统适配
    │
    ├─► 搜索错误模式库
    │       - 本文档
    │       - archives/{软件}/README.md
    │
    └─► 记录解决方案
            - 更新 manifest.yaml
            - 更新 README.md
```

---

## 快速诊断命令

```bash
# 系统信息
uname -a

# 编译器
clang --version
which clang llvm-ar

# 环境变量
echo $CC $CFLAGS $LDFLAGS

# 库依赖
llvm-readelf -d /path/to/binary | grep NEEDED

# 符号表
llvm-nm /path/to/library

# SELinux 上下文
ls -Z /path/to/file
```

---

*文档版本: 2.0*  
*最后更新: 2024-03-22*