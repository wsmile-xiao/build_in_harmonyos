# complete-striped-smith-waterman 1.2.5 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure/CMake/Meson）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4（OHOS 平台，aarch64）
- 状态: published

## 编译步骤
1. `python3 scripts/ohc-run.py init-build complete-striped-smith-waterman 1.2.5 --url=https://github.com/mengyao/Complete-Striped-Smith-Waterman-Library/archive/refs/tags/v1.2.5.tar.gz`
   说明：首次传入仓库根 URL 会下载到 HTML 页面，必须使用官方 tag tarball 精确 URL。
2. 核验 SHA-256：本地重新下载官方 v1.2.5 tarball，sha256 = b294c0cb6f0f3d578db11b4112a88b20583b9d4190b0a9cf04d83bb6a8704d9a，与 init-build 缓存一致。
3. `lang-preflight` 通过：expected=cpp, detected=cpp（manifest=顶层 Makefile，源统计 c 36% + cpp 18%，无 ≥70% 主体，按 manifest 判 cpp）。
4. 直接 make 编译（上游 Makefile 硬编码 CC=gcc，须命令行覆盖）：
   `make CC=clang CXX=clang++ default`
   产物：ssw_test（CLI）、example_c（C API 示例）、example_cpp（C++ API 示例）、libssw.so。
5. 运行验证：`./ssw_test -h` rc=0；`./example_c` 输出 optimal_alignment_score: 21；`./example_cpp` 输出 Best Smith-Waterman score: 21。
6. Conan 配方：`ohc-run.py conan-init` 生成模板后手工重写（模板为 autotools，本库为纯 Makefile）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 报"下载内容是 HTML" | 传入仓库根 URL 返回 GitHub HTML 页面而非 tarball | 改用官方 tag tarball 精确 URL `.../archive/refs/tags/v1.2.5.tar.gz` |
| 2 | make 编译报 `gcc: No such file or directory` | 上游 Makefile 硬编码 `CC = gcc`，环境无 gcc；Makefile 内赋值优先于环境变量 | make 命令行传参覆盖：`make CC=clang CXX=clang++`（命令行变量优先级最高） |
| 3 | conan-init 模板为 Autotools（configure+make） | 生成器按 BUILD_SYSTEM=autotools 推断，但上游无 configure | 重写 conanfile.py：`make -j1 CC=... CXX=... default` 直接构建，package() 拷贝 libssw.so + ssw.h/ssw_cpp.h/sse2neon.h |
| 4 | main.c 链接需要 zlib | Makefile 链接行含 `-lz`（kseq gzip 读取），main.c include <zlib.h> | requirements 声明 zlib/1.3.1（ohpcd registry 已发布，R35 conan download 验证通过），generate() 把 -I/-L 注入 CPPFLAGS/LDFLAGS |
| 5 | 模板 test_package/test.c 为空壳（仅 printf） | 生成器模板无实质断言，违反 R34 | 重写为真实消费者用例：通过 ssw.h 调用 ssw_init/ssw_align，断言 score1>=21（上游实证值）+ cigar 非空 |
| 6 | ssw.h include "sse2neon.h" 消费者编译需要 | ssw.h 内部使用 SSE2 类型（__m128i profile），arm64 需 sse2neon 纯头翻译 | package() 把 sse2neon.h 一并装入 include/ |

## 依赖版本
- zlib/1.3.1（ohpcd registry，os=OHOS arch=armv8 clang15 Release 已发布）

## 验证结果
```bash
# 源码编译
make -j1 CC=clang CXX=clang++ default   # rc=0
# 上游 CLI 入口
./ssw_test -h                            # rc=0，Usage 正常
# 上游 C API 示例
./example_c                              # rc=0，optimal_alignment_score: 21
# 上游 C++ API 示例
./example_cpp                            # rc=0，Best Smith-Waterman score: 21
# 消费者用例（test_package）
./test_complete-striped-smith-waterman   # PASSED，score1=21，cigar 非空
```

## 注意事项
- 上游无 make check/CTest/Meson 测试目标；测试入口为官方三个独立可执行程序（ssw_test/example_c/example_cpp），已在 MANIFEST.yml 申报并在 Step 2 实际运行。
- ssw_test 是 CLI（提供 -h），但本包为库类型交付（libssw.so + 头文件），不安装 bin/，故不需要 commands.json。
- 上游 sse2neon.h 已内嵌（341KB），SSE2->NEON 翻译开箱即用，无需 SIMDe 外部依赖。
---

**编译结束**: 2026-09-21 16:31
**最终状态**: built

## 知识候选台账与七轴查重（路径判定：new_draft / 路径 B）

### 候选 1：conandata.yml 注释中的 https URL 被 CI pre-download 正则误匹配（HTML 仓库页当 tarball 下载 → NotADirectoryError）

- 真实错误/根因/修复：W3 的 build_and_test.sh Pre-download 从 conandata.yml **全文**（含注释）提取
  `https?://` URL；注释里的仓库主页 URL 是真实 tarball URL 的前缀子串，被下载为 HTML（>100 字节判成功），
  `content.replace` 污染真实 URL 中段为 `file://.../predl_cache/{hash}_...`，conan 端
  `NotADirectoryError: .../predl_cache/4c56c7d5_Complete-Striped-Smith-Waterman-Library/archive/refs/tags/v1.2.5.tar.gz`。
  修复：conandata.yml 注释不写任何协议 URL（上游信息用无协议形态，主页由 conanfile.py homepage 承载），
  并清理 `.build-cache/predl_cache`（坏 HTML 缓存会以 `[cached]` 复活）。验证：清缓存 + 注释去 URL 后
  W3 conan create 通过（rc=0）。
- 七轴查重：
  - exact_duplicate: 是（既有草稿 DRAFT-8960-raqm-0.11.0-conandata-comment-url-predl-pollution 完全覆盖
    同一根因/触发工具/解法）
  - causal_duplicate: 是（根因相同：predl 正则提取注释 URL）
  - trigger_overlap: 是（触发条件相同：conandata.yml 注释含 https URL）
  - solution_overlap: 是（解法相同：注释去协议 URL + 清 predl_cache）
  - combination_novelty: 否；boundary_novelty: 否；test_migration_novelty: 否
- 既有条目覆盖部分：DRAFT-8960 已完整覆盖（含自查命令 `grep -E '^#.*https?://' conandata.yml`、
  清缓存要求、E333 同族关系说明）。
- 本轮新增部分：无（仅新增 complete-striped-smith-waterman 实例；查重差异为空）。
- 适用边界/反例：任何 conandata.yml 注释含协议 URL 的库都会命中；CI 侧若未来只解析 YAML 数据段则失效。
- 关系：similar_to DRAFT-8960（同一实例族）；caused_by build_and_test.sh pre-download 正则范围；
  prerequisite_of 无；conflicts_with 无。
- 决定：**reuse_existing**（复用 DRAFT-8960，不建新草稿）。

### 候选 2：上游 Makefile 硬编码 `CC = gcc`，OHOS 无 gcc 导致 `gcc: No such file or directory`

- 真实错误/根因/修复：上游 Makefile 首行 `CC = gcc`/`CXX = g++`，make 内赋值优先于环境变量，
  直接 make 报 `make: gcc: No such file or directory`。修复：make 命令行传参覆盖
  `make CC=clang CXX=clang++`（命令行变量优先级最高）；conan 配方中从
  `tools.build:compiler_executables` conf 取编译器（R33）再以命令行参数传入。验证：编译 rc=0 全部产物生成。
- 七轴查重：
  - exact_duplicate: 否（无同库实例条目）
  - causal_duplicate: 是（根因相同：Makefile 硬编码 gcc 需命令行覆盖——E568 已覆盖"手写 Makefile 的
    工具链注入陷阱：命令行变量覆盖语义（复合定义 CC vs +=）"）
  - trigger_overlap: 是（触发条件相同：OHOS 无 gcc + Makefile 硬编码 CC）
  - solution_overlap: 是（解法相同：命令行变量覆盖 / 工具链注入）
  - combination_novelty: 否；boundary_novelty: 否；test_migration_novelty: 否
- 既有条目覆盖部分：E568（命令行变量覆盖语义）已覆盖核心；E575 覆盖 raw Makefile 配方传 CFLAGS 转义。
- 本轮新增部分：无（仅新增本库实例）。
- 适用边界/反例：Makefile 硬编码 gcc/g++ 的纯 Makefile 库通用；`ifdef __arm__` 等条件分支不影响本解法。
- 关系：similar_to E568；caused_by 上游 Makefile 硬编码；conflicts_with 无。
- 决定：**reuse_existing**（复用 E568，不建新草稿）。

### 候选 3：纯 Makefile 共享库链接行缺少 DT_SONAME → L5 SONAME 门禁失败

- 真实错误/根因/修复：W3 的 L5a 门禁报 `libssw.so 缺少 DT_SONAME`。上游 Makefile 手写链接行
  `$(CC) $(CFLAGS) -fPIC -shared -rdynamic -o $@ $<` 从不传 `-Wl,-soname`，产物无 DT_SONAME；
  与 CMake 场景（E383：CMake 4.x 无 Platform/HarmonyOS.cmake 导致 SONAME flag 为空）触发面不同——
  此处与 CMake 平台模块无关，是 Makefile 链接行自身缺项。修复：补丁给链接规则追加
  `-Wl,-soname,libssw.so`，conandata.yml patches 段声明，W3 重跑 L5_RESULT=pass，
  `readelf -d libssw.so | grep SONAME` → `[libssw.so]`。
- 七轴查重：
  - exact_duplicate: 否
  - causal_duplicate: 否（根因不同：CMake 平台模块缺失 vs Makefile 链接行缺项）
  - trigger_overlap: 部分（同为 L5 SONAME 门禁触发，但上游构建系统不同）
  - solution_overlap: 部分（都是注入 `-Wl,-soname`，但实现形态不同：CMake conan flag vs Makefile 补丁）
  - combination_novelty: 是（"纯 Makefile 手写链接行 + 补丁注入 SONAME" 为既有条目未覆盖组合）
  - boundary_novelty: 是（E383/DRAFT-cmake-harmonyos-platform-soname-flag 均为 CMake 场景，
    纯 Makefile 场景边界未覆盖）
  - test_migration_novelty: 否
- 既有条目覆盖部分：E383、DRAFT-cmake-harmonyos-platform-soname-flag 覆盖 CMake 场景
  （`CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG="-Wl,-soname,"`）；E274/E330/E537 覆盖
  SONAME symlink/运行时相对路径场景；DRAFT-binn 覆盖 raw makefile strip 后符号问题（不同机因）。
- 本轮新增部分：纯 Makefile（无 CMake）共享库缺 DT_SONAME 时，以 patches 补丁改写 Makefile
  链接规则注入 `-Wl,-soname,<libname>.so` 的完整处置（含补丁 hunk 行数注意事项），
  已由本轮真实日志验证（L5 fail → pass）并可跨库复用（任何 raw Makefile 构建 .so 的库）。
- 适用边界/反例：适用——纯 Makefile/手写链接规则的共享库，L5a 报缺 DT_SONAME；
  反例——CMake 工程走 E383 flag 方案；上游已带 versioned SONAME（libfoo.so.0）无需裸名；
  纯静态库无此门禁。
- 关系：similar_to E383、DRAFT-cmake-harmonyos-platform-soname-flag（SONAME 注入同族）；
  caused_by L5 SONAME 门禁 + Makefile 链接行缺项；prerequisite_of 无；conflicts_with 无。
- 决定：**new_draft**（建 `knowledge/drafts/DRAFT-raw-makefile-shared-lib-soname-patch.md/.kv` 配对草稿，
  路径 B【知识库扩展】）。

### 路径决定

- reuse_existing：候选 1（DRAFT-8960）、候选 2（E568）——完整重复，复用既有知识。
- new_draft：候选 3（DRAFT-raw-makefile-shared-lib-soname-patch）——部分覆盖且存在已验证、可跨库复用的
  新增差异（纯 Makefile 链接行注入 SONAME）。
- 结论：**路径 B【知识库扩展】**，new_draft 配对（.md/.kv）与三方库归档进入同一 PR。
