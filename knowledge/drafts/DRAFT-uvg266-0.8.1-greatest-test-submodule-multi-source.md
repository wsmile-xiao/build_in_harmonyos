# DRAFT: 测试框架子模块不在 release tarball — conan 配方多 source 直下子目录

> 来源: uvg266 0.8.1 HarmonyOS 适配（VVC 编码器，C 语言，CMake 构建）
> 状态: 草稿 (draft) — 与 DRAFT-uvg266-0.8.1-greatest-test-submodule-multi-source.kv 配对

## 问题

uvg266 官方 GitHub release tarball 中 `greatest/` 目录为空：`greatest` 是 git
子模块（`.gitmodules` → `https://github.com/ultravideo/greatest.git`），tar
归档只落地目录骨架，不含内容。而 `tests/*.c` 全部 `#include "greatest/greatest.h"`，
上游 CMakeLists 以 `if(EXISTS "${PROJECT_SOURCE_DIR}/greatest/greatest.h" AND
BUILD_TESTS)` 决定是否 `add_subdirectory(tests/)` —— 子模块缺失时测试被静默
跳过，`uvg266_tests` 无法编译。

## 根因

- GitHub release tarball 不随带 submodule 内容（gitlink 不进入 tar）；
- 测试框架被直接 `#include`（无 `find_package(QUIET)` 回退路径）；
- ohpcd 制品仓无 greatest 包装可 `test_requires` 替代；
- 空目录保留（E425 占位方案）无法让测试编译。

## 方案

配方 `conandata.yml` 增加 `greatest:` 第二 source（官方子模块 URL + 上游
v0.8.1 钉扎提交 `60e25ce7658ced49f03b52ac14c553cf6ea33de4` + SHA-256
`3914a24a613e2eefae0076d059d963ccfeea661ce9f249770ca61a78d4d326d7`），
`source()` 中直接 `get(..., destination=greatest/)`：

```python
def source(self):
    get(self, **self.conan_data["sources"], strip_root=True)   # uvg266 本体
    get(self, **self.conan_data["greatest"], strip_root=True,   # 测试框架
        destination=os.path.join(self.source_folder, "greatest"))
```

结果：上游 `uvg266_tests`（39 个 greatest TEST）在 W3 `conan create` 中真实
编译并全部通过（`Test_uvg266` Passed 0.03s）；不污染 PR diff；不依赖网络 git
操作（CI 干净环境可复现）；钉扎提交 + SHA-256 双重固定可审计。

## 边界（何时不该用本方案）

- 上游用 `find_package(<FW> QUIET)` + 未命中回退 `add_subdirectory(third_party)`，
  且制品仓有该框架 conan 包装 → 用 **test_requires + CMakeDeps** 让 find_package
  命中（DRAFT-kangaru-4.3.2-catch2-submodule-test-requires）。
- 子模块仅作构建辅助（.cmake 工具），本体不编译测试 → **export_sources 打包恢复**
  （DRAFT-rapidyaml-0.7.2-c4core-cmake-submodule-vendoring）。
- 该 submodule 功能不属于当前包交付范围 → E425 空占位即可。
- 本方案适用于：测试框架被直接 include、无 find_package 回退、制品仓无替代包。

## 验证证据

- `conan create` W3 日志：`Test_uvg266 ...................... Passed 0.03 sec`、
  `test_external_symbols ........... Passed 0.08 sec`、`100% tests passed (2/2)`。
- 双口径：source_declared_total=40；configured_executable_total=39；
  executed_passed_total=39。（1 个 inter_recon_bipred 用例被上游
  tests/CMakeLists 显式 REMOVE_ITEM 排除，非本方案影响。）

## 关系

- similar_to: E150（release tarball 缺 submodule manual-download）、
  DRAFT-kangaru-4.3.2-catch2-submodule-test-requires、
  DRAFT-rapidyaml-0.7.2-c4core-cmake-submodule-vendoring
- caused_by: [] / prerequisite_of: [] / conflicts_with: []

## 适用反例

- 制品仓已有等价测试框架 conan 包且上游有 find_package 回退 → 应走 kangaru 方案；
- 测试框架内容 ≥50MB 或嵌套子模块 → 优先拆独立库发布（E425 依赖拆分思路）。