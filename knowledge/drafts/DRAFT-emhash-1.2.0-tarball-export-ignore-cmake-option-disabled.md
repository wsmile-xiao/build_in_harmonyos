# DRAFT-emhash-1.2.0-tarball-export-ignore-cmake-option-disabled

> Draft: DRAFT-emhash-1.2.0-tarball-export-ignore-cmake-option-disabled
> 来源: emhash 1.2.0 适配（R01, executor pc2-31, 2026-09-22）
> 状态: 草稿（待审核 promote）

## 错误特征

```text
CMake Error at CMakeLists.txt:158 (add_subdirectory):
  add_subdirectory given source "docs/examples" which is not an existing directory.
```

## 触发条件

- 构建系统: cmake
- 阶段: configure
- 前提: 官方 release tarball 按 .gitattributes export-ignore 排除了 docs/examples、tests、bench、thirdparty、scripts 等目录，但 CMakeLists 默认 option 为 ON（如 WITH_EXAMPLES=ON）直接 add_subdirectory 引用被排除目录

## 根因分析

GitHub codeload 生成的 release tarball 遵循仓库 .gitattributes 中 `export-ignore` 规则
（已核验 emhash v1.2.0 blob 556018ba…：`tests export-ignore`、`docs export-ignore`、
`bench export-ignore`、`thirdparty export-ignore`、`scripts export-ignore`）。因此
`git archive` 产物不含这些目录，但 CMakeLists.txt 仍完整引用它们；默认 option
（WITH_EXAMPLES=ON）导致 `add_subdirectory(docs/examples)` 直接失败。这与 git tag
完整树（含 tests/、docs/examples/）不一致——上游 tag 源码完整，但 release 分发物被
包装排除。

## 推荐方案

**方法**: tarball-export-ignore-cmake-option-disabled

**说明**: 取官方 codeload tarball 后先核对其顶层目录与 .gitattributes export-ignore
规则（与 git tag 树 API 对照），据此在配方/构建命令中关闭引用被排除目录的 CMake
option（-DWITH_EXAMPLES=OFF -DWITH_TESTS=OFF -DWITH_BENCHMARKS=OFF），再配置构建。
被排除的若是非必需构建单元（样例/测试/基准）可安全关闭；若被排除的是必需依赖
（见 E458 restinio bundled deps），则不能关 option，必须恢复依赖。

**验证/命令**:
```bash
tar tzf <lib>-<ver>.tar.gz | sed 's|^[^/]*/||' | awk -F/ '{print $1}' | sort -u   # 核对排除目录
cmake .. -DWITH_EXAMPLES=OFF -DWITH_TESTS=OFF -DWITH_BENCHMARKS=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build . && cmake --install .
```

## 关键词

export-ignore, .gitattributes, release tarball, codeload, add_subdirectory, WITH_EXAMPLES, header-only, cmake
