# bitmapplusplus 1.1.1 适配笔记

## 编译环境
- 构建系统: headeronly（上游为 CMake INTERFACE 头文件库，`lib/include/BitmapPlusPlus.hpp` 单头文件）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4 / clang++ (OHOS aarch64 profile)
- 状态: built（conan-verify 通过，未 upload）

## 编译步骤

```bash
# 1. init-build：官方 tag v1.1.1 tarball
#    https://github.com/baderouaich/BitmapPlusPlus/archive/refs/tags/v1.1.1.tar.gz
#    sha256=dd1ca714c0b1a99f7738f3e340016982409987388348e1378e1b06bc6eaa3c15
python3 scripts/ohc-run.py init-build bitmapplusplus 1.1.1 --url=https://github.com/baderouaich/BitmapPlusPlus

# 2. lang-preflight：cpp 匹配通过（R47）
python3 scripts/ohc-run.py lang-preflight bitmapplusplus 1.1.1 --src <work>/bitmapplusplus-1.1.1.work

# 3. conan-init（headeronly 模板）+ 手工修正：
#    - conanfile.py: package() 复制 lib/include/*.hpp（上游头文件在子目录，非源码根）
#    - conanfile.py: package_type = "header-library"（否则 conan create 报
#      "Package type is 'library', but no 'shared' option declared"）
#    - conandata.yml: 官方 archive tarball URL + sha256
python3 scripts/ohc-run.py conan-init bitmapplusplus 1.1.1 --force

# 4. 上游示例验证（BPP_BUILD_EXAMPLES=ON 时 10 个示例经 add_test 注册为 ctest）
cmake -S . -B <tmp>/bpp-examples-build -DBPP_BUILD_EXAMPLES=ON
cmake --build <tmp>/bpp-examples-build -j4
ctest --test-dir <tmp>/bpp-examples-build --output-on-failure   # 10/10 passed

# 5. conan-verify（G0-G4 + L2/L4/L5 全通过）
python3 scripts/ohc-run.py conan-verify bitmapplusplus 1.1.1
#    conan create 内 test_package 消费者测试真实运行：
#    ./test_bitmapplusplus        11 组断言 ALL PASS
#    ./test_bitmapplusplus_ohos   4 组断言 ALL PASS（鸿蒙特有：临时目录+BMP 全量回环+异常路径）

# 6. finish published（W2 结构 + R36 依赖 + W3 conan create 门禁）
python3 scripts/ohc-run.py finish bitmapplusplus 1.1.1 published
```

## 上游测试完整枚举台账（官方 tag v1.1.1 源码，可复制枚举）

统计口径：全目录枚举（examples/ + integration_tests/）；上游无单元测试框架、无
TEST_CASE 宏，样例程序不计独立用例但全部列账并实际构建运行。

| 入口 | 类型 | 是否独立上游用例 | 是否实际运行 | 结果 |
|------|------|------------------|-------------|------|
| examples/bernoulli_dist.cpp | 样例程序（add_test 注册） | 否（样例） | 是 | 通过 |
| examples/chess_board.cpp | 样例程序（add_test 注册） | 否（样例） | 是 | 通过 |
| examples/draw_primitives.cpp | 样例程序（add_test 注册） | 否（样例） | 是 | 通过 |
| examples/julia.cpp | 样例程序（add_test 注册） | 否（样例） | 是 | 通过 |
| examples/mandelbrot.cpp | 样例程序（add_test 注册） | 否（样例） | 是 | 通过 |
| examples/polymorphic_shapes.cpp | 样例程序（add_test 注册） | 否（样例） | 是 | 通过 |
| examples/read_bitmap.cpp | 样例程序（add_test 注册） | 否（样例） | 是 | 通过 |
| examples/rotation.cpp | 样例程序（add_test 注册） | 否（样例） | 是 | 通过 |
| examples/variant_shapes.cpp | 样例程序（add_test 注册） | 否（样例） | 是 | 通过 |
| examples/write_bitmap.cpp | 样例程序（add_test 注册） | 否（样例） | 是 | 通过 |
| integration_tests/cpm/Main.cpp | 集成演示（CPM 拉取，非本库测试） | 否 | 否（依赖网络拉取 master，不纳入本库验证） | 不适用 |
| integration_tests/fetchcontent/Main.cpp | 集成演示（FetchContent，非本库测试） | 否 | 否（同上） | 不适用 |
| integration_tests/cpm/CPM.cmake | 框架脚本（第三方 CPM 分发） | 否（框架文件） | - | - |

双口径统计：
- source_declared_total（官方 tag 可复制枚举测试声明数）：0 个独立 TEST_CASE
  （上游无测试框架；10 个 add_test 注册项均为样例程序，按规则不计独立用例）
- configured_executable_total：10（BPP_BUILD_EXAMPLES=ON 实例化的样例可执行）
- executed_passed_total：10（ctest 10/10 通过，exit 0）
- failed：0；未运行/未实例化：0（样例）；集成演示 2 个按分类不纳入
- 全量通过率（独立用例口径）：0/0（无独立用例）；样例执行通过率：10/10 (100%)
- 消费者验证（硬门禁）：test_package 消费者用例 2 个（test_bitmapplusplus 6 断言 +
  test_bitmapplusplus_ohos 4 断言）真实编译链接运行并通过，均只经公开头文件
  `#include <BitmapPlusPlus.hpp>` 与公开 API（构造/clear/operator[]/save/load/
  迭代器/异常），不触及私有实现。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 github.com 直连超时 | 本机访问 github.com 网页超时，codeload 可达 | 先用官方 codeload archive tarball 预下载核验 sha256，再 init-build 复用 tarball；conandata 保持官方 archive URL，G2 时 E017 自动注入 ghfast 镜像 |
| 2 | conan create: "Package type is 'library', but no 'shared' option declared" | Conan 2 对 package_type=library 要求声明 shared option；header-only 无此概念 | 改用 package_type = "header-library"（与 magic_enum/cppitertools/doctest 同款） |
| 3 | header-only 模板 package() 从源码根复制 *.hpp | 上游把单头文件放在 lib/include/ 子目录 | package() 复制 lib/include/*.hpp → include/，并导出 cmake 目标 bmp::BitmapPlusPlus |
| 4 | 上游测试 API 名为 clear() 而非 fill() | 本库全像素填充 API 语义为 std::fill，方法名 clear() | 消费者测试按真实 API 编写，断言 clear 后像素一致 |

## 源码修改
- 无补丁（patches/ 为空）。仅配方层修正（conanfile.py/conandata.yml/test_package），不改上游源码。

## 依赖版本
- 无外部依赖（header-only，requirements 为空）

## 验证结果

```bash
# 上游样例（ctest，10/10）
Test #1..10: bernoulli_dist/chess_board/draw_primitives/julia/mandelbrot/
             polymorphic_shapes/read_bitmap/rotation/variant_shapes/write_bitmap
100% tests passed, 0 tests failed out of 10

# 消费者（conan create test_package）
./test_bitmapplusplus       → ALL PASS (11 checks)
./test_bitmapplusplus_ohos  → ALL PASS (4 checks)

# 配方门禁
G1/G2/G3/G4 + L2/L4/L5 全通过；W3 .ci-result.json 由 finish 写入
```

## 交付物
- archives/b/bitmapplusplus/1.1.1/{conanfile.py, conandata.yml, manifest.yaml, notes.md}
- archives/b/bitmapplusplus/1.1.1/test_package/{conanfile.py, CMakeLists.txt,
  test_bitmapplusplus.cpp, test_bitmapplusplus_ohos.cpp, MANIFEST.yml}
- 无 CLI（header-only 库，无 commands.json，R38 不适用）

## 注意事项
- 头文件位于 lib/include/ 子目录，消费者 include 路径为 <BitmapPlusPlus.hpp>，
  目标名 bmp::BitmapPlusPlus（上游 CMake ALIAS）。
- 全像素填充 API 名为 clear()（语义 std::fill），非 fill()。

## 知识候选台账（knowledge_candidate_ledger）

### 候选 K1：header-only 模板 package() 复制 *.hpp 从源码根，漏掉 lib/include/ 子目录头文件
- 真实错误：G2 conan create 无报错（头文件缺失直到消费者 include 才暴露），
  header-only 模板 copy(self,"*.hpp",src=source_folder) 对位于非 include/ 子目录
  （lib/include/）的单头文件无效 → include/ 为空。
- 根因：header-only 模板假设头文件在源码根或 include/ 下；本库把 BitmapPlusPlus.hpp
  放在 lib/include/。
- 修复：package() 复制 lib/include/*.hpp → include/，并导出 cmake 目标
  bmp::BitmapPlusPlus。
- 验证：conan create + test_package 消费者（#include <BitmapPlusPlus.hpp> + 公开 API
  断言）真实编译链接运行通过（6+4 断言 ALL PASS）。
- 适用范围：头文件位于非 include/ 子目录（如 lib/include/）的 header-only 库。
- 查重：
  - 正式知识 E321（martinmoene lite header-only 迁移）：同为 header-only +
    package_type=header-library + cmake 目标导出，但 E321 的 lite 库头文件在
    include/nonstd/ 下（模板 copy 能命中 include/ 子树），未覆盖"非 include/ 子目录
    漏复制"；
  - 正式知识 E217（check-cmake-header-install-subdir）：触发同为头文件子目录安装
    导致 include 路径不匹配，但 E217 是 install DESTINATION include/<subdir> +
    includedirs 声明问题，方案是 includedirs 指向子目录；本候选是 header-only 模板
    复制源路径问题，方案是 package() src 指向实际子目录 —— 触发场景不同、方案不同；
  - 草稿 DRAFT-collections-c-2.3.3（静态分支 PUBLIC_HEADER 缺失 → package() 显式
    copy src/include）：方案形态相近（package() 显式复制子目录头文件），但根因
    （CMake 静态分支不安装头文件）与本候选（header-only 模板复制路径）不同，适用
    边界不同（编译型静态库 vs header-only）；
  - 草稿 DRAFT-concurrencpp-0.1.7（install 版本化子目录 + INSTALL_INTERFACE 未导出）：
    同为头文件子目录，但属 install/includedirs 声明侧，非模板复制侧。
- 七轴：
  - exact_duplicate: false
  - causal_duplicate: false（与 E217/concurrencpp 根因不同：模板复制源 vs install 声明）
  - trigger_overlap: partial（都是头文件子目录/消费者 include 失败，触发面不同）
  - solution_overlap: partial（与 collections-c 同有 package() 显式复制，但场景不同）
  - combination_novelty: true（header-only 模板 + 非 include/ 子目录 + 复制路径修复）
  - boundary_novelty: true（明确"header-only 模板对非 include/ 子目录头文件漏复制"边界）
  - test_migration_novelty: false（消费者测试常规编写）
- 关系：similar_to E217/E321、collections-c/concurrencpp 草稿（部分重叠）；无
  caused_by/prerequisite_of/conflicts_with。

### 候选 K2：package_type="library" 但无 shared 选项声明
- 真实错误：conan create "Package type is 'library', but no 'shared' option declared"。
- 根因：header-only 库无 shared 概念，但模板默认 package_type="library"。
- 修复：package_type = "header-library"（与 E321/E322 同款）。
- 验证：G2 conan create PASS。
- 查重：正式知识 E283（declare-shared-contract）命中同类错误签名但方案为声明
  shared 选项（非 header-only 场景）；E321/E322 已覆盖 header-only → header-library。
  → 完整重复（复用 E321/E322 结论），无新增差异，不建新草稿。
- 七轴：exact_duplicate=true（E321/E322 已覆盖）→ reuse_existing。

### 候选 K3：G2 时 GitHub URL 下载超时
- 现象：init-build urllib 直连 github.com 超时；G2 由 conan-verify E017 注入
  ghfast.top 镜像自动成功（恢复后 conandata 保持官方 URL）。
- 根因/修复：已知机制（E017 镜像注入 + 官方 archive tarball），非新知识。
- 查重：正式知识/工具已有覆盖 → 噪声（既有工具行为），不建草稿。

## 路径决定
- K1 为已验证、可跨库复用、查重部分覆盖且存在新增差异（header-only 模板对
  非 include/ 子目录头文件漏复制）→ **路径 B：new_draft**
- K2 完整重复 → reuse_existing（E321/E322）
- K3 既有工具机制 → 不建草稿
- 知识库草稿：knowledge/drafts/DRAFT-bitmapplusplus-1.1.1-header-only-subdir-header-copy.{md,kv}
  （与本库归档同 PR）
---

**编译结束**: 2026-09-25 06:54
**最终状态**: built
