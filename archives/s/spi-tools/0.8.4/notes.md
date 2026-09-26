# spi-tools 0.8.4 适配笔记（hw-9）

- 任务号：10849（平台 id）；包名/版本：spi-tools/0.8.4；分支：`feat/spi-tools-0.8.4`
- worktree：设备 `~/qzy/hw-9-spi-tools-0.8.4`，基线 `upstream/main` = `32018bae04`（`git ls-remote upstream main` 实测与本地一致）
- CONAN_HOME：`~/tmp/ch/home-hw-9-spi-tools`（global.conf / remotes.json 复制自 `home-hw-9-jaula`，`tools.build:jobs=2` 已核）

## 1. 上游与交付形态（先定档，再写配方）

| 项 | 取值 | 取证 |
|---|---|---|
| 上游仓库 | `https://github.com/cpb-/spi-tools` | Ubuntu `spi-tools_0.8.4-1build1.dsc` 的 `Homepage:` 字段（作者 Christophe Blaess，Debian 维护者 Lubomir Rintel） |
| 官方归档件 | `https://github.com/cpb-/spi-tools/archive/refs/tags/0.8.4.tar.gz` | 实测 HTTP 200、13346 B |
| sha256 | `201ffcb53e64f28a05aa0a8de5686f7ac644268da1305c0d5f70a3d96b4a22ce` | 本地 `sha256sum` 与 .dsc 的 `Checksums-Sha256` 双向一致 |
| tag 命名 | **无 `v` 前缀**（`0.8.4`）；`v0.8.4` 实测 404 | codeload 直取 |
| 与 Ubuntu pool orig 的关系 | **逐字节同一物**（尺寸 13346 + sha256 全等） |  ⇒ pool 件不是 Debian 重压缩产物，本包无 PF7 风险；但仍按"官方 URL 入交付"落 conandata.yml，镜像/pool URL 一律不写 |

> 登记表原记上游为 `crzwd/spi-tools-linux`，经核实**是错的**：该仓库在 GitHub 全站 404（repo 根、`refs/heads/{main,master}.tar.gz`、`/tags` 四个 URL 逐一实测均 404），`api.github.com` 亦撞 rate limit。纠偏已写进登记表备注。

## 2. 源码结构与构建体系（Windows 侧解包直读，11 个文件）

```
configure.ac  Makefile.am(SUBDIRS=src man)  src/{spi-config.c(252), spi-pipe.c(191), Makefile.am}
man/{Makefile.am(dist_man_MANS), spi-config.1, spi-pipe.1}  LICENSE(GPL-2.0 全文)  README.md  .gitignore
```

- 构建系统 = **autotools**（`AM_INIT_AUTOMAKE([foreign])` + `AC_PROG_CC`），README 自述安装法 `autoreconf -fim → ./configure → make → make install`。
- **GitHub tag 归档件不含任何 autotools 生成物**（无 `configure`/`aclocal.m4`/`Makefile.in`/`config.h.in`）⇒ 必须自举。
- 依赖 = 仅 libc + Linux UAPI 头（`src/*.c` 的 `*_LDADD` 全为空）。
- 无任何测试入口：`TESTS`/`check_PROGRAMS`/`dist_check_SCRIPTS` 全树 0 命中 ⇒ `N_static = 0`（清点结论，见 `test_package/MANIFEST.yml`）。

## 3. 关键结构判断与对应处置

| # | 判断 | 依据 | 处置 |
|---|---|---|---|
| 1 | 自举只需 autoconf+automake，**不需要 libtool** | `configure.ac` 无 `LT_INIT`/`AC_PROG_LIBTOOL`，产物是 `bin_PROGRAMS` 而非 `.la` | `tool_requires("automake/1.18")` 一条；**不 tool_requires autoconf**（HNP 自带 autoconf 2.72，而 conan 的 autoconf 依赖 perl，其 `Cwd.so` 在 HMDFS 上无执行权限——comptty/1.0.3 已实证并改用系统 autoconf） |
| 2 | 无三元组挡路 | `configure.ac` 无 `AC_CANONICAL_HOST/SYSTEM` ⇒ `config.sub` 根本不被调用 | 不传 `--build`/`--host`，免 E007/E122/E160 一族补丁（对照 jaula：那条在本包不适用） |
| 3 | `VERSION` 宏来源 | `spi-config.c:104`、`spi-pipe.c:89` 打印 `VERSION`，而 `config.h.in` 不在归档件里 | 由 autoheader 生成 `src/config.h.in`、configure 的 `DEFS` 注入 `-DVERSION=\"0.8.4\"`；test.sh 用 `-v` 输出串**直接断言这条链路成立**（版本断言失败即说明自举链有问题） |
| 4 | `make install` 在 HMDFS 上不可靠 | E182/E188 家族：真机 `install -c` 报 Error 64（aribb24 为此专门写 install shim） | `package()` 不跑 `make install`，直接实体拷贝 `build/src/spi-{config,pipe}` → `bin/`、`man/*.1` → `share/man/man1/`、`LICENSE` → `licenses/`；拷贝后校验文件存在，防止静默产出空包 |
| 5 | `umask 077` / `pwd` 复验两处 HMDFS 敌意 | E011/E114（config.status 临时目录不可写→静默不产出 Makefile/config.h）、E386（getcwd 失败） | `autoreconf` **之后**对生成的 `configure` 做定向改写（`umask 077`→`022`；`ac_pwd=\`pwd\` &&` → 失败回退 `$PWD`），改写不落补丁、不进 PR diff，理由与 aribb24 同源 |
| 6 | `DOXYGEN`/`HELP2MAN` 探测不阻塞 | `AC_CHECK_PROGS([DOXYGEN])` 只 `AC_MSG_WARN`；`AC_PATH_PROG(HELP2MAN, help2man, echo No help2man)` 有兜底值，且 `man/Makefile.am` 用 `dist_man_MANS`（预置静态页），构建期不调用 help2man | 不加任何工具依赖（对照 jaula 的 `doc/Makefile.in` 无守卫 `test -n "$(DOXYGEN)" &&` 短路——本包 `doc/` 目录不存在，同类问题不存在） |
| 7 | 并发必须 -j1 | HMDFS 无 `mkfifo` ⇒ make jobserver 不可用 | `autotools.make(args=["-j1"])` |

## 4. 测试口径

- 上游：`N_static = 0`（无入口），`0 passed` 不写成"通过"，也不冒充跑过 `make check`。
- 消费者（`test_package/test.sh`，`N_consumer = 1` 程序 / **35 条断言**；有 `/dev/spidev*` 节点时 39 条）：以使用者身份运行打包后的两个 ELF，退出码 + 输出子串共同决定；覆盖 `-v` 版本宏、`-h` usage、8 组参数校验负例、无设备分支、不存在节点的 `open()` 失败路径（真实系统调用面）。
- SPI ioctl 数据面（`SPI_IOC_RD_MODE` 等）在**没有 spidev 节点的机器上物理不可执行**：脚本如实打印 SKIP 并在 MANIFEST 的 `conditional_skip` 说明原因，不把它并入"通过"、也不从分母里偷偷删除。

## 5. 待设备实证清单（已逐项给结论，凭据在 `~/tmp/uc2/hw-9/logs/`）

| # | 待证事项 | 结果（真机实测） |
|---|---|---|
| 1 | `tool_requires("automake/1.18")` 制品可取性 | **可取**。`conan install --tool-requires=automake/1.18 --build=never -pr:h -pr:b` 实测 `Downloaded recipe revision 65a7ba60…` + 二进制宜告 `…:01d92cf3…#74f532f1… - Download (ohpcd)`；**1.17 与 1.16.5 均 not resolved**（只有 1.18 有制品）。注意：`preflight_check.sh` 必须在任务 `CONAN_HOME` 下跑——未导出时它打到 `~/.conan2`，把"远端不可达"报成"依赖未发布"（我第一次就吃到这个假阴性），带 home 后为 `[OK] 已发布` |
| 2 | conan 的 automake 与 HNP 的 autoconf/perl/m4 混用能否完成 `autoreconf -fi` | **能**。日志实测自举补齐 `configure.ac:13: installing './compile'`、`'./install-sh'`、`'./missing'`、`src/Makefile.am: installing './depcomp'`，并产出 `aclocal.m4`、顶层与 `src/`、`man/` 的 `Makefile.in`、`src/config.h.in` |
| 3 | autoconf 2.72 消化 2014 风格 `configure.ac`（`AC_PROG_CC_C99`、`AC_HEADER_STDBOOL` 已废弃）是否致命；autoheader 是否产出 config.h.in | **不致命**：configure 全程跑到 `config.status: creating src/config.h`，废弃宏只属告警；`src/config.h.in` 实测存在 |
| 4 | `DEFS` 是否真注入 `-DVERSION="0.8.4"` | **是**。消费者测试的 `-v` 断言逐字回显 `spi-config - 0.8.4` / `spi-pipe - 0.8.4` 并通过 |
| 5 | OHOS sysroot 的 `<linux/spi/spidev.h>` + `<linux/ioctl.h>` 是否足以编译 | **足够**。两个 TU 真编真链：`/data/service/hnp/bin/clang … -c -o spi-config.o …/src/spi-config.c` → `-o spi-config spi-config.o`（spi-pipe 同），无任何缺头/缺符号报错 |
| 6 | `Autotools.configure()` 直接调用是否可行 | **不可行（本包唯一的真失败点，已定档根因）**。r1 日志：`configure: error: working directory cannot be determined`。取证链：①`conanbuildenv-release-armv8.sh` 第 17-18 行 `export SHELL/CONFIG_SHELL="/data/service/hnp/bin/bash"`，其来源是框架共享 profile `ci/conan/profiles/ohos-aarch64` 的 `[buildenv]`（该文件只读，不能改）；②autoconf 生成的 configure 序言 `exec $CONFIG_SHELL $as_opts "$as_myself"` 会用它自重执行；③在**同一 conan 缓存目录**里 `hnp bash -c pwd` → rc=1 + `shell-init: error retrieving current directory: getcwd`，`/bin/sh -c pwd` → rc=0；④受控单因子实验（scratch 副本 + VPATH，只变这两个变量）：**C1 hnp bash ⇒ rc=1 报同一错**，**C2 /bin/sh ⇒ rc=0 正常产出 Makefile**，**C3 不设该变量 ⇒ rc=0**。⇒ 修法＝`_configure_with_binsh()`：用 `load_toolchain_args()` 取回 AutotoolsToolchain 的 `configure_args`（不手抄 `--prefix`），再以 `env CONFIG_SHELL=/bin/sh SHELL=/bin/sh` 前缀执行。副证：C2 生成的 `Makefile` 里 `SHELL = /bin/sh`，故后续 make 的 recipe shell 也一并回到 /bin/sh |
| 7 | 真机 `make` 产物落点 | **`<build_folder>/src/`**（`basic_layout` 下 source_folder=`<base>/b`、build_folder=`<base>/b/build-release`，VPATH 构建）⇒ `package()` 的 `built = build_folder/src` 正确；成品包实测含 `bin/ licenses/ share/`，`conan list` 的 package_id `6b129b068851896169fae42d399fa922d239ce8a`（OHOS/armv8/clang 15/Release） |
| 8 | test.sh 断言结果 + memcap 峰值 + 是否有 spidev 节点 | **r2 `conan create` rc=0**：`断言合计：通过 35 / 失败 0 / 条件未满足 1`；`MEMCAP[run] peak=124MB budget=2048MB rc=0 用时44.0s`（远低于 1GB ⇒ 轻构建档 `gate.sh 4000` + `build-slot --mem 4000` 成立，实测 `GATE_PASS MemAvailable=6497MB`）。设备 **无任何 `/dev/spidev*` 节点**（`ls /dev \| grep -c spidev` = 0，通配枚举亦空）⇒ SPI_IOC 数据面那组断言如实 SKIP，未并入通过率 |
| 9 | B 判定 | 见登记表备注（本轮出结论）：sct 提的"SPI 设备节点 ioctl 数据面 OHOS 偏差"**无法取证**（第 8 项：本机无节点），不得据此报 create；本包真机撞到的新机制是第 6 项（profile `[buildenv]` 钉 hnp bash × Autotools 助手无 env 钩子 × `load_toolchain_args` 保参绕法） |
---

**编译结束**: 2026-09-25 16:40
**最终状态**: built
