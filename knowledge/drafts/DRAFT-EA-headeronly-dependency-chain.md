# EA Header-only 依赖链的 Conan 干净构建适配（草案）

> 草稿编号：DRAFT-EA-headeronly-dependency-chain
> 来源：eaassert 0.0.0-e5e1812 适配（EAAssert, electronicarts/EAAssert @ e5e181255de2e883dd1f987c78ccc42ac81d3bca）
> 生成日期：2026-09-15

## 问题描述

EA 开源 C/C++ 库族（EABase / EAAssert / EASTL / EAStdC / EATest / EAThread / EAMain）的公开头文件相互 include 构成依赖链（如 `eaassert.h` 内 `#include "EABase/eabase.h"`）。在 Conan 2 干净构建（os=OHOS, aarch64）下，出现两类编译/配置失败：

1. **依赖 include 目录不传播**：
   ```
   eaassert.cpp:5: fatal error: 'EABase/eabase.h' file not found
   test.cpp:12:  fatal error: 'EABase/eabase.h' file not found
   ```
   上游 CMakeLists 用**裸链接目标名** `target_link_libraries(EAAssert EABase)` 假设 EABase 以 `add_subdirectory` 内嵌在源码树（git 子模块）；干净 Conan 构建无该目标，eabase 依赖的 include 路径进不了编译行。且 header-only 依赖（eabase）经 CMakeDeps 生成 data cmake 时 `INCLUDE_DIRS` 为空，`self.cpp_info.requires` 单独不足以把头文件路径传给消费者。

2. **子模块内 cmake 模块缺失**：
   ```
   CMake Error at CMakeLists.txt:16 (include): include could not find requested file: CommonCppFlags
   ```
   上游 `CMAKE_MODULE_PATH` 指向 `test/packages/EASTL/scripts/CMake`（git 子模块），GitHub archive tarball 不含子模块内容，`include(CommonCppFlags)`（仅设编译器标准标志）失败。

## 根因

- EA 库族公开头文件互相 include，构成 **header-only 公共依赖链**，消费者必须同时拿到本包与依赖包两套 include 目录。
- 上游 CMake 面向"子模块全量源码树"开发（`add_subdirectory` + 裸目标名 + 子模块内 .cmake），与 Conan 干净制品树（`find_package` + 命名空间目标 + 仅本包源码）结构不兼容。
- Conan 2 CMakeDeps 对 header-only 依赖（`package_info` 清空 bindirs/libdirs 但头文件在 include/）生成的 `INCLUDE_DIRS` 可能为空，requires 传递链不补 include 路径。

## 解决方案

三层组合（配方层根治，非消费者侧兜底）：

### 1) 上游裸目标桥接（补丁）

```cmake
# 替换: target_link_libraries(EAAssert EABase)
find_package(eabase REQUIRED)
target_link_libraries(EAAssert eabase::eabase)
```

### 2) 配方 package_info 显式传播依赖 include

```python
generators = "CMakeDeps"
requires = "eabase/0699a15"

def package_info(self):
    self.cpp_info.requires = ["eabase::eabase"]   # 公共头文件依赖声明
    if "eabase" in self.dependencies:             # 兜底：显式追加依赖 include 绝对路径
        for rel in self.dependencies["eabase"].cpp_info.includedirs:
            abs_dir = os.path.join(self.dependencies["eabase"].package_folder, rel)
            if abs_dir not in self.cpp_info.includedirs:
                self.cpp_info.includedirs.append(abs_dir)
    self.cpp_info.libs = ["EAAssert"]
```

关键点：CMakeDeps 对 header-only 依赖生成 `eabase_INCLUDE_DIRS_RELEASE` 为空时，仅 `cpp_info.requires` 不被 CMakeDeps 解析为 include 目录；用 `self.dependencies[...].cpp_info.includedirs + package_folder` 显式追加**绝对路径**到本包 includedirs，保证消费者只链接 `eaassert::eaassert` 也能 resolve `<EABase/eabase.h>`。

### 3) 子模块 cmake 模块守卫（补丁）

```cmake
set (CMAKE_MODULE_PATH "${CMAKE_MODULE_PATH};${CMAKE_CURRENT_SOURCE_DIR}/test/packages/EASTL/scripts/CMake")
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/test/packages/EASTL/scripts/CMake/CommonCppFlags.cmake")
    include(CommonCppFlags)
endif()
```

## 验证

- `conan-verify` G2 = conan create（干净构建，OHOS profile, clang 15, CMake 4.1.2）：
  - 库本体 libEAAssert.a 编译链接通过；
  - test_package 消费者仅 `find_package(eaassert)` + 链接 `eaassert::eaassert` 即编译、链接、运行成功，12 项断言语义断言（失败回调逐字段、带消息/格式化断言、EA_FAIL、表达式副作用按 EA_ASSERT_ENABLED 求值、EA_PANIC 真值、编译期断言）errors=0。
- 上游测试 EAAssertTest（含 EAThread/EAMain/EATest/EASTL 子模块恢复后全量构建）运行 RETURNCODE=0。
- 补丁序列：0001/0002 CMake 最小版本 3.5；0003/0004 CommonCppFlags include 守卫；0005 find_package(eabase)+eabase::eabase。

## 适用范围与边界

- **适用**：EA 系列库族（EABase→EAAssert，以及未来 eastl/EAStdC/EATest/EAThread/EAMain 依赖链）；任何公开头文件 include header-only 依赖头文件的库（cmake+conan 打包）。
- **边界/反例**：依赖包本身非 header-only（有编译产物且 CMakeDeps 正常生成 INCLUDE_DIRS）时，`cpp_info.requires` 已足够，显式追加 includedirs 属冗余但无害；系统同名库仍需 R26 静态隔离，与本模式正交。
- **前置**：依赖库必须先发布到制品仓（R36/W0），否则 find_package 解析失败属依赖缺失而非本模式覆盖范围。

## 关系

- **similar_to**：E216（CMakeDeps INTERFACE_INCLUDE_DIRECTORIES 不传播，消费者侧 glob 兜底）、E322（header-only CMakeDeps 配方）、E150（子模块缺失 manual-download）、E221（CMakeDeps 目标建模）
- **caused_by**：无上游缺陷（工具链/打包结构差异）
- **prerequisite_of**：EA 系列后续库（eastl/eamain/EAStdC/EATest/EAThread）适配
- **conflicts_with**：无