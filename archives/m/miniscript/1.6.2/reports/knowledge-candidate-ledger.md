# 知识候选台账 — miniscript 1.6.2（R01，pc4-38）

## 候选枚举（非噪声候选逐项记录）

### 候选 A：OHOS/arm64 默认 unsigned char 破坏上游 signed-char 语义断言

- **真实错误**：`miniscript` CLI 启动时 `main()` 无条件执行 `UnitTest::RunAllTests()`，
  `TestString` 的 `Assert(s.atB(0) == -26)`（UTF-8 字节 API，0xE6 期望按 signed char
  解释为 -26）在 OHOS/arm64 默认 unsigned char 下向 stderr 打印 `Assert failed`。
- **根因**：C/C++ 将 plain char 符号性定义为实现相关；OHOS/arm64（clang 15）默认
  unsigned，上游在 x86 Linux（signed）开发。存储字节不变，但整数提升使 230 而非 -26。
- **修复**：配方 `generate()` 注入 `-fsigned-char`（C/CXX），与 x86 Linux 语义对齐。
- **验证**：重建后断言消失、ctest 2/2（11/11 全量口径）通过、CLI 启动无噪音。
- **适用范围**：任何用 plain char 承载 signed 8-bit 值、且上游测试在 signed-char
  宿主上开发的 C/C++ 库，OHOS/arm64 交叉编译场景。
- **四范围查重**：
  - 正式知识（E*.kv）：**命中 E419**（librasterlite2，同为 -fsigned-char +
    plain char 符号性，error_signature/rec_command 与本候选一致）。
  - 图谱（doc/）：doc/E2158.md 覆盖。
  - 草稿（drafts/）：无独立新草稿需要。
  - 结论：`exact_duplicate` → 复用 E419，不建新草稿。

### 候选 B：上游 CMake 仅 install(TARGETS) 未安装头文件，配方 package() 需补装

- **真实错误**：`conan create` test_package 阶段 configure 失败（G2）：
  `Imported target "miniscript::miniscript" includes non-existent path
  .../p/include`（CMakeDeps INTERFACE_INCLUDE_DIRECTORIES 指向不存在的 include）。
- **根因**：上游 CMakeLists 只有 `install(TARGETS miniscript-cpp minicmd)`，无
  `install(DIRECTORY ...)`；Conan package() 产物缺 include/。
- **修复**：conanfile.py `package()` 在 `cmake.install()` 后用
  `copy(self, "*.h", src=<source_folder>/MiniScript-cpp/src/MiniScript,
  dst=<package_folder>/include/MiniScript)` 补装公开头文件，保持上游目录结构；
  并修正 `cpp_info.libs=["miniscript-cpp"]` 与上游 target 名一致。
- **验证**：G2 PASS，G0-G4 全 PASS；test_package 消费者通过公开 Interpreter API
  运行脚本并校验输出与全局变量；W3 本地 CI 通过。
- **适用范围**：上游 CMake 仅 install(TARGETS) 未安装头文件的 C/C++ 库，
  OHOS aarch64 + Conan 2 CMakeDeps 下 conan create 必现。
- **四范围查重**：
  - 正式知识：E322（header-only INTERFACE 配方）、E498（headerless 清 include）、
    E216/E447（CMakeDeps 组件/Find 模块传播）均不覆盖"上游根本没安装头文件"这一签名。
  - 图谱：未命中。
  - 草稿：无同签名草稿（DRAFT-EA-headeronly 是依赖链 include 传播，非本模式）。
  - 结论：**未命中/部分覆盖且存在新增差异** → 路径 B（知识库扩展），
    `new_draft`（同 stem 的 .kv/.md 已建：knowledge/drafts/miniscript-1.6.2-cmake-install-targets-missing-headers.{kv,md}）。

## 七轴查重汇总

| 轴 | 候选 A | 候选 B |
|---|---|---|
| exact_duplicate | 是（E419） | 否 |
| causal_duplicate | 是（同根因） | 否 |
| trigger_overlap | 是（同为测试/运行期符号性） | 部分（同为 CMake 打包域，但签名不同） |
| solution_overlap | 是（同为 -fsigned-char） | 否（package() copy 补装，E322/E498 无此方案） |
| combination_novelty | 否 | 是（install(TARGETS) 缺头文件 + package() 补装组合） |
| boundary_novelty | 否 | 是（适用于"上游未安装头文件"边界，与 E322/E498 互补） |
| test_migration_novelty | 否 | 是（以 test_package 消费者 API 校验验证补装正确性） |

## 关系字段

- 候选 A：`similar_to=[E419]`、`caused_by=[]`、`prerequisite_of=[]`、`conflicts_with=[]`
- 候选 B：`similar_to=[E322,E498]`、`caused_by=[]`、`prerequisite_of=[]`、`conflicts_with=[]`

## 路径决定

- 候选 A：复用 E419（`reuse_existing`），不产生新草稿。
- 候选 B：`new_draft`（知识库扩展路径 B），草稿与归档同 PR 交付。
- 最终：**路径 B（知识库扩展）**，PR 前缀 `【知识库扩展】`。
