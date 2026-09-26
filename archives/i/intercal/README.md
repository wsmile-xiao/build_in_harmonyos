# intercal 0.30 for HarmonyOS PC

## 概述

INTERCAL（International Corfu-Optimized Recursive Computer Access Language，0.30）在 HarmonyOS / OpenHarmony（aarch64, musl libc）上的编译记录与测试说明。INTERCAL 是一门 Esoteric 编译型语言：`ick` 将 `.i` 源码翻译为 C，再由目标平台 C 编译器产出原生可执行文件。本次交付为命令行工具（`package_type=application`）。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | intercal |
| 版本 | 0.30 |
| 上游主页 | https://www.catb.org/~esr/intercal/ |
| 源码包 | http://catb.org/~esr/intercal/intercal-0.30.tar.gz |
| sha256 | b38b62a61a3cb5b0d3ce9f2d09c97bd74796979d532615073025a7fff6be1715 |
| 构建系统 | autotools（含嵌套 autoconf `buildaux/buildconfig`） |
| 交付物 | bin/ick（INTERCAL 编译器）、bin/convickt（源码转换器） |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 目标三元组 | aarch64-unknown-linux-ohos |
| 架构 | aarch64 |
| 编译器 | clang / clang++ 15（libc++ / musl） |
| 构建并发 | -j1（`-fcommon` 见下） |

## 编译步骤（配方视角）

1. 从 `self.conf` 的 `tools.build:compiler_executables` 解析 cc/ar/ranlib（R33，不读裸 shell 环境变量）。
2. 在构建目录建 `_toolshim`，软链 `ar→llvm-ar`、`ranlib→llvm-ranlib`、`gcc/cc→OHOS clang` 并置于 PATH 最前——`configure` 以 `env -i "PATH=$PATH"` 调用嵌套 `buildconfig`，会剥掉 CC/AR/RANLIB/TMPDIR，只有 PATH 能穿透。
3. 播种随包的 `prebuilt/{parser.c,parser.h,lexer.c,oil-oil.c}`，并把 `parser.y/lexer.l/oil.y` 的 mtime 调旧，阻止 make 用空 `$(YACC)` 重生成。
4. `configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`。
5. `make -j1 CFLAGS='-g -O2 -fcommon'`：`-fcommon` 用于兼容 clang 默认 `-fno-common` 与 intercal 遗留的重复暂定定义 `int yydebug;`（lld duplicate-symbol）。
6. `make install`（无 DESTDIR）：`ICKINCLUDEDIR/ICKDATADIR` 在编译期烤进二进制指向 `$(prefix)/...`，按 package_folder 安装后 `ick` 自定位运行时。

## 源码补丁

| 补丁 | 作用 |
|------|------|
| `0001-configure-portability.patch` | `configure` 两处 `umask 077`→`022`（HMDFS mktemp/subs1.awk 权限，E011）；嵌套 `buildconfig` 调用前注入 `TMPDIR=$PWD`（`env -i` 剥 TMPDIR、`/tmp` 只读） |
| `0002-buildconfig-umask-022.patch` | `buildaux/buildconfig` 两处 `umask 077`→`022` |

## 编译状态

- ✅ 编译打包通过：`conan create` 在设备真机（OHOS aarch64）成功产出 `ick`/`convickt`。
- ✅ 消费者测试通过：`test_package` 用装好的 `ick -b hello.i` 编译并运行 INTERCAL 程序，stdout 断言 `hello, world`。
- ⚠️ 上游回归套件受平台限制：静态注册 30 例，本机真实执行并通过 7 例，跳过 23 例（详见下）。

## 已知限制（no-bison / 2010-era 旧解析器）

本 OHOS 设备**无 bison/flex/yacc**，且 0.30 发行 tarball 仅冻结了 2010-09-02 的 `prebuilt/parser.c`（当前语法只存于 `src/parser.y`，本机无法重生成）。因此 `ick` 只能编译 2010 语法子集内的程序：

- `noexe`（20 例）：使用后 2010 构造（COME FROM 扩展、所有格/受控一元操作符等），旧解析器在**编译期**以 ICL997I/ICL405I 拒绝，出码失败 → 无二进制。
- `nochk`（2 例：quine、yapp）：随包无对应 `.chk`（由上游运行时动态生成），无法逐字节比对。
- `timeout`（1 例：tests/count）：按设计为死循环（旧 parser 下不收敛），60s 超时后计为 SKIP。

**这不是配方缺陷，而是目标缺 bison 的平台限制。** 未静默删除任何用例，逐例给出原因（§10）。相关可复用机制已沉淀为路径 B 知识草稿：`knowledge/drafts/DRAFT-intercal-0.30-no-bison-stale-prebuilt-parser.{kv,md}`。
