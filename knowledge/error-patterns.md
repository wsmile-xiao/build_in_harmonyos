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
| [E027](#e027-libintl_gettext-链接失败) | 链接 | libintl_gettext undefined symbol | 🟡 中等 |
| [E028](#e028-用户编译的共享库与系统库冲突) | 运行时 | 共享库覆盖系统库导致终端崩溃 | 🔴 阻塞 |
| [E029](#e029-bash-内置-malloc-与-musl-不兼容) | 运行时 | bash-malloc 与 musl 不兼容 | 🟡 中等 |
| [E030](#e030-鸿蒙无-32-位兼容层导致-strace-编译失败) | 配置 | m32 personality 检测失败 | 🟡 中等 |
| [E031](#e031-proc-文件系统-selinux-访问限制) | 运行时 | /proc/stat Permission denied | 🔴 阻塞 |
| [E032](#e032-_gnu_source-未定义导致-dirent-api-不完整) | 编译 | unknown type name DIR | 🟡 中等 |
| [E033](#e033-ncurses-宽字符函数需要-_xopen_source_extended) | 编译 | unknown type name cchar_t | 🟡 中等 |
| [E034](#e034-系统缺少-ca-证书包) | 运行时 | unable to load client CA certificates | 🟡 中等 |
| [E035](#e035-libtoolize-shell-函数加载失败) | 工具链 | func_add_hook inaccessible or not found | 🟢 轻微 |
| [E036](#e036-平台字符串含空格导致构建路径错误) | 配置 | get_platform 路径含空格 | 🟡 中等 |
| [E037](#e037-usrbinenv-不存在导致-shebang-失败) | 环境 | /usr/bin/env bad interpreter | 🟡 中等 |
| [E038](#e038-groff-宏文件缺失) | 运行时 | cannot find macro file | 🟡 中等 |
| [E039](#e039-musl-iconv-不支持-ignore-后缀) | 兼容性 | iconv_open Invalid argument | 🟡 中等 |
| [E040](#e040-man_owner-空指针解引用段错误) | 运行时 | SIGSEGV in mandb | 🔴 阻塞 |
| [E041](#e041-automake-版本不匹配触发重生成) | 构建 | requires automake >= x.y | 🟡 中等 |

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

*文档版本: 2.1*  
*最后更新: 2026-03-23*