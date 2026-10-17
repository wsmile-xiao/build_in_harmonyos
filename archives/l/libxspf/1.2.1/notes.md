# libxspf 1.2.1 适配笔记

## 编译环境

- 构建系统: autotools（configure + make，2021 年生成的配置脚本直接可用）
- 编译日期: 2026-09-15
- 编译器: clang / clang++（HarmonyOS aarch64，profile: ci/conan/profiles/ohos-aarch64）
- 状态: built（首轮工作树，待 HMBS 真机预检通过后转 published）

## 源码身份

- 官方主页: https://libspiff.sourceforge.net/
- 上游仓库: https://gitlab.xiph.org/xiph/libxspf（tag libxspf-1.2.1）
- 官方发布包: https://downloads.sourceforge.net/project/libspiff/Sources/1.2.1/libxspf-1.2.1.tar.bz2
- 实际 SHA-256: ce78a7f7df73b7420b6a54b5766f9b74e396d5e0b37661c9a448f2f589754a49（本地下载实测，与 Homebrew 公式一致）
- 许可证: BSD-3-Clause（库本体；test/ 目录为 LGPL，仅构建时使用、不打包）

## 上游测试审计（147 用例的来源）

上游测试入口为 `make check`，对应 Makefile.am 中的 `TESTS = test/xspf_test`
（CppTest 框架，`test/test.cpp` 把 9 个 Suite 聚合成一个测程序）。
TEST_ADD 注册数（从发布包源码数出）：

| Suite | 文件 | TEST_ADD 数 |
|---|---|---|
| OfficialSuite | test/OfficialSuite.cpp | 97 |
| DateTimeSuite | test/DateTimeSuite.h | 23 |
| WhiteSpaceSuite | test/WhiteSpaceSuite.cpp | 11 |
| MaliciousXmlSuite | test/MaliciousXmlSuite.cpp | 6 |
| ChunkCallbackSuite | test/ChunkCallbackSuite.cpp | 4 |
| ExtensionReaderFactorySuite | test/ExtensionReaderFactorySuite.cpp | 2 |
| ReadWriteSuite | test/ReadWriteSuite.cpp | 2 |
| MemoryModelSuite | test/MemoryModelSuite.cpp | 1 |
| ProjectOpusSuite | test/ProjectOpus/ProjectOpusSuite.cpp | 1 |
| 合计 | | **147** |

CppTest TextOutput 的成功摘要行为 `Total: 147 tests, 100% correct ...`，
每个 Suite 一行 `<Suite>: n/n, 100% correct ...`。配方在 build() 中同时校验：
automake test-suite.log（TOTAL/PASS/FAIL）、Total 行总数等于 147、
9 个 Suite 行齐全。任一项不满足即构建失败，防止"空跑报 PASS"的假阳性。

## 编译步骤

1. `source()`: 取官方 tar.bz2（strip_root）。
2. `generate()`: AutotoolsDeps + PkgConfigDeps；`-std=c++11`；
   shared=False 时 `--disable-shared --enable-static`；
   OHOS 下追加 `--build/--host=aarch64-unknown-linux-gnu`。
3. `build()`:
   - configure 脚本先做 `umask 077 → umask 022` 替换（HMDFS 兼容）。
   - 下载官方 CppTest 2.0.0（sha256 校验）并静态安装到 build 树前缀，
     PKG_CONFIG_PATH 指向它，然后正常 configure（测试默认启用）。
   - `make -j1`，再单独构建 `test/xspf_test` 并自签名，
     最后 `make -j1 check` 运行完整上游套件并输出
     `HMBS_UPSTREAM_TEST_RESULT` 标记。
4. `package()`: `make install`，删除 `.la`，COPYING 进 licenses/，
   bin/ 下的 ELF 工具自签名。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C++17 下 `std::auto_ptr` 编译失败 | 库与测试源码使用 C++17 已移除的 auto_ptr | 全局追加 `-std=c++11`（库、C bindings、CppTest 均满足，CppTest 官方即要求 C++11） |
| 2 | `PKG_CHECK_MODULES([CPPTEST]...)` 找不到 libcpptest | ohpcd 制品仓无 cpptest 配方 | build() 内 vendor 官方 2.0.0 源码（双镜像 + sha256 校验），静态构建到 build 树，交付物不含它 |
| 3 | 老 config.guess 不认识 HarmonyOS | 2021 年的 guess 脚本无 HongMeng/HarmonyOS 表项 | 显式传 GNU 三元组，完全绕开 guess（a52dec 同法） |
| 4 | 测试二进制在真机上无法执行 | HarmonyOS 要求 ELF 自签名 | 先构建测程序、签名、再跑 `make check`；交付工具同样签名 |

## 依赖版本

- expat/2.8.2.1（SONAME 已修复的版本线，transitive_headers）
- uriparser/1.0.2（transitive_headers）
- CppTest 2.0.0（仅构建时 vendor，不进 requires）

## 验证结果

```bash
# 由 HMBS 后台在 HarmonyOS aarch64 真机执行（本轮仅准备工作树）：
# conan create archives/l/libxspf/1.2.1 --profile ohos-aarch64
# 期望：make check 147/147 通过；test_package 10/10 通过
```

## 交付物

- lib/libxspf.a（默认静态）或 libxspf.so.4（shared=True 时，version-info 4:3:0）
- bin/xspf_check、bin/xspf_strip
- include/xspf/ 公共头（含 C bindings 的 xspf_c.h）
- lib/pkgconfig/xspf.pc

## 注意事项

- 首轮未提交：所有文件保持未提交工作树状态，等真机 evidence 轮回填实测数字。
- 若将来 ohpcd 上架 cpptest 配方，可把 vendor 逻辑换成正式 requires。
