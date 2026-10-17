# dirent 1.26 — 适配笔记

## 基本信息
- 上游: https://github.com/tronkko/dirent (tronkko), tag 1.26 (2025-07-15)
- 类型: 纯头文件兼容库 (CMake INTERFACE target `dirent`) —— 为 MSVC 提供 dirent.h；
  Linux/OHOS 上由系统 libc 提供 dirent API，头文件与 CMake 目标向下游暴露同一接口。
- License: MIT
- 依赖: 无（header-only，零编译产物进入包；系统 dirent API 由平台 libc 提供）
- 官方源码 SHA-256: `a91662ee5243d2dae5aee7ed8527f95097afda517cc5cc7ca2699648a74a419c`
  （gh-proxy.com 与 ghfast.top 双镜像代理下载核验一致，字节等于官方 tarball）

## 适配要点
1. 上游 CMakeLists.txt: `add_library(dirent INTERFACE)`，`DIRENT_TEST`/`DIRENT_EXAMPLES`
   三态开关；`DIRENT_TESTS=ON` 注册 9 个 CTest 可执行测试（SKIP_RETURN_CODE=77），
   `DIRENT_EXAMPLES=OFF`（示例是演示 CLI，非交付物，不进包 → 无 bin/ 产物，无需 commands.json）。
2. 配方 `package_type="header-library"`，`package()` 走 `cmake.install()`
   （安装 `include/dirent-1.26/dirent.h` + `lib/cmake/Dirent-1.26/` 配置），
   另复制 LICENSE；`package_id()` clear → 单一包 ID。
3. `package_info()` 镜像上游 `cmake_file_name=Dirent` / `cmake_target_name=dirent`，
   消费者可 `find_package(Dirent)` + link `dirent`。
4. OHOS 交叉：CMakeToolchain 设 `CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`、
   `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`（沿用仓库既有 header-only 配方模式）。

## 上游测试（R51 台账，双口径）
源码声明 9 个独立上游测试可执行文件（CMakeLists.txt foreach 列表，非框架宏/SECTION）：
t-compile.c, t-dirent.c, t-scandir.c, t-unicode.c, t-cplusplus.cpp,
t-telldir.c, t-strverscmp.c, t-utf8.c, t-symlink.c
→ 全部在 build() 中经 ctest 实例化并执行；每个测试依赖 tests/1..4 下的 fixture 数据目录。

### 双口径统计（实测，cwd=conan build/Release）
- source_declared_total = 9（CMakeLists.txt `foreach(... ITEMS ...)` 枚举的全部独立测试源）
- configured_executable_total = 9（`ctest -N` 注册 9 项，全部实例化为独立可执行）
- executed_passed_total = 7，failed = 0，skipped/uninstantiated = 2
- 全量通过率：7/9 (77.8%)；当前配置可执行集合通过率：7/7 (100%)
- 实际命令：`ctest --output-on-failure`，退出码 0
- 日志：`~/.oh-runner/dirent-evidence/ctest-full.log`（SHA-256 a8a273dcdf48d12c062881e33068636fa3e5e6939681c45b534a086d85857584）

| 源码声明 -> 构建目标 -> ctest 注册 -> 实际结果 | 分类 | 说明 |
|---|---|---|
| tests/t-compile.c -> t-compile -> Test#1 | ✅ 通过 | 编译干净性（含 winsock 冲突场景） |
| tests/t-dirent.c -> t-dirent -> Test#2 | ✅ 通过 | dirent 核心 API（检索/不存在/rewind/chdir 等） |
| tests/t-scandir.c -> t-scandir -> Test#3 | ✅ 通过 | scandir/alphasort/versionsort/1000 文件大目录 |
| tests/t-unicode.c -> t-unicode -> Test#4 | ⏭️ skipped(77) | 上游 `#ifdef WIN32` 专用（宽字符/locale），非 Windows 平台 exit(77) |
| tests/t-cplusplus.cpp -> t-cplusplus -> Test#5 | ✅ 通过 | C++ 编译兼容性 |
| tests/t-telldir.c -> t-telldir -> Test#6 | ✅ 通过 | telldir/seekdir 定位 |
| tests/t-strverscmp.c -> t-strverscmp -> Test#7 | ✅ 通过 | strverscmp 版本串比较（libc 探针兜底） |
| tests/t-utf8.c -> t-utf8 -> Test#8 | ⏭️ skipped(77) | 上游 `#ifdef WIN32` 专用（UTF-8 文件名），非 Windows 平台 exit(77) |
| tests/t-symlink.c -> t-symlink -> Test#9 | ✅ 通过 | 符号链接识别（limits.h + TMPDIR 补丁） |

跳过说明（不计失败，也不冒充通过）：t-unicode/t-utf8 在上游源码中即限定
`#ifdef WIN32`（非 Windows 分支 `fprintf(stderr,"Skipped"); exit(77)`），
CMakeLists 对全部测试设 `SKIP_RETURN_CODE 77`；OHOS 无对应 Windows
locale/宽字符路径，属上游自身设计，非本次适配引入。

适配改动（全部为可复现补丁，见 patches/）：
1. 0001 t-symlink：补 `<limits.h>`（PATH_MAX）+ 测试临时目录尊重 $TMPDIR
2. 0002 t-strverscmp：libc 探针兜底 dirent 自带可移植 strverscmp（R8 例外）
3. 0003 t-scandir：libc 探针兜底 versionsort/strverscmp + test_large 尊重 $TMPDIR

## 鸿蒙专项测试
test_package/test_dirent.c —— 消费者用例：链接包的 `dirent` CMake 目标，
调用 opendir/readdir/closedir/scandir/alphasort/telldir/seekdir/rewinddir
对真实目录迭代、排序、定位，验证可观察结果（≥1 条业务 API 断言）。

## 外部阻塞 / 网络
github.com 直连不可达；源码下载经仓库 CI 既定镜像通路（见
ci/conan/build_and_test.sh mirror fallback）。conandata.yml 保留官方 URL。

## 知识候选台账（Path B 判定，四范围查重）

**候选 1 — OHOS musl 缺 GNU strverscmp()/versionsort()，上游测试源码 libc 探针兜底**
- 真实错误：`ld.lld: undefined symbol: strverscmp`（t-strverscmp.c）、
  `use of undeclared identifier 'versionsort'`（t-scandir.c）
- 根因：OHOS 运行时 libc 为 musl，不提供 glibc 的 GNU 扩展
  strverscmp()/versionsort()；dirent 自带 include/dirent.h 内有可移植实现，
  但非 Windows 平台测试链接的是系统 dirent.h，拿不到该符号。
- 修复：测试文件顶部 `#if !defined(__GLIBC__) && !defined(_MSC_VER)` libc
  探针内提供 dirent_portable_strverscmp/dirent_portable_versionsort
  （函数体复用 dirent.h 自带实现），宏映射 strverscmp/versionsort。
- 验证：t-strverscmp PASS、t-scandir PASS（断言全部保留，非伪造）。
- 适用边界：OHOS/musl 上任何直接调用 strverscmp/versionsort 的 C/C++
  测试源码；glibc 平台零影响；R8 libc 探针例外已在 PR 说明理由。

**候选 2 — OHOS PC /tmp 只读 erofs，上游测试硬编码 /tmp 路径，$TMPDIR 探针替换**
- 真实错误：`Cannot create directory /tmp/xxx`（t-symlink）、
  `Assertion failed: ok == 0`（t-scandir test_large 1000 文件用例）
- 根因：OHOS PC 的 /tmp 是 erofs 只读挂载（`/dev/block/dm-0 ro`），测试
  源码硬编码 `strcpy(dirname,"/tmp/")` 不读 TMPDIR 环境变量，mkdir 必失败。
- 修复：测试源码改为 `getenv("TMPDIR")`（回退 /tmp）拼接；conanfile
  build()/test() 内建 build_folder/test-tmp 并设 TMPDIR/TMP/TEMP。
- 验证：t-symlink PASS、t-scandir PASS；9/9 实例化，7/7 可执行集通过。
- 适用边界：测试源码硬编码 /tmp 的 C 库；不适用于 libc tmpfile() 调用
  （DRAFT-8959）或 configure/config.status 临时目录（E136/E052）。

**候选 3 — 非候选（外部环境）**：github.com 直连不可达 → CI 镜像 fallback，
已有机制，不入库。

### 四范围查重结果（七轴）

| 轴 | 候选 1 (strverscmp/versionsort) | 候选 2 (/tmp 硬编码) |
|---|---|---|
| exact_duplicate | 否 | 否 |
| causal_duplicate | 部分：E534（busybox musl GNU 扩展兼容层）根因相同，但 E534 是**库侧** weak 符号方案 | 部分：E002（/tmp erofs 根因相同）是 environment 层设 TMPDIR，对硬编码路径测试源码无效 |
| trigger_overlap | 高（undefined symbol: strverscmp 已在 E534 error_signature） | 高（/tmp read-only erofs 已在 E002） |
| solution_overlap | 中：E534 库内 weak 符号 / E093-E094 source-patch 同族；本候选是**测试源码侧** libc 探针 + 复用 dirent 自带实现 | 中：DRAFT-8959（musl tmpfile 硬编码 /tmp → 代码级 TMPDIR 替代）同族但为 libc 函数侧；本候选是测试源码字面路径侧 |
| combination_novelty | 有：libc 探针 + 测试上下文 + 自带实现复用组合，可跨库套用 | 有：字面 "/tmp/" 拼接场景 + 构建侧 env 注入组合 |
| boundary_novelty | 有：明确划分测试源码侧（本）vs 库侧（E534）vs 框架 tmpfile（DRAFT-8959） | 有：测试源码路径侧（本）vs libc 函数侧（DRAFT-8959）vs configure（E136） |
| test_migration_novelty | 有：把既有 musl-GNU-扩展知识迁移到上游测试适配，全量台账可追溯 | 有：把 E002 知识迁移到测试源码适配，实测 7/7 通过 |

**关系字段**：similar_to E534/E093/E094/DRAFT-8959；caused_by（触发根因）
E002（/tmp erofs）；prerequisite_of 无；conflicts_with 无。

**路径决定**：`new_draft`（Path B）。任一候选已验证（真实日志）、可跨库
复用（任意 OHOS/musl C 库测试源码均可套用），且查重为部分覆盖并存在新增
差异（测试源码侧探针补丁组合），故必须走 Path B 并建立同 stem 草稿：
`knowledge/drafts/DRAFT-DIRENT-1.26-OHOS-UPSTREAM-TEST-LIBC-PROBE-TMPDIR`
（.kv/.md 配对）。草稿与 dirent 归档同 PR 交付。
---

**编译结束**: 2026-09-22 16:08
**最终状态**: built
