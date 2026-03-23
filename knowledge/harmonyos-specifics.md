# 鸿蒙系统特性和平台对比

本文档介绍鸿蒙系统与其他平台的差异，以及鸿蒙特有的一些机制。

## 1. 与其他平台对比

### 1.1 vs Linux

| 方面 | Linux | HarmonyOS | 说明 |
|------|-------|-----------|------|
| **核心功能** | 100% | 100% ✅ | 完全兼容 |
| **编译选项** | 完全相同 | 完全相同 ✅ | 继承 Linux 配置 |
| **线程支持** | pthreads | pthreads ✅ | 完全兼容 |
| **动态链接** | dlfcn | dlfcn ✅ | 完全兼容 |
| **系统宏** | 无 | `__OHOS__` | 鸿蒙特有 |
| **编译器** | gcc | clang | 使用 LLVM 工具链 |
| **C 库** | glibc | musl libc | 有差异需注意 |
| **sed** | GNU sed | toybox sed | 功能受限 |
| **awk** | gawk/mawk | toybox awk | 功能受限 |
| **shell** | bash | mksh/sh | 语法略有差异 |
| **/tmp** | 可写 | 只读 | 需设置 TMPDIR |

### 1.2 vs Android

| 方面 | Android | HarmonyOS | 说明 |
|------|---------|-----------|------|
| **基础继承** | linux-generic32 | linux-generic32.0 ✅ | 相同 |
| **汇编方案** | linux64 | linux64 ✅ | 相同 |
| **bn_ops** | RC4_CHAR | RC4_CHAR ✅ | 相同 |
| **NDK 检测** | 复杂 | 无 | 更简洁 |
| **环境变量** | 动态检测 | 依赖系统 | 更简单 |
| **SELinux** | 强制 | 强制 | 都有限制 |

### 1.3 vs iOS

| 方面 | iOS | HarmonyOS | 说明 |
|------|-----|-----------|------|
| **工具链** | Xcode (xcrun) | LLVM (clang) | 不同 |
| **汇编方案** | ios64 | linux64 | 不同 |
| **SDK** | iPhoneOS SDK | 系统自带 | 不同 |
| **版本限制** | 需要 | 不需要 | 更简单 |

### 1.4 toybox 工具兼容性

| 工具 | GNU 版本 | toybox 版本 | 差异点 |
|------|----------|-------------|--------|
| **sed** | GNU sed | toybox sed | 不完全支持复杂脚本（多行块、分支命令） |
| **awk** | gawk/mawk | toybox awk | 功能有限，某些扩展不可用 |
| **expr** | GNU expr | toybox expr | **不支持复合正则表达式 `\|`** |
| **grep** | GNU grep | toybox grep | 基本功能相同 |
| **sh** | bash | mksh | 语法略有差异 |

**toybox sed 已知问题**：
1. 复杂的多行命令块 `{...}` 处理可能异常
2. 分支命令 `:label` 和 `b`、`t` 跳转可能不完整
3. 某些正则表达式特性不支持
4. 建议对于复杂的 autotools 项目，configure 后检查生成的 Makefile

---

## 2. ELF 可执行文件签名

### 2.1 签名机制

在鸿蒙系统上，ELF 可执行文件需要正确的签名才能运行。当使用 `patchelf`、`strip` 等工具修改 ELF 文件后，签名会失效，需要重新签名。

### 2.2 问题场景

```bash
# 使用 patchelf 修改 RPATH
patchelf --set-rpath /new/path myprogram

# 使用 strip 移除调试符号
llvm-strip myprogram

# 以上操作后，签名失效，执行时会报错
./myprogram  # 错误：签名验证失败
```

### 2.3 解决方案

使用 `binary-sign-tool` 重新签名：

```bash
# 1. 重新签名
binary-sign-tool sign -inFile myprogram -outFile myprogram -selfSign 1

# 2. 恢复可执行权限（签名后权限会丢失）
chmod +x myprogram

# 3. 首次执行需要用户确认弹窗
./myprogram  # 弹窗确认后可正常执行
```

### 2.4 完整流程示例

```bash
# 场景：修改 ELF 文件的 RPATH 后重新签名

# 步骤 1: 修改 ELF
patchelf --set-rpath $HOME/usr/local/lib myprogram

# 步骤 2: 重新签名
binary-sign-tool sign -inFile myprogram -outFile myprogram -selfSign 1

# 步骤 3: 恢复权限
chmod +x myprogram

# 步骤 4: 首次执行确认
./myprogram
```

### 2.5 注意事项

1. **签名后权限丢失**：每次签名后需要重新 `chmod +x`
2. **首次执行确认**：首次运行需要用户在弹窗中确认
3. **修改即失效**：任何对 ELF 文件的修改都会使签名失效

---

## 3. Shell 脚本 Shebang 写法

### 3.1 推荐写法

在鸿蒙系统上，推荐使用以下 Shebang 写法：

```bash
#!/bin/sh
# 或
#!/usr/bin/env bash
```

### 3.2 不推荐的写法

```bash
#!/bin/bash  # 可能不存在
#!/usr/bin/bash  # 可能不存在
```

### 3.3 原因

- 鸿蒙系统的 bash 可能安装在用户目录
- `/bin/sh` 通常指向系统 shell（mksh）
- 使用 `#!/usr/bin/env bash` 可以自动查找 PATH 中的 bash

### 3.4 检查 Shell

```bash
# 检查系统 shell
ls -la /bin/sh
# 通常输出: /bin/sh -> /system/bin/mksh

# 检查 bash 是否安装
which bash
# 可能输出: /data/service/hnp/bin/bash 或 $HOME/usr/local/bin/bash
```

---

## 4. 典型问题排查案例：toybox expr bug

### 4.1 问题现象

编译 ncurses 时，`config.status` 执行过程中 sed 进程卡住，生成的 Makefile 包含乱码。

### 4.2 排查过程

```bash
# 第一步：找到卡住的进程
$ ps aux | grep sed
USER  PID  ... COMMAND
user  60545 ... sed s,@top_srcdir@,../<乱码>...,;t t

# 第二步：查看进程命令行
$ cat /proc/60545/cmdline | tr '\0' ' '
sed s,@top_srcdir@,../...乱码...,;t t

# 第三步：分析乱码来源
# 乱码在 $ac_top_srcdir 变量中

# 第四步：追踪 config.status
$ bash -x ./config.status --file=ncurses/Makefile 2>&1 | grep ac_dots
+ ac_dots='../<乱码>...'

# 第五步：分析 ac_dots 的计算
# ac_dots 来自 expr 命令的输出

# 第六步：对比测试
$ expr X"ncurses/Makefile" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
mOkk...  # toybox expr 输出乱码！

$ /path/to/gnu/expr X"ncurses/Makefile" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
ncurses  # GNU expr 正确！
```

### 4.3 根因分析

| 因素 | 说明 |
|------|------|
| 触发条件 | config.status 使用复合正则表达式（`\|` 操作符） |
| 问题工具 | toybox expr |
| 问题表现 | 复合正则表达式输出乱码 |
| 影响范围 | 所有使用 autotools 的项目 |

### 4.4 解决方案

```bash
# 编译安装 GNU coreutils（包含 GNU expr）
# 参考: archives/c/coreutils/9.10/

# 设置 PATH 优先使用 GNU 工具
export PATH=$HOME/usr/local/bin:$PATH
```

### 4.5 经验总结

1. **工具兼容性问题可能很隐蔽**：简单命令正常，复杂命令出错
2. **对比测试很重要**：与已知正确的工具对比行为
3. **追踪变量来源**：使用 `bash -x` 追踪脚本执行
4. **系统化排查**：从现象 → 进程 → 变量 → 命令 → 工具

---

## 5. 测试流程规范

### 5.1 官方测试

```bash
# 运行官方测试套件
make check

# 或
make test
```

**注意事项**：
- 鸿蒙系统的签名机制可能导致测试二进制无法直接运行
- 可能需要手动确认弹窗
- 某些测试依赖 PTY 功能（系统限制）

### 5.2 自定义测试

当官方测试无法运行时，创建自定义测试：

```bash
#!/bin/bash
# test-basic.sh - 基本功能测试

echo "=== 基本功能测试 ==="

# 测试 1: 检查可执行文件
if [ -x ./myprogram ]; then
    echo "✅ 可执行文件存在"
else
    echo "❌ 可执行文件不存在"
    exit 1
fi

# 测试 2: 基本运行
./myprogram --version
if [ $? -eq 0 ]; then
    echo "✅ 基本运行成功"
else
    echo "❌ 基本运行失败"
    exit 1
fi

# 测试 3: 功能验证
result=$(./myprogram --test-feature)
if [ "$result" = "expected" ]; then
    echo "✅ 功能测试通过"
else
    echo "❌ 功能测试失败"
    exit 1
fi

echo "=== 所有测试通过 ==="
```

### 5.3 测试报告规范

测试报告应包含：

1. **测试环境**
   - 系统版本
   - 编译器版本
   - 依赖版本

2. **测试统计**
   - 总测试数
   - 通过数
   - 失败数
   - 跳过数

3. **失败详情**
   - 失败测试名称
   - 失败原因
   - 错误输出

4. **已知限制**
   - 系统限制导致的失败
   - 功能缺失

---

## 6. 总结

### 6.1 鸿蒙特有机制

| 机制 | 说明 | 处理方式 |
|------|------|----------|
| ELF 签名 | 可执行文件需要签名 | 修改后重新签名 |
| SELinux | 强制访问控制 | 使用管道语法绕过 |
| toybox | 工具功能受限 | 编译 GNU 工具替代 |
| /tmp 只读 | 临时目录限制 | 设置 TMPDIR |
| musl libc | C 库差异 | 条件编译处理 |

### 6.2 迁移建议

从 Linux 迁移到 HarmonyOS 时：

1. **工具链**：使用 clang + LLVM 工具链
2. **脚本**：注意 shebang 写法，测试 toybox 兼容性
3. **测试**：准备自定义测试方案
4. **签名**：修改 ELF 后重新签名

---

## 7. SELinux 域转换对子进程执行 SDK 二进制的限制 ⭐ 重要

### 7.1 限制描述

HarmonyOS 使用 SELinux 强制访问控制，存在**域转换（Domain Transition）**机制。当用户进程创建子进程执行 SDK 工具时，子进程会因 SELinux 策略而执行失败。

### 7.2 根因分析

| 场景 | 进程类型 | SELinux Context |
|------|----------|-----------------|
| Shell 进程 | 受信任进程 | `u:r:hishell_hap:s0` |
| Python 解释器 | 用户程序 | `u:r:adhoc_bin:s0` |
| 用户编译的 C 程序 | 用户程序 | `u:r:adhoc_bin:s0` |
| SDK clang-15 | 系统工具 | `u:object_r:hnp_file:s0` |
| 用户编译的文件 | 用户文件 | `u:object_r:hmdfs:s0` |

**域转换流程：**

```
hishell_hap:s0          执行用户程序           adhoc_bin:s0
(Shell 进程)   ───────────────────────>    (Python/C程序)

✅ 可以执行 hnp_file    ───────────────>    ❌ 不能执行
   (SDK 工具)                              hnp_file
```

### 7.3 问题现象

```python
import subprocess
# 执行 SDK 工具失败
subprocess.run(['clang', '--version'])  # returncode: 1, 无输出
os.system("clang --version")            # exit code: 1
```

**关键点**：SDK 的 clang-15 是一个 109MB 的 ELF 二进制，当 `adhoc_bin` 域的进程尝试 `execve()` 它时：

1. `execve()` 系统调用成功（没有返回错误）
2. SELinux 在内核层面拦截了执行
3. 进程立即以 exit code 1 退出
4. **没有任何错误输出**（因为二进制根本没有真正开始执行）

### 7.4 解决方案：管道语法绕过 SELinux 限制

使用管道语法 `cmd | cat` 可以绕过 SELinux 限制！

```python
# 直接执行 - 失败
os.system("clang test.c -o test")  # exit code: 1

# 管道执行 - 成功！
os.system("clang test.c -o test | cat")  # exit code: 0
```

**原理**：管道强制 shell 创建子进程来执行管道的左侧命令。这个子进程的 SELinux 上下文可能具有不同的权限。

### 7.5 管道方式对比测试结果

| 方法 | Exit Code | 文件生成 | 推荐 |
|------|-----------|----------|------|
| `clang ...`（无管道） | 1 | ❌ No | - |
| `clang ... \| cat` | 0 | ✅ Yes | ⭐ 推荐 |
| `clang ... \| head -N` | 0 | ✅ Yes | ⭐ 推荐 |
| `clang ... \| true` | 0 | ✅ Yes | 可用 |
| `clang ... & wait` | 0 | ❌ No | 不稳定 |

### 7.6 正确实现（使用 `pipefail` 获取真实退出码）

```python
# HarmonyOS workaround
cmd_str = f"set -o pipefail; {cmd} 2>&1 | cat"
status = os.system(cmd_str)
```

### 7.7 受影响的软件

- **Python**: `setup.py` 通过 `_bootsubprocess.Popen` 调用 `clang` 编译扩展模块
- **Perl**: `ExtUtils::CBuilder` 编译 XS 模块
- **Ruby**: `mkmf.rb` 编译原生扩展
- **任何**通过子进程调用 SDK 编译器的构建系统

---

## 8. 软链接访问和创建限制

### 8.1 访问限制

**根本原因**：HarmonyOS 的 SELinux 策略限制了用户进程对软链接的访问。

| 系统/工具 | SELinux Context | readlink/lstat |
|-----------|-----------------|----------------|
| toybox | `u:object_r:toybox_exec:s0` | ✅ 成功 |
| 用户程序 | `u:object_r:hmdfs:s0` | ❌ EACCES |

### 8.2 受影响的 GNU coreutils 命令

| 命令 | toybox | GNU coreutils | 原因 |
|------|--------|---------------|------|
| ls | ✅ | ❌ | lstat 获取链接属性 |
| stat | ✅ | ❌ | lstat 获取链接状态 |
| rm | ✅ | ❌ | lstat 检查文件类型 |
| cp | ✅ | ❌ | lstat 检查是否为链接 |
| mv | ✅ | ❌ | lstat 检查源文件 |
| chmod | ✅ | ❌ | lstat 获取文件状态 |
| readlink | ✅ | ❌ | readlink 系统调用受限 |

### 8.3 解决方案

对于涉及软链接的操作，使用 toybox 命令作为兜底：

```bash
# 在 .zshrc 或脚本中添加别名
alias ls='/bin/ls'
alias rm='/bin/rm'
alias cp='/bin/cp'
alias mv='/bin/mv'
alias stat='/bin/stat'
```

### 8.4 创建软链接受限

在某些场景下，用户进程**创建软链接也会失败**：

```bash
# 在用户安装目录创建软链接可能失败
ln -s ncursesw/curses.h curses.h
# 错误: ln: cannot create symbolic link 'curses.h': Permission denied
```

**通用解决方案：使用 `cp` 复制代替 `ln -s` 软链接**

```bash
# 不要使用软链接
ln -s source.txt link        # ❌ 可能失败

# 使用复制代替
cp source.txt link           # ✅ 成功

# 对于目录中的多个文件
for f in ncursesw/*.h; do
    cp "$f" "$(basename $f)"
done
```

### 8.5 toybox ln -sf 的特殊问题

```bash
# 正常创建
ln -s source.txt link        # 创建: link -> source.txt ✓

# 强制覆盖问题
ln -sf source.txt link       # 创建: link_GdinNM -> source.txt ✗ (随机后缀)
```

建议在鸿蒙系统上避免使用 `ln -sf`，改用：
```bash
rm -f link && ln -s source.txt link
```

---

## 8.6 共享库安全警告案例：ncurses 编译导致 Shell 崩溃 ⚠️ 严重

### 问题背景

鸿蒙系统的 `/bin/zsh` 依赖系统预装的 `libncursesw.so.6`。如果用户编译 ncurses 时生成了共享库，可能覆盖或干扰系统库，导致严重后果。

### 事故经过

```
用户编译 ncurses（默认生成共享库）
    ↓
安装后系统库路径被影响
    ↓
所有 zsh 进程启动时加载错误的 libncursesw.so.6
    ↓
Shell 崩溃，所有终端无法打开
    ↓
系统陷入不可用状态
```

### 影响范围

- 所有依赖 Shell 的终端应用无法使用
- 无法通过终端执行任何命令
- 只能通过文件管理器或系统恢复

### 根因分析

1. **系统关键组件依赖共享库**：`/bin/zsh` → `libncursesw.so.6`
2. **共享库版本冲突**：用户编译的库与系统库冲突
3. **库加载顺序问题**：LD_LIBRARY_PATH 或 rpath 导致加载错误版本
4. **无恢复机制**：Shell 崩溃后无法通过终端修复

### 正确做法

**✅ 鸿蒙系统编译 ncurses 时必须使用静态库**

```bash
./configure --prefix=$HOME/usr/local \
    --without-shared \        # ⭐ 关键：不生成共享库
    --enable-widec \
    --enable-overwrite \
    --without-debug \
    --without-profile \
    --without-ada \
    --without-manpages \
    --without-progs \
    --without-tests \
    --without-cxx \
    --without-cxx-binding

make && make install
```

### 通用原则

| 库类型 | 编译选项 | 适用场景 | 风险 |
|--------|----------|----------|------|
| **静态库** | `--without-shared` | 系统关键依赖的库 | ✅ 安全 |
| 共享库 | `--with-shared` | 非系统关键库 | ⚠️ 需谨慎 |

**判断标准**：
- 如果系统已有同名共享库（如 libncursesw.so），优先使用静态库
- 如果是新库，不影响系统组件，可以考虑共享库
- Python 扩展模块可以静态链接库（如 `_curses.so` 静态链接 `libncursesw.a`）

### 紧急恢复方案

如果已经发生 Shell 崩溃：

```bash
# 方案 1: 通过文件管理器
# 删除用户安装的共享库
rm -f $HOME/usr/local/lib/libncursesw.so*

# 方案 2: 通过 Android Debug Bridge (ADB)
adb shell
rm -f /data/service/el2/user/0/users/currentUser/usr/local/lib/libncursesw.so*

# 方案 3: 系统恢复
# 重置应用数据（最后手段）
```

### 经验教训

1. **编译前检查系统依赖**：`ldd /bin/zsh` 查看系统关键组件依赖的库
2. **优先使用静态库**：避免共享库冲突风险
3. **不要修改系统库路径**：保持 LD_LIBRARY_PATH 在用户目录
4. **备份关键配置**：在修改库之前做好恢复准备

---

## 9. fstat() 对管道/终端的限制

### 9.1 限制描述

| 文件描述符类型 | fstat() 结果 | write() 结果 | 说明 |
|---------------|-------------|--------------|------|
| 普通文件 | ✅ 成功 | ✅ 成功 | 正常 |
| 管道 (pipe) | ❌ EACCES | ✅ 成功 | 可以写入，但无法获取元信息 |
| 终端 (tty) | ❌ EACCES | ✅ 成功 | 可以输出，但无法获取元信息 |
| 套接字 (socket) | ❌ EACCES | ✅ 成功 | 可以通信，但无法获取元信息 |

### 9.2 受影响的软件

- GNU coreutils: cat, head, tail, dd, split, tee 等
- 其他调用 `fstat(STDIN_FILENO)` 或 `fstat(STDOUT_FILENO)` 的软件

### 9.3 解决方案模板

```c
/* harmonyos-fstat-compat.h */
#ifdef __OHOS__

static inline int
ohos_fstat_compat (int fd, struct stat *st)
{
  if (fstat (fd, st) == 0)
    return 0;

  if (errno == EACCES || errno == EPERM)
    {
      /* HarmonyOS returns EACCES for pipes/terminals/sockets */
      memset (st, 0, sizeof (*st));
      st->st_blksize = 4096;      /* Default I/O block size */
      st->st_mode = S_IFIFO;      /* Treat as pipe/FIFO */
      return 0;
    }

  return -1;
}

#define OHOS_FSTAT(fd, st) ohos_fstat_compat ((fd), (st))

#else /* !__OHOS__ */

#define OHOS_FSTAT(fd, st) fstat ((fd), (st))

#endif /* __OHOS__ */
```

**参考补丁**：`archives/c/coreutils/9.10/patches/0002-fix-fstat-for-harmonyos.patch`

---

*文档版本: 1.1*  
*最后更新: 2024-03-22*

## 10. Perl 测试框架依赖问题

### 问题描述

许多 GNU 软件的测试套件使用 Perl 编写，需要额外的 CPAN 模块。系统预装的 Perl 5.42.0 缺少这些模块。

### 常见缺失模块

- `HTTP::Daemon` - HTTP 服务器模拟（wget 测试需要）
- `HTTP::Request` / `HTTP::Response` - HTTP 消息处理
- `Test::More` - 测试框架
- `Module::Build::Tiny` - 构建工具

### 解决方案

**推荐：安装 cpanm**

```bash
# 下载 cpanm
curl -L https://cpanmin.us -o cpanm
chmod +x cpanm

# 安装模块
./cpanm --notest HTTP::Daemon HTTP::Message LWP
```

**配置本地 Perl 库**

```bash
# 创建本地库目录
mkdir -p ~/perl-lib

# 设置环境变量
export PERL5LIB="$HOME/perl-lib/lib/perl5:$PERL5LIB"
export PERL_MM_OPT="INSTALL_BASE=$HOME/perl-lib"
export PERL_MB_OPT="--install_base $HOME/perl-lib"
```

### 受影响的软件测试

| 软件 | 测试依赖 | 状态 |
|------|----------|------|
| wget | HTTP::Daemon, HTTP::Message | 需安装模块 |
| curl | HTTP::Daemon 等 | 需安装模块 |
| 其他 Perl 测试软件 | 各种 CPAN 模块 | 视情况而定 |

### 替代验证方式

当测试框架无法运行时，采用手动验证：

```bash
# 功能测试
wget --version
wget --no-check-certificate -q https://example.com/ -O /dev/null && echo "OK"

# 断点续传测试
wget -c ...

# 递归下载测试
wget -r ...
```
## 11. /proc 文件系统访问限制

### 问题描述

鸿蒙系统的 SELinux 策略限制了普通用户对 `/proc` 文件系统的访问。即使文件权限显示所有用户可读（`-r--r--r--`），普通用户仍然无法读取。

### 现象

```bash
$ cat /proc/stat
cat: /proc/stat: Permission denied

$ ls -la /proc/stat
-r--r--r-- 1 root root 0 2026-03-16 22:23 /proc/stat

$ ls -Z /proc/stat
u:object_r:proc_stat_file:s0 /proc/stat
```

### 受影响的工具

- **htop** - 需要 sudo 运行
- **top** - 可能受影响
- **ps** - 可能受影响
- 任何需要读取 `/proc` 的进程监控工具

### 解决方案

1. 使用 `sudo` 运行受影响的工具
2. 或使用鸿蒙提供的替代方案

### 相关信息

- 用户组 `readproc(3009)` 可能与进程读取权限相关
- SELinux 上下文类型：`proc_stat_file`, `proc_t` 等

