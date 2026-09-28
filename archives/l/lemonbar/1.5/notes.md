# lemonbar 1.5 适配笔记

## 编译环境
- 构建系统: makefile（上游 1.5 为纯 POSIX Makefile，无 configure）
- 编译日期: 2026-09-21
- 编译器: clang（来自 conan profile `tools.build:compiler_executables.c`，设备上为 Harmonybrew OHOS SDK clang）
- 目标平台: HarmonyOS PC / aarch64-linux-ohos（armv8）
- 状态: built

## 上游审计（先于动手，避免误判）

| 项 | 结论 | 证据 |
|----|------|------|
| 测试套件 | **无** | tarball 仅 7 个文件（.gitignore/LICENSE/Makefile/README.pod/lemonbar.c/utils.c/utils.h）；Makefile target 只有 all/doc/debug/clean/install/uninstall/.c.o，无 check/test；无 autotools/meson/cmake；`check.yml` 末行 `./lemonbar -h \|\| exit 0` 无条件成功 |
| 构建系统 | 纯 Makefile | `CC ?= gcc`、`CFLAGS += ...`、`LDFLAGS += -lxcb -lxcb-xinerama -lxcb-randr` |
| 产物 | 单个可执行文件 | `EXEC = lemonbar`（lemonbar.c + utils.c） |
| 手册 | 需 `pod2man` | `doc:` target 跑 pod2man 生成 lemonbar.1；构建机不保证有该工具，本包不附带 man |

## 编译步骤
```bash
# 配方内构建命令（R9）-j1；VERSION 以命令行变量覆盖 Makefile 回退值
make -j1 CC=<ohos-clang> VERSION=1.5

# 注入依赖路径走环境变量，不走 make 命令行变量
export CFLAGS="-I<libxcb-include>"
export LDFLAGS="-L<libxcb-lib> -L<libxau-lib> -L<libxdmcp-lib> \
  -Wl,--disable-new-dtags -Wl,-rpath,'\$ORIGIN'"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 产出自报版本为 **1.4**，而适配的是 v1.5 | Makefile 形如 `VERSION = 1.4` + `GIT_DESC=$(shell test -d .git && git describe --always)` + `ifneq "$(GIT_DESC)" "" VERSION=$(GIT_DESC) endif`；tag 归档内没有 `.git`，探测为空 → 条件赋值不生效 → 回退硬编码常量（上游从未随 tag 上调该常量） | 构建时以**命令行变量** `VERSION=1.5` 传入（命令行赋值优先级最高，覆盖 Makefile 的一切赋值）。零补丁 |
| 2 | 若按上游 CI 的写法 `make CFLAGS='-I... -DWITH_XINERAMA=1'`，会丢上游默认编译标志 | GNU make 中命令行变量等价于被 `override`：Makefile 里的 `CFLAGS += -Wall -std=c99 -Os -DVERSION -D_GNU_SOURCE` 对命令行赋值的变量**不再追加**，全部丢失（`-DVERSION` 丢失后 `printf(... VERSION)` 的 VERSION 成为未定义标识符） | 依赖路径改经**环境变量** `CFLAGS`/`LDFLAGS` 注入——Makefile 的 `+=` 对来自环境变量的值照常追加，上游默认标志一个不丢；`VERSION` 单独用命令行变量传 |
| 3 | `-Wl,-rpath,$ORIGIN` 写成裸 `$ORIGIN` 会被 shell 展开成空 | make 的链接行由 shell 执行，`$ORIGIN` 会被 shell 变量展开 | LDFLAGS 中写成 `-Wl,-rpath,'$ORIGIN'`（含字面单引号），shell 剥引号后把 `$ORIGIN` 原样交给链接器；并加 `-Wl,--disable-new-dtags` 强制 DT_RPATH |
| 4 | 无 X server 时程序只能走到失败路径，`-h`/版本输出不可达 | `main()` 在 `getopt()` **之前**调用 `xconn()`；`xconn()` 在 `xcb_connect()` 失败时 `fprintf(stderr, "Couldn't connect to X\n"); exit(EXIT_FAILURE)` | 接受该上游行为并**把它当成断言对象**：test_package 断言退出码 1 + stderr 原文，同时断言「无加载器错误」——能走到这句就证明整条动态链接链解析成功 |
| 5 | README 宣称支持 Xinerama，Makefile 却从不定义 `WITH_XINERAMA` | 整个仓库无任何地方定义该宏（Makefile 无 `-DWITH_XINERAMA`，无 config.h）；上游靠 `.github/workflows/check.yml` 的 `CFLAGS='-DWITH_XINERAMA=1'` 在**命令行**打开它 | 本包保持与上游默认 `make` 一致的编译面（不额外打开），因为这是特性开关而非适配所需；`-lxcb-xinerama` 仍按上游 Makefile 无条件链接 |
| 6 | `make install` 依赖 `install(1)`；`make doc` 依赖 `pod2man` | CI worker PATH 不保证有这两个工具 | `package()` 直接 `copy()` 产物到 `bin/`（并 `chmod 0755`），不执行上游 install/doc；手册不随包分发 |
| 7 | 运行期 `.so` 找不到 | OHOS musl 加载器忽略 `LD_LIBRARY_PATH`；构建机无系统 libxcb | `$ORIGIN` rpath + 把 `libxcb*.so*` / `libXau*.so*` / `libXdmcp*.so*` 一并装入 `bin/`（xeyes/myman 同款） |
| 8 | CI L2 smoke 以 `--version`/`--help` 探测二进制 | lemonbar 无长选项；且 `xconn()` 先于 getopt，任何参数组合在无 X 时都只得到连接错误 | L2 为**非阻塞**项（见 `ci/conan/build_and_test.sh` 的 `[warn] ... (non-blocking)`）；test_package 已实测真实启动语义并如实断言 |

## 源码修改

无平台宏、无补丁（`patches/` 为空 `{}`）。`lemonbar.c`/`utils.c` 未经修改即可在 OHOS aarch64 编译。唯一的构建期干预是两个 make 变量：`CC`（来自 conan conf，R33）与 `VERSION=1.5`（修正 tag 归档的版本回退）。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| libxcb | 1.17.0.1 | `<xcb/xcb.h>` 协议绑定；组件 `xcb`（核心）、`xcb-randr`、`xcb-xinerama` |
| libxau | 1.0.12 | `libxcb.so.1` 的 `DT_NEEDED`（X 授权） |
| libxdmcp | 1.1.5 | `libxcb.so.1` 的 `DT_NEEDED`（XDMCP） |

均为 ohpcd 已发布的 OHOS armv8 binary（`conan list ... -r ohpcd` 核实）。`xorgproto` 作为 libxcb 的传递头依赖自动带入。

## 验证结果

```text
# 上游测试：本包上游**没有**测试套件（真实计数 0，审计证据见
#   test_package/MANIFEST.yml 的 upstream_test_audit；非“未运行”）
# 构建：make -j1 CC=<ohos-clang> VERSION=1.5 → bin/lemonbar（arm64 ELF）
# test_package 功能测试（sh test_lemonbar.sh）：8/8 PASS
1..8
ok - lemonbar is installed on PATH and executable
ok - exits 1 when no X display is available
ok - reports "Couldn't connect to X" on stderr
ok - writes nothing to stdout on the failure path
ok - DISPLAY=:99 (nothing listening) fails the same way
ok - -h exits 1 with the X error instead of printing help
ok - no dynamic loader errors (bundled libxcb chain resolved)
ok - runtime libraries are bundled next to the binary
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/lemonbar | 主程序（arm64 ELF，自报 version 1.5） |
| bin/libxcb.so* / libxcb-randr.so* / libxcb-xinerama.so* | xcb 运行期库 |
| bin/libXau.so* / libXdmcp.so* | libxcb 的传递运行期依赖 |

## 注意事项

- 产物为可执行命令，已在软件级 `archives/l/lemonbar/commands.json` 声明（R38）。
- lemonbar 需要**可连接的 X server** 才能做任何事；本包在无 X 环境下的行为（退出码 1 + `Couldn't connect to X`）是上游设计，不是适配缺陷。
- 上游 Makefile 的 `WITH_XINERAMA` 开关**不在 Makefile 里**：若某个平台需要 Xinerama，必须由打包方显式传 `-DWITH_XINERAMA=1`（仅经环境变量或命令行 `CFLAGS`）；本包有意不打开，以与上游默认 `make` 产物保持一致的编译面。
- 手册（`lemonbar.1`）未随包分发：生成需要 `pod2man`，构建机不保证存在。命令行语义以上游 `README.pod` 为准。
- 若后续需要真实渲染验证，须在带 X server 的环境（真机/开发机）上运行，CI 构建机无 X server。
