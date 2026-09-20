# libhistory for OpenHarmony (HarmonyOS)

本包为 GNU History 库（libhistory）提供 OpenHarmony（鸿蒙）适配。libhistory 与
GNU readline 同源同版发布，负责命令行历史记录管理（记录、检索、读写历史文件），
不含行编辑功能。通过修改 autotools 的配置脚本让构建系统识别鸿蒙平台，并以静态
方式交付，可安全链入鸿蒙 PC 上的共享库与应用。

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | libhistory |
| 版本 | 8.3.3 |
| 官网 | https://tiswww.cwru.edu/php/chet/readline/rltop.html |
| 源码下载 | https://ftp.gnu.org/gnu/readline/readline-8.3.tar.gz |

### 版本语义

libhistory 无独立上游 tarball，随 readline 同源发布：

- 源码基线：readline-8.3.tar.gz（GNU 官方 FTP）
- 官方补丁：readline83-001、readline83-002、readline83-003
- 8.3.3 = readline-8.3 + 前 3 个官方补丁，沿用官方 readline-8.2.13 的
  「基线.补丁数」命名惯例

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 代码准备

- 下载代码使用官方代码下载
  ```bash
  wget https://ftp.gnu.org/gnu/readline/readline-8.3.tar.gz
  tar -xzf readline-8.3.tar.gz
  cd readline-8.3
  ```

- 应用官方补丁与本适配补丁（readline83-00*.patch 为官方 context 补丁的 unified
  等价转换，git apply 全链回验与官方原文件应用产物逐字节一致）
  ```bash
  git apply readline83-001.patch readline83-002.patch readline83-003.patch
  patch -p1 < 0001-config.guess.patch
  ```

## 编译步骤

### 1. 配置

```bash
# ⚠️ 关键：必须设置 CFLAGS="-fPIC"，否则静态库链接到共享库会报错
CFLAGS="-fPIC -O2" ./configure --prefix=$HOME/usr/local --enable-static --disable-shared
```

### 2. 编译

```bash
make -j$(nproc)
```

### 3. 安装（仅保留 history 组件）

```bash
make install
rm -f $HOME/usr/local/lib/libreadline*
rm -f $HOME/usr/local/lib/pkgconfig/readline.pc
```

## ⚠️ 关键注意事项

### CFLAGS="-fPIC" 必须设置

OHOS 的 musl libc 默认 BIND_NOW（符号立即解析），静态库链入共享库时必须
带 -fPIC，否则报 `relocation R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC`。

### 系统同名库必须静态编译 (R26)

readline/libhistory 是系统同名库族，构建 .so 会污染 `/lib`、`/lib64`，
统一 `--enable-static --disable-shared`。

### history 库无需 curses

history 库不使用 termcap/ncurses（只有 readline 行编辑库需要），本包构建
不传 `--with-curses`，无 curses 依赖。

### HMDFS 上 configure 的 umask 问题

HMDFS 文件系统 umask 077 会阻止 config.status 在 mktemp 创建的目录内写入，
需将 configure 中 `umask 077` 改为 `umask 002`（conanfile.py build() 已处理）。

## 编译结果

安装后本包交付（Conan 包已剔除 readline 组件）：

```
<package>/
├── lib/
│   ├── libhistory.a      # 静态库（带 -fPIC）
│   └── pkgconfig/history.pc
└── include/
    └── readline/
        ├── history.h     # history API
        └── ...           # rltypedefs.h 等 history.h 依赖头（全集保留）
```

使用方式：

```c
#include <readline/history.h>

using_history();
add_history("command");
HIST_ENTRY *e = history_get(history_base);
```

## 依赖关系

### 依赖

- 无（history 库不使用 termcap/ncurses）

### 被依赖

需要命令行历史功能的程序，如各类交互式 CLI、REPL、数据库客户端。
（需要行编辑功能的程序请依赖 readline 包）

## 官方补丁说明（随 8.3.3 版本应用）

| 补丁 | 内容 |
|------|------|
| readline83-001 | input.c：事件钩子等待输入时的死循环修复；patchlevel 0→1 |
| readline83-002 | display.c：rl_save_prompt 后 NULL 指针解引用修复；patchlevel 1→2 |
| readline83-003 | input.c：反向增量搜索中 SIGINT 导致的段错误修复；patchlevel 2→3 |
| 0001-config.guess | config.guess 添加 HarmonyOS 检测（aarch64-unknown-linux-ohos） |

## 验证编译结果

```bash
# 检查包内文件
ls -lh <package>/lib/libhistory.a
ls <package>/include/readline/history.h

# test_package 运行 9 项 API 断言（版本宏、增删查、历史统计与清理）
ctest --output-on-failure -C Release
```

## 参考资料

- readline 官方文档：https://tiswww.cwru.edu/php/chet/readline/rltop.html
- GNU readline FTP：https://ftp.gnu.org/gnu/readline/
- OpenHarmony 官方网站：https://www.openharmony.cn/

## 许可证

本修改遵循 readline 原有许可证（GPL v3）。
