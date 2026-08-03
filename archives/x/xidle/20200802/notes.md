# xidle 20200802 适配笔记

## 编译环境
- 构建系统: custom (BSD bmake + bsd.prog.mk 上游，HarmonyOS 无 bmake，直接 clang 编译)
- 编译日期: 2026-07-31
- 编译器: clang 15
- 状态: built

## 上游分析

xidle 是 MirBSD 项目的一个 X11 工具，由 Federico G. Schwindt 编写，用于在用户空闲或鼠标移动到屏幕边缘时运行指定程序（通常是 xlock）。

### 源码结构

```
xidle-20200802/
├── Makefile          # BSD bmake Makefile，include bsd.prog.mk
├── xidle.c           # 主程序
├── strtonum.c        # OpenBSD strtonum(3) 实现
├── xidle.1           # man page
└── debian/
    ├── mbsdport.h    # MirBSD 可移植层头文件
    ├── rules         # Debian 构建规则
    ├── changelog
    ├── control
    ├── copyright
    ├── install
    ├── manpages
    └── source/
```

### 构建系统决策

上游使用 BSD 的 `bmake` 配合 `bsd.prog.mk` 构建，Debian/rules 中通过 `bmake -m /usr/share/bmake/mk-netbsd` 调用。HarmonyOS PC 上没有 bmake 或 bsd.prog.mk，因此本配方直接用 clang 编译 `xidle.c` 和 `strtonum.c`。

关键编译参数（来自 debian/rules 分析）：
- `-DNEED_STRTONUM`：启用 strtonum.c 中 `strtonum` 函数定义
- `-DMBSDPORT_H="debian/mbsdport.h"`：包含可移植层头文件
- `-D_FILE_OFFSET_BITS=64`：64-bit 文件偏移
- `-Wall -Wextra -Wformat`：警告

链接参数（来自上游 Makefile）：
- `-lXss -lXext -lX11`：X11 ScreenSaver 扩展、Xext、X11

### 上游测试套件审计

**审计结论：上游无测试套件。**

1. 源码包仅含 `xidle.c`、`strtonum.c`、`Makefile`、`xidle.1`，无任何 test/ 目录或测试源文件。
2. 上游 `Makefile` 仅定义 `PROG=xidle` 和 `SRCS`，include `bsd.prog.mk`，无 `check`/`test` 目标（bsd.prog.mk 不提供 check 目标）。
3. Debian `debian/rules` 中无 `override_dh_auto_test`，也无任何测试调用；`override_dh_auto_build` 仅执行 `bmake depend && bmake xidle && test -x xidle`（此处 `test -x` 是 shell 内建测试，非测试框架）。
4. Debian `debian/control` 的 `Build-Depends` 仅含 `debhelper-compat`, `bmake`, `libxss-dev`，无 `libtest-*` 或测试框架依赖。

因此本配方在 `test_package/MANIFEST.yml` 声明 `upstream_tests_exist: false`，并提供 `test_package/` 消费者测试（实际调用 xidle 二进制）。

## 编译步骤

1. 源码获取：从 Debian pool 下载 `xidle_20200802.tar.xz`
2. 解压后进入源码目录
3. 编译 xidle.c：
   ```bash
   clang -Wall -Wextra -Wformat \
     -D_FILE_OFFSET_BITS=64 \
     -DNEED_STRTONUM \
     -DMBSDPORT_H=\"debian/mbsdport.h\" \
     -I${DEFAULT_PREFIX}/include \
     -c xidle.c -o xidle.o
   ```
4. 编译 strtonum.c：
   ```bash
   clang -Wall -Wextra -Wformat \
     -D_FILE_OFFSET_BITS=64 \
     -c strtonum.c -o strtonum.o
   ```
5. 链接：
   ```bash
   clang xidle.o strtonum.o \
     -L${DEFAULT_PREFIX}/lib \
     -lXss -lXext -lX11 \
     -o xidle
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bmake + bsd.prog.mk 不可用 | HarmonyOS PC 无 BSD make 工具链 | 直接用 clang 编译 xidle.c + strtonum.c，绕过 bmake |
| 2 | `__progname` 符号可能缺失 | MirBSD/OpenBSD 扩展，HarmonyOS bionic 不提供 | 上游 `<err.h>` 已处理；如缺失可在 mbsdport.h 定义 `#define __progname program_invocation_short_name` |
| 3 | `_PATH_DEVNULL` 路径 | glibc/musl 定义为 `/dev/null`，HarmonyOS 一致 | 无需修改 |

## 源码修改

- 无源码补丁；通过编译参数 `-DNEED_STRTONUM -DMBSDPORT_H` 复用上游自带的可移植层。

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| libx11 | 6.4.0 | cmd-pkgs 预装 |
| libxext | 6.4.0 | cmd-pkgs 预装 |
| libxss | 1.2.3 | 自建：cmd-pkgs 仓库无 libxss 预编译包，从上游 libXss 1.2.3 源码 vendor `src/XScrnSaver.c`，build 阶段 clang 编成 `libXss.so.1` 装进 ~/usr/local/lib |
| xorgproto | 2024.1 | cmd-pkgs 预装 |

## 验证结果

```bash
$ file xidle
xidle: ELF 64-bit LSB executable, ARM aarch64, dynamically linked, not stripped

$ readelf -d xidle | grep NEEDED
NEEDED libXss.so.1
NEEDED libXext.so.6
NEEDED libX11.so.6
NEEDED libc.so
```

test_package 验证：编译链接 xidle 的消费者测试程序，运行 `xidle --help` 验证二进制可执行。

## 注意事项

- xidle 是 X11 图形程序，运行时需要 X server；headless 环境下 `XOpenDisplay` 会失败（exit 1），这是预期行为。
- 上游无测试套件，本配方提供 test_package 消费者测试（调用 xidle 二进制验证 `--help` 退出码）。
- 上游测试为本地实测，CI 侧未接入门禁。
- **libXss 自建**：cmd-pkgs 仓库（OpenHarmonyPCDeveloper/cmd-pkgs 的 pkgs release，2193 个 assets）经 GitCode API 全量枚举确认**不存在任何 libxss 预编译包**（无论 1.2.0 或 1.2.3），配方若从 cmd-pkgs 下载 libxss 必然 404，导致链接 `ld.lld: unable to find library -lXss`。改为从上游 libXss 1.2.3 源码包 vendor `src/XScrnSaver.c`（单文件实现），build 阶段用 clang `-fPIC -shared` 编成 `libXss.so.1` 装进 ~/usr/local/lib，并建 `libXss.so` 软链供 `-lXss` 解析。编译所需 X11 内部头（Xlibint.h/Xext.h/extutil.h/saverproto.h/saver.h）由 cmd-pkgs libx11-6.4.0 包自带，scrnsaver.h（公共 API 头）从 libXss 源码 vendor。
- **__progname shim**：xidle.c 第 98 行 `extern char *__progname;` 依赖 libc 提供该 BSD libc 全局符号，但 HarmonyOS 的 musl libc 既无 `__progname` 也无 `program_invocation_name`/`program_invocation_short_name`（皆 glibc 扩展，musl 不实现）。配方曾在 ohos-mbsdport.h 里 `#define __progname program_invocation_short_name`，导致 `ld.lld: undefined symbol: program_invocation_short_name`。改为配方自带 shim `ports/ohos-progname.c`：定义 `char *__progname = "xidle";` 并用 `__attribute__((constructor))` 在 main 前从 `/proc/self/cmdline` 读 argv[0] basename 填入，build 阶段把该 .o 编入链，链接缺失符号即解。上游原版 `debian/mbsdport.h` 不定义 `__progname`，本配方保持一致，仅额外提供 shim 源文件。
