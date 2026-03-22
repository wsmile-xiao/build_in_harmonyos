# 鸿蒙系统环境特性

## 1. 系统信息

| 项目 | 值 |
|------|-----|
| 系统名称 | HarmonyOS / OpenHarmony |
| 内核 | HongMeng Kernel |
| 架构 | aarch64 (主要), arm, x86_64 |
| C 库 | musl libc |

## 2. 编译工具链

### 2.1 编译器

| 工具 | 路径 | 版本 |
|------|------|------|
| clang | /data/service/hnp/bin/clang | 15.0.4 |
| clang++ | /data/service/hnp/bin/clang++ | 15.0.4 |

### 2.2 LLVM 工具链

鸿蒙使用 LLVM 工具链替代 GNU 工具：

| GNU 工具 | LLVM 替代 | 用途 |
|----------|-----------|------|
| ar | llvm-ar | 静态库管理 |
| ranlib | llvm-ranlib | 库索引 |
| nm | llvm-nm | 符号表查看 |
| strip | llvm-strip | 符号移除 |
| objdump | llvm-objdump | 反汇编 |
| objcopy | llvm-objcopy | 对象文件操作 |

### 2.3 其他工具

| 工具 | 版本 | 状态 |
|------|------|------|
| make | GNU Make 4.4.1 | ✅ 可用 |
| cmake | 4.1.2 | ✅ 可用 |
| autoconf | 2.72 | ✅ 可用 |
| perl | 5.42.0 | ✅ 可用 |
| git | 2.45.2 | ✅ 可用 |

## 3. 预定义宏

Clang 在鸿蒙系统上自动定义以下宏：

```c
__OHOS__           // OpenHarmony 系统标识（官方标准）
__OHOS_FAMILY__    // OpenHarmony 家族标识
__OHOS_Major__     // 主版本号
```

**验证方式**：
```bash
clang -dM -E - < /dev/null | grep OHOS
```

## 4. 环境变量配置

推荐在 `~/.zshrc` 中配置：

```bash
# 安装前缀
export DEFAULT_PREFIX=$HOME/usr/local

# PATH
export PATH=$PATH:$HOME/npm/bin:$HOME/.local/bin:$DEFAULT_PREFIX/bin

# 库路径
export LIBRARY_PATH=$DEFAULT_PREFIX/lib:$LIBRARY_PATH
export LD_LIBRARY_PATH=$DEFAULT_PREFIX/lib:$LD_LIBRARY_PATH

# 头文件路径
export C_INCLUDE_PATH=$DEFAULT_PREFIX/include:$C_INCLUDE_PATH
export CPLUS_INCLUDE_PATH=$DEFAULT_PREFIX/include:$CPLUS_INCLUDE_PATH

# 编译器设置
export CC="clang"
export CXX="clang++"
export AR="llvm-ar"
export RANLIB="llvm-ranlib"
export NM="llvm-nm"
export STRIP="llvm-strip"

# ⭐ 关键：所有编译都使用 -fPIC
export CFLAGS="-fPIC -O2"
export CXXFLAGS="-fPIC -O2"
export LDFLAGS="-L$DEFAULT_PREFIX/lib"

# 临时目录（鸿蒙 /tmp 不可写）
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR

# 便捷别名
alias configure='./configure --prefix=$DEFAULT_PREFIX'
alias cmake='cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX'
alias Configure='./Configure --prefix=$DEFAULT_PREFIX'
```

## 5. 系统限制

### 5.1 文件系统

| 限制 | 说明 | 解决方案 |
|------|------|----------|
| `/tmp` 不可写 | erofs 只读挂载 | `export TMPDIR=$HOME/tmp` |
| 软链接访问受限 | SELinux 策略 | 使用 `cp` 替代 `ln -s` |
| `fstat(pipe)` 返回 EACCES | 安全限制 | 使用兼容性封装 |

### 5.2 SELinux 域转换

用户进程执行 SDK 工具时会触发域转换：

```
hishell_hap:s0 → adhoc_bin:s0 → 无法执行 hnp_file
```

**解决方案**：使用管道语法绕过
```bash
# 直接执行失败
clang --version

# 管道执行成功
clang --version | cat
```

## 6. 三元组格式

鸿蒙系统的标准三元组：

```
<架构>-unknown-linux-ohos
```

示例：
- `aarch64-unknown-linux-ohos`
- `arm-unknown-linux-ohos`
- `x86_64-unknown-linux-ohos`

## 7. 系统检查命令

```bash
# 系统信息
uname -s    # HarmonyOS
uname -m    # aarch64
uname -r    # 1.11.0

# 编译器
clang --version

# LLVM 工具
which llvm-ar llvm-ranlib llvm-nm

# 预定义宏
clang -dM -E - < /dev/null | grep -E "OHOS|GLIBC"
```

## 8. 与 Linux 的主要差异

| 方面 | Linux | HarmonyOS |
|------|-------|-----------|
| C 库 | glibc | musl libc |
| 编译器 | gcc | clang |
| ar | GNU ar | llvm-ar |
| /tmp | 可写 | 只读 |
| SELinux | 通常禁用 | 强制启用 |
| 软链接 | 正常 | 部分受限 |