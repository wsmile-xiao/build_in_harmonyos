# zycore-c 1.5.1 adaptation notes

## Scope

- Task: zycore 1.5.1 第一轮完整适配（知识库扩展）
- Branch: `feat/zycore-1.5.1`
- Package: `zycore-c/1.5.1`

## W0 dependency check

The upstream CMake project links no third-party libraries. Its only optional
test dependency is GoogleTest (found via `find_package(GTest QUIET)`, else
downloaded during configuration when `ZYCORE_BUILD_TESTS` is on). The package
recipe disables upstream tests to keep source and build stages offline and
adds no Conan requirements. No dependency adaptation needs to be split out.

## Source and build analysis

- Official source: `https://codeload.github.com/zyantific/zycore-c/tar.gz/refs/tags/v1.5.1`
- SHA-256: `292ec0b30a68a6be416119756238efb5ab34122de80cca884e269e28f6fc126b`
- License: MIT.
- Upstream provides CMake and Meson; this recipe uses CMake because it exports
  and installs the `Zycore::Zycore` CMake target directly.
- `ZYCORE_BUILD_SHARED_LIB`, `ZYCORE_BUILD_EXAMPLES`, and `ZYCORE_BUILD_TESTS`
  are explicit. The default package is static, matching upstream's default.
  Doxygen discovery is disabled to avoid an incidental documentation build.
- The upstream CMake test suite has three GoogleTest executables: `String`,
  `Vector`, and `ArgParse`. It is kept out of the package recipe because it
  downloads or locates GoogleTest during configuration; it is validated on the
  device with the upstream-pinned GoogleTest revision.

## Consumer test

`test_package/test.c` links the installed `Zycore::Zycore` target and exercises
allocator-backed `ZyanVector` initialization, insertion, size retrieval,
indexed value retrieval, and destruction. This is an API and runtime assertion,
not an include-only smoke test.

## Version-relative notes vs 1.5.2

Recipe copied from the 1.5.2 archive with version/SHA updated. 1.5.1 and 1.5.2
differ only in minor source files (CMakeLists, Defines.h, Zycore.h, tests,
examples); no adaptation-relevant upstream change exists between them.

## Knowledge candidate ledger (知识候选台账)

| 候选 | 描述 | 真实错误/现象 | 根因 | 修复 | 验证 | 适用 | 查重结果 | 路径决定 |
|---|---|---|---|---|---|---|---|---|
| K1 | 上游测试在配置期下载 GTest | ZYCORE_BUILD_TESTS=ON 时 find_package(GTest) 未命中 → ExternalProject 下载 googletest | 测试框架网络引导，库本身无此运行时依赖 | 配方 ZYCORE_BUILD_TESTS=OFF + 独立消费者 test | conan create 通过；上游 GTest 单独在 OHOS 工具链下 28/28 | 同类 CMake 库 | exact_duplicate → E342 (disable-networked-upstream-tests-and-run-consumer-test) | reuse_existing |
| K2 | codeload URL basename 无扩展名导致 Conan 误判 zip | codeload tar.gz 的 basename 为 v1.5.1（无扩展名），get() 按 zip 解压 | Conan 按 basename 选解压器 | conandata.yml 显式 filename: zycore-c-1.5.1.tar.gz | conan create 源码解压成功 | 所有 codeload 源 | exact_duplicate → E276 (filename 修复) | reuse_existing |
| K3 | OHOS 下上游 Linux-only Threads 链接分支失效 | 上游 `if (CMAKE_SYSTEM_NAME STREQUAL "Linux")` 才 find_package(Threads)+链接 Threads::Threads；OHOS 下分支不执行，静态库无 pthread 链接信息，下游静态消费者链接 undefined reference pthread_* | 平台分支精确匹配未覆盖 OHOS；库源码实际使用 pthread API | 配方 package_info 对 Linux/OHOS 声明 system_libs=["pthread"] | conan create exit 0；test_zycore_ohos 调用 ZyanThreadTlsAlloc 实际运行输出 `zycore-c ohos test passed` | 上游 Linux-only 条件链接 Threads 且源码用 pthread 的 CMake 静态库 | partial_overlap → E607(平台分支漏编源文件)/E003(-pthread flag) 均部分相关但修复面不同（配方层 vs 源码/CFLAGS 层） | new_draft → E543 (draft) |

## Seven-axis dedup (七轴查重)

### K1 vs E342
- exact_duplicate: **true**（同一错误签名：ExternalProject/FetchContent 配置期下载 GTest；同一方案：禁用上游网络测试 + 消费者测试兜底）
- causal_duplicate: true
- trigger_overlap: true
- solution_overlap: true
- combination_novelty: false
- boundary_novelty: false
- test_migration_novelty: false
- 决定：完整重复，复用 E342，无独立差异。

### K2 vs E276
- exact_duplicate: **true**（codeload basename 无扩展名 → 显式 filename）
- causal_duplicate: true
- trigger_overlap: true
- solution_overlap: true
- combination_novelty: false
- boundary_novelty: false
- test_migration_novelty: false
- 决定：完整重复，复用 E276，无独立差异。

### K3 vs E607/E003
- exact_duplicate: false
- causal_duplicate: false（E607 缺的是被平台分支漏编的**源文件**；K3 缺的是**链接库依赖**，所有源文件都已编译）
- trigger_overlap: partial（同属"CMAKE_SYSTEM_NAME 平台分支未覆盖 OHOS"，但 K3 触发在静态链接期且表现为 pthread undefined reference）
- solution_overlap: partial（E607 修源码/补丁层；E003 加 CFLAGS -pthread；K3 修 Conan 配方 package_info system_libs 层，三方案均不相同）
- combination_novelty: **true**（配方层 system_libs 透传 pthread 给下游静态消费者，E003/E607 均未覆盖此交付形态）
- boundary_novelty: **true**（适用边界：上游 Linux-only 条件链接 Threads + 源码使用 pthread + 静态交付；反例：无条件 find_package(Threads) 或共享库交付不适用）
- test_migration_novelty: false
- 决定：部分重复但存在已由本轮真实日志验证（conan create + ohos 专项测试实际运行）且可跨库复用的新增差异 → **new_draft**，建立 E543-draft 草稿（.kv/.md 配对）。

## Path decision

- `reuse_existing`: K1(E342)、K2(E276)
- `new_draft`: K3(E543-draft-E932.kv / .md)
- `path_a_no_knowledge`: 不适用（存在已验证新增知识 → 路径 B 成立）
- 关系：E543 similar_to E607/E003，caused_by 无，prerequisite_of 无，conflicts_with 无。
- 知识库草稿与 zycore-c 1.5.1 归档文件进入同一 PR。
---

**编译结束**: 2026-09-18 02:48
**最终状态**: built
