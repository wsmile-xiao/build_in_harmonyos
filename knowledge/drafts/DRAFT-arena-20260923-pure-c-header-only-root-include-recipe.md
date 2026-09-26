# DRAFT-arena-20260923-pure-c-header-only-root-include-recipe：无 include/ 子目录的纯 C 单头文件库配方（copy 到包根 + includedirs=["."]）

> Contributor: pc2-47 | Status: Draft | Updated: 2026-09-24
> Source: arena 20260923 适配（feat/arena-20260923，tsoding/arena）
> 对应：`knowledge/drafts/DRAFT-arena-20260923-pure-c-header-only-root-include-recipe.kv`

## 问题现象

tsoding/arena 是 stb 风格单头文件 C 库（arena.h，消费者 `#define ARENA_IMPLEMENTATION`
后 include 即得实现），上游**没有任何构建系统**，且**头文件位于源码根目录、没有
include/ 子目录**。conan-init 按 autotools 模板生成配方后：

1. `conan create` 直接失败（autotools 模板假设有 configure/make）；
2. 改写为 header-only 配方时若照抄既有 header-only 条目（E257/E470/E322）的
   `copy(dst="include") + includedirs=["include"]` 形态，`package()` 把 arena.h 拷进
   build 目录而非包内 include/，test_package 配置期报：

```text
CMake Error in CMakeLists.txt:
  Imported target "arena::arena" includes non-existent path
    ".../.conan2/p/b/arenae702a57616487/p/include"   ← 包内没有 include/
  in its INTERFACE_INCLUDE_DIRECTORIES.
```

## 根因分析

1. **形态误判链**：init-build 的 autotools 模板（G1 又要求 build()/export_sources()/
   apply_conandata_patches 三方法显式声明，即使 0 补丁）与"头文件在源码根、无 include/
   子目录"的库不匹配。
2. **copy() 目标语义**：Conan 2 `copy()` 的 `dst` 相对路径按 build 目录解析；
   且对"头文件在源码根、无 include/ 子目录"的库，照抄
   `copy(dst="include")`（隐含 include/ 子目录）+ `includedirs=["include"]` 会造成
   包内路径空洞（package 无 include/），CMakeDeps 的 INTERFACE_INCLUDE_DIRECTORIES
   指向不存在的包路径。
3. **正确形态**：源码根目录即公开头文件根 → 直接
   `copy(src=source_folder, dst=package_folder)` 把头文件落到**包根**，
   `cpp_info.includedirs = ["."]`（无需制造 include/ 子目录）。

## 方案

```python
# conanfile.py（header-only，无 include/ 子目录、头文件在源码根）
class ArenaConan(ConanFile):
    name = "arena"
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)          # G1 要求

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)           # G1 要求

    def build(self):
        pass                                     # header-only，无伪造编译日志（R34）

    def package(self):
        copy(self, "arena.h", src=self.source_folder, dst=self.package_folder)
        copy(self, "LICENSE*", src=self.source_folder, dst=self.package_folder,
             keep_path=False)

    def package_id(self):
        self.info.clear()                        # header-only → 单一 package_id

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["."]        # 头文件在包根
```

test_package 消费者按 stb 风格真实调用：
```c
#define ARENA_IMPLEMENTATION
#include "arena.h"      /* 包根 include 路径即可 */
```

## 验证（arena 20260923 本轮真实日志）

1. conan-verify G1-G4 + L2/L4/L5 全部 PASS（conan create 干净构建通过）；
2. test_ohos 鸿蒙专项（T1-T7，12 项语义断言，跨 Region/snapshot-rewind/压力循环）ALL PASS；
3. test_package 消费者（arena_alloc/arena_sprintf/arena_reset/arena_free）G2 通过。

## 适用范围与边界

- 所有"头文件在源码根、无 include/ 子目录"的纯 C 单头文件库（stb 风格，ARENA_IMPLEMENTATION
  消费者模式；同类：sv/sb 等 tsoding 单头库、纯 C 单文件库）。
- 边界：有 include/ 子目录的库仍走 E470/E321/E322 的 include/ 形态；有真实 .a 产物的
  stb 风格实现库走 DRAFT-enet（勿误用 header-only）；无构建系统但有 .c 源文件的库走
  DRAFT-cobs-c 自定义编译。

## 查重（七轴）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false |
| causal_duplicate | false（E257 只覆盖 G1 build() 声明；DRAFT-cobs-c 覆盖无构建系统但有 .c 的库；DRAFT-boost-te 覆盖 copy 相对/绝对路径；均未覆盖"无 include/ 子目录 → 包根 + includedirs=['.']"形态） |
| trigger_overlap | true（G1 三方法声明与 E257 同源） |
| solution_overlap | partial（includedirs=['.'] 包根形态为新增） |
| combination_novelty | true（header-only + 无 include/ 子目录 + 包根 includedirs 组合） |
| boundary_novelty | true（明确"头文件在源码根"边界，区别于 include/ 形态） |
| test_migration_novelty | true（ARENA_IMPLEMENTATION 消费者测试模式迁移） |

> 依据: knowledge/doc/E257.md、E470.md、E321.md、E322.md、E311.md；knowledge/drafts/
> DRAFT-cobs-c-0.4、DRAFT-boost-te-1.0.0、DRAFT-enet-2.7.0、DRAFT-fastnoiselite-1.1.1
> （W3 基线垃圾单包口径已在既有草稿覆盖，本库复用不再新建）。
