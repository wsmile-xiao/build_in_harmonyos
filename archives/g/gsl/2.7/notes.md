# gsl 2.7 适配笔记

## 编译环境

| 项 | 值 |
|----|----|
| 构建系统 | autotools（`configure` 由 GNU Autoconf 2.71 生成 + Automake + Libtool） |
| 编译日期 | 2026-09-29 |
| 编译器 | clang 15 / clang++（OHOS SDK，`os=OHOS` `arch=armv8`） |
| 目标平台 | `aarch64-unknown-linux-ohos` |
| profile | `ci/conan/profiles/ohos-aarch64`（host 与 build 同 profile） |
| 状态 | built |
| 交付形态 | conan 配方 `archives/g/gsl/2.7/conanfile.py`（`conan create` 可复现） |

- 状态: built（conan-verify G0–G4 全通过；上游 `make check` 59/59；test_package 鸿蒙消费者用例 6/6）

## 上游测试申报表（R51）

| 项 | 值 |
|----|----|
| 上游测试入口 | `make check`（GNU Automake parallel test harness） |
| 清点方式 | 源码树各子目录 `Makefile.am` 的 `TESTS = $(check_PROGRAMS)` 汇总 + 顶层 `pkgconfig.test` / `test_gsl_histogram.sh`；清点命令见本文件「清点证据」节 |
| 上游用例总数 N | **59**（覆盖 55 个目录） |
| 实际运行数 N′ | **59**（无不可运行项） |
| 通过 | **59** |
| 失败 | **0** |
| 跳过 | **0** |
| 通过率 | **100%**（59/59） |
| 运行环境 | 本机（HarmonyOS PC，`uname -s`=`HarmonyOS`）原生执行，`configure` 判定 `cross_compiling=no`，非交叉模拟 |
| 日志 | `/data/storage/el2/base/cache/gsl-2.7-check3.log`（本机绝对路径，未随 PR 入库；统计口径与本表同源，另存 `reports/test-report.md`，`reports/` 按仓库默认 .gitignore 规则不入库） |

> 说明：首轮运行 `vector/test` 与 `vector/test_static` 两例 FAIL，根因见「问题 4」（本机动态加载器不跟随符号链接解析 DT_NEEDED），把依赖库摊平为实体文件后复跑即 59/59 全绿。该现象与 gsl 源码无关。

### 清点证据

```bash
# 1) 生效的测试目录（TESTS = $(check_PROGRAMS)）
grep -rn "^TESTS =" */Makefile | wc -l            # → 55 个目录

# 2) 实际注册的用例名（automake 输出的 PASS/FAIL 行）
grep -E "^PASS: |^FAIL: " <log> | sort | uniq -c
#     54 PASS: test
#      2 PASS: test_static
#      1 PASS: test_c11
#      1 PASS: pkgconfig.test
#      1 PASS: test_gsl_histogram.sh
```

## 鸿蒙特有测试申报表（rule12：具名端到端消费者用例）

> 按**用例数**申报（不填断言数）。每条都是一条完整端到端流程：构造真实输入 → 调 GSL 公开 API → 产出真实结果 → 由 `test_package/test.sh` 逐字比对 consumer 打印的真实计算值与独立参考值。

| 用例 | 名称 | 端到端流程 | 参考值来源 | 实测值 | 结果 |
|------|------|-----------|-----------|--------|------|
| HC-1 | 特殊函数：贝塞尔 J0(5) 端到端求值 | `gsl_sf_bessel_J0(5.0)` | A&S 9.4.1（教科书值） | `-0.177597` | ✅ PASS |
| HC-2 | 线性代数：LU 分解解 2×2 方程组（走 CBLAS 符号） | `gsl_linalg_LU_decomp` + `LU_solve` | 手算 2x+y=3, x+3y=5 | `0.800000,1.400000` | ✅ PASS |
| HC-3 | 随机数：mt19937 固定种子复现序列 | `gsl_rng_set(42)` 两次取序列比对 | MT19937 `init_genrand(42)` 独立复算 | `1608637542,3421126067` | ✅ PASS |
| HC-4 | 统计：样本均值与总体标准差 | `gsl_stats_mean` + `sd_with_fixed_mean` | 手算（n=8） | `5.000000,2.000000` | ✅ PASS |
| HC-5 | BLAS：dgemm 2×2 矩阵乘法 | `gsl_blas_dgemm` | 手算矩阵乘 | `19.000000,22.000000,43.000000,50.000000` | ✅ PASS |
| HC-6 | 直方图：4 箱分箱计数与越界样本丢弃 | `gsl_histogram_set_ranges_uniform` + `increment` | 手算（8 样本，1 个越界） | `2,1,3,1` | ✅ PASS |
| **合计** | — | — | — | — | **6/6 PASS** |

判定口径：`sh test_package/test.sh <runtime-dir>`，对每条用例做三重校验——consumer 退出码 `rc==0`、裁决行用例号与请求一致、`VALUE` 与参考值**逐字相等**。

> 参考值独立性：HC-1/2/4/5/6 为教科书值或手算值；HC-3 由**不依赖 GSL** 的独立 MT19937 复算程序（`init_genrand(42)` + 标准 twist/temper）得出。六条实测值全部与参考值逐字相符。

## 编译步骤（conan 配方）

1. 应用两个平台识别补丁（`conandata.yml` 的 `patches` 段，由 `export_conandata_patches` 导出随配方走）：

   ```bash
   patch -p1 < patches/0001-config.guess.patch   # config.guess 认 HarmonyOS
   patch -p1 < patches/0002-config.sub.patch     # config.sub 认 linux-ohos
   ```

2. 补丁后三元组探测结果（实测）：

   ```bash
   $ ./config.guess
   aarch64-unknown-linux-ohos
   $ ./config.sub aarch64-unknown-linux-ohos
   aarch64-unknown-linux-ohos
   ```

3. `configure`（配方 `generate()` 下发，另由 `AutotoolsToolchain` 补 `CC/CXX/CFLAGS`）：

   ```bash
   ./configure --host=aarch64-unknown-linux-ohos --enable-shared --disable-static
   ```

4. `make -j1`（鸿蒙 SELinux 禁止并行 jobserver FIFO，必须 `-j1`）。
5. `make install` → `package()`。
6. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`。
   实测通过（EXIT=0，10m12s）：build + package + test_package（**鸿蒙消费者用例 6/6 PASS**）。
   日志：`/data/storage/el2/base/cache/wt-gsl-create2.log`

产物（`package/` 内）：

```
lib/libgsl.so.25.1.0        (soname libgsl.so.25)
lib/libgslcblas.so.0.0.0    (soname libgslcblas.so.0)
lib/pkgconfig/gsl.pc
include/gsl/*.h
bin/gsl-histogram  bin/gsl-randist
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识编号 |
|---|------|------|----------|----------|
| 1 | `config.guess` 不识别 HarmonyOS，三元组探测落到 unknown | 脚本 `case "${UNAME_MACHINE}:${UNAME_SYSTEM}..."` 无 HarmonyOS 分支（`uname -s` 实测返回 `HarmonyOS`） | 应用 `0001-config.guess.patch`，补 `*:HarmonyOS:*:*` → 输出 `{arch}-unknown-linux-ohos` | E007 |
| 2 | `config.sub` 拒绝 `aarch64-unknown-linux-ohos` | KERNEL-OS 白名单缺 `linux-ohos*` | 应用 `0002-config.sub.patch`，补 `linux-ohos*` 与 `ohos-linux` 反向形式 | E007 |
| 3 | configure 报 `C compiler cannot create executables`（实际 `cat: -: Permission denied`） | conan `buildenv` 注入的 `CONFIG_SHELL` 指向 hnp bash，该 bash 在 HMDFS 目录上 `cat -` 失败 → `conftest.c` 被截断 → `undefined symbol: main` | 在 `build()` 里向 `conanbuild.sh` **尾部追加** `export CONFIG_SHELL=/system/bin/sh`（追加才能覆盖 buildenv 的赋值） | E386 |
| 4 | 上游 `vector/test`、`vector/test_static` 运行期 `Error loading shared library libgslcblas.so.0` + 全部 `cblas_*` 重定位失败 | libtool 安装出的 `.so` 版本号是**符号链接**（`libgsl.so.25 -> libgsl.so.25.1.0`），本机动态加载器不跟随符号链接解析 DT_NEEDED | 把 `lib/` 下每个 `.so` 名字按实体文件摊平复制到临时目录，再用 `LD_LIBRARY_PATH` 指向该目录运行（`test_package` 与上游 `make check` 均如此） | E050 |
| 5 | （预防性，非本次实际报错）configure 建临时目录不可写 | `configure`/`config.status` 用 `umask 077` 建 conf 临时目录；在 HMDFS 上实测建出的是 `drwx--S--- 2700`（setgid + 无组权限），只要写入进程的 UID 映射与 owner 不一致即被拒（E114 的 `can't create ./confXXXXXX/subs1.awk: Permission denied`） | `build()` 中把 `configure` 里的 `umask 077` 归一化为 `umask 022`。**本次构建目录在 `/data/storage/el2/base/cache`（非 HMDFS），未触发**；保留是因为远程/他人默认 `CONAN_HOME=$HOME/.conan2` 落在 HMDFS 上，且仓库内已有 1272 份 autotools 配方做同样处理 | E011、E114 |
| 6 | conan-verify 的 G0 预查询报「已知风险 E490（autotools 助手脚本执行位）未在配方中处理」 | E490 的场景是「适配路径保留了源码内容但丢掉可执行位」；本包的 `configure` / `config.guess` / `config.sub` 在 tarball 内自带 `0755`，conan 解包后保持 | **判定不需处置**：G2 干净 `conan create` 实测通过，说明执行位未丢失。按 E490 的 `forbid_1_pattern` 提示未做 `chmod -R +x`（那会无差别放开权限）；如后续在 HMDFS 传输出问题再按 `restore-known-autotools-script-modes` 幂等补位 | E490 |

### 问题 4 的隔离实验（结论性证据）

同一份字节、同一个目录，只改「是软链还是实体文件」：

```bash
$ LD_LIBRARY_PATH=$B/withsym  ./.libs/test    # .so.0 -> .so.0.0.0 软链
Error loading shared library libgslcblas.so.0: (needed by ./.libs/test)
... cblas_sdsdot: symbol not found ...
rc=127

$ LD_LIBRARY_PATH=$B/realfile ./.libs/test    # .so.0 为实体文件
Completed [37327/37327]
rc=0
```

## 发现与知识（knowledge_gained）

> 本节的每条都在 `manifest.yaml` 的 `knowledge_gained` 里有对应条目。

- ✅ **E007** — GSL 2.7 源码包（`configure` 由 GNU Autoconf 2.71 生成）的 `config.guess` 没有 HarmonyOS 分支；本机 `uname -s` 实测为 `HarmonyOS`，不补丁则三元组探测落到 unknown。`config.sub` 需同时补 `linux-ohos*`，否则 `--host=aarch64-unknown-linux-ohos` 被拒。两个补丁是同一问题的两面，必须成对应用。
- ✅ **E386** — conan 的 `AutotoolsToolchain`/buildenv 会把 `CONFIG_SHELL` 设为 hnp 的 bash，且 buildenv 在配方选定 shell **之后**才被 source，会静默覆盖配方里的赋值。本包的具体表现是：该 bash 在 HMDFS 目录读取 stdin（`cat -`）失败，导致 `config.status` 读到的 `conftest.c` 被截断，configure 报出与真实原因完全无关的 `C compiler cannot create executables`。修法是**在 `conanbuild.sh` 尾部追加** `export CONFIG_SHELL=/system/bin/sh`（放在生成脚本里而非 `tc.environment.define()`，后者会被随后 source 的 buildenv 覆盖），与 E386「在 conanbuild 之后重新断言 shell」的方案一致。
- ✅ **E050** — 动态加载器不跟随符号链接解析 DT_NEEDED（实测：同一目录同一字节，软链失败、实体文件成功，vector 测试 `Completed [37327/37327]`）。libtool 产出的 `.so.major -> .so.major.minor` 布局在本机必然触发；消费侧测试须把 `.so` 名字摊平成实体文件后再跑。
- ✅ **E011 / E114** — 同一现象的两个条目：E011 的方案就是 `edit-umask-in-configure`（把 `configure` / `config.status` 里的 `umask 077` 换成 `umask 022`），E114 则记录其根因与错误特征（`can't create ./confXXXXXX/subs1.awk: Permission denied`、HMDFS 上 `mktemp -d` 建出 `drwx--S---` 2700+setgid 目录、chmod 也改不动）。本包按 E011 的方案处理；仓库内已有 1272 份配方在同一位置做同样处理（如 `archives/a/abiword-plugin-*/3.0.8/conanfile.py` 的 `E114` 注释），故本包不在 `patches/` 里改 `configure`，而在 `build()` 中归一化（`configure` 属上游生成产物，R6 要求走 `generate()`/构建时归一化，不变更仓库内文件）。
- ✅ **GSL 消费特征** — `libgsl.so` 把 CBLAS 符号留给消费方解析，必须同时链 `-lgsl -lgslcblas`；只 `dlopen("libgsl.so")` 会报 `cblas_sdsdot: symbol not found`。此约束已固化进 `test_package/consumer.c`（HC-5 专测 `gsl_blas_dgemm`）。

## 对话记录

### 对话 #1 [2026-09-29]

- 问题: 接手上游 `archives/g/gsl/2.7` 骨架（只有 `manifest.yaml` + `notes.md` + 两个补丁，没有 conanfile/conandata/test_package），需要产出可复现的 conan 配方并跑通真机验证
- 操作: 先按 2.8 的做法（`--build/--host=...-musl` 跳过 config.guess）试通，随后发现骨架已明确声明走补丁路线，按 `manifest.yaml` 的 `patches_applied` 与 `notes.md` 的 `--host=aarch64-unknown-linux-ohos` 重做为补丁路线
- 结果: 补丁后 `config.guess` → `aarch64-unknown-linux-ohos`；conan create 打通

### 对话 #2 [2026-09-29]

- 问题: conan create 在 configure 阶段报 `C compiler cannot create executables`，而手工 `./configure` 完全正常
- 操作: 对比 conan 生成的 `conanbuild.sh` 与手工环境，定位到 `CONFIG_SHELL=/data/service/hnp/bin/bash`；用 `cat -` 复现 stdin 失败
- 结果: 在 `build()` 里追加 `export CONFIG_SHELL=/system/bin/sh` 到 `conanbuild.sh` 尾部，configure 立即通过（知识 E386）

### 对话 #3 [2026-09-29]

- 问题: `test_package` 能编译但运行期找不到 `libgsl.so.25`，多种 `LD_LIBRARY_PATH` 写法均无效；上游 `make check` 的 vector 两例同样失败
- 操作: 做软链 vs 实体文件的隔离实验，确认加载器不跟随符号链接；改为摊平复制实体文件
- 结果: test_package 4/4 通过；上游 `make check` 由 57/59 变为 **59/59 全绿**（知识 E050）

### 对话 #4 [2026-09-29]

- 问题: `conan-verify` G1 判 FAIL（缺少 `export_sources()`），且 `source()` 下载 tarball 时 ftp.gnu.org 连接卡死
- 操作: 补 `export_conandata_patches(self)` 并把补丁正式接进 `conandata.yml`；用 conan 的 sources download cache 预置 tarball（`core.sources:download_cache`），命中后 `Source ... retrieved from local download cache`
- 结果: G1 通过；源码获取不再依赖外网稳定性

### 对话 #5 [2026-09-29]

- 问题: 按 rule12 复核鸿蒙特有测试口径——原 `test_package/test.c` 是「4 条数值断言」的断言集合，在 PR 统计表里只能按 1 项填报，会被判「仅断言、无完整消费者用例」
- 操作: 把 test_package 重构为具名端到端消费者用例：新增 `consumer.c`（HC-1..HC-6，六条完整流程覆盖 sf / linalg / rng / statistics / blas / histogram）与 `test.sh` 驱动（逐字比对 VALUE 与参考值）；删去被取代的 `test.c`；同步更新 `MANIFEST.yml`（`harmony_consumer_case_count: 6`）、版本级 `manifest.yaml`（`harmony_consumer_cases: 6`）
- 结果: `conan create` EXIT=0，鸿蒙消费者用例 **6/6 PASS**；其中 HC-1/2/4/5/6 的手算参考值与 HC-3 的独立 MT19937 复算值全部与真机实测值逐字相符

## 交付物
| 文件 | 说明 |
|------|------|
| `conanfile.py` | v3.0 配方，autotools + 补丁路线 + 两处本机修复 |
| `conandata.yml` | 源码 URL（官方 ftp.gnu.org + 3 个国内镜像，由 finish 的 mirror-fallback 自动生成）+ 真实 sha256 + 2 个补丁声明 |
| `patches/0001-config.guess.patch` | config.guess 认 HarmonyOS |
| `patches/0002-config.sub.patch` | config.sub 认 linux-ohos |
| `test_package/` | 消费侧测试（`consumer.c` 六条端到端用例 HC-1..HC-6 + `test.sh` 驱动 + `MANIFEST.yml`） |
| `reports/test-report.md` | 上游 59 例 + test_package 实测报告（**本机留存，`reports/` 按仓库默认 .gitignore 规则不入库**；其结论已回填至本文件与 `manifest.yaml`） |
| `manifest.yaml` | 版本级元数据（含 R51 测试回填） |

## 注意事项

1. `make` 必须 `-j1`（鸿蒙 SELinux 禁止 automake jobserver FIFO）。
2. 两个补丁只涉及**平台识别**，不改动任何数值算法源码。
3. `libgsl.so` 不含 CBLAS 实现，消费方必须同时链接 `-lgslcblas`。
4. `test_package/consumer.c` 的 6 条用例全部做真实数值计算并核对参考值（非空壳打印、非纯断言清单），同时满足 R34 与 rule12。
5. 本机（HarmonyOS PC）加载器不跟随符号链接的结论仅影响**本机运行期测试**；安装到真机时 `.so` 软链同样需注意，建议部署时摊平实体文件。
---

**编译结束**: 2026-09-29 15:30
**最终状态**: built
