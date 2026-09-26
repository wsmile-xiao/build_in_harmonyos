# DRAFT-bitmapplusplus-1.1.1-header-only-subdir-header-copy

> Contributor: pc1-38 | Status: Draft | Updated: 2026-09-25
> Source: bitmapplusplus 1.1.1 HarmonyOS PC 适配（R01，conan-verify G2 后消费者验证）
> 领域：Conan 配方（header-only 模板复制路径）

## 背景

BitmapPlusPlus 1.1.1 是单文件 header-only C++17 库，但上游把头文件放在
`lib/include/BitmapPlusPlus.hpp`（**非** `include/`、非源码根）。用
`conanfile-headeronly.py.tmpl` 生成配方后，`package()` 执行
`copy(self, "*.hpp", src=self.source_folder, dst=include/)` 对位于
`lib/include/` 子目录的头文件**完全不生效** → 包内 `include/` 为空。
`conan create` 本身不报错（header-only 无编译），缺陷直到消费者
`#include <BitmapPlusPlus.hpp>` 时以 "file not found" 暴露。

## 错误签名

```text
（G2 conan create 静默通过）
test_package: fatal error: 'BitmapPlusPlus.hpp' file not found
include/ 目录存在但为空（无任何 .hpp）
```

## 根因

header-only 模板的 `package()` 假设头文件位于源码根或 `include/` 子树；
对头文件位于非 `include/` 子目录（`lib/include/`、`src/include/` 等）的库，
`copy("*.hpp", src=source_folder)` 无法命中深层头文件。E321（martinmoene lite）
头文件在 `include/nonstd/` 下可被模板命中，未覆盖此场景；E217（install
DESTINATION include/<subdir>）与 DRAFT-concurrencpp 属 install/includedirs 声明侧，
方案为 `includedirs` 指向子目录；DRAFT-collections-c 属 CMake 静态分支
PUBLIC_HEADER 缺失，方案虽同为 package() 显式复制但边界是编译型静态库。

## 修复

```python
def package(self):
    copy(self, "*.hpp",
         src=os.path.join(self.source_folder, "lib", "include"),  # 实际子目录
         dst=os.path.join(self.package_folder, "include"))
    copy(self, "LICENSE*", src=self.source_folder,
         dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
```

## 验证

- conan-verify G1–G4 + L2/L4/L5 全通过；G2 conan create 内 test_package
  消费者真实编译链接运行：`test_bitmapplusplus`（6 组断言）+
  `test_bitmapplusplus_ohos`（4 组断言）ALL PASS；
- 消费者仅经公开头 `#include <BitmapPlusPlus.hpp>` 与公开 API
  （构造/clear/operator[]/save/load/迭代器/异常），不触私有实现。

## 适用边界

- header-only 库且头文件位于**非 include/ 子目录**（如 lib/include/）；
- 不适用：头文件在源码根或 include/ 下（模板默认命中）、编译型库的
  install/includedirs 声明问题（走 E217/E321/collections-c 路径）。

## 查重差异（七轴）

| 轴 | 结论 |
|----|------|
| exact_duplicate | false（无同库同场景条目） |
| causal_duplicate | false（模板复制源 vs install 声明/静态分支属性，根因不同） |
| trigger_overlap | partial（均为头文件子目录 → 消费者 include 失败） |
| solution_overlap | partial（与 collections-c 同有 package() 显式复制，边界不同） |
| combination_novelty | true（header-only 模板 + 非 include/ 子目录 + 复制路径修复） |
| boundary_novelty | true（明确"模板对非 include/ 子目录头文件漏复制"边界） |
| test_migration_novelty | false |

similar_to: E217, E321, DRAFT-collections-c-2.3.3, DRAFT-concurrencpp-0.1.7
