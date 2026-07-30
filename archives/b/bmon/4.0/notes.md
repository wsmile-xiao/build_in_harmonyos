# bmon 4.0 —— HarmonyOS PC 适配笔记

## 软件概述
bmon 是一个可移植的网络带宽监控与速率估算命令行工具（作者 Thomas Graf），
上游 https://github.com/tgraf/bmon 。产物为可执行文件 `bmon`。

## 依赖分析
bmon 4.0 的构建依赖：
- **libconfuse**（`PKG_CHECK_MODULES([CONFUSE])`，无条件硬依赖，用于解析配置文件）；
- **libnl-3.0 / libnl-route-3.0**（仅 `target_os` 为 `linux*|uclinux*` 时要求，用于 netlink 输入模块）；
- **ncurses**（curses UI 输出模块）；
- **libm**（musl 下并入 libc）。

其中 libconfuse / libnl / ncurses 均**未发布到制品仓**（`conan install --requires` 在 ohpcd
远端返回 "Unable to find ... in remotes"），构建容器 sysroot 也不含这些库/头文件。因此不能声明为
Conan 依赖，需在配方内自包含处理。

## 适配策略（自包含，零外部 Conan 依赖）

### 1. libconfuse —— 源码静态编入
libconfuse 是无法绕过的硬依赖。conandata.yml 以第二源码项 `confuse` 拉取 libconfuse 3.3 官方
发布包，`build()` 中用工具链直接编译 `confuse.c` + `lexer.c`（发布包已内置 flex 生成的 lexer.c，
无需 flex/bison），生成 `libconfuse.a`。为其提供一份最小 `config.h`（现代 musl/POSIX 特性宏），
不运行 libconfuse 自身的 autotools，避免其 config.sub/gettext 链路。

通过给 bmon 的 configure 注入 `CONFUSE_CFLAGS` / `CONFUSE_LIBS` 环境变量，
`PKG_CHECK_MODULES([CONFUSE])` 会直接采用它们并跳过 pkg-config 探测，从而静态链接该 .a。

### 2. libnl / netlink —— 编译移除，改用 /proc/net/dev
目标平台无 libnl。`patches/0001` 将 `src/in_netlink.c` 的顶层守卫改为
`#if !defined(SYS_BSD) && !defined(BMON_NO_NETLINK)`，配合 `-DBMON_NO_NETLINK` 使整个 netlink
输入模块（及其 `<netlink/*.h>` 引用）编译为空。`src/input.c` 的默认输入选择跳过 netlink，直接选用
`proc` 模块（读取 `/proc/net/dev`）。configure 侧的 `LIBNL_*` PKG 检查用空白环境变量绕过。

这是实质性的平台适配：bmon 在 OHOS 上通过 procfs 真实读取各网络接口的 RX/TX 字节与包统计
（test_package 已验证输出接口统计表），并非空壳 stub。

### 3. ncurses / curses UI —— 编译移除，保留文本输出
目标平台无 ncurses。`patches/0001`：
- `include/bmon/config.h`：新增 `BMON_NO_CURSES` 分支，跳过 curses 头文件包含与 `#error`，
  并补齐 `layout.h` 仍会引用的标准 SysV/ncurses 颜色（`COLOR_*`）与属性（`A_*`）常量定义
  （取 ncurses 规范数值，仅供配置解析存储，不参与渲染）；
- `src/out_curses.c`：`-DBMON_NO_CURSES` 下整文件编译为空（不注册 curses 输出模块）；
- `src/conf.c`：`cfg_layout[]` 原仅在 `HAVE_CURSES` 下定义，但配置解析路径无条件引用它，
  故将守卫扩展为 `HAVE_CURSES || BMON_NO_CURSES`（修正上游无 curses 构建时的链接缺失）。

configure 的 `AX_WITH_CURSES` 硬要求彩色 curses，用预置 cache 变量
`ax_cv_curses=yes ax_cv_curses_color=yes` 跳过。bmon 仍提供 `ascii` / `format` 文本输出模块。

### 4. config.sub 识别 ohos 三元组
`patches/0002`：bmon 自带 config.sub（2015-01-01）不识别 `aarch64-*-linux-ohos`，Conan 传入的
`--build=aarch64-...-linux-ohos` 会触发 "Invalid configuration"。补丁在 KERNEL-OS 与 OS 白名单中
加入 `linux-ohos*` / `-linux-ohos*`，规范化后 `target_os=linux-ohos` → 命中 `linux*` → 定义 SYS_LINUX。

### 5. 构建环境细节
- 镜像内无 automake/autoconf；`make`/`make install` 传入
  `ACLOCAL=: AUTOCONF=: AUTOHEADER=: AUTOMAKE=: MAKEINFO=:` 以空化 maintainer 重生成规则，
  避免时间戳漂移触发 Makefile.in 重建（缺 automake 会失败）。

## 验证结果（构建容器，ci/conan/profiles/ohos-aarch64）
- `conan create` 通过；产物 `bin/bmon` 为 ELF aarch64（musl），`readelf -d` 仅 `NEEDED libc.so`
  （libconfuse 静态、无 ncurses/libnl）。
- test_package：`bmon --version` 通过；`bmon -i proc -o ascii` 经 /proc/net/dev 真实读出接口统计表。

## 备注
- 版本号取上游 `4.0`（首次适配）。
- 若后续目标平台提供 libnl/ncurses 预编译包，可回退这些移除补丁、恢复 netlink 输入与 curses UI。
