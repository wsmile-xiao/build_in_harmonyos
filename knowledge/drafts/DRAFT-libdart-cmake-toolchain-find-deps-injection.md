# DRAFT-libdart: CMakeToolchain 依赖/include 双路注入（find_* 探测 + -I 编译）

> 草稿（B 类知识库贡献候选）。关联任务：libdart 1.4.0（task_id libdart-1.4.0-r01-pc1-6-20260926T212202Z）。
> 关联正式条目：E293（AutotoolsToolchain 标志注入，不同工具链）、E376（find_library NOTFOUND）、E447（vendored Find 模块）。

## 错误现场

libdart 1.4.0（header-only C++14 JSON 库，上游 CMake 用
`find_path(libgsl gsl/gsl)`、`find_library(libyaml yaml)` 探测依赖）在
OHOS aarch64 + Conan 2.29.1 交叉工具链下依次出现：

**错误 1**（conan-verify G2，conan create）：
```
ERROR: libdart/1.4.0@ohpcd/stable: Error in generate() method, line 87
	tc.cxxflags.extend("-I" + d for d in inc_dirs)
	AttributeError: 'CMakeToolchain' object has no attribute 'cxxflags'
```

**错误 2**（仅注入 -I 编译标志时）：
```
CMake Error at CMakeLists.txt:31 (message):
  Microsoft GSL, or gsl-lite must be installed.
```
（find_path(libgsl gsl/gsl) 找不到 → FATAL_ERROR）

**错误 3**（仅注入 CMAKE_INCLUDE_PATH、缺 -I 时）：
```
include/dart/common.h:35:10: fatal error: 'yaml.h' file not found
```
且 yaml_test 目标未注册（ctest -N 只有 3 项）。

## 根因

1. **Conan 2 的 CMakeToolchain 没有 cxxflags/cflags 属性**。E293 中的
   `tc.extra_cxxflags.append(...)` 是 AutotoolsToolchain 场景，不适用于
   CMakeToolchain；对 CMakeToolchain 直接写 `tc.cxxflags` 抛 AttributeError。
   编译器标志必须写入 `tc.variables["CMAKE_CXX_FLAGS"]` /
   `tc.variables["CMAKE_C_FLAGS"]`（CMakeToolchain 会渲染进
   conan_toolchain.cmake 的 `set(CMAKE_CXX_FLAGS ...)`）。
2. **find_path/find_library 探测与编译 -I 是两套机制**：
   - `find_path(libgsl gsl/gsl)` / `find_library(libyaml yaml)` 只搜索
     CMAKE_PREFIX_PATH / CMAKE_INCLUDE_PATH / CMAKE_LIBRARY_PATH（find_*
     的搜索路径变量），命令行 `-I`/`-L` 不参与探测 → 只注入 -I 会导致
     GSL/yaml 探测失败、目标（yaml_test/abi）未注册；
   - 而被探测到的头文件被源码 `#include` 时（DART_HAS_YAML 下
     `include/dart/common.h` include 了 `yaml.h`），编译期仍需 `-I` 出现在
     编译命令行 → 只注入 CMAKE_INCLUDE_PATH 会导致 yaml.h not found。
3. 两者必须**同时注入**（双路），缺一不可。

## 解法：generate() 双路注入

```python
def generate(self):
    tc = CMakeToolchain(self)
    inc_dirs = []; lib_dirs = []
    for dep_name in ("ms-gsl", "rapidjson", "libyaml"):
        dep = self.dependencies.get(dep_name)
        if dep is None:
            continue
        for d in dep.cpp_info.includedirs:
            inc_dirs.append(os.path.join(dep.package_folder, d))
        for d in dep.cpp_info.libdirs:
            lib_dirs.append(os.path.join(dep.package_folder, d))
    if inc_dirs:
        # (a) find_* 探测路径（CMAKE_INCLUDE_PATH/LIBRARY_PATH 分号为分隔）
        tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(inc_dirs)
        # (b) 编译命令行 -I（空格分隔，供 #include 头文件）
        tc.variables["CMAKE_CXX_FLAGS"] = " ".join("-I" + d for d in inc_dirs)
        tc.variables["CMAKE_C_FLAGS"] = " ".join("-I" + d for d in inc_dirs)
    if lib_dirs:
        tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(lib_dirs)
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = " ".join("-L" + d for d in lib_dirs)
    tc.generate()
```

注意：`CMAKE_INCLUDE_PATH` 是 find_* 搜索路径（分号分隔），
`CMAKE_CXX_FLAGS` 是编译选项（空格分隔）——两者语素不同，不能互相替代。

## 验证

- conan-verify G2 conan create 通过：4 个上游 ctest 目标全部注册
  （dart_unit_tests/json/yaml/abi），243 个 TEST_CASE/SCENARIO 全量通过
- 本地复现：仅 -I 无 CMAKE_INCLUDE_PATH → configure 报 GSL not found；
  仅 CMAKE_INCLUDE_PATH 无 -I → 编译报 yaml.h not found
- test_package 消费者（test.cpp）与鸿蒙专项测试（test_ohos.cpp）均真实
  调用公开 API 且 PASS（R34/PF3 非空壳）

## 适用边界 / 反例

- 适用于：上游 CMake 用 find_path/find_library 探测 header/库依赖，且被
  探测头文件会被源码 #include 的 Conan 2 配方（header-only 依赖
  ms-gsl/rapidjson、探测型依赖 libyaml 均适用）
- 不适用：CMakeDeps + find_package(CONFIG) 全套的项目（走 target 注入，
  见 E447/E473）；Meson/autotools 项目（不走 CMakeToolchain）
- 反例：若被依赖头文件从不被 #include（纯探测用途），可只注入
  CMAKE_INCLUDE_PATH，但这是退化子集，双路注入仍无副作用

## 查重差异（七轴）

- exact_duplicate: false（graph/doc/drafts 无同模式条目）
- causal_duplicate: false
- trigger_overlap: false（E293 触发是 C++17 动态异常规范，不同）
- solution_overlap: false（E376 是 find_library libm NOTFOUND 的 target
  绑定缓存问题；E447/E473 是 vendored Find 模块/CMakeDeps target 失配）
- combination_novelty: true（探测+编译双路组合注入）
- boundary_novelty: true（可跨库复用的最小注入模式，含
  "CMakeToolchain 无 cxxflags 属性" 的明确边界）
- test_migration_novelty: false
- 关系: similar_to(E293, E376, E447)
- 决策: **new_draft**（路径 B）