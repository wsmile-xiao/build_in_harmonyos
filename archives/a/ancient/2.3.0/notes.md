# ancient 2.3.0 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am，发布 tag 归档无预生成 configure，配方内自举)
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4 / clang++ 15.0.4 (OHOS aarch64 profile: ci/conan/profiles/ohos-aarch64)
- 状态: built (conan-verify 全绿，可标记 published)

## 编译步骤
1. `ohc-run.py init-build ancient 2.3.0 --url=https://github.com/temisu/ancient/archive/refs/tags/v2.3.0.tar.gz`
   （github.com 主域超时，tarball 由官方 codeload CDN 预下载；sha256=5d1d71f0…）
2. `ohc-run.py lang-preflight` → cpp/cpp 匹配
3. 手动编译验证（work 源码树）：autogen.sh → configure --prefix=$DEFAULT_PREFIX → make -j2 → make check（TOTAL 0，autotools 无注册用例）→ make install DESTDIR=TEST_PREFIX
4. `ohc-run.py conan-init` + 配方改写（见"遇到的问题"），`ohc-run.py conan-verify` → G0-G4/L2/L4/L5 全过
5. `ohc-run.py finish ancient 2.3.0 built` → W3 本地 CI 通过（.ci-result.json exit_code=0）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 报 `configure: cannot find required auxiliary files: config.guess config.sub ltmain.sh compile ar-lib missing install-sh` (exit 127) | 官方 tag 归档等价 git-archive 快照，只含 configure.ac/Makefile.am，无预生成 configure 与 build-aux | 配方内自举链 libtoolize → aclocal → autoconf → automake --add-missing --copy --force-missing（configure.ac 无 AC_CONFIG_HEADERS，R02 起不调用 autoheader）；tool_requires automake/1.18 + libtool/2.5.4（制品仓已发布） |
| 2 | autoconf 报 `possibly undefined macro: AC_SUBST/AC_DEFINE`；configure 残留 `PKG_PROG_PKG_CONFIG(0.24)` 语法错误 | configure.ac 引用 autoconf-archive（AX_CXX_COMPILE_STDCXX/AX_CHECK_COMPILE_FLAG/AX_CXXFLAGS_WARN_ALL）与 pkg.m4 宏，发布归档 m4/ 只含 libtool 宏，CI 沙箱无 $HOME/.local/share/aclocal | m4/*.m4（ax_*.m4 + pkg.m4）随 export_sources 携带；generate() 内 buildenv_info.append_path("ACLOCAL_PATH", source_folder/m4) 先于 VirtualBuildEnv.generate() |
| 3 | `configure: error: cannot guess build type` (config.guess 2024-07-27 无法识别 uname -s=HarmonyOS) | GNU config.guess 无 HarmonyOS 分支 | 显式等值双三元组 --build=aarch64-linux --host=aarch64-linux（仅 OHOS/Linux armv* 原生构建，保留 AC_RUN_IFELSE） |
| 4 | `make check` 报 # TOTAL: 0；上游真实测试 testing/test.cpp 不在 tarball | 上游 .gitattributes 声明 `testing export-ignore`，发布归档剔除 testing/，但上游 CI（Makefile.unix）仍实际运行 | 按源码测试入口恢复规则从官方 tag（git clone --depth 1 --branch v2.3.0）拉取 testing/，按上游 CI 同法 make -f Makefile.unix obj/test 并运行，201/201 通过 |
| 5 | conan-verify E017 镜像注入残留 conandata.yml.ghfast-bak | G2 临时注入 ghfast.top 镜像下载后恢复 | finish 前清理残留；提交前核对 conandata.yml 为官方 URL |

## 源码修改
- 无源码补丁（patches/ 内为 auto-difflib 生成的自举产物快照记录：0001-Makefile.in.patch / 0002-aclocal.m4.patch / 0003-ancient.patch / 0004-test-artifacts.sha256.patch，conandata `patches: {}` 不应用，构建由配方自举链替代）

## 依赖版本
- 运行时依赖: 无（纯 C++17 库，无外部库依赖）
- 构建依赖 (tool_requires): automake/1.18、libtool/2.5.4（制品仓已发布，abiword 系先例）
- 工具链: clang 15.0.4 (aarch64-unknown-linux-ohos)，GNU make 4.4.1，cmake 4.1.2，autoconf 2.72

## 验证结果
```bash
make -f Makefile.unix CXX=clang++ CC=clang EXTRA_CFLAGS= obj/test   # exit 0
./obj/test                                                            # exit 0，201/201 通过
conan create archives/a/ancient/2.3.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing  # exit 0，test_package 双测试 Passed
./consumer_ancient testing/test_files/test_C1.rnc1 out.raw            # exit 0，输出与官方 test_C1.raw 逐字节一致
```
- 上游测试台账: reports/upstream-test-ledger.md（source_declared_total=201，executed_passed_total=201，100%）
- 测试报告: reports/test-report.md；conan 验证: reports/conan-verify-report.md；W3: reports/w3-local-ci.log

## 注意事项
- 上游 v2.3.0 的 testing/ 被 export-ignore 排除出发布 tarball——评估/回报上游测试时必须以官方 git tag 为源码事实源，不能只看 tarball
- 若上游改用 make dist 类 release tarball（自带 configure），不得保留 automake/libtool tool_requires（DRAFT-5982-gmime forbid 规则）
- 消费者用例二进制与测试产物仅本地验证用，不入 PR
---

**编译结束**: 2026-09-24 05:00
**最终状态**: built
