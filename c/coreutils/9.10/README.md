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

# 7. 安装
make install-exec
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

## 测试结果

```bash
# 所有命令管道测试通过
echo "hello" | cat          # ✓
echo "test" | dd            # ✓
echo -e "a\nb\nc" | split -l 1  # ✓
echo -e "a\nb\nc" | tail -1 # ✓
echo -e "z\na\nm" | sort    # ✓
echo -e "a\nb\nc" | head -2 # ✓
```

## 其他注意事项

### toybox 工具兼容性

建议编译安装 GNU coreutils 替代 toybox 工具：
- `expr`: 解决复合正则表达式 bug
- `sed`: 解决复杂脚本兼容性问题

### 参考

- [OpenHarmony third_party_toybox](https://gitcode.com/openharmony/third_party_toybox)
- toybox 使用固定缓冲区大小（4096），不调用 fstat

## 版本历史

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-03-15 | 1.0 | 初始版本 |
| 2026-03-15 | 2.0 | 添加 head.c, sort.c 修复，完善 lseek 处理 |