# DRAFT-cmake-cpm-addpackage-local-package-offline — CMake 项目经 CPMAddPackage 拉依赖时：用本地包离线满足（无需 patch 上游）

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-12
> **Severity**: 🟡 medium | **Category**: cmake / cpm / conan / offline / test / dependency

## 与既有条目的关系（互补，不重叠）

| 既有条目 | 关系 |
|---------|------|
| **`DRAFT-cmake-test-framework-fetch-to-conan-find-package`** | 讲 **FetchContent** 场景：必须 **patch 上游 CMakeLists** 把 FetchContent 改成 `find_package`，且还需 CMakeDeps 生成 config。查重：该条目 `CPMAddPackage` / `CPM_USE_LOCAL_PACKAGES` 命中 **0** —— 不涉及 CPM 路径。**修法完全不同（patch vs 零 patch）** |
| **`DRAFT-glob-0.0.1-cmake-offline-install`** | 讲 **`CPM.cmake` / `PackageProject.cmake` 助手模块本身**在 configure 期被下载（缺模块）；本条讲的是**依赖包**如何离线命中（`CPM_USE_LOCAL_PACKAGES` 命中 **0**）|
| **E301** | 讲 `CMake.test(cli_args=…)` 是 build 参数而非 ctest 参数。同批适配用到，本条**不重复**其结论，仅一句指路 |

> 查重（2026-09-12）：`CPM_USE_LOCAL_PACKAGES` 全库命中 **0**；`--output-on-failure`、`cmake.test(` 命中 **0**（后者已被 E301 覆盖 → 不重复）。

## Scope（何时用）

禁网 / 受限网络 CI 中，上游 CMake 项目用 **CPM.cmake** 获取依赖，在 **configure 阶段**就失败：

```
CPM: error: Failed to download ...
fatal: unable to access 'https://<host>/...'
```

**尤其**针对「只为跑上游测试」而引入的测试框架依赖（Catch2 / GoogleTest 等）—— 这类依赖通常只出现在 `BUILD_TESTING` 分支内。

## 根因：直觉修法是 patch 上游，但 CPM 本身给了免改上游的开关

直觉上要 **patch 上游 CMakeLists** 把 `CPMAddPackage` 改写成 `find_package` —— 那要维护补丁、还要处理 config 生成（既有 FetchContent 条目的路线）。

**但 CPM 提供了免改上游的开关**。一旦上游在 `CPMAddPackage` **之前**设了：

```cmake
set(CPM_USE_LOCAL_PACKAGES ON)      # 实测 mrc 的 CMakeLists.txt:65
```

CPM 对每个依赖会**先尝试 `find_package(<name>)`**，**命中即不再联网下载**。

### 于是离线满足只需两步，零 patch

1. 把该依赖作为**本地可用包**提供（conan 侧放进依赖图 —— 测试框架建议 `test_requires`）
2. 告诉 CMake 去哪找它的 config —— 设 **`<Pkg>_DIR`** 指向包内**上游自带**的 config 目录

### 实测效果（mrc，禁网环境）

```
-- CPM: Using local package Catch2@3.8.1
```

→ 随后 ctest 正常执行上游 9 个 TEST_CASE，`100% tests passed, 0 tests failed out of 1`。

## ⚠️ 关键陷阱：`<Pkg>_DIR` 的包名是「CMake 包名」，不是 conan 包名

| conan 包名 | CMake 包名 | 差异 |
|-----------|-----------|------|
| `libmcfp` | `mcfp` | 前缀不同 |
| `catch2` | `Catch2` | **大小写不同** |

因此：

- **不要**用 conan 包名去拼目录名（`libmcfp` / `catch2` 都拼不中）
- 应**按 marker 文件定位**：`Catch2Config.cmake`、`mcfpConfig.cmake`
- `find_package(X)` 对 X **大小写敏感** → 必须匹配上游源码里写的名字（**照抄 `CPMAddPackage` 的首参**）

## 方案（三步，全部在配方侧，不动上游源码）

### ① 确认开关（决定性）

```bash
grep -nE 'CPM_USE_LOCAL_PACKAGES' <src>/CMakeLists.txt
```

- **有** → 走本条（零 patch）
- **无** → 才考虑 patch 成 `find_package`（见备选）

### ② 提供本地包 + 设 `<Pkg>_DIR`

```python
# requirements()：门控，仅在开启时注入测试依赖
if self.options.run_upstream_tests:
    self.test_requires("catch2/3.8.1")

# generate()：按 marker 定位上游 config（注意 CMake 名大小写）
for _n, dep in self.dependencies.items():
    pf = dep.package_folder
    for rel in (("lib", "cmake", "Catch2"), ("share", "cmake", "Catch2")):
        cand = os.path.join(pf, *rel)
        if os.path.isfile(os.path.join(cand, "Catch2Config.cmake")):
            tc.variables["Catch2_DIR"] = os.path.abspath(cand)
```

### ③ 验证命中

配置输出应出现 **`CPM: Using local package <名>@<版本>`** —— 这是「没联网」的确证；若仍见 `Downloading` / `fatal` 则未命中。

### 门控建议

把「跑上游测试」做成 option（**默认关**），开启时才加 `test_requires` 与 `<Pkg>_DIR`：

- **交付包依赖不变**（package_id 不受影响、消费者不被拖入测试框架）
- CI / 本地仍能**实跑上游测试套件**（R34 意义上的真验证）

> 附带（同批适配用到，此处不展开）：Conan 2 里 `CMake.test()` 的 `cli_args` 会路由给 `cmake --build`，要传 ctest 选项得用 **`CMake.ctest()`** —— 详见 **E301**。

## 备选（fallback）

若上游**没有**设 `CPM_USE_LOCAL_PACKAGES`（或该版本 CPM 行为不支持），才退回**改上游**路线：用配方 patch 流水线把 `CPMAddPackage(...)` 替换为 `find_package(<Pkg> REQUIRED)`，并确保 config 可被找到。

代价：多一份需随上游版本维护的补丁 —— 故**先查开关**再决定。

## 禁止

- ❌ **不先查 `CPM_USE_LOCAL_PACKAGES` 就 patch 上游** —— 上游可能已设该开关，此时**零 patch**即可离线满足 → 平白多维护一份补丁（还要随上游版本更新），且 patch 失败风险自找
- ❌ **用 conan 包名拼 `<Pkg>_DIR`** —— `<Pkg>` 是 **CMake 包名**，与 conan 包名常不同（`libmcfp`↔`mcfp`、`catch2`↔`Catch2`），拼出来命不中 → 配置阶段仍去联网，且**报错指向网络而掩盖真实原因（名字不对）**
- ❌ **测试依赖走 `self.requires`** —— 应走 `test_requires`（并建议门控 option），否则交付包带上仅测试才需要的依赖 → package_id 变化、消费者被迫拉入测试框架

## 实证

- **mrc/1.3.17（PR #9566）**：上游 `CMakeLists.txt:65` 设 `set(CPM_USE_LOCAL_PACKAGES ON)`，并在 `BUILD_TESTING` 分支里 `CPMAddPackage("gh:catchorg/Catch2@3.5.0")`（CI 禁网）
  - 实测：**不 patch 上游**，仅加门控 option + `test_requires("catch2/3.8.1")` + 把 `Catch2_DIR` 指向包内 `lib/cmake/Catch2`
  - configure 输出 **`-- CPM: Using local package Catch2@3.8.1`**
  - 上游 **9/9 TEST_CASE 全通过（32 assertions）**，ctest `100% tests passed, 0 tests failed out of 1`
  - 同批另有 mcfp 依赖走同一机制（conan 名 `libmcfp` vs CMake 名 `mcfp`）
