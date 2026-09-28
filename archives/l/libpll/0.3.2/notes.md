# libpll 0.3.2 适配笔记

## 编译环境
- 构建系统: autotools（tag 归档为 git snapshot，无 configure，autoreconf 引导）
- 编译日期: 2026-09-17（2026-09-20 重跑 conan create：build() 内真实执行上游 21 用例，CONAN_CREATE_RC=0）
- 编译器: clang 15.0.4（ohos-aarch64 profile，交叉 aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

conan create（conan-verify G2 驱动，dlcache 命中预置源码）→ 配方 build()：
1. `env -u CONFIG_SHELL SHELL=/bin/sh autoreconf -fi`（bootstrap，m4/ 宏随源码树提供）；
2. E114 umask 077 剥离 + E490 辅助脚本 exec 位修复；
3. VPATH configure（--build/--host 双 aarch64-unknown-linux-ohos 三元组；--disable-sse --disable-avx --disable-avx2 关闭 x86 SIMD 内核；--enable-static --disable-shared；--prefix=package_folder）；
4. `make -j1`（E074 单线程）编译 libpll.a + 全部 examples；
5. 上游自带校验框架 test/（未接入 automake）由配方 `_run_upstream_test_suite()` 驱动：`make -j1 -e -C test src/common.o obj/<case>` 编译 21 个用例（CLIBS 传配方产出的静态库绝对路径，`-e` 让工具链的 CC/CFLAGS 覆盖上游 Makefile 里写死的 gcc）→ 逐用例执行 → stdout 与 `test/out/<case>.out` 全文比对，等价于上游 runtest.py 的判据；
6. `make install` 安装 include/libpll/pll.h + lib/libpll.a。
test_package：消费者程序 test_libpll 链接 libpll::libpll，test() 直接执行二进制并断言退出码。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag 归档无 configure | git snapshot，仅 autogen.sh + configure.ac | build() 内 autoreconf -fi（tool_requires automake/1.18 + libtool/2.5.4；flex/bison 由设备 /data/service/hnp/bin 提供） |
| 2 | configure: error: working directory cannot be determined（E386 家族） | profile [buildenv] 默认 CONFIG_SHELL=hnp bash，HMDFS 上 getcwd() 失败 | build() 内联 `env -u CONFIG_SHELL SHELL=/bin/sh`（唯一可靠覆盖位置） |
| 3 | aarch64 上编译 core_*_avx2.c 报 __m256d 未声明 | 上游 AC_ARG_ENABLE 的 SIMD 开关默认开启（cpuid 检测代码被上游注释） | configure 传上游预留的交叉编译开关 --disable-sse --disable-avx --disable-avx2，只编纯 C 内核 |
| 4 | test_package 报 pll.h not found | 上游用 pkginclude_HEADERS，头装在 include/libpll/pll.h | 消费者按上游布局 `#include <libpll/pll.h>` |
| 5 | 解析 "((A,B),(C,D));" 报语法错误 | libpll 解析无根树，基节点必须三分类（trifurcation） | 测试改用 4-tip 无根树 "(A:0.1,B:0.2,(C:0.3,D:0.4):0.5);"，计数约定经设备实测校准（tip=4 inner=2 edge=5 integrity=1） |
| 6 | 上游 test/ 语料缺失（tag 归档不含 testdata/，7 个用例 `pll_fasta_open` 直接 fatal） | 语料在配套仓库 xflouris/assets，上游 runtest.py 用 wget 现拉 | 配方 `get()` 按 pinned commit + sha256 从官方 GitHub 端点取 assets 并铺到 test/testdata；取不到时该用例记为 skipped 而非静默通过（本次实测 0 skipped） |
| 7 | 3 个用例（derivatives / derivatives-oddstates / scaling）输出与 glibc 基线不逐字节一致 | 上游 out/ 基线录制于 x86+glibc；musl 的 exp/log 最后一位不同（导数项在 1e-15/1e-30 量级、远低于其出自的 ~1e2 似然值 1 ulp 的抵消下限），musl 把 NaN 无符号位拼作 `nan` 而基线为 `-nan` | 不放宽比对：`_delta_kind()` 校验差异必须保持"仅指数项尾数变化 / 仅 NaN 拼写"这一形状（行数不同、定点似然值变化、多出第二列差异一律 FAIL），再按 (用例, 形状) 白名单接受，并在日志逐项打印原因 |

## 源码修改

无补丁（patches 为空）。适配点全部在配方内完成：configure 开关、`autoreconf -fi` 引导，以及对**生成物** configure 的 E114 umask 剥离 / E490 exec 位（`replace_in_file`，不触碰上游源码与 test/ 任何文件）。上游测试用例源与 `test/out/` 期望输出均未修改。

## 依赖版本

无运行时依赖（纯 C，仅 libm）。构建工具依赖：automake/1.18、libtool/2.5.4（tool_requires）；flex/bison 由设备工具链提供（AC_PROG_LEX/AC_PROG_YACC，Newick 词法/语法解析器生成）。

## 验证结果

测试账本五维（2026-09-20 设备实测，日志 `~/tmp/uc2/libpll-0.3.2/create-5.log`，CONAN_CREATE_RC=0）：

| 维度 | 数值 | 口径 |
|------|------|------|
| N_static | 21 | 上游 tag 0.3.2 `test/src/*.c` 用例源数（22 个 .c 排除公共 common.c，与 test/Makefile 的 CFILES 同口径） |
| N_registered(automake) | 0 | 该框架未接入 automake：顶层 SUBDIRS 不含 test/，全树无 TESTS/check_PROGRAMS，`make check` 无注册用例 |
| N_executed | 21 | 配方 build() 内逐用例编译并执行，stdout 与 `test/out/<case>.out` 全文比对 |
| 未执行/跳过 | 0 skipped | 语料缺失才记 skip；本次 assets 已取到，7 个依赖语料的用例全部真实执行 |
| N_consumer | 1（7 断言） | test_package/test.c 消费者程序 test_libpll，另列并计入适配后总数 |

执行结果（配方打印，原文照录）：

```
UPSTREAM TESTS: 18 passed, 3 passed with a documented platform delta, 0 skipped, 0 failed (of 21 cases)
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", ..., "discovered": 21, "executed": 21,
                           "passed": 18, "failed": 0, "skipped": 0, "documented_delta": 3}
```

即 **21/21 执行且通过**：18 例逐字节一致；3 例（derivatives、derivatives-oddstates、scaling）差异被 `_delta_kind()` 校验为"仅指数项尾数 / 仅 NaN 拼写"后按白名单接受，逐项在日志打印原因；任一用例出现基线外的差异形状即抛 ConanException 使构建失败。

```bash
# conan-verify（G0/G1/G2/G3/G4 全 PASS，Verdict: PASS）
python3 scripts/ohc-run.py conan-verify libpll 0.3.2
# 消费者测试（test_package/test.c，test() 直接执行二进制）：
#   test_libpll：pll_utree_parse_newick_string 解析 4-tip 无根树；断言 tip/inner/edge 计数
#   （4/2/5）、pll_utree_check_integrity 结构完整性、叶标签精确匹配 A-D、畸形输入被拒
#   且置错误信息；7 项断言全通过（输出 "test_libpll: all assertions passed"，退出码 0）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| include/libpll/pll.h | ~120KB | 公共 API 头（上游 pkginclude_HEADERS 布局） |
| lib/libpll.a | ~1.5MB | 静态库（R26 默认静态；纯 C 内核，无 x86 SIMD） |
| share/man/man3/libpll.3 | 手册页 | make install 随附 |
| share/doc/libpll/examples/ | 示例源码 | make all 已验证可编译 |

## 注意事项

- 上游 test/ 框架的用例数如实记 N_static=21（`test/src` 用例源，22 个 .c 排除 common.c）；"无 automake 注册"只说明 `make check` 为空，不等于上游无用例——此前按 0 申报已被赛事审查 rule4 判为少报，2026-09-20 起改为配方内真实执行 21 例。
- 3 例平台差异按"形状校验 + 白名单"接受，不是放宽比对：任何超出已记录形状的改动都会让构建失败；复核可从 `create-5.log` 的 `DOCUMENTED` 行与 `test/result/testfail_*` 取证。
- x86 SIMD 内核（SSE3/AVX/AVX2）由上游预留开关关闭，属交叉编译标准路径，非裁剪上游功能；aarch64 平台本就无法使用。
- libpll 为 AGPL-3.0 许可，配方 license 字段为 AGPL-3.0-only。
- 设备网络事实（仅供本地复现参考，不进交付）：`github.com/.../archive/...tar.gz` 在设备直连不可达、`codeload.github.com` 可达且 tarball 内容 sha256 与官方一致（45107d59…），本地验证期临时把 conandata url 指到 codeload，**提交前已 `git checkout` 恢复官方 URL**；共享 dlcache 条目会被其他窗口的 conan 判脏清除。

## 路径 B 判定（2026-09-20 复核）

不成立，按纯路径 A。理由：本 PR 的可复用增量（HMDFS getcwd/E386 shell 路由、E114/E074/E490、上游独立测试框架在交叉环境下的驱动范式与 musl 浮点尾差口径）均已命中知识库既有条目家族（E386/E114/E074/E490 及经验汇总 §12.72「上游实测 N 的四种上游形态口径」——本例属"独立框架"形态），无条目外的新行为偏差；单库补丁不构成跨仓库复用新知识。3 例 musl vs glibc 的尾差属 libc 已知行为差异，已被 §12.72 的申报口径覆盖，不另立知识草稿。

## finish 收尾块

- finish: `python3 scripts/ohc-run.py finish libpll 0.3.2 built`
- result: conan-verify PASS（milestone=conan_verify_passed）后 finish 标记 built；release/upload 流水线确认上传前不使用 published。
---

**编译结束**: 2026-09-17 04:37
**最终状态**: built
