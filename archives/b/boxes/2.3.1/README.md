# boxes 2.3.1 在 OpenHarmony 上的编译指南

## 概述

本文档记录了 boxes 2.3.1（ASCII 框绘制工具）在 OpenHarmony/HarmonyOS 系统上的编译过程、关键修改点和测试结果。

### 编译结果

| 项目 | 结果 |
|------|------|
| 软件版本 | boxes 2.3.1 |
| 目标平台 | aarch64-unknown-linux-ohos |
| 编译器 | clang (系统自带) |
| 安装位置 | `$HOME/usr/local/bin/boxes` |
| 文件大小 | ~383 KB (stripped) |
| 编译日期 | 2026-04-13 |

## 软件信息

| 项目 | 信息 |
|------|------|
| 软件名称 | boxes |
| 版本 | 2.3.1 |
| 官方网站 | https://boxes.thomasjensen.com/ |
| 下载地址 | https://github.com/ascii-boxes/boxes/archive/refs/tags/v2.3.1.tar.gz |
| 许可证 | GPL v3 |
| 描述 | 命令行 ASCII 框绘制/移除工具 |

## 鸿蒙环境

| 项目 | 信息 |
|------|------|
| 系统版本 | HarmonyOS HongMeng Kernel 1.12.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM 15.0.4) |
| 构建系统 | Makefile |
| 依赖工具 | flex, bison |

## 依赖关系

| 依赖库 | 版本 | 状态 | 说明 |
|--------|------|------|------|
| libunistring | 1.0 | ✅ 已编译 | Unicode 字符串处理 |
| PCRE2 | 10.40 | ✅ 已编译 | 正则表达式库（32位） |
| ncurses | 6.4 | ⏭️ 绕过 | 使用 stub 函数替代 |

## 编译步骤

### 1. 下载源码

```bash
cd $HOME/tmp
curl -L -O https://github.com/ascii-boxes/boxes/archive/refs/tags/v2.3.1.tar.gz
tar -xzf v2.3.1.tar.gz
cd boxes-2.3.1
```

### 2. 编译依赖库

boxes 需要以下依赖库，需在 vendor 目录下编译：

```bash
# 创建 vendor 目录
mkdir -p vendor

# 编译 libunistring 1.0
curl -L -O https://ftp.gnu.org/gnu/libunistring/libunistring-1.0.tar.gz
tar -xzf libunistring-1.0.tar.gz -C vendor
cd vendor/libunistring-1.0
# 更新 config.guess/config.sub（见下方补丁说明）
./configure --enable-static --prefix=$PWD/ohos-install
make -j$(nproc)
make install
cd ../..

# 编译 PCRE2 10.40
curl -L -O https://github.com/PCRE2Project/pcre2/releases/download/pcre2-10.40/pcre2-10.40.tar.gz
tar -xzf pcre2-10.40.tar.gz -C vendor
cd vendor/pcre2-10.40
# 更新 config.guess/config.sub
./configure --enable-static --prefix=$PWD/ohos-install --build=aarch64-unknown-linux-gnu
make -j$(nproc)
make install
cd ../..
```

### 3. 应用补丁

```bash
# 应用补丁（修改 Makefile 和 boxes.c）
patch -p1 < patches/0001-boxes-harmonyos-compat.patch
```

### 4. 配置编译参数

修改 `src/Makefile`：
```makefile
# 允许环境变量覆盖编译器
CC ?= gcc

# 添加依赖库路径
CFLAGS_ADDTL += -I../vendor/libunistring-1.0/ohos-install/include
CFLAGS_ADDTL += -I../vendor/pcre2-10.40/ohos-install/include
LDFLAGS += -L../vendor/libunistring-1.0/ohos-install/lib
LDFLAGS += -L../vendor/pcre2-10.40/ohos-install/lib
```

### 5. 编译安装

```bash
# 设置编译器
export CC=clang

# 编译
make build CC=clang

# 手动 strip（若 strip 命令缺失）
llvm-strip out/boxes

# 安装
cp out/boxes $HOME/usr/local/bin/
cp boxes-config $HOME/usr/local/share/boxes/
```

### 6. 验证

```bash
$HOME/usr/local/bin/boxes --version
# 输出: boxes 2.3.1
```

## 补丁说明

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/Makefile` | 修改 CC 变量、添加依赖库路径、移除 ncurses 链接 |
| `src/boxes.c` | 添加 HarmonyOS 兼容性代码、stub ncurses 函数 |

### 关键修改详解

#### src/Makefile - 编译器适配

**问题背景**：
- Makefile 硬编码 `CC = gcc`，无法使用环境变量覆盖
- 缺少依赖库的 include/lib 路径
- 原链接命令包含 `-lncurses`，但 ncurses 编译困难

**解决方案**：
```makefile
# 允许环境变量覆盖
CC ?= gcc

# 添加依赖库路径
CFLAGS_ADDTL += -I../vendor/libunistring-1.0/ohos-install/include
CFLAGS_ADDTL += -I../vendor/pcre2-10.40/ohos-install/include

# 移除 ncurses 链接
# 原: $(CC) $(LDFLAGS) $^ -o $@ -lunistring -lpcre2-32 -lncurses
# 改: $(CC) $(LDFLAGS) $^ -o $@ -lunistring -lpcre2-32
```

#### src/boxes.c - ncurses stub

**问题背景**：
- ncurses configure 在 HarmonyOS 上创建乱码目录名
- Makefile 生成失败
- boxes 仅使用 ncurses 的 terminfo 功能

**解决方案**：
添加 stub 函数替代 ncurses：
```c
/* HarmonyOS: ncurses stub functions */
#ifdef __OHOS__
static int setupterm(const char *term, int fd, int *errret) {
    return 0;  /* 成功 */
}
static int tigetnum(const char *capname) {
    if (strcmp(capname, "cols") == 0) return 80;   /* 默认列数 */
    if (strcmp(capname, "lines") == 0) return 24;  /* 默认行数 */
    return -1;
}
#endif
```

## 遇到的问题

### 问题 1：Makefile 硬编码 gcc

**现象**：
```
make[2]: gcc: No such file or directory
```

**原因**：
- Makefile 使用 `CC = gcc` 赋值，环境变量 `CC=clang` 无效

**解决方案**：
- 修改为 `CC ?= gcc`（允许环境变量覆盖）
- 或直接使用 `make build CC=clang`

### 问题 2：libunistring configure 无法识别 HarmonyOS

**现象**：
```
configure: error: cannot guess build type; you must specify one
```

**原因**：
- 原版 config.guess 不支持 HarmonyOS 系统（`uname -s` 返回 `HarmonyOS`）

**解决方案**：
- 下载 GNU config 最新版 config.guess/config.sub
- 在 config.guess 中添加 `HarmonyOS` case 分支
- 在 config.sub 中添加 `ohos-linux` 和 `ohos*` 识别

### 问题 3：PCRE2 build 类型识别失败

**现象**：
```
config.sub: invalid configuration `aarch64-unknown-linux-ohos': OS `ohos' not recognized
```

**原因**：
- config.sub 不接受 `linux-ohos` 操作系统

**解决方案**：
- 使用 `--build=aarch64-unknown-linux-gnu` 指定构建类型
- 符合 skill R15 原则：native 编译时可用此 workaround

### 问题 4：ncurses 编译困难

**现象**：
- configure 创建乱码目录名
- Makefile 生成失败

**原因**：
- ncurses configure 与 HarmonyOS 环境深度不兼容

**解决方案**：
- 使用 stub 函数绕过 ncurses 依赖
- boxes 仅使用基本 terminfo 功能，可安全替代

### 问题 5：strip 命令缺失

**现象**：
```
strip: command not found
```

**原因**：
- 系统未安装 GNU strip，但有 llvm-strip

**解决方案**：
- 使用 `llvm-strip` 手动 strip

## 测试结果

### 基本功能测试

| 测试项 | 结果 |
|--------|------|
| 版本显示 | ✅ 通过 |
| 基本框绘制 | ✅ 通过 |
| 框移除 | ✅ 通过 |
| 自定义样式 | ✅ 通过 |

### 测试命令

```bash
# 基本框绘制
echo "Hello World" | boxes
# 输出:
# /*************/
# /* Hello World */
# /*************/

# 指定样式
echo "Test" | boxes -d shell
# 输出:
# # Test #

# 移除框
echo "Hello" | boxes | boxes -r
# 输出: Hello

# 查看可用样式
boxes -l
```

## 注意事项

1. **必须编译依赖库**：boxes 依赖 libunistring 和 PCRE2，需先编译
2. **ncurses 被绕过**：使用 stub 函数，终端列数/行数固定为 80/24
3. **flex/bison 必需**：解析配置文件需要这两个工具
4. **首次运行**：鸿蒙系统首次执行新编译的二进制会弹窗确认
5. **配置文件**：需要安装 `boxes-config` 到 `/usr/share/boxes/`

## 经验总结

1. **优先级③修改**：Makefile 直接修改是最后手段，需在 PROGRESS.md 记录
2. **依赖库隔离**：在 vendor 目录编译依赖库，避免污染系统环境
3. **stub 策略**：当依赖库编译困难且功能简单时，可使用 stub 绕过
4. **native 编译**：使用 `--build=linux-gnu` 作为 HarmonyOS 的 workaround

## 参考资料

- boxes 官方文档: https://boxes.thomasjensen.com/docs/
- boxes GitHub: https://github.com/ascii-boxes/boxes
- libunistring: https://ftp.gnu.org/gnu/libunistring/
- PCRE2: https://github.com/PCRE2Project/pcre2
- OpenHarmony 编译知识库: `build_in_harmonyos/SKILL.md`
- 相关依赖库归档: `build_in_harmonyos/archives/l/libunistring/1.0/README.md`