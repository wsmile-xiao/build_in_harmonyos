# lsw 0.3 适配笔记

## 编译环境
- 构建系统: makefile（suckless 纯 Makefile + config.mk，无 configure、无 VPATH）
- 编译日期: 2026-09-22
- 编译器: clang 15（profile: ci/conan/profiles/ohos-aarch64，os=OHOS arch=armv8）
- 状态: built（conan-verify 通过；发布态由 release 流水线确认）

## 编译步骤
1. W0 依赖检查：`bash ci/scripts/preflight_check.sh lsw/0.3` → `[OK] 已发布: libx11/6.4.0`，
   "所有依赖均已发布，可以安全开始适配"。
2. `build()` 内一条 make 命令完成编译（零补丁）：
   `make CC=<conf tools.build:compiler_executables 的 c 项> INCS="<全部 host 依赖的绝对 -I>" LIBS="<全部 host 依赖的绝对 -L> -lX11" lsw`
   —— 覆盖的是上游 `config.mk` 的**聚合变量** `INCS`（=`-I${X11INC}`）与 `LIBS`（=`-L${X11LIB} -lX11`），
   因而无需逐个改写被烧死的 `CC`/`X11INC`/`X11LIB`；上游 `all` 目标只打印 options，
   真实构建目标是 `lsw`。R1 参数最少化：除此之外不传任何 flags。
3. `make install DESTDIR=<包目录> PREFIX=/ MANPREFIX=/share/man`
   （上游 install 用 cp -f + chmod + sed，设备均可用；chmod 在 HMDFS 静默不生效属已知平台
   限制 E046，不影响交付）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.mk 烧死 `CC = cc`，设备无 cc | suckless 惯例（cc/cc89 链接），OHOS 只有 clang | make 命令行覆盖 CC（R33：值来自 conf 而非裸 shell 变量） |
| 2 | config.mk 把 X11INC/X11LIB 烧死为 /usr/X11R6，设备无该目录 | 上游硬编码 X11 安装前缀 | 命令行覆盖聚合变量 INCS/LIBS（见下"症状链"） |
| 3 | 只注入 libx11 一个包的 include 目录仍报缺头 | `X11/Xlib.h` 由 libx11 交付，但其内部 `#include <X11/X.h>` 的协议头属 **xorgproto** 包 | 遍历**全部 host 依赖（含传递）** 收集 includedirs/libdirs，`os.path.join(dep.package_folder, d)` 转绝对路径后拼 `-I`/`-L` |
| 4 | 设备与 CI 均 headless（无 X server、无 Xvfb 可发布），无法正程运行 lsw | XOpenDisplay 必然失败 | 消费者测试走确定性错误路径断言（clipnotify 1.0.2 test_nox.sh 同款，E471 no-display-api-probes 家族）：无 DISPLAY 时 lsw 必须非零退出且 stderr 含 "cannot open display"（lsw.c L18-20），真实执行了 X11 动态链接链加载 |

### 症状链（三层，逐层剥开）

```
# 层 1：原始 make（配方未注入前）
make: cc: No such file or directory                 # Error 127：设备无 cc 别名
# 层 2：只覆盖 CC 后
fatal error: 'X11/Xlib.h' file not found            # -I/usr/X11R6/include 不存在
# 层 3：只把 X11INC 指到 libx11 的 includedirs[0] 后（G2 首错，本包最隐蔽的一层）
.../p/libx17963afb6a17e9/p/include/X11/Xlib.h:44:10: fatal error: 'X11/X.h' file not found
make: *** [Makefile:19: lsw.o] Error 1
```

### 根因

GNU make 语义中**命令行变量覆盖文件内赋值**。上游 `config.mk`（实测行号）：

```
5:PREFIX = /usr/local        8:X11INC = /usr/X11R6/include    12:INCS = -I${X11INC}
6:MANPREFIX = ${PREFIX}/share/man   9:X11LIB = /usr/X11R6/lib 13:LIBS = -L${X11LIB} -lX11
17:CFLAGS = -ansi -pedantic -Wall -Os ${INCS} ${CPPFLAGS}      21:CC = cc
18:LDFLAGS = -s ${LIBS}
```

`CFLAGS`/`LDFLAGS` 只引用聚合变量 `INCS`/`LIBS`，所以在命令行覆盖 `INCS`/`LIBS` 即可
一次性整体替换注入面。层 3 的额外根因是 **X11 头族跨两个 Conan 包**：`X11/Xlib.h` 属
libx11，`X11/X.h`/`Xproto.h` 属 xorgproto 协议头包（归档内 `archives/l/libx11/6.4.0/conanfile.py`
以 `requires("xorgproto/2025.1", transitive_headers=True)` 声明）。另注：
`cpp_info.includedirs`/`libdirs` 是**相对** `package_folder` 的路径，必须 join 成绝对路径再喂 make。

### 最小复现

```sh
# 复现层 3（只注入直接依赖首项）
python3 scripts/ohc-run.py conan-create lsw 0.3     # build() 写成 X11INC=libx11.includedirs[0]
# → Xlib.h:44:10: fatal error: 'X11/X.h' file not found
# 排除"依赖未发布"误判的两步判别（两步均过 ⇒ 属注入面不全，不得 block 依赖）
grep -n "requires\|transitive_headers" archives/l/libx11/6.4.0/conanfile.py   # 见 xorgproto
bash ci/scripts/preflight_check.sh lsw/0.3                                    # 所有依赖均已发布
```

### 已试过的失败方案

1. **只注入单个 include 目录**（`x11.cpp_info.includedirs[0]` → `X11INC=`）：
   G2 挂在层 3 的 `X11/X.h file not found`。已废弃。
2. **打补丁改上游 `config.mk`**（把 `cc`/`/usr/X11R6` 就地改掉）：**未采用**——
   会引入 `patches/*.patch`（审查面变大），并使"零补丁、命令行覆盖聚合变量"这一机制主张
   无法沉淀为知识条目（本包路径 B 承载的就是这条机制）。
3. **把"缺 X11/X.h"当成 xorgproto 未发布去 block 依赖**：**误判**，见上面两步判别证据。
4. 另记一条环境侧假故障（非配方问题）：新建 CONAN_HOME 缺 `remotes.json` 会让
   `preflight_check.sh` 误报 `libx11/6.4.0 未发布`；补齐 `remotes.json`+`global.conf` 后即通过。
   `conan download --only-recipe` 在本远端报 `system acceleration policy not enabled`，
   该探针在此远端不可用作 binary 判据。

### 最终方案

`build()` 单条 make 命令，命令行覆盖聚合变量 `INCS`/`LIBS` 与 `CC`，遍历全部 host 依赖
（含传递）拼绝对 `-I`/`-L`；`patches/` 为空、`conandata.yml` 无 patches 段，上游源码零改动。
实测 RUN 行（`reports/w3-local-ci.log`）：

```
RUN: make CC=/data/service/hnp/bin/clang INCS="-I.../libx11.../include -I.../xtrans.../include
-I.../libxcb.../include -I.../libxau.../include -I.../libxdmcp.../include -I.../xorgproto.../include"
LIBS="-L.../libx11.../lib -L.../libxcb.../lib -L.../libxau.../lib -L.../libxdmcp.../lib -lX11" lsw
→ CC -c lsw.c / CC -o lsw → Package built
```

### 适用边界

- **适用**：suckless 家族（dmenu/dwm/st/slock/lsw/lsx/sselp/sent/tabbed/wmname 等）与一切
  裸 Makefile/config.mk 把编译器与系统路径烧死的 X11 小工具；其中"层 3"（协议头属 xorgproto，
  须遍历全部 host 依赖而非只取直接依赖的 `includedirs[0]`）适用于所有 include `X11/Xlib.h`
  的 OHOS 交叉包，不限于 suckless。
- **不适用**：autotools 包（configure 按平台重算路径）、CMake 包（toolchain 注入路径）。
- **前提**：覆盖聚合变量前须先读 Makefile，确认上游没有在 recipe 内重新赋值 `INCS`/`LIBS`
  （重新赋值会使命令行覆盖失效，届时退回覆盖被引用的路径变量本身）。
- **本包风险点（如实记录，未触发失败）**：`package()` 的 `make install` 未再传 CC/INCS/LIBS
  覆盖，上游 `install: all` 会先打印 options（实测输出 `CC = cc`、`-I/usr/X11R6/include`），
  依赖 in-source 构建产物时间戳新于源码才不重编。当前 in-source 布局下实测通过
  （`Calling package()` → installing executable/manual page），但若上游目标关系变化，
  需给 `make install` 同步传覆盖变量。
- lsw 只依赖 libx11/6.4.0 单包，不出现同家族的 X11 双版本冲突（libxft 钉 libx11/1.8.13
  vs libxinerama 钉 libx11/6.4.0），勿照抄他包的禁用参数。

## 源码修改
无补丁（patches/ 为空）；全部适配通过 make 命令行变量覆盖完成。

## 依赖版本
- libx11/6.4.0（ohpcd 制品仓；transitive_headers/transitive_libs，与归档内 11 个 X11 工具配方同款）
- 传递依赖（同图参与注入）：xorgproto/2025.1、libxcb/1.16、libxau/1.0.11、libxdmcp/1.1.5、xtrans/1.6.0

## 上游测试（R51 五维账本）

| 维度 | 数值 | 依据 |
|------|------|------|
| 静态声明总数 `N_static` | **0** | 上游 tag 源码清点（命令与输出见下） |
| 构建系统注册/可执行数 `N_registered` | **0** | Makefile 9 条目标行中无 test/check/installcheck；无 `TESTS`/`check_PROGRAMS` |
| 上游实测通过数 | **0 / 0** | 无可执行项（分母 0，不虚报） |
| 上游跳过数 / 失败数 | **0 / 0** | 同上 |
| 消费者测试 `N_consumer` | **1** | `test_package/test_lsw_nox.sh`（`N_assertion = 2`，括注） |
| 适配后合计 | **1 项消费者测试，2/2 断言通过** | ≥ `N_static`（1 ≥ 0） |

上游 `N_static = 0` 的清点证据（tarball sha256 与 conandata.yml 声明一致：
`0b3f3ce16eef060df6e0d90327ee82593dfd75281347908698747cfa3f8d0655`）：

```sh
$ grep -nE '^[A-Za-z0-9_.-]+:' Makefile
9:all: options lsw        11:options:      17:.c.o:       21:lsw: ${OBJ}
25:clean:                 29:dist: clean   37:install: all  47:uninstall:
53:.PHONY: all options clean dist install uninstall
$ grep -nE '^[ ]*(check|test|installcheck|check-local)[ ]*:' Makefile   → (none)
$ grep -nE 'TESTS|check_PROGRAMS|RUNTEST' Makefile *.mk                 → (none)
$ grep -rn "make check\|ctest\|pytest" .                                → (none)
$ tar tzf lsw-0.3.tar.gz   # 全量 6 文件
LICENSE  Makefile  README  config.mk  lsw.1  lsw.c
$ find . -type f \( -iname '*test*' -o -iname '*spec*' -o -iname 'check*' \) → 0 个
$ grep -nE '\b(ck_assert|START_TEST|TEST_F|CuTest|EXPECT_)\w*\s*\(' *.c       → (none)
⇒ N_static = 0，N_registered = 0
```

消费者测试口径（防误读）：`test_lsw_nox.sh` 自述 "ALL 2/2 CONSUMER ASSERTIONS PASSED"，
即 **2 组检查点**（与 `test_package/MANIFEST.yml` 的 `assertion_count: 2` 同源）；底层是
3 条否定式判定（`[ -x "$BIN" ]`、`rc -ne 0`、`grep -q "cannot open display"`）。
这 2 组断言**属消费者补位，不是 2 个上游用例**，不得并入 `N_static`。
单看第 1 组（仅查文件存在）不满足赛道二门禁，合格性由第 2 组（真实执行 + 退出码 + stderr 内容）承担。
L1e 破坏性反向测试（把 bin/ 移走后必须失败）已实证该测试真依赖交付物。

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify lsw 0.3      # G0/G1/G2/G3/G4 + L2/L4/L5
$ python3 scripts/ohc-run.py finish lsw 0.3 built       # W2 结构 + R36 依赖 + W3 本地 CI 模拟
# 证据日志：archives/l/lsw/0.3/reports/w3-local-ci.log（15306 B，sha256 7a7edb6dd637903c…）
#   L195 lsw/0.3: Building from source
#   L203 lsw/0.3: Calling build()      L213 lsw/0.3: Calling package()
#   L278-279 OK 1/2 / OK 2/2 → ALL 2/2 CONSUMER ASSERTIONS PASSED
#   L0_RESULT=pass  L1_RESULT=pass  L2_RESULT=skip  L4_RESULT=pass  L5_RESULT=pass
#   [ok] L1e: Negative test confirmed — test genuinely depends on lsw
#   Total: 1  Success: 1  Failed: 0  Pass rate: 100.0%
# .ci-result.json: exit_code=0, step=W3_local_ci
```

> **证据选型（重要）**：`reports/w3-local-ci.log` 才配当"从源码构建 + 测试真跑过"的证据——
> 它含 `Building from source` / `Calling build()` / `Calling package()` 与 2/2 断言原文。
> `reports/conan-create.log`（6741 B）是 **binary cache 命中版**（`lsw/0.3@ohpcd/stable … - Cache`、
> 全程无 `Calling build()`），只能证明包可解析/可安装，**不得**用作编译与测试通过的证据。
> 绿门禁 ≠ 测试跑过：L1a/L1b 与 L1e 是 test_package 真执行的独立判据，两者都要看。
> L2 smoke `skip` 是"lsw 无 --version/--help 处理分支"（suckless 惯例忽略参数），属门禁项非测试用例。

## 注意事项
- 上游 -ansi（C89）+ -Wall 编译干净；`LDFLAGS = -s`（strip）由 lld 支持，无需改动。
- lsw 读取 X root window 的属性（列窗口标题），仅在有 X server 的会话中有实际输出；
  headless 下唯一可观察行为即 XOpenDisplay 失败分支。
- 交付物：`bin/lsw`（1 file）+ `share/man/man1/lsw.1`（1 个 .1 文件）；无库文件，
  故 `package_info()` 清空 includedirs/libdirs/libs，`bindirs=["bin"]`，
  软件级 `archives/l/lsw/commands.json` 声明 `type: tool`（R38/PF8）。
- 路径 B：本包新增机制知识为"裸 Makefile 烧死路径 ⇒ make 命令行覆盖聚合变量 INCS/LIBS +
  遍历全部 host 依赖"，草稿对
  `knowledge/drafts/DRAFT-lsw-0.3-suckless-baked-paths-makevar-override.{kv,md}`，
  关联 Issue #3258；无 X 错误路径断言本身属 E471 家族 hit，不另计 B。
---

**编译结束**: 2026-09-23 01:15
**最终状态**: built
