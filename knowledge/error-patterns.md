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
| [E042](#e042-扩展模块-rpath-遗漏导致运行时库找不到) | 打包 | ImportError: cannot open shared object file | 🔴 阻塞 |
| [E043](#e043-activatesh-中-bash_source-在-hishell-不可用) | 脚本 | 环境变量未设置（脚本静默失败） | 🟡 中等 |
| [E044](#e044-可移植包缺少-pythonhome-导致标准库找不到) | 运行时 | ModuleNotFoundError: No module named 'encodings' | 🔴 阻塞 |
| [E045](#e045-mmap-rwx-被拒w^x-策略) | 系统调用 | mmap: Invalid argument, CFUNCTYPE MemoryError | ✅ 已解决 |
| [E046](#e046-chmod-完全不生效) | SELinux/FS | chmod: Permission denied, st_mode unchanged | 🟡 中等 |
| [E047](#e047-文件权限-other-read-被额外屏蔽) | FS | st_mode: missing 0o004 bit | 🟢 轻微 |
| [E048](#e048-udplite-协议不支持) | 内核 | IPPROTO_UDPLITE: Permission denied | 🟢 轻微 |
| [E049](#e049-find_library-崩溃ldconfig-不存在) | 系统调用 | find_library, SubprocessError, ldconfig | 🟡 中等 |
| [E050](#e050-hmdfs-符号链接不可跟踪导致链接器找不到库) | FS/链接 | unable to find library, symlink | 🔴 阻塞 |
| [E051](#e051-未实现-syscall-触发-sigsys-导致进程崩溃) | 内核/信号 | SIGSYS, setreuid, setregid, chroot, clock_settime, core dump, exit 159 | 🔴 阻塞 |
| [E052](#e052-rpath-缺失导致子进程找不到-libpython) | 构建/RPATH | subprocess exit 127, libpython3.9.so not found, LD_LIBRARY_PATH | 🔴 阻塞 |
| [E053](#e053-cc1plus-不可用必须使用-clang) | 工具链 | cc1plus: error, CXX compiler cannot create executables | 🔴 阻塞 |
| [E054](#e054-外来二进制首次执行被安全确认弹窗阻止) | 安全机制 | Permission denied, 首次执行后消失, make check 误判 | 🟡 中等 |

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
lseek: Permission denied (管道/终端输入时)
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

**lseek() 修复模板**（同样受此限制）：
```c
if (lseek(fd, offset, whence) < 0) {
#ifdef __OHOS__
    if (errno == EACCES || errno == EPERM)
        return -1;  /* 不可 seek，静默返回 */
#endif
    error(0, errno, "%s", filename);
    return -1;
}
```

**参考补丁**：`archives/c/coreutils/9.10/patches/`

**相关知识**：[harmonyos-specifics.md §9](harmonyos-specifics.md#9-fstat-和-lseek-对非文件-fd-的限制)

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
rm -f /path/to/link && ln -s /source/file /path/to/link

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

## E049: find_library 崩溃（ldconfig 不存在）

### 错误特征

```python
from ctypes.util import find_library
find_library("c")
# SubprocessError: Command '('/sbin/ldconfig', '-p')' returned non-zero exit status 127.
```

### 根因

HarmonyOS 没有 `/sbin/ldconfig`（Linux 标准的共享库缓存管理工具）。`ctypes.util.find_library()` 内部调用 `_findSoname_ldconfig()` 时，直接执行 `ldconfig -p` 命令，因命令不存在而触发 `SubprocessError`。

**问题链**：
```
ctypes.util.find_library(name)
    ↓
_findSoname_ldconfig(name, True)
    ↓
subprocess.run(['/sbin/ldconfig', '-p'], ...)
    ↓
ldconfig 不存在 → FileNotFoundError → SubprocessError
```

### 影响范围

| 影响程度 | 说明 |
|----------|------|
| 🔴 严重 | 所有调用 `find_library()` 的代码直接崩溃（SubprocessError） |
| 🟡 中等 | 返回 `None` 本身是合法行为（表示找不到库），崩溃才是问题 |

**受影响的三方库**：

| 三方库 | 影响场景 |
|--------|---------|
| cffi | `ffi.dlopen()` 内部调用 find_library 查找共享库 |
| trio | 调用 find_library 进行 DNS 解析器发现 |
| Django GIS | Spatialite 库查找依赖 find_library |
| Sphinx | 文档构建工具的部分扩展依赖 find_library |

### 验证命令

```python
from ctypes.util import find_library

# 修复前：SubprocessError
# find_library("c") → SubprocessError: Command '('/sbin/ldconfig', '-p')' returned non-zero exit status 127.

# 修复后（补丁 0022）：安全返回 None
# find_library("c") → None
```

### 解决方案

**补丁 0022**（Python 3.9.0）：在 `Lib/ctypes/util.py` 的 `_findSoname_ldconfig()` 函数头部跳过鸿蒙平台：

```python
# Lib/ctypes/util.py _findSoname_ldconfig() 函数
import sys

def _findSoname_ldconfig(name, is64):
    # HarmonyOS has no /sbin/ldconfig, skip to avoid SubprocessError
    if sys.platform.startswith(('ohos', 'harmonyos')):
        return None
    # ... original code ...
```

修复后 `find_library()` 安全返回 `None`（表示找不到共享库），与无 ldconfig 的 Linux 系统行为一致。

### 涉及软件

Python 3.9.0（补丁 0022）、cffi、trio、Django、Sphinx

---

## E050: HMDFS 符号链接不可跟踪导致链接器找不到库

### 错误特征

```
ld.lld: error: unable to find library -lpython3.9
pip install xxx  →  "error: command 'clang' failed with exit code 1"
```

### 根因

HMDFS 文件系统不正常跟踪符号链接。`os.path.exists()` 对符号链接返回 `False`，动态链接器（ld.lld）通过符号链接搜索库文件时也无法找到目标。

```
make install 创建:
  libpython3.9.so → libpython3.9.so.1.0  (符号链接)

Python 进程中:
  os.path.exists("libpython3.9.so")      → False  (符号链接不可见)
  os.path.exists("libpython3.9.so.1.0")  → True   (真实文件可见)

链接器搜索:
  -L/usr/local/lib -lpython3.9
    → 找 libpython3.9.so → 符号链接 → 无法解析 → "unable to find library"
```

### 影响范围

- `pip install` 编译所有 C 扩展包时链接失败
- 任何通过 `-l` 链接符号链接 `.so` 的操作都受影响

### 验证命令

```python
import os
symlink = '/usr/local/lib/libpython3.9.so'
real = '/usr/local/lib/libpython3.9.so.1.0'
print(f'symlink exists: {os.path.exists(symlink)}')  # False
print(f'real file exists: {os.path.exists(real)}')    # True
```

### 解决方案

**用文件副本替代符号链接**：

```bash
# 删除符号链接
rm /usr/local/lib/libpython3.9.so
# 复制真实文件
cp /usr/local/lib/libpython3.9.so.1.0 /usr/local/lib/libpython3.9.so
```

对于 Python 的 `make install`，补丁 0024 将 `$(LN_FORCE)` 改为 `$(HARDLINK)`（鸿蒙上为 `cp -p`）：

```makefile
# Makefile.pre.in sharedinstall
# 修改前：
(cd $(DESTDIR)$(LIBDIR); rm -f $(LDLIBRARY); $(LN_FORCE) $(INSTSONAME) $(LDLIBRARY))
# 修改后：
(cd $(DESTDIR)$(LIBDIR); rm -f $(LDLIBRARY); $(HARDLINK) $(INSTSONAME) $(LDLIBRARY))
```

### 代价

额外占用约 10MB 磁盘空间（共享库的副本）。

### 涉及软件

Python 3.9.0（补丁 0024）、任何使用 `make install` + 符号链接分发共享库的 C/C++ 项目

---

## E053: cc1plus 不可用，必须使用 clang++

### 错误特征

```
cc1plus: error: unrecognized command-line option '-Wno-deprecated-register'
CXX compiler cannot create executables
configure: error: C++ compiler cannot create executables
```

或在软件内部调用 C++ 编译器时失败，例如 Python 3.9.0 编译 `_ctypes` 模块：

```
cc1plus: error: unrecognized option '-Wno-unused-result'
```

### 根因

鸿蒙 SDK 工具链**不提供 `cc1plus`**（GCC 的 C++ 编译器前端）。鸿蒙使用 LLVM/Clang 工具链，
`clang++` 是 C++ 编译器，但部分 autotools 项目的 configure 脚本或 Makefile 硬编码调用 `cc1plus`，
或者 configure 的 C++ 编译器检测逻辑在 clang++ 上误判。

**问题链**：
```
configure 或 Makefile 调用 C++ 编译器
    ↓
默认使用 g++ 或检测到 cc1plus → 不存在 → 失败
    ↓
或 clang++ 被检测为 C++ 编译器但编译参数不兼容 → 编译器报错
```

### 验证命令

```bash
# 确认 cc1plus 不存在
which cc1plus  # 不存在

# 确认 clang++ 可用
which clang++  # /data/service/hnp/bin/clang++
clang++ --version
```

### 解决方案

**方案 1：显式指定 C++ 编译器为 clang++**

```bash
export CXX=clang++
./configure --prefix=$HOME/usr/local CXX=clang++
```

**方案 2：确保 CXX 环境变量在 configure 之前设置**

```bash
export CC=clang
export CXX=clang++
# 确保 CXX 被正确检测
./configure --prefix=$HOME/usr/local
grep "CXX" config.log | head -5
```

**方案 3：如果 Makefile 硬编码了 cc1plus 调用**

```bash
# 搜索硬编码的 cc1plus
grep -rn 'cc1plus' Makefile* configure.ac
# 替换为 clang++
sed -i 's/cc1plus/clang++/g' Makefile*
```

### 影响范围

所有使用 C++ 代码且 configure 脚本不正确检测 C++ 编译器的 autotools 项目。

### 涉及软件

Python 3.9.0（`_ctypes` 模块编译）、其他包含 C++ 代码的 autotools 项目

### 相关知识

- [error-patterns.md E012](#e012-找不到-llvm-ar) — LLVM 工具链配置
- [build-systems.md §3](build-systems.md#3-autotools-适配) — Autotools 适配策略

> 来源：`archives/p/python/3.9.0/manifest.yaml`

---

## E054: 外来二进制首次执行被安全确认弹窗阻止

### 错误特征

- 编译产物在 `make install` 后 Permission denied
- `make check` 中测试用例全部失败（误判为功能问题）
- 首次手动执行后问题消失

### 根因

鸿蒙安全机制要求用户确认非系统预装二进制的执行权限。

### 修复方案

1. `make install` 后手动执行一次二进制触发确认
2. 批量触发：`find $PREFIX/bin -type f -exec {} --version \;`
3. `make check` 前确保所有产物已完成确认

### 参考档案

`archives/c/coreutils/9.10/`

### 知识层级

L1 平台真理

### 相关章节

[harmonyos-specifics.md §18](harmonyos-specifics.md#18-外来二进制首次执行确认弹窗)

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

## E051: 未实现 syscall 触发 SIGSYS 导致进程崩溃

### 错误特征

- 进程意外退出，无错误信息输出
- Exit code 159（128 + 31 = SIGSYS）
- 可能产生 core dump
- Python: `OSError` 或直接 `killed`，无 traceback

### 触发条件

调用鸿蒙内核未实现的 syscall，已确认的包括：
- `setreuid()` / `setregid()` — **SIGSYS 不可捕获，进程直接终止**
- `chroot()` — SIGSYS 可捕获但返回垃圾值
- `clock_settime()` — SIGSYS 可捕获但 errno 不确定

### 根因分析

鸿蒙内核对未实现的 syscall 发送 SIGSYS 信号（signal 31），但其行为与 Linux seccomp SIGSYS **完全不同**：

| 特性 | Linux seccomp SIGSYS | HarmonyOS 未实现 syscall |
|------|---------------------|------------------------|
| sigaction 可捕获？ | ✅ 全部可捕获 | ❌ 部分不可捕获（setreuid/setregid） |
| handler 中 si_syscall | ✅ 包含 syscall 号 | ❌ 不确定 |
| handler 返回后 | 返回 -ENOSYS | 进程被终止（不可捕获时） |

**关键发现**：`setreuid`/`setregid` 的 SIGSYS 不触发任何 signal handler（包括 C 层 sigaction），进程直接被终止。这意味着**信号处理方案完全不可行**，必须在源码层面拦截。

### 验证命令

```bash
# Python 层面
python3 -c "import os; os.setreuid(0,0)"
# 预期: exit code 159 (killed by SIGSYS)

# C 层面
cat > test_sigsys.c << 'EOF'
#include <unistd.h>
int main() {
    setreuid(0, 0);
    return 0;
}
EOF
clang test_sigsys.c -o test_sigsys && ./test_sigsys
echo "exit=$?"  # 159
```

### 解决方案

在 C 源码中用 `#ifdef __OHOS__` 守卫，在 syscall 调用前直接返回 ENOSYS：

```c
int some_function(...) {
#ifdef __OHOS__
    /* HarmonyOS: unimplemented syscall sends uncatchable SIGSYS.
       Return ENOSYS to avoid process death. */
    errno = ENOSYS;
    return -1;
#endif
    return actual_syscall(...);
}
```

**为什么不用信号处理？**
- Python `signal.signal(signal.SIGSYS, handler)` → ❌ 进程仍 core dump
- C `sigaction(SIGSYS, &sa, NULL)` → ❌ setreuid/setregid 不触发 handler
- C handler + longjmp → ❌ setreuid/setregid 不触发 handler

### 编译注意事项

- `__OHOS__` 由鸿蒙 SDK 的 clang 自动定义，无需额外 `-D` 参数
- 编译器会警告原始 syscall 调用变为不可达代码（`code will never be executed`），这是预期的
- 修改 C 源码后需要重新编译并链接

### 影响范围

所有调用未实现 syscall 的 C/C++ 程序。不仅限于 Python，任何从 Linux 移植到鸿蒙的软件都可能遇到。

### 相关补丁

- Python 3.9.0: 0039（timemodule.c clock_settime）、0040（posixmodule.c setreuid/setregid/chroot）

### 相关知识

- `ohos-adaptation-patterns.md` — "未实现 syscall 提前拦截"适配模式
- `harmonyos-specifics.md` — SIGSYS 信号行为章节

---

*文档版本: 2.6*  
*最后更新: 2026-03-29*
*新增 E051：未实现 syscall 触发 SIGSYS 导致进程崩溃（补丁 0039/0040 修复）*
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

*文档版本: 2.9*
*最后更新: 2026-03-30*
*加强 E008：新增 lseek() 对非文件 fd 的限制*
*新增 E054：外来二进制首次执行被安全确认弹窗阻止*