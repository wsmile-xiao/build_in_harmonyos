# libsmacker 1.1.1r35 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am，发行 tarball **不含** configure）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，HarmonyOS PC 原生）
- 状态: built

## 编译步骤

1. `get()` 下载 SourceForge 官方 tarball（sha256 `bb9c22c0…a454630`），`strip_root=True`
   解包到 `libsmacker-1.1.1/`。
2. `apply_conandata_patches()` 打 `patches/0001-install-header.patch`。
3. `build_requirements()` 注入 `automake/1.18` + `libtool/2.5.4`；`_prepare_autotools_env()`
   把 `AUTOCONF/AUTOHEADER/AUTOM4TE/SED` 指向 PATH 上真实存在的可执行文件。
4. `autoreconf -fi` 引导出 `configure`（`AC_PROG_LIBTOOL` 需要 `libtoolize` 拷入
   `m4/libtool*.m4` 与 `ltmain.sh`）。
5. 对生成的 `configure` 做 `umask 077 → umask 022 + mkdir -p` 归一（两处，打点
   `[umask-fix] targets=2 residual_umask077=0`，命中数不符即抛错，杜绝静默 no-op）。
6. `./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos
   --prefix=/ … --enable-static --disable-shared`（`--build/--host` 显式给定，绕过
   `config.guess` 探测）。
7. `make -j1`（E074：并行 jobserver FIFO 在 HMDFS 被拒）。
8. `build()` 末尾跑上游演示程序 `driver` 的端到端冒烟（见下）。
9. `autotools.install()` 后手工删除 `lib/*.la` 包装文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoreconf` 报 `configure.ac:8: undefined or overquoted macro: AC_PROG_LIBTOOL` | 发行 tarball 无 `configure`，必须引导；设备与 CI worker 只有 autoconf 家族，**没有** `libtoolize`/`aclocal`（`~/.harmonybrew/bin` 不在 worker PATH 上，device-facts §一.4） | `build_requirements()` 拉 `automake/1.18` + `libtool/2.5.4`（ohpcd 制品仓均已发布） |
| 2 | `config.guess: can't create …/dummy.c: Permission denied` → `unable to guess system type` | `uname -s = HarmonyOS` 不被识别，且其编译探针要写临时目录，HMDFS 拒绝 | `configure_args` 显式追加 `--build=`/`--host=aarch64-unknown-linux-ohos`（`config.sub` 实测接受该三元组），完全绕过探测 |
| 3 | `configure: creating ./config.status` 后 `config.status: error: could not setup config files machinery`（`can't create ./confXXXXXX/subs1.awk: Permission denied`） | `umask 077 && mktemp -d` 在 HMDFS 生成 `drwx--S---`，属主被映射成共享属主，**自己也写不进去** | `build()` 内把 `configure` 的两处 `umask 077` 归一为 `umask 022 && mkdir -p`，并打印命中/残留计数做反静默自检（同族先例 E114 / abiword `_drop_umask_077`） |
| 4 | 上游 `Makefile.am` 没有任何 `include_HEADERS`，`make install` 只装 `.a` 不装头 | 上游疏漏（Conan Center 的同款配方也补了这一行） | `patches/0001-install-header.patch` 增加 `include_HEADERS = smacker.h`，同时给 `libsmacker_la_LDFLAGS` 加 `-no-undefined` |
| 5 | 上游**没有任何测试**：无 `tests/`、`Makefile.am` 无 `TESTS`/`check_PROGRAMS`，`make check` 输出 `Nothing to be done for 'check'.` | 上游只提供 demo 程序 `driver.c` / `smk2avi.c`，不提供断言 | 见下节「测试面」：按四口径清点 N=0，另建真断言消费者测试 |

## 源码修改

- `patches/0001-install-header.patch`（modified-file diff，仅动 `Makefile.am`）：
  - `libsmacker_la_LDFLAGS` 追加 `-no-undefined`
  - 文件末尾追加 `include_HEADERS = smacker.h`

生成的 `configure` 中的 `umask 077` 归一**不属于源码补丁**：它在 `build()` 内对
autoreconf 产物就地处理，上游 tarball 与提交面均不含该改动（标准适配，免 refresh_patch）。

## 依赖版本

- 运行期依赖：**无**（上游源码只 `#include` 自身头与 `stdio/stdlib/string/errno`）
- 构建期工具（tool_requires，随 build profile 解析）：`automake/1.18`、`libtool/2.5.4`
- 工具链：clang 15.0.4 / lld、GNU Make 4.4.1、autoconf 2.73（设备）

## 测试面（上游 N=0 的四口径清点）

| 口径 | 计数 | 取数命令 / 依据 |
|---|---|---|
| 源码宏数 | 0 | `grep -rnE "\bassert\s*\(|#include <assert\.h>\|EXPECT_\|ASSERT_\|CK_assert\|cmocka\|CuTest\|TEST\(\|START_TEST" --include=*.c --include=*.h .` → 0 命中（9 个源文件） |
| 框架注册数 | 0 | `Makefile.am` 无 `TESTS` / `check_PROGRAMS`；`grep -nE "^(TESTS\|check_PROGRAMS\|TEST_EXTENSIONS\|check-local)" Makefile` → 0 行；`make -n check` 输出 `Nothing to be done for 'check'.` |
| assertion 数 | 0 | 同源码宏数；`driver.c`/`smk2avi.c` 只打印与写文件，不做断言 |
| 消费者断言数（上游自带） | 0 | `driver.c` 成功路径 `return 0` 无条件返回；打开失败 `return -1`，无断言 |
| **N = max(候选)** | **0** | 四口径全 0，差额 0 |

适配后新增（**不计入上游分母**）：
1. `test_package/test_libsmacker.c` 消费者断言测试 —— **41 条断言**（见 MANIFEST.yml）。
2. `build()` 内上游演示程序 `driver` 端到端冒烟 —— 3 条产物断言（BMP magic / 尺寸 / 像素色）。

## 验证结果

```bash
conan create archives/l/libsmacker/1.1.1r35 \
  -pr:h <repo>/ci/conan/profiles/ohos-aarch64 \
  -pr:b <repo>/ci/conan/profiles/ohos-aarch64 --build=missing
# [umask-fix] targets=2 residual_umask077=0
# [demo-check] OK magic=BM size=1142 pixels=64 colour=0x20
# 1..41 / # libsmacker consumer test: 41 checks, 0 failures
# rc=0
```

## 注意事项

- 交付形态为**静态库**（默认 `shared=False`，R26 口径）；`package_info.libs = ["smacker"]`，
  公共头为 `include/smacker.h`。
- `driver` / `smk2avi` 是上游 `noinst_PROGRAMS`，**不随包安装**（与上游 install 面一致）。
- 源码版本串：`AC_INIT` 内为 `1.1.1`，`r35` 是 SourceForge 发布修订号，不进源码；
  全量 grep 实测源码内**不存在** `1.1.1r35`/`1.1.1-r35`/`1.1.1_r35` 任何形态。
