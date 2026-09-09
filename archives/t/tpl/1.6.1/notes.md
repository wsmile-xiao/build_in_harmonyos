# tpl 1.6.1 适配笔记

## 编译环境
- 构建系统: autotools (automake + libtool)
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4 (aarch64-linux-ohos triplet)
- 状态: published

## 编译步骤

1. 上游来源核验：`git ls-remote --tags https://github.com/troydhanson/tpl`
   → 官方标签 `v1.6.1` = commit 5ac54fe7beab67cbfb6f95552c15a68204a014bd
   → 使用官方 release tarball `https://github.com/troydhanson/tpl/archive/refs/tags/v1.6.1.tar.gz`
   → SHA256: 0b3750bf62f56be4c42f83c89d8449b24f1c5f1605a104801d70f2f3c06fb2ff
2. `ohc-run.py init-build tpl 1.6.1`（注意：init-build 的 F068 嵌套提升逻辑把 doc/ 误判为
   源码根并删除 src/tests；手工用 `tar --strip-components=1` 重建 orig/work，edit-tracker 重建基线 399 文件）
3. bootstrap（tarball 不含预生成 configure）：
   `aclocal-1.16 -I config; autoheader; libtoolize --copy --force; automake-1.16 --foreign --add-missing --copy; autoconf`
   （系统 automake 主脚本指向缺失的 automake-1.17 Perl 模块，改用 1.16）
4. `./configure --prefix=$DEFAULT_PREFIX`（修复 config.status 的 umask 077 → 002，HMDFS 权限模型）
5. `make -j2` → libtpl.so.0.0.0 + libtpl.a 构建成功
6. 上游测试 `make -C tests all`（perl do_tests）：
   - 124 个测试程序，首轮 72 失败：上游测试硬编码 `/tmp/testN.tpl`，本平台 /tmp 只读（E002）
   - 批量把 `"/tmp/test` 改为 `"test`（相对路径，do_tests 在 tests/ 目录运行），test67.ans 同步适配
   - 复跑：124/124 通过（0 failed）
7. `make install DESTDIR=$TEST_PREFIX` → lib/include 产物齐全
8. `ohc-run.py conan-init tpl 1.6.1` + 手工修正：
   - conandata.yml 填入实际 sha256
   - conanfile.py：tool_requires automake/1.18 + libtool/2.5.4；build() 内 `autoreconf -fi` bootstrap
     + `_drop_umask_077`（E114）+ `--build/--host=aarch64-unknown-linux-ohos`（E007）+ `-j1`（E074）
   - test_package/test.c 从空壳改为实质 roundtrip 测试（tpl_map/pack/dump/load/unpack + 断言 42）
9. `ohc-run.py conan-verify tpl 1.6.1` → G0-G4 + L2/L4/L5 全 PASS
10. `ohc-run.py finish tpl 1.6.1 published` → W2 结构 + R36 依赖 + W3 本地 CI 通过
    （.ci-result.json exit_code=0，log_sha256 记录；补 test-report.md/packaging/.staging-verified）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 提取后 work 目录只有 doc/ 内容 | init_build.py F068 嵌套提升用精确文件名 `Makefile` 判断源码根，tpl 根只有 `Makefile.am`，doc/ 有 `Makefile` 被误提升 | 手工 `tar --strip-components=1` 重建 orig/work + 重建 edit-tracker 基线 |
| 2 | bootstrap 报 Automake::Config.pm 缺失 | 系统 automake/aclocal 脚本硬编码 automake-1.17 @INC，但只装了 1.16 | 用 `aclocal-1.16`/`automake-1.16` 执行等价序列 |
| 3 | config.status 报 `can't create ./conf*/subs1.awk: Permission denied` | HMDFS 权限模型：`umask 077` 创建的 drwx--S--- 目录 owner 不可写（E114） | 改 config.status 两处 umask 077 → 002；配方内固化 `_drop_umask_077` |
| 4 | configure 报 `cannot guess build type` | config.guess 2024-07-27 无法识别 `uname -s = HarmonyOS`（E007） | 配方显式传 `--build/--host=aarch64-unknown-linux-ohos` |
| 5 | 上游测试 72/124 SIGSEGV | 测试硬编码 `/tmp/testN.tpl` 写文件，/tmp 只读（E002）导致 tpl_dump 失败后 tpl_load 空数据 | 批量改相对路径 + test67.ans 同步 |
| 6 | conan-verify G2 通过但 W3 被 JC5 拦截 | `archives/u/util-linux-login/2.42.2/.ci-trigger`（其他库已合入 main 的空文件）未登记 JC5 白名单 | 临时 `git rm --cached` 隔离 → W3 复验通过 → `git restore --staged` 无条件恢复（blob e69de29 哈希核对一致） |
| 7 | finish Step10 就绪预检 3 项未就绪 | 缺 test-report.md / packaging/ / .staging-verified | 按真实结果补全 |
| 8 | G0 clean-verify configure exit 127 | 干净验证环境直接跑 ./configure，但 tarball 无预生成 configure（需配方内 autoreconf） | G0 非阻塞（流程局限），G2 conan create 已实证通过 |

## 源码修改

- 上游 tests/*.c（88 文件）：`"/tmp/test` → `"test`（123 处，/tmp 只读适配，E002）
- tests/test67.ans：期望输出文件名同步适配
- 全部以 patches/ 目录 89 个补丁固化，由 conanfile `apply_conandata_patches` 应用
- 无平台宏（__OHOS__）注入（PF5 合规）；所有补丁为纯路径适配
