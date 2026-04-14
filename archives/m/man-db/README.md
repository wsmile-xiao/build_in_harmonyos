# man-db 2.13.1 鸿蒙系统编译指南

## 一、概述

man-db 是标准的 Unix 手册页查询工具集，用于浏览和搜索系统手册页。它提供了 `man`、`apropos`、`whatis`、`mandb` 等命令，是命令行环境中最常用的文档查阅工具。man-db 使用 gdbm 存储手册页索引数据库，配合 groff 进行页面格式化渲染。

## 二、软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | man-db |
| 版本 | 2.13.1 |
| 官方网站 | https://www.nongnu.org/man-db/ |
| 下载地址 | https://download.savannah.nongnu.org/releases/man-db/man-db-2.13.1.tar.xz |
| 构建系统 | Autotools (configure) |

## 三、鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel |
| 架构 | aarch64 |
| 编译器 | Clang 15.0.4 |
| C 库 | musl libc |
| 工具链 | LLVM (ld.lld) |

## 四、依赖关系

### 4.1 必需依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| gdbm | 1.23 | 手册页索引数据库存储 |
| bzip2 | 1.0.8 | .bz2 压缩手册页解压 |
| libpipeline | 1.5.8 | 管道处理框架 |
| groff | 1.23.0 | 运行时依赖，手册页格式化渲染 |

### 4.2 可选依赖

无。

## 五、编译步骤

### 5.1 下载和解压源码

```bash
cd $HOME
mkdir -p man-db-src
cd man-db-src
curl -LO https://download.savannah.nongnu.org/releases/man-db/man-db-2.13.1.tar.xz
tar -xf man-db-2.13.1.tar.xz
mv man-db-2.13.1/* .   # 将内容展开到 man-db-src 目录
```

### 5.2 VPATH 构建设置

man-db 需要较高版本的 automake (≥1.17)，但 HarmonyOS 系统仅提供 automake 1.16.5。为避免 configure 过程重新生成 Makefile 导致版本检查失败，使用 VPATH 构建策略（源码目录和构建目录分离）：

```bash
mkdir -p $HOME/build-man-db
cd $HOME/build-man-db
```

### 5.3 应用补丁

在源码目录中应用补丁：

```bash
cd $HOME/man-db-src

# 补丁 1: HarmonyOS 系统检测（config.guess/config.sub）
# 补丁 2: 去除 MAN_OWNER 依赖（lib/security.c / config.h）
# 补丁 3: charset_table 设备修复（lib/encodings.c）
# 补丁 4: nroff 设备修复（src/man.c）
```

详细补丁内容见 [第六节](#六补丁说明)。

### 5.4 配置

```bash
cd $HOME/build-man-db

export PREFIX=$HOME/usr/local
export CFLAGS="-fPIC -O2"

# 绕过 automake 版本检查（系统 automake 1.16.5 不满足 ≥1.17 要求）
export ACLOCAL="/bin/true"
export AUTOHEADER="/bin/true"
export AUTOMAKE="/bin/true"

$HOME/man-db-src/configure \
    --prefix=$PREFIX
```

**关键配置说明：**

| 选项/变量 | 说明 |
|-----------|------|
| `--prefix=$HOME/usr/local` | 安装路径前缀 |
| `CFLAGS="-fPIC -O2"` | 位置无关代码 + 优化 |
| `ACLOCAL=/bin/true` | 绕过 automake 版本不匹配问题 |
| `AUTOHEADER=/bin/true` | 绕过 automake 版本不匹配问题 |
| `AUTOMAKE=/bin/true` | 绕过 automake 版本不匹配问题 |

> **注意**: SELinux 限制下，FIFO 管道被禁止使用，因此必须使用 `make -j1`（单线程编译），不能使用并行编译。

### 5.5 编译和安装

```bash
cd $HOME/build-man-db
make -j1          # 必须单线程，SELinux 禁用 FIFO
make install
```

### 5.6 安装后配置修改

安装完成后需要修改 `man_db.conf` 配置文件：

```bash
vi $HOME/usr/local/etc/man_db.conf
```

**修改 1: 添加本地 man 路径**

```
MANDATORY_MANPATH /storage/Users/currentUser/usr/local/share/man
```

**修改 2: MANDB_MAP 改为本地路径**

```
MANDB_MAP /storage/Users/currentUser/usr/local/share/man /storage/Users/currentUser/var/cache/man/local
```

**修改 3: DEFINE nroff 去掉不兼容的宏选项**

原配置：
```
DEFINE nroff groff -Tutf8 -mg -msafe -mpadj -mandoc
```

修改为：
```
DEFINE nroff groff -Tutf8 -mandoc
```

原因：groff 1.23.0 没有以下宏包，需移除：
| 宏选项 | 宏文件 | 说明 |
|--------|--------|------|
| `-mg` | g.tmac | groff 宏 |
| `-msafe` | safe.tmac | 安全宏 |
| `-mpadj` | padj.tmac | 段落调整宏 |

### 5.7 安装后初始化

```bash
export PATH=$HOME/usr/local/bin:$PATH
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$HOME/usr/local/lib/man-db:$LD_LIBRARY_PATH
mkdir -p $HOME/var/cache/man/local
mandb -C $HOME/usr/local/etc/man_db.conf -c $HOME/usr/local/share/man
```

## 六、补丁说明

### 6.1 修改文件列表

| 文件 | 补丁编号 | 修改内容 |
|------|----------|----------|
| `config.guess` / `config.sub` | 补丁 1 | HarmonyOS 系统检测 |
| `config.h` | 补丁 2 | #undef MAN_OWNER |
| `lib/encodings.c` | 补丁 3 | charset_table 设备修复 |
| `src/man.c` | 补丁 4 | nroff 设备修复 |

### 6.2 关键修改详解

#### 补丁 1: HarmonyOS 系统检测（config.guess/config.sub）

**问题背景**: autotools 的 `config.guess` 脚本无法识别 HarmonyOS 系统，`config.sub` 无法识别 `linux-ohos` 操作系统标识。

**解决方案**: 与所有 autotools 项目相同的 HarmonyOS 补丁模板。

**config.guess 修改** — 添加 `__OHOS__` LIBC 检测和 HarmonyOS case：

```c
*:HarmonyOS:*:*)
    # HarmonyOS/OpenHarmony detection
    case "$UNAME_MACHINE" in
        aarch64|arm64)
            echo "aarch64-unknown-linux-ohos"
            ;;
        armv7*|arm*)
            echo "arm-unknown-linux-ohos"
            ;;
        x86_64|amd64)
            echo "x86_64-unknown-linux-ohos"
            ;;
        i?86)
            echo "i686-unknown-linux-ohos"
            ;;
        *)
            echo "$UNAME_MACHINE-unknown-linux-ohos"
            ;;
    esac
    exit ;;
```

**config.sub 修改** — 三处支持：

1. **maybe_os 匹配**（第 118 行附近）: 添加 `ohos-linux` 匹配
2. **OS 允许列表**: 添加 `ohos*` 到操作系统允许列表
3. **kernel-os 验证**: 添加 `linux-ohos*` 到合法 kernel-OS 组合

#### 补丁 2: 去除 MAN_OWNER 依赖

**问题背景**: HarmonyOS 没有 `man` 系统用户。`lib/security.c` 中的 `get_man_owner()` 函数调用 `getpwnam("man")`，在用户不存在时返回 NULL。调用方对返回值进行解引用，导致段错误。

**解决方案**: 在 `config.h` 中将 `#define MAN_OWNER "man"` 改为 `#undef MAN_OWNER`。

```c
/* 原始 */
#define MAN_OWNER "man"

/* 修改为 */
#undef MAN_OWNER
```

**效果**: MAN_OWNER 未定义时，`security.c` 中整个权限相关的代码（包括 `get_man_owner()`）在编译时被 `#ifdef MAN_OWNER ... #endif` 排除，避免了 NULL 解引用。

#### 补丁 3: charset_table 设备修复

**问题背景**: `lib/encodings.c` 中的 `charset_table` 数组使用 `"locale"` 作为 groff 设备名，但 groff 1.23.0 没有 `devlocale` 设备目录。

**解决方案**: 将 `"locale"` 改为 `"utf8"`：

```c
/* 原始 */
{"locale", "locale", ...}

/* 修改为 */
{"utf8", "utf8", ...}
```

#### 补丁 4: nroff 设备修复

**问题背景**: `src/man.c` 中 `HEIRLOOM_NROFF` 分支设置 `roff_device = "locale"`，但 groff 1.23.0 没有 locale 设备。

**解决方案**: 将 `"locale"` 改为 `"utf8"`：

```c
/* 原始 */
roff_device = "locale";

/* 修改为 */
roff_device = "utf8";
```

## 七、遇到的问题

### 问题 1: automake 版本不匹配

**现象**:
```
configure: error: Automake 1.17 or better is required.
```

**原因**: man-db 2.13.1 需要 automake ≥ 1.17，但 HarmonyOS 系统提供的是 automake 1.16.5。

**解决方案**: 使用 VPATH 构建（源码目录与构建目录分离），同时设置环境变量绕过 automake：
```bash
export ACLOCAL="/bin/true"
export AUTOHEADER="/bin/true"
export AUTOMAKE="/bin/true"
```

VPATH 构建是避免 autotools 重新生成 Makefile 的关键策略。

### 问题 2: MAN_OWNER NULL 解引用段错误

**现象**: 编译成功但运行时 `man` 命令段错误。

**原因**: HarmonyOS 没有 `man` 系统用户，`getpwnam("man")` 返回 NULL，调用方解引用 NULL。

**解决方案**: 在 `config.h` 中 `#undef MAN_OWNER`，使权限相关代码在编译时被排除。

### 问题 3: groff 设备不存在

**现象**:
```
groff: can't find `devlocale' description file
```

**原因**: groff 1.23.0 移除了 locale 设备。

**解决方案**: 将所有引用 `"locale"` 设备的地方改为 `"utf8"`（见补丁 3 和补丁 4）。

### 问题 4: groff 宏包不存在

**现象**:
```
groff: can't find `g.tmac'
groff: can't find `safe.tmac'
groff: can't find `padj.tmac'
```

**原因**: groff 1.23.0 相比旧版移除了 `g.tmac`、`safe.tmac`、`padj.tmac` 宏包。

**解决方案**: 在 `man_db.conf` 中移除 `-mg`、`-msafe`、`-mpadj` 选项：
```
DEFINE nroff groff -Tutf8 -mandoc
```

### 问题 5: musl iconv 不支持 //IGNORE 后缀

**现象**:
```
iconv_open ("UTF-8//IGNORE", "utf-8") Invalid argument
```

**原因**: `manconv` 工具调用 `iconv_open` 时使用 `"UTF-8//IGNORE"` 格式，这是 glibc 特有的扩展。musl libc 的 iconv 实现不支持 `//IGNORE` 等后缀。

**影响**: mandb 运行时所有 man page 的 whatis parse 失败。`apropos` 和 `whatis` 搜索不可用，但 man page 正常显示不受影响。

**解决方案**: 暂无完美解决方案。这是 musl 和 glibc 的行为差异，需要上游 man-db 或 musl 适配。

### 问题 6: SELinux 限制

| 限制 | 影响 | 解决方案 |
|------|------|----------|
| 不能从 `$HOME/tmp` 执行二进制 | FIFO 管道被禁 | `make -j1` 单线程编译 |
| `ln -sf` 软链接无法被动态链接器跟随 | 共享库加载失败 | 用 `cp` 代替 `ln -s` 安装 .so 文件 |

## 八、安装结果

### 8.1 安装的文件

```
$HOME/usr/local/
├── bin/
│   ├── man              # 手册页查看器
│   ├── mandb            # 手册页数据库管理
│   ├── manpath          # 显示 man 搜索路径
│   ├── apropos          # 关键词搜索手册页
│   ├── whatis           # 简要描述搜索
│   ├── catman           # 批量格式化手册页
│   ├── man-recode       # 手册页编码转换
│   ├── accessdb         # 访问手册页数据库
│   └── zsoelim          # 处理 .so 引用
├── lib/
│   └── man-db/
│       ├── libman-2.13.1.so      # man 库
│       └── libmandb-2.13.1.so    # mandb 库
├── libexec/
│   └── man-db/
│       ├── manconv         # 字符编码转换工具
│       └── globbing        # 文件名通配处理
├── etc/
│   └── man_db.conf         # 主配置文件
└── share/
    └── man/                # man-db 自带手册页
```

### 8.2 验证结果

| 测试项 | 结果 | 说明 |
|--------|------|------|
| `man man` | ✅ 成功 | 显示 man-db 自带手册页，带 ANSI 颜色格式化 |
| `apropos man` | ❌ 失败 | musl iconv //IGNORE 兼容性问题 |
| `whatis man` | ❌ 失败 | musl iconv //IGNORE 兼容性问题 |

### 8.3 已知问题

- **mandb whatis parse 失败**: `iconv_open("UTF-8//IGNORE", "utf-8")` 返回 Invalid argument。原因是 musl libc 的 iconv 不支持 glibc 的 `//IGNORE` 后缀。影响 `apropos` 和 `whatis` 功能，但 man page 显示不受影响。

## 九、经验总结

### 9.1 关键经验

| 经验 | 详情 |
|------|------|
| VPATH 构建 | 源码目录与构建目录分离，避免 autotools 重生成 Makefile，是处理 automake 版本不匹配的关键策略 |
| MAN_OWNER 处理 | 未定义 MAN_OWNER 时，security.c 中权限代码被编译时排除，避免 NULL 解引用 |
| groff 设备适配 | groff 1.23.0 没有 locale 设备，需改用 utf8；且移除了 g/safe/padj 宏包 |
| musl iconv 限制 | musl 不支持 glibc 的 `//IGNORE` 扩展，影响 manconv 的 whatis 解析功能 |
| SELinux 限制 | FIFO 被禁需 `make -j1`；软链接不可用需 `cp` 代替 `ln -s` |
| automake 绕过 | 设置 `ACLOCAL=/bin/true` 等环境变量绕过版本检查 |

### 9.2 依赖关系图

```
man-db
├── gdbm 1.23          (编译时，索引数据库)
├── bzip2 1.0.8        (编译时，压缩手册解压)
├── libpipeline 1.5.8  (编译时，管道框架)
└── groff 1.23.0       (运行时，手册页渲染)
```

### 9.3 与其他项目的对比

| 项目 | 特点 |
|------|------|
| man-db | 现代 man 实现，使用 gdbm 索引，支持压缩手册 |
| man-db (glibc) | 在 glibc 系统上功能完整，apropos/whatis 正常 |
| mandoc (OpenBSD) | 轻量级替代方案，不依赖 groff |

## 十、参考资料

- man-db 官方网站: https://www.nongnu.org/man-db/
- man-db 源码下载: https://download.savannah.nongnu.org/releases/man-db/
- groff 官方文档: https://www.gnu.org/software/groff/
- musl iconv 文档: https://musl.libc.org/
- Autotools HarmonyOS 移植指南: 参考 gdbm 归档的 config.guess/config.sub 补丁

---

*文档生成时间: 2026-03-23*
