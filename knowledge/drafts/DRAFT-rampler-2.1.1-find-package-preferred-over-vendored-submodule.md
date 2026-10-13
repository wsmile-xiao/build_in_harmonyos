# DRAFT-rampler-2.1.1 — CMake find_package(QUIET) 优先结构下，已发布 conan 依赖可令空 vendored 子模块不被触碰

> 配套 `.kv`：`DRAFT-rampler-2.1.1-find-package-preferred-over-vendored-submodule.kv`（同 stem 成对，随本 PR 原子提交）。
> 触发实例：rampler 2.1.1 适配（本 PR），2026-09-30，OHOS aarch64 真机（HarmonyOS PC + conan 2.29.1）。

## 可复现症状（M2 场景）

rampler 2.1.1 的 tag 归档（codeload）带 `.gitmodules` 但 `vendor/bioparser/` 为空
（子模块内容不随归档分发）。上游 CMakeLists 结构：

```cmake
find_package(bioparser 3.0.15 QUIET)
if (NOT bioparser_FOUND)
  FetchContent_Declare(bioparser
    GIT_REPOSITORY https://github.com/rvaser/bioparser
    GIT_TAG 3.0.15)
  FetchContent_Populate(bioparser)
  add_subdirectory(...)
endif ()
# biosoup 0.10.0 同构
```

若不做处理，configure 会进入 FetchContent 分支尝试 git clone GitHub（OHOS 设备/CI
网络不可达 ⇒ 挂起或失败）；归档内 `vendor/bioparser/` 自身无 CMakeLists 亦不可编译。

## 根因与判别

M2（submodule 分发形态）在本包的**变体**：release 无 2.1.1 源码资产（仅 2.0.0/1.1.1
的打包资产），M2"改用 make-dist 资产"的正解不适用。但上游把依赖解析写成
**find_package(QUIET) 优先、FetchContent 兜底**——这给了一条不改归档的路：只要
find_package 命中，兜底分支永远不会执行。

领坑时 30 秒判别三步：

```sh
tar tz <tag归档> | grep -c 'vendor/<sub>/.*\.'        # =0 ⇒ 子模块空（M2 场景）
grep -A2 'find_package(<sub>' CMakeLists.txt           # find_package 在前 ⇒ 本条适用
conan download <sub>/<ver> --only-recipe -r=ohpcd      # 200 ⇒ 依赖已发布 ⇒ 三绿
```

## 已尝试方案（含失败）

| 尝试 | 结果 |
|---|---|
| 按 M2 找 2.1.1 的 release 源码资产 | 无——release 仅 2.0.0/1.1.1 资产且为打包形态 ⇒ M2 正解不适用 |
| 走 E150 手工拷子模块源入树 | 可行但要多下一个源码包并改归档内容；发现上游结构后弃用（本条更优） |
| **声明已发布依赖 + CMakeDeps** | **✅ find_package 命中，FetchContent 分支零执行，零补丁** |

## 最终方案与真实验证

```python
def requirements(self):
    self.requires("bioparser/3.0.15")   # ohpcd 远端已发布
    self.requires("biosoup/0.10.0")     # 同上

def generate(self):
    tc = CMakeToolchain(self); tc.generate()
    deps = CMakeDeps(self); deps.generate()
```

验证读数：conan create 成功（configure 日志无任何 FetchContent 痕迹）；
`conan-verify rampler 2.1.1` **G0-G4 全 PASS**；test_package 三条确定性断言通过
（`--version`→`2.1.1`；`-o .`→`missing arguments`；无参数→usage 路径）。

## 适用范围 / 反例 / 解除条件

- **适用**：CMake 上游对 vendored 子模块采用"find_package(QUIET) 在前、FetchContent 兜底"
  结构，且对应 conan 包已发布（或可按拓扑序先发布）。
- **反例**：上游无条件 FetchContent（无 find_package 分支）⇒ 走 E150；依赖未发布 ⇒
  先按拓扑序适配依赖本身；conan 依赖版本低于 find_package 要求的最低版本 ⇒ QUIET 失败
  仍落 FetchContent，须升版本。
- **解除条件**：无——结构是上游源码属性；若上游改为无条件 FetchContent 本条失效。

## 查重与新增价值

- **E150**（拷子模块源入树）：同族**不同解法**——本条不改归档、零补丁、利用上游探测结构；
  并给出两者之间的**选择判据**（find_package 是否在前）。
- **M2 草稿**（prefer-make-dist-asset-over-tag-archive）：前提是 release 有源码资产；
  本条覆盖"release 无源码资产"的 M2 变体，两草稿互补而非重复。
- **新增价值**：把 M2 家族的处置从"只有拷入一条路"扩展为"先看上游探测结构"；
  给出三步判别 + 与 E150/M2 的明确分流。
