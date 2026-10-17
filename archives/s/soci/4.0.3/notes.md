# soci 4.0.3 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists；SOCI_SHARED/SOCI_STATIC/SOCI_TESTS 顶层开关 + WITH_<BACKEND> 后端开关）
- 编译日期: 2026-09-20（QC-2 起）/ 2026-09-23（主代理-3 验证收敛）
- 编译器: clang/clang++ 15（profile: ci/conan/profiles/ohos-aarch64，os=OHOS arch=armv8）
- 状态: built（conan-verify G0-G3 通过；发布态由 release 流水线确认）

## 编译步骤
1. W0 依赖检查：sqlite3/3.53.4 已在 ohpcd 制品仓（二进制 `conan install --build=never` 实测可拉）。
2. 源码：官方 tag `v4.0.3`（conandata URL=官方 GitHub archive，SHA256 `4b1ff9c8…4928` 已对官方 URL
   直连复算一致；dlcache 已按官方+ghfast 双 URL 播种）。
3. generate()：CMakeDeps + CMakeToolchain，关键 cache 变量：
   - `CMAKE_SYSTEM_NAME=Linux` 别名（E092：CMake 不识别 HarmonyOS，上游 SociVersion.cmake 按 UNIX 判 ABI）；
   - `SOCI_VISIBILITY=OFF`：上游默认 hidden 会让 type_holder<T> 的 typeinfo 在各 DSO 各留副本，
     跨 DSO dynamic_cast 失配 → holder::get<T>() 抛 bad_cast（9 个动态绑定用例会全挂，预防性关闭）；
   - 只开 `WITH_SQLITE3=ON`（可离线），MYSQL/ORACLE/POSTGRESQL/FIREBIRD/DB2/ODBC 全 OFF（需真实服务端）；
   - `SQLite3_*` + `SQLITE3_*` 双大小写变量显式给路径（FindSQLite3 交叉环境看不到 sysroot；
     SociBackend.cmake 按大写取依赖路径，缺大写则 include 目录为空）；
   - `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 cmake_minimum_required 2.8，设备 CMake 4.1 已移除 <3.5 兼容）；
   - `CMAKE_INSTALL_RPATH=<build>/lib;`（见问题 #1 的字节改写坑，配合 package() 覆盖双保险）。
4. build()：apply 补丁 0001 → cmake configure+build → ctest（`--no-tests=error`，注册 0 不得静默判过；
   连接串与 --invisibles 由上游 SociBackend.cmake 的 add_test 注入）。
5. package()：cmake install → **用 build 树原始 .so 覆盖安装产物**（见问题 #1）→ 清理 cmake/ 元数据 → 拷 LICENSE。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 消费者运行期 `Error loading shared library libsoci_sqlite3.so.4.0`（冒号后**空 errno**）+ 连锁 `Error relocating … symbol not found`；被点名的库文件明明存在 | `cmake --install` 对**带 RUNPATH 的 .so** 做字节级改写（实测 p/lib 与 b/build 树 sha 不同；三轮迭代分别观察到 RUNPATH 整段摘除、`.dynstr`/`.dynamic` 重排、单字节尾冒号 `:`→NUL 归一化），改写产物经 musl 按名加载即失败；矩阵二分实锤：同字节 LD_PRELOAD 直投可过、LD/RUNPATH 指回 build 树 100% 可通、LD 首个命中者定生死（P 目录排前即败）。钉 `CMAKE_INSTALL_RPATH`（含尾 `;` 变体）三轮均未能让 sha 打平 | **终局双修**：① `package()` 用 build 树**原始字节**覆盖安装产物（其自带 RUNPATH 指 `b/build/Release/lib`，与上游构建树语义一致，矩阵实测可载）——修后 p/lib 与 b/build sha 逐字节相同（`50bd9ca9…`）；② `test()` 内联 `LD_LIBRARY_PATH` **build 树 lib 排最前** + SDK llvm lib（libc++_shared，VirtualRunEnv 挂不到）+ 各依赖 lib，`ctest` 直跑（`cmake.test()` 默认 env 空串不可靠）。症状与 musl 空 errno 诊断见通用池 `DRAFT-PKG-VER-musl-ldso-inner-missing-empty-errno` |
| 2 | test_package 首验编译不过：`fatal error: 'sqlite3.h' file not found` | `soci-sqlite3.h` 直接 `#include <sqlite3.h>`；本版 conan 的 CMakeDeps 没为**透传依赖**在测试侧落盘 `sqlite3-config.cmake`（generators/ 仅 soci-*，soci data.cmake 的 find_dependency 名单为空 append） | test_package `requirements()` 显式直连同版 `sqlite3/3.53.4`（图内同版自动去重）+ CMakeLists `find_package(sqlite3)` + 链接 `sqlite3::sqlite3` |
| 3 | 消费者测试本体是 printf-only 死文件（R34 风险：只打印不调 API、从未被 CMakeLists 引用编译） | 草稿期占位产物 | 重写为 `test.cpp` 真调 soci API：`soci::session(sqlite3, ":memory:")` 建表/插值/`into` 取回（往返值 42 的单点断言），异常路径非零退出；CMakeLists 改 CXX 并链接 soci::soci |
| 4 | 上游默认 `CMAKE_CXX_VISIBILITY_PRESET=hidden` 的跨 DSO dynamic_cast 失配（预防，配方注释有完整机理） | typeinfo 每 DSO 一份本地副本 | `SOCI_VISIBILITY=OFF` |
| 5 | 上游 cmake_minimum_required(2.8) 在设备 CMake 4.1 直接拒 | CMake 4.x 移除 <3.5 兼容 | `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 6 | Catch v1 内嵌头在 OHOS libc++ URNG 检查下 `result_type` 必须 unsigned | 平台 libc++ 静态断言差异 | 补丁 `0001-tests-catch.hpp.patch`（Q-6 期生成，per-file-difflib，portability） |

## 源码修改
- **patches/0001-tests-catch.hpp.patch**（portability）：Catch v1 内嵌头 `RandomNumberGenerator::result_type`
  改 unsigned，过 OHOS libc++ 的 URNG 检查；不改任何用例/断言。
- build() 内无 replace 改写；config 与打包侧调整全部在配方 cache 变量与 package() 内（见步骤3/5）。

## 依赖版本
- sqlite3/3.53.4（ohpcd 制品仓；静态 libsqlite3.a，链接期直入）
- 运行期系统库：libc++_shared.so（SDK/系统提供，非 conan 包；test() 内联 LD 已覆盖）

## 上游测试（R51 五维账本）
- N_static = **150**（源码静态清点：common-tests.h 共享头 61（62 个含 TEST_CASE 行中第 607 行是注释，W4 审计修正）+ 后端自有 89
  = sqlite3 10 + postgresql 24 + oracle 19 + mysql 14 + firebird 13 + odbc 5 + db2 3 + empty 1；
  `grep -r "TEST_CASE(" tests --include=*.cpp --include=*.h` = 89 后端自有，+61 共享 = 150）
- 构建启用后端：sqlite3 + empty（其余后端需真实数据库服务端，本配置未启用未编译，见 §12.72 数量变化说明）
- N_executed = **66 用例 / 1715 断言，全部通过**（ctest 2/2 + Catch 汇总双源同源：
  `soci_sqlite3_test` → `All tests passed (1715 assertions in 65 test cases)`（10 自有 + 55 共享）；
  `soci_empty_test dummy --invisibles` → `1 | 1 passed`）
- N_registered（本配置 ctest 注册）= 2 个测试程序；ctest exit≠0 即败，`--no-tests=error` 防 0 注册静默过
- 未执行 = **84 用例** = 78（**6 个**禁用后端自有：pg24+oracle19+mysql14+fb13+odbc5+db2 3 = 78，即 89−sqlite310−empty1）
  + 6（common 共享中被 tag/条件门控未注册：61−55）
- N_consumer = **1 程序 / 1 处断言**（test.cpp：建表/插值/`into` 取回**往返值 42 的单点断言**
  + 异常路径非零退出兜底；执行过程兼证包内共享库可加载——三个观测面、一处显式断言）
  由 test_package/conanfile.py `test()` 经 ctest 真实执行

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify soci 4.0.3   # 2026-09-23 主代理-3 终版
# G0 PASS / G1 PASS / G2 PASS（conan create + 上游 ctest 2/2 + 消费者 100%）/ G3 PASS
# test_package: "test soci 4.0.3: sqlite3 in-memory round-trip OK (42)"
# p/lib 与 b/build 树 libsoci_sqlite3.so.4.0.3 sha256 逐字节相同（50bd9ca9…，覆盖修复生效）
```

- 证据（均随 PR 入库、跨机可证）: reports/conan-create.log（上游 ctest `100% tests passed,
  0 tests failed out of 2` + 消费者 `out of 1`，且 RUN 行含 bd_lib 排首的 LD）；
  reports/upstream-tests-LastTest.log（Catch `All tests passed (1715 assertions in 65
  test cases)`）；reports/consumer-test-LastTest.log（`round-trip OK (42)` + Test Passed）；
  reports/w3-local-ci.log（W3 本地 CI 模拟 100%）。

## 注意事项
- **勿移除 package() 的 build 树覆盖**：cmake --install 的 RUNPATH 字节改写产物 musl 按名加载必败（#1）。
- **test() 内联 LD 顺序敏感**：build 树 lib 必须排最前（LD 首个命中者定生死）；SDK llvm lib 供 libc++_shared。
- 扩后端（WITH_MYSQL 等）前先起对应真实服务端，否则 78 个未执行用例会在连接期成批失败——按 §12.72 先改申报再开。
- `.gitmodules` 预扫提示（登记表）：上游含 submodule 形态（E150 路径），本配置 SQLite3 源码包未触发子模块拉取；
  若后续后端需子模块，按 E150 单独取源拷入。
---

**编译结束**: 2026-09-23 04:38
**最终状态**: built
