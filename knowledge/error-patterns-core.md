# 🔧 错误模式：平台与环境类 (E001-E020)

> **父文档**: [error-patterns.md](./error-patterns.md)
> **类别**: 平台约束 / 工具链兼容性 / 环境配置 / 权限与安全
> **适用阶段**: Phase 1 环境检测 / Phase 2 编译初始化

---

## 错误模式列表

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
*属于 [error-patterns.md](./error-patterns.md) 的模块化子集*
