# libproc2 4.0.6 适配笔记

## 目标库身份

- **libproc2 没有独立上游项目**：它是 **procps-ng 提供的库组件**（源码树
  `library/`，产物 `lib/libproc2.a`，pkg-config 模块名 `libproc2`，公开头文件
  安装到 `include/libproc2/`）。唯一上游来源是官方发布包
  `procps-ng-4.0.6.tar.xz`（SourceForge `procps-ng/Production/`）。
- 本包**只打包库组件**（lib/ + include/ + lib/pkgconfig/ + licenses/）：
  OHOS 系统自身已提供 `/usr/bin/{ps,free,top,uptime,...}`，CLI 工具集归属既有
  `procps` 包（`archives/p/procps/4.0.7`），避免同一个上游产出两个同名 CLI 包。

## 编译环境

- 构建系统: autotools（configure + make）
- 编译日期: 2026-09-15
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，由 Conan 工具链注入，R33）
- 目标平台: OHOS 6.0 / aarch64（armv8），triplet `aarch64-unknown-linux-ohos`
- Conan: 2.29.1（OHOS 适配版），profile = `ci/conan/profiles/ohos-aarch64`
- 状态: built（conan-verify G0-G4 PASS + W3 本地 CI 通过，未 upload）

## 源码核验

```bash
sha256sum procps-ng-4.0.6.tar.xz
# 67bea6fbc3a42a535a0230c9e891e5ddfb4d9d39422d46565a2990d1ace15216
# 与 SourceForge 官方文件元数据（files/Production/ 列表 API）给出的
# sha1=6e23f716…/md5=20c23dc3…/sha256=67bea6fb… 逐字一致；
# 与官方 GitLab tag v4.0.6 归档的 configure.ac/Makefile.am/library/*.c 等逐字节一致
xz -t procps-ng-4.0.6.tar.xz        # 完整性 OK
cat procps-ng-4.0.6/.tarball-version # 4.0.6
```

> 官方源本网络实测单连接 ~1.0 KB/s（30 s 仅 32 KB），完整下载约需 26 min；
> 源码按官方 URL 以 16 路范围续传取得，产物 sha256 与官方元数据一致（M6）。

## 编译步骤

```bash
# 1) 探索构建（staging 隔离）
./configure --prefix=$DEFAULT_PREFIX \
            --disable-nls --disable-numa --without-systemd --with-ncurses \
            --enable-static --disable-shared \
            ac_cv_header_utmpx_h=no          # OHOS 专用（见问题 3）
make -j1 && make install DESTDIR=$TEST_PREFIX
make check -j1

# 2) 配方固化
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init libproc2 4.0.6
python3 $SKILL_ROOT/scripts/ohc-run.py refresh-patch --auto libproc2 4.0.6
conan create archives/l/libproc2/4.0.6 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build="libproc2/*"
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libproc2 4.0.6
python3 $SKILL_ROOT/scripts/ohc-run.py finish libproc2 4.0.6 built
```

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 最小修改 | 知识 |
|---|---------------------|------|----------|------|
| 1 | `./config.guess: unable to guess system type` → `configure: error: cannot guess build type; you must specify one`（exit 1） | config.guess 无 HarmonyOS 分支（`uname -s` = `HarmonyOS`，无任何 case 命中）；**注意 4.0.6 的 config.sub 已认识 `linux-ohos`（`config.sub:2070,2213`），无需改** | 0003-config.guess.patch：新增 `*:HarmonyOS:*:*` → `<machine>-unknown-linux-ohos`（无平台宏） | E007 |
| 2 | `./config.status[1040]: can't create ./confMKmKam/subs1.awk: Permission denied` → `config.status` 随后报 `error: could not setup config files machinery`（exit 1） | configure/config.status 用 `(umask 077 && mktemp -d ./confXXXXXX)` 建"安全临时目录"；HMDFS 下该目录变成 `drwx--S---`，**用户不可写**（且 `chmod` 在该文件系统上不生效，E046），写文件即 Permission denied | 0004-configure.patch：移除两处 `umask 077`（临时目录改为继承父目录可写权限位） | E011/E114 |
| 3 | 若按 config.h 的 `HAVE_UTMPX_H=1` 编译：`src/w.c:1190:5: error: incompatible integer to pointer conversion assigning to 'utmp_t *' (aka 'struct utmpx *') from 'int'`（隐式声明 `setutxent/getutxent/endutxent`） | OHOS sysroot **有** `utmpx.h`（`AC_CHECK_HEADERS` 判定 yes → `HAVE_UTMPX_H` 被定义），但该头**只声明 `struct utmpx`**，utmpx 函数既未声明也未由 libc 导出；OHOS 的 `utmp.h` 则提供可用的 stub API（`setutent/getutent/endutent/utmpname`，`getutent()` 返回 NULL） | **不引入平台宏**：配方在 OHOS 下追加 configure 缓存变量 `ac_cv_header_utmpx_h=no`，让源码走 `<utmp.h>` 分支（4.0.7 用的是 `__OHOS__ + #undef HAVE_UTMPX_H` 源码补丁，本版改为等价但无宏的写法） | E121 |
| 4 | 链接 libproc2 时 `undefined symbol: strverscmp` | musl libc（OHOS）无 `strverscmp`；上游仅在 CYGWIN 分支把自带的 `local/strverscmp.c` 加入编译 | 0001/0002 补丁把 `local/strverscmp.c` 加入 libproc2 源列表（源 `Makefile.am` + 生成物 `Makefile.in`，本机无 automake 无法重生成） | E534 |
| 5 | 上游 `make check`：`FAIL: library/tests/test_version` | `procps_linux_version()` 用 `%u.%u.%u` 解析 `/proc/sys/kernel/osrelease`，本平台为 `"HongMeng Kernel 1.12.0"`（非标准）→ sscanf 返回 0 → `-ERANGE`；回退路径 `/proc/version` 不可读（`cat: Permission denied`） | **环境性失败，禁改断言**：`build()` 内 `try/except` 记录后继续（该程序另一子用例 `LINUX_VERSION macro` PASS） | 环境限制 |
| 6 | `make -j2+`：`make: jobserver mkfifo ... Operation not permitted` | HMDFS 不允许 FIFO | 全程 `make -j1` | 已知平台限制 |
| 7 | `Header file /usr/include/linux/capability.h not found, cannot rebuild local/capnames.h` | OHOS 无该宿主机头文件 | 仅打印提示，`local/capnames.h` 随发布包分发，不影响编译/测试 | — |

## 源码修改（4 个补丁，全部无平台宏，`patch_generation.method = per-file-difflib`）

| 补丁 | 内容 | 说明 |
|------|------|------|
| `0001-Makefile.am.patch` | `local/strverscmp.c` 加入 `library_libproc2_la_SOURCES` | +1/-0 |
| `0002-Makefile.in.patch` | `local/strverscmp.lo` 加入目标列表 + 依赖规则 | +3/-1（**生成产物**补丁，R6 例外：本机缺 automake，无法 `automake` 再生成 `Makefile.in`；`0001` 已同步改源文件 `Makefile.am`，源/产物一致） |
| `0003-config.guess.patch` | HarmonyOS 平台识别 | +13/-0（**生成产物**，R6 例外：gnulib 脚本随包分发，上游未提供 `config.guess.in`。分支插在该 `case` 末尾、`esac` 之前——语义等价（无 catch-all 分支）且避开 NetBSD 注释里的 "tar**gets**" 触发 CI L4 危险函数扫描器 `gets\b` 的误报） |
| `0004-configure.patch` | 移除两处 `umask 077` | +2/-2（**生成产物**补丁，R6 例外：本机 `autoconf` 可再生成 `configure`，但会引入 autoconf 版本差异导致巨量 diff；`configure.ac` 未改，`0004` 语义与其一致） |

> 与 4.0.7 的差异：4.0.7 用了 6 个补丁（含 config.sub、w.c）；4.0.6 的
> `config.sub` 已原生支持 `linux-ohos`，utmpx 改由 configure 缓存变量解决，
> 因此补丁数减到 4 个，且 **4 个补丁的新增行中不含任何平台宏**。

## 依赖版本

| 依赖 | 版本 | 类型 | 来源 | 用途 |
|------|------|------|------|------|
| ncurses | 6.6 | R 强制第三方 | conan ohpcd（静态宽字符，`pkg_config_name=ncursesw`） | `./configure` 探测 `ncursesw` 硬失败；CLI 分支链接 |
| gettext / libnuma / systemd(elogind) | — | O（禁用） | — | `--disable-nls --disable-numa --without-systemd` |
| dejagnu/expect/tcl | — | T（缺失即跳过） | — | DejaGnu 套件，缺 `runtest` 时上游打印 WARNING 跳过 |
| pkg-config ≥ 0.29 | 0.29.2（`/data/service/hnp/bin/pkg-config`） | B | 系统 | configure 硬依赖 |

- R26/R4：OHOS 强制静态（`--enable-static --disable-shared`，`shared=False`）——
  系统 shell 依赖系统 `libncursesw.so.6`，共享构建会引发 RPATH/同名库冲突。
- libproc2 自身**零第三方链接依赖**：上游 `library/libproc2.pc.in` 无
  `Requires:`、`Libs.private:` 为空（`Makefile.am:289` 的 `LIB_KPARTS` 全树未定义）。
- W0 复核：`conan download ncurses/6.6 -r=ohpcd` → `exit=0`（armv8/OHOS 6.0/clang 15，
  `shared=False`；包 ID `21b17f8b…`）。

## 上游测试统计（`make check`，单独汇报）

测试命令：`make check -j1`（= `check-am` → `check-TESTS` + `check-DEJAGNU`），
在 `conanfile.py` 的 `build()` 内真实执行（与 CI 同路径）。

| 指标 | 数值 |
|------|------|
| 用例总数 | **8** |
| 通过 | **7** |
| 失败 | **1**（`library/tests/test_version`，环境性） |
| 跳过 | **0**（DejaGnu 套件被上游自身逻辑跳过运行，见下） |
| 通过率 | 87.5%（`# TOTAL: 8  # PASS: 7  # FAIL: 1  # SKIP: 0  # ERROR: 0`） |
| 退出码 | `make check` = 2（因 1 个环境性 FAIL；`conan create` 内 `try/except` 记录后继续） |

| # | 用例 | 结果 |
|---|------|------|
| 1 | library/tests/test_escape | PASS |
| 2 | library/tests/test_pids | PASS |
| 3 | library/tests/test_uptime | PASS |
| 4 | library/tests/test_sysinfo | PASS |
| 5 | library/tests/test_version | **FAIL**（子用例：`LINUX_VERSION macro` PASS / `procps_linux_version()` FAIL） |
| 6 | library/tests/test_namespace | PASS |
| 7 | src/tests/test_fileutils | PASS |
| 8 | src/tests/test_strtod_nol | PASS |

未运行项（如实说明）：
- DejaGnu 套件 `testsuite/`（50 个 `.test`）：本机与 CI 均无 `runtest`
  （`testsuite/Makefile.in:555-562` → `WARNING: could not find 'runtest'`，上游自身
  静默跳过，既非 PASS 也非 SKIP 计数）。
- `check_PROGRAMS` 中不自动运行的 4 个（`test_strutils`、`test_process`、
  `test_shm`、`test_Itemtables`）：需显式 `make check-lib`，上游默认不跑，本次未跑。

日志：`logs/10_make_check.log`、`logs/11_upstream_test_detail.log`、
`archives/l/libproc2/4.0.6/reports/conan-create.log`。

## 验证结果

```bash
$ conan create archives/l/libproc2/4.0.6 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build="libproc2/*"
libproc2/4.0.6: Package '044971e9092dd6608b4c967bac722a276b7cc911' created   # exit=0
libproc2/4.0.6 (test package): RUN: "./test_libproc2"
procps_uptime: up=7148.6s idle=84955.6s
procps_loadavg: 39.92 37.96 37.37
pids API: 84 PIDs fetched via PIDS_ID_PID
libproc2 4.0.6 C API: all checks passed

$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libproc2 4.0.6      # exit=0
G0 PASS（命中 E490，非阻塞）/ G1 PASS / G2 PASS / G3 PASS（纯库包，无系统同名冲突）/ G4 PASS
```

产物（`Package folder`）：`lib/libproc2.a`（312 KB）、`include/libproc2/*.h` ×8、
`lib/pkgconfig/libproc2.pc`、`licenses/COPYING.LIB`。

## 交付物

| 类别 | 内容 |
|------|------|
| 库 | `lib/libproc2.a`（`-lproc2`，`pkg_config_name=libproc2`） |
| 头文件 | `include/libproc2/*.h` ×8（diskstats/meminfo/misc/pids/slabinfo/stat/vmstat/xtra-procps-debug） |
| pkg-config | `lib/pkgconfig/libproc2.pc`（`Version: 4.0.6`，`Libs: -lproc2`，无 Requires） |
| 配方 | `conanfile.py` + `conandata.yml` + `patches/`×4 + `test_package/`（真实 C API 消费者测试） |
| 报告 | `reports/conan-verify-report.md`、`reports/conan-create.log` |

## 注意事项

- **包名归属**：`libproc2` 与既有 `procps/4.0.7` 来自同一上游、同一库产品线，
  本包只提供库组件（不装 CLI），两者 `pkg_config_name` 均为 `libproc2`——
  消费时二者不应同时出现在同一依赖图中（待主编/用户确认命名口径）。
- OHOS 强制静态（R26/R4）；`make` 全程 `-j1`（HMDFS FIFO 限制）。
- 消费者 API 速查：`procps_uptime(double*,double*)`、`procps_loadavg(double*,double*,double*)`、
  `procps_pids_new/unref` + `PIDS_VAL(idx,s_int,stack)`（成功调用返回 0，语义与上游 testsuite 一致）；
  头文件推荐按上游文档 `#include <libproc2/pids.h>` 使用。
- 若后续需要 CLI 工具集，应更新 `procps` 包（或另立命令包），不要在本包内追加 `bin/`。
---

## 对话记录（适配过程）

### 对话 #1 [2026-09-15]

- 问题: W0 依赖复核——libproc2 是否有未发布的强制第三方依赖
- 操作: `conan download ncurses/6.6 -r=ohpcd`
- 结果: exit 0（armv8 / OHOS 6.0 / clang 15，shared=False）；强制依赖仅 ncurses/6.6
  且可消费，无需先适配下层库（R36 无阻塞）

### 对话 #2 [2026-09-15]

- 问题: 首轮 `./configure` 直接失败：`config.guess: unable to guess system type` →
  `cannot guess build type; you must specify one`（exit 1）
- 操作: 在 config.guess 增加 `*:HarmonyOS:*:*` 分支 → `aarch64-unknown-linux-ohos`；
  同时核验 config.sub 已原生支持 `ohos-linux`（无需补丁）
- 结果: `./config.guess` 输出 `aarch64-unknown-linux-ohos`，configure 越过平台判定

### 对话 #3 [2026-09-15]

- 问题: 第二轮 configure 在 config.status 阶段失败：`can't create ./confMKmKam/subs1.awk:
  Permission denied`
- 操作: 最小复现（`umask 077 && mktemp -d` → `drwx--S---` 不可写，且 chmod 无效）；
  移除 configure 中两处 `umask 077`
- 结果: configure exit 0，config.status 正常生成 Makefile

### 对话 #4 [2026-09-15]

- 问题: utmpx 不可用（w.c 隐式声明 setutxent/getutxent/endutxent 报错）、musl 无 strverscmp
- 操作: utmpx 改用 configure 缓存变量 `ac_cv_header_utmpx_h=no`（不引入平台宏）；
  `local/strverscmp.c` 补入 libproc2 源列表（Makefile.am/.in）
- 结果: `make -j1` exit 0，`make install DESTDIR=...` exit 0

### 对话 #5 [2026-09-15]

- 问题: 上游 `make check` 1 个失败（test_version）
- 操作: 定位为 OHOS 环境限制（HongMeng 内核版本串 + /proc/version 不可读），
  在 `build()` 内 try/except 记录；**未改上游断言**
- 结果: 8 总 / 7 PASS / 1 FAIL / 0 SKIP，`conan create` exit 0

### 对话 #6 [2026-09-15]

- 问题: config.guess 补丁首版把分支插在 case 开头，CI L4 因上下文里 NetBSD 注释的
  "tar**gets**" 命中危险函数模式 `gets\b` 而报 warn
- 操作: 把分支移到该 case 末尾（`esac` 前）——语义等价（该 case 无 catch-all 分支），
  重新生成补丁并更新 conandata 的 sha256
- 结果: `L4_RESULT=pass: patches clean`
---

**编译结束**: 2026-09-16 08:02
**最终状态**: built
