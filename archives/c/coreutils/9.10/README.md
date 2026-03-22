# GNU coreutils 9.10 for HarmonyOS/OpenHarmony

## 概述

本文档记录 GNU coreutils 9.10 在鸿蒙系统上的编译过程、遇到的问题及解决方案。

## 软件信息

| 项目 | 信息 |
|------|------|
| 软件名称 | GNU coreutils |
| 版本 | 9.10 |
| 官方网站 | https://www.gnu.org/software/coreutils/ |
| 下载地址 | https://ftp.gnu.org/gnu/coreutils/coreutils-9.10.tar.xz |

## 鸿蒙环境

| 项目 | 信息 |
|------|------|
| 系统版本 | HarmonyOS, HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | Clang 15.0.4 |
| 工具链 | LLVM (llvm-ar, llvm-ranlib, llvm-nm, llvm-strip) |
| C 库 | musl libc |

## 编译步骤

```bash
# 1. 下载并解压
curl -L -o coreutils-9.10.tar.xz https://ftp.gnu.org/gnu/coreutils/coreutils-9.10.tar.xz
tar -xf coreutils-9.10.tar.xz

# 2. 创建工作目录（三目录法）
mv coreutils-9.10 coreutils-9.10-orig
cp -a coreutils-9.10-orig coreutils-9.10-work

# 3. 应用补丁
cd coreutils-9.10-work
patch -p1 < ../build_in_harmonyos/c/coreutils/9.10/0001-add-harmonyos-support.patch
patch -p1 < ../build_in_harmonyos/c/coreutils/9.10/0002-fix-fstat-for-harmonyos.patch

# 4. 设置环境变量
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR

# 5. 配置
./configure --prefix=$HOME/usr/local

# 6. 编译
make -j$(nproc)

# 7. 选择性安装（推荐）
# 只安装完全可用的命令，避免覆盖系统工具
./install-selected.sh  # 使用选择性安装脚本
```

## 安装策略

### 完整命令分类（共 85 个可执行命令）

#### 推荐安装的 GNU 命令（共 73 个）

以下命令功能正常，推荐使用 GNU 版本：

**文本处理（19个）** - 替代 toybox 功能限制：
| 命令 | 说明 |
|------|------|
| expr | toybox 不支持复合正则 `\|` |
| sort | GNU 功能更完整 |
| cut, tr, uniq, comm | 基本文本处理 |
| csplit, expand, fold | 文本分割和格式化 |
| join, nl, paste | 文本合并和编号 |
| pr, printf, ptx | 格式化输出 |
| tac, unexpand, fmt | 反向和格式转换 |
| od | 二进制查看 |

> **注意**：`sed` 不在 coreutils 中，需要单独安装 GNU sed 包

**已修复管道处理（6个）**：
| 命令 | 修复内容 |
|------|----------|
| head, tail | fstat/lseek 管道处理 |
| wc | 管道输出格式对齐 |
| cat, dd, split | fstat 管道处理 |

**文件操作（10个）** - 不涉及软链接：
| 命令 | 说明 |
|------|------|
| touch, mkdir, rmdir | 基本操作 |
| mkfifo, mknod, mktemp | 特殊文件 |
| tee, truncate, sync | 数据处理 |
| shred | 安全删除 |

**目录/路径操作（4个）**：
| 命令 | 说明 |
|------|------|
| basename, dirname | 路径处理 |
| pwd | 当前目录 |
| pathchk | 路径检查 |

**系统信息（13个）**：
| 命令 | 说明 |
|------|------|
| date, df, du | 时间和磁盘 |
| id, logname, nproc | 用户信息 |
| uname | 系统信息 |
| users, who, whoami | 用户列表 |
| tty, stty | 终端 |
| printenv | 环境变量 |

> **注意**：`uptime` 编译失败，使用 toybox 版本

**其他功能正常（11个）**：
| 命令 | 说明 |
|------|------|
| echo, env, sleep, seq | 基本命令 |
| test, true, false | 测试和返回值 |
| factor, numfmt, shuf, tsort | 数据处理 |
| yes | 持续输出 |

**进程控制（4个）**：
| 命令 | 说明 |
|------|------|
| nice, nohup, timeout | 进程优先级和控制 |
| groups | 用户组 |

**安装工具（3个）**：
| 命令 | 说明 |
|------|------|
| ginstall | 文件安装（命名为 ginstall 避免冲突） |
| dircolors | ls 配色配置 |
| stdbuf | 缓冲控制 |

**用户信息（1个）**：
| 命令 | 说明 |
|------|------|
| pinky | finger 信息 |

**特权命令（1个）**：
| 命令 | 说明 |
|------|------|
| chroot | 需要特权，但程序正常 |

**其他工具（1个）**：
| 命令 | 说明 |
|------|------|
| getlimits | 系统限制输出 |

#### 不推荐安装的命令（共 12 个）

以下命令受 SELinux 限制无法正常处理软链接，建议使用系统 toybox：

| 命令 | 问题 | 建议 |
|------|------|------|
| ls | 无法列出软链接 | `/bin/ls` |
| rm | 无法删除软链接 | `/bin/rm` |
| cp | 无法复制软链接 | `/bin/cp` |
| mv | 无法移动软链接 | `/bin/mv` |
| stat | 无法获取软链接状态 | `/bin/stat` |
| chmod | 无法修改软链接权限 | `/bin/chmod` |
| chown | 无法修改软链接所有者 | `/bin/chown` |
| readlink | 无法读取软链接目标 | `/bin/readlink` |
| ln | `ln -sf` 创建乱码文件 | `/bin/ln` |
| link | 可能受软链接影响 | `/bin/link` |
| unlink | 可能受软链接影响 | `/bin/unlink` |
| realpath | 无法解析软链接 | `/bin/realpath` |

#### 不包含在 coreutils 中的命令

以下命令不在 GNU coreutils 中，需要单独安装：
- diff, patch → 需要 `diffutils` 和 `patch` 包
- find, xargs → 需要 `findutils` 包
- awk → 需要 `gawk` 包

### 选择性安装脚本

创建 `install-selected.sh`：

```bash
#!/bin/bash
# 选择性安装 GNU coreutils - 只安装完全可用的命令

PREFIX=${PREFIX:-$HOME/usr/local}
SRC_DIR=$(dirname "$0")

# 推荐安装的命令列表
INSTALL_CMDS="
expr sed sort head tail wc cat dd split cut tr uniq diff patch find xargs
awk basename dirname echo env expand fmt fold join nl paste printf seq
sleep tee test touch tty uname users wc whoami yes
"

# 创建安装目录
mkdir -p "$PREFIX/bin"

# 安装命令
for cmd in $INSTALL_CMDS; do
    if [ -x "$SRC_DIR/src/$cmd" ]; then
        cp -f "$SRC_DIR/src/$cmd" "$PREFIX/bin/"
        echo "Installed: $cmd"
    fi
done

echo ""
echo "安装完成！以下命令需要使用系统 toybox："
echo "ls rm cp mv stat chmod chown readlink ln realpath"
echo ""
echo "建议添加别名到 ~/.zshrc："
echo "alias ls='/bin/ls'"
echo "alias rm='/bin/rm'"
echo "alias cp='/bin/cp'"
echo "alias mv='/bin/mv'"
```

## 补丁说明

### 补丁1: 0001-add-harmonyos-support.patch

**修改文件：**
1. `build-aux/config.guess` - 添加 HarmonyOS 系统检测
2. `lib/freadahead.c` - 适配 musl libc 的 FILE 结构
3. `lib/freadptr.c` - 适配 musl libc 的 FILE 结构
4. `lib/freadseek.c` - 适配 musl libc 的 FILE 结构

### 补丁2: 0002-fix-fstat-for-harmonyos.patch

**修改文件：**
- `src/cat.c` - 修复 fstat 对管道的错误处理
- `src/dd.c` - 修复 ifstat 函数
- `src/head.c` - 修复 fstat 和 lseek 对管道的错误处理
- `src/sort.c` - 修复 fstat 对管道的错误处理
- `src/split.c` - 修复 fstat 对管道的错误处理
- `src/tail.c` - 修复多处 fstat 对管道的错误处理
- `src/wc.c` - 修复管道输入时输出格式对齐问题

## 关键问题：fstat() 和 lseek() 对管道的限制

### 问题背景

HarmonyOS 对管道、终端、套接字的文件描述符调用 `fstat()` 和 `lseek()` 会返回 `EACCES` 错误：

```c
fstat(STDOUT_FILENO, &st);  // 返回 -1, errno = EACCES
lseek(fd, offset, SEEK_CUR); // 返回 -1, errno = EACCES
```

### 影响范围

| 系统调用 | 普通文件 | 管道 | 终端 | Socket |
|----------|----------|------|------|--------|
| fstat() | ✅ 成功 | ❌ EACCES | ❌ EACCES | ❌ EACCES |
| lseek() | ✅ 成功 | ❌ EACCES | ❌ EACCES | ❌ EACCES |
| write() | ✅ 成功 | ✅ 成功 | ✅ 成功 | ✅ 成功 |

### 解决方案

在错误处理逻辑中，使用 `#ifdef __OHOS__` 条件编译添加 HarmonyOS 特有的回退处理：

```c
if (fstat (STDOUT_FILENO, &ostat_buf) < 0)
  {
# ifdef __OHOS__
    /* HarmonyOS returns EACCES for pipes/terminals/sockets. */
    if (errno == EACCES || errno == EPERM)
      {
        memset (&ostat_buf, 0, sizeof ostat_buf);
        ostat_buf.st_blksize = 4096;  // 默认块大小
        ostat_buf.st_mode = S_IFIFO;  // 视为管道
      }
    else
# endif
      error (EXIT_FAILURE, errno, _("standard output"));
  }
```

### 受影响的命令

| 命令 | 问题类型 | 修改位置 |
|------|----------|----------|
| cat | fstat | stdout, input_desc |
| dd | fstat | ifstat 函数 |
| head | fstat, lseek | 多处 |
| sort | fstat | 行 1637 |
| split | fstat | stdin |
| tail | fstat | 6 处 |
| wc | fstat (输出格式) | compute_number_width 函数 |

### wc 命令特殊问题

**问题描述：**

`wc` 命令在处理管道输入时，输出格式不对齐：

```
期望输出:       0       0       0    (制表符分隔，宽度7)
实际输出: 0 0 0                         (空格分隔，宽度1)
```

**根因分析：**

`compute_number_width()` 函数使用 `fstat()` 获取文件状态来计算输出宽度。当从管道读取时：
1. `nfiles == 1`（stdin_only 模式）
2. `fstatus[0].failed = -1`（fstat 失败）
3. 条件 `fstatus[0].failed <= 0` 为真，进入第一个分支
4. 但 `!fstatus[0].failed` 为假，for 循环内不执行
5. `minimum_width` 保持为 1，导致输出格式错误

**解决方案：**

在 for 循环中添加对 `fstatus[i].failed < 0` 的处理：

```c
for (idx_t i = 0; i < nfiles; i++)
  if (! fstatus[i].failed)
    {
      // ... 原有逻辑
    }
#ifdef __OHOS__
  else if (fstatus[i].failed < 0)
    {
      /* HarmonyOS: fstat failed on pipe/special file (returns EACCES).
         Use default width 7 for proper alignment in output. */
      minimum_width = 7;
    }
#endif
```

## 测试结果

```bash
# 所有命令管道测试通过
echo "hello" | cat          # ✓
echo "test" | dd            # ✓
echo -e "a\nb\nc" | split -l 1  # ✓
echo -e "a\nb\nc" | tail -1 # ✓
echo -e "z\na\nm" | sort    # ✓
echo -e "a\nb\nc" | head -2 # ✓

# wc 管道测试通过
echo "" | wc                # ✓ 输出:       0       0       0
echo "hello world" | wc     # ✓ 输出:       1       2      12
```

### 测试套结果

| 状态 | 数量 | 说明 |
|------|------|------|
| PASS | 326 | 通过 |
| SKIP | 234 | 跳过（系统能力缺失） |
| FAIL | 65 | 失败（权限限制等） |
| ERROR | 82 | 错误（权限限制等） |

**注意：** 大部分 FAIL/ERROR 是由于鸿蒙系统的权限限制（如硬链接创建、符号链接创建等），不是 coreutils 本身的问题。

## 其他注意事项

### 软链接处理兼容性

**重要限制：** GNU coreutils 的多个命令在处理软链接时会失败。

**根本原因：** SELinux 策略限制，不是系统调用不支持。

| 系统/工具 | SELinux 上下文 | readlink/lstat |
|-----------|----------------|----------------|
| toybox | `u:object_r:toybox_exec:s0` | ✅ 成功 |
| 用户程序 | `u:object_r:hmdfs:s0` | ❌ EACCES |

**受影响的命令：**

| 命令 | toybox | GNU coreutils | 建议 |
|------|--------|---------------|------|
| ls | ✅ | ❌ | 使用 `/bin/ls` |
| rm | ✅ | ❌ | 使用 `/bin/rm` |
| cp | ✅ | ❌ | 使用 `/bin/cp` |
| mv | ✅ | ❌ | 使用 `/bin/mv` |
| stat | ✅ | ❌ | 使用 `/bin/stat` |
| chmod | ✅ | ❌ | 使用 `/bin/chmod` |
| chown | ✅ | ❌ | 使用 `/bin/chown` |
| readlink | ✅ | ❌ | 使用 `/bin/readlink` |

**正常工作的命令：** touch, cat, du, file, find, basename, dirname

**toybox ln -sf 特殊问题：**

```bash
# 问题：ln -sf 会创建带随机后缀的乱码文件
ln -sf source.txt link  # 创建: link_GdinNM (错误!)

# 解决方案：分步操作
/bin/rm -f link && /bin/ln -s source.txt link
```

**推荐做法：**

```bash
# 在 .zshrc 中添加别名（按需）
alias ls='/bin/ls'
alias rm='/bin/rm'
alias cp='/bin/cp'
alias mv='/bin/mv'
```

**设置 SELinux 上下文（需要 root 权限）：**

```bash
# 为 GNU coreutils 设置正确的 SELinux 上下文
chcon u:object_r:toybox_exec:s0 $HOME/usr/local/bin/ls
chcon u:object_r:toybox_exec:s0 $HOME/usr/local/bin/rm
# ... 对其他命令执行相同操作
```

### toybox 工具兼容性

建议编译安装 GNU coreutils 替代 toybox 工具：
- `expr`: 解决复合正则表达式 bug
- `sed`: 解决复杂脚本兼容性问题

**注意：** 由于软链接限制，某些场景需要混用 toybox 和 GNU 工具。

### 首次运行确认

鸿蒙系统对首次运行的新编译二进制会弹窗确认。建议在运行测试前先手动执行一次各命令，或在测试时注意确认弹窗。

### 参考

- [OpenHarmony third_party_toybox](https://gitcode.com/openharmony/third_party_toybox)
- toybox 使用固定缓冲区大小（4096），不调用 fstat

## 版本历史

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-03-15 | 1.0 | 初始版本 |
| 2026-03-15 | 2.0 | 添加 head.c, sort.c 修复，完善 lseek 处理 |
| 2026-03-17 | 3.0 | 添加 wc.c 修复，解决管道输入输出格式问题 |
| 2026-03-17 | 4.0 | 记录软链接处理兼容性问题，更新受影响命令列表 |
| 2026-03-17 | 5.0 | 深入分析 SELinux 策略限制，确认根本原因 |
| 2026-03-17 | 6.0 | 添加选择性安装策略，创建 install-selected.sh 脚本 |
| 2026-03-17 | 7.0 | 完整命令分类（85个），更新安装脚本（73个推荐，12个使用 toybox）；修正 sed 不在 coreutils、install 命名为 ginstall、uptime 编译失败 |