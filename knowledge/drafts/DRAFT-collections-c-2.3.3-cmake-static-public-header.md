# DRAFT-collections-c-2.3.3-cmake-static-public-header

> Contributor: pc4-6 | Status: Draft | Updated: 2026-09-06
> Source: collections-c 2.3.3 HarmonyOS PC 适配（R01，conan-verify G2 失败链）
> 领域：CMake + Conan 配方（静态分支头文件安装）

## 背景

collections-c 2.3.3 是纯 C 数据结构库（CMake 构建，`project(collectc)`），
默认静态编译。Conan 适配后 `conan create` 在 **test_package 阶段**失败：
CMake 报 Imported target `collections-c::collectc` includes non-existent path
`<pkg>/include/collectc`。包目录实测只有 lib/ 与 licenses/，**没有任何头文件**。

## 错误签名

```text
CMake Error in CMakeLists.txt:
  Imported target "collections-c::collectc" includes non-existent path
    ".../p/include/collectc" in its INTERFACE_INCLUDE_DIRECTORIES.
ERROR: collections-c/2.3.3@ohpcd/stable (test package): Error in build() method
```

## 根因

上游 `src/CMakeLists.txt` 双分支只在一侧设置 PUBLIC_HEADER：

```cmake
if(SHARED)
    add_library(collectc SHARED ...)
    set_target_properties(collectc PROPERTIES PUBLIC_HEADER "${header_files}")
else()
    add_library(collectc STATIC ...)          # ← 无 PUBLIC_HEADER
    set_target_properties(collectc PROPERTIES OUTPUT_NAME collectc)
endif()
install(TARGETS collectc ... PUBLIC_HEADER DESTINATION include/collectc)
```

静态分支未设置 `PUBLIC_HEADER` → `install(TARGETS ... PUBLIC_HEADER ...)` 为空，
`cmake.install()` 不安装头文件。配方 `cpp_info.includedirs=["include/collectc"]`
指向的路径在包内不存在，test_package find_package 的导入目标 include 路径悬空。

## 修复

`conanfile.py package()` 在 `cmake.install()` 后显式拷贝头文件：

```python
from conan.tools.files import copy
copy(self, "*.h", src=os.path.join(self.source_folder, "src", "include"),
     dst=os.path.join(self.package_folder, "include", "collectc"))
copy(self, "memory/*.h", src=..., dst=.../"include/collectc/memory")
copy(self, "sized/*.h",  src=..., dst=.../"include/collectc/sized")
```

## 验证

- conan-verify G1–G4 全通过（G2 conan create 含 test_package 编译运行）；
- test_package 冒烟 `size=3 elem=2`、鸿蒙专项测试皆通过。

## 适用边界

- 上游 CMake 静态/共享分支 install 行为不对称（PUBLIC_HEADER 只在一侧）的库；
- 头文件位于源码子目录（如 src/include/）且安装目标为 include/<lib>/ 的情况。

## 查重差异

- 与 **DRAFT-concurrencpp-0.1.7-cmake-header-install-subdir** 触发场景同为
  test_package 头文件解析失败，但根因不同：concurrencpp 是头文件安装到版本化子目录
  （include/concurrencpp-0.1.7/）+ INSTALL_INTERFACE 未导出 → `includedirs` 声明
  与实际子目录不匹配；本条目是**静态分支压根不安装头文件**（PUBLIC_HEADER 属性缺失）
  → 需在 `package()` 显式拷贝。方案也不同（includedirs 声明 vs 拷贝头文件），
  属部分重叠、存在新增差异（静态分支属性缺失模式）。
- 与 E035（header-only 复制）场景不同：本库需编译，仅修安装缺失。