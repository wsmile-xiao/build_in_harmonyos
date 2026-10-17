# CMake include 模块内无条件 set() 回置会静默丢弃 -D 命令行 cache 覆盖，需 if(NOT DEFINED) 守卫尊重显式输入

## 问题描述

CMake 模块（被 `include()` 的 .cmake 文件）里文件级写死的默认值：

```cmake
# Keep track if we have all dependencies.
set(ENABLE_CHECK_TARGETS TRUE)     # 无条件，每次 include 都执行
```

会在当前目录作用域创建同名**普通变量**并遮蔽用户经 `-DENABLE_CHECK_TARGETS=OFF` 传入的 **cache** 输入。用户显式覆盖被静默丢弃、无任何警告——配置继续按"开关为默认值"走，直到在别处以 configure 致命错误的形式爆炸。

案例（括注）：libomptarget-rtl-amdgpu 18.1.8（LLVM openmp monorepo）。插件包不构建 in-tree clang，按上游惯例以 `-DENABLE_CHECK_TARGETS=OFF` 关闭 lit 测试套件；该开关被 `openmp/cmake/OpenMPTesting.cmake` 第 2 行无条件回置为 TRUE，configure 死于：

```text
CMake Error at cmake/modules/AddLLVM.cmake:1962 (add_dependencies):
  The dependency target "clang" of target "check-openmp" does not exist.
Call Stack (most recent call first):
  cmake/modules/AddLLVM.cmake:2028 (add_lit_target)
  openmp/cmake/OpenMPTesting.cmake:220 (add_lit_testsuite)
  openmp/cmake/OpenMPTesting.cmake:243 (add_openmp_testsuite)
  openmp/CMakeLists.txt:154 (construct_check_openmp_target)
```

（check-openmp/check-libomp 等四处同名错误。）

## 根因机理

完整因果链：

1. **工具语义**：`set()` 无 `CACHE` 时在当前作用域创建普通变量；普通变量在目录作用域内**遮蔽**同名 cache 条目。include 模块文件级的无条件 `set(<VAR> 默认值)` 因此每次 include 都把用户 cache 覆盖压掉。
2. **触发命令**：`cmake -B build -S <llvm>/llvm -DLLVM_ENABLE_PROJECTS=openmp -DENABLE_CHECK_TARGETS=OFF`。
3. **失败点**：开关失效 → `construct_check_openmp_target`（openmp/CMakeLists.txt:154）→ `add_openmp_testsuite`（OpenMPTesting.cmake:243）→ `add_lit_testsuite`（:220）→ `add_lit_target` → `add_dependencies(clang)`（AddLLVM.cmake:1962）→ 目标 `clang` 不存在 → configure 致命错误。
4. **归类**：构建系统变量作用域语义问题（include 内普通变量遮蔽 cache 输入），非平台问题——任何"模块内写死默认值 + 用户可 -D 覆盖"的 CMake 工程都可能踩中。

## 解决方案

**主案（守卫默认值，尊重显式输入）**——把无条件 `set` 改为 `NOT DEFINED` 守卫，对默认构建零行为变化：

```cmake
if(NOT DEFINED ENABLE_CHECK_TARGETS)
  set(ENABLE_CHECK_TARGETS TRUE)
endif()
```

验证：带 `-DENABLE_CHECK_TARGETS=OFF` 的 configure 通过、不再创建依赖 clang 的 check-* 目标；不带该开关时行为与上游完全一致。补丁最小、可向上游提交（本 run 以注册补丁交付）。

**fallback（钉死必缺测试依赖，触发上游自身降级；仅退路）**：

```sh
cmake -B build -S <llvm-project>/llvm -DLLVM_ENABLE_PROJECTS=openmp \
      -DOPENMP_LLVM_LIT_EXECUTABLE=/nonexistent -G Ninja
```

`find_standalone_test_dependencies()` 找不到 llvm-lit 时会自行 `set(ENABLE_CHECK_TARGETS FALSE PARENT_SCOPE)`，check-* 不再创建，configure 输出 "The check targets will not be available!" 警告。诚实权衡：这是靠"弄缺一个探测"触发降级的绕道而非修复——check 套件被整体禁用（在确实需要跑测试的上下文不可用），且依赖上游探测顺序的稳定性。

**禁止项**：不得重复传同一 `-D` 或用 `CACHE FORCE` 再压制（在丢弃语义上叠掩盖，值的有效性依赖 include 顺序）；不得删除 `OpenMPTesting.cmake` include 或整体剔除 check 目标创建逻辑（绕过上游测试基建，不可向上游提交）。

## 验证（自包含，任意 llvm-project checkout 可复现）

```sh
# 1) 定位无条件回置（预期：set(ENABLE_CHECK_TARGETS TRUE) 无 NOT DEFINED 守卫）
grep -n -A3 'Keep track if we have all dependencies' <llvm-project>/openmp/cmake/OpenMPTesting.cmake

# 2) 带 -D 复现丢弃（monorepo、从 llvm/ 父目录、不构建 clang 的上下文）
cmake -B /tmp/ovr-probe -S <llvm-project>/llvm -DLLVM_ENABLE_PROJECTS=openmp \
      -DENABLE_CHECK_TARGETS=OFF -G Ninja
# 预期：CMake Error at cmake/modules/AddLLVM.cmake:1962 (add_dependencies)：
#       The dependency target "clang" of target "check-openmp" does not exist.

# 3) 应用守卫补丁后重复步骤 2：configure 通过，无 check-* 目标创建错误
```

## 诚实权衡（边界）

本条修复的是"显式输入被默认值压制"的语义缺陷本身；但不改变上游对 check 套件依赖面的其他假设（如 lit/FileCheck 的查找位置）。若上游在别的模块也以同样模式固化其他开关，需要逐一按同法处理——本条提供的判别式是通用的：**`grep -n '^set(' <被include的模块>.cmake`，凡与文档化 `-D` 开关同名的无条件 `set()`，即为静默丢弃点**。

## 适用范围与同族条目

任何"被 include 的 CMake 模块内无条件 set() 固化默认值、同时文档允许 -D 覆盖"的工程（feature/测试/安装开关皆可能中招）。同族条目差异：E526 是 conan 工具层（apply_conandata_patches 默认 strip=0）丢弃/改变用户语义，本条是 CMake 变量作用域层；E096 是探测/默认值未尊重显式标准设定（C++ 标准族）；E100 是组件被禁用后残留引用导致链接失败（下游症状，非 cache 覆盖机理）。本条新增价值：给出"include 模块内无条件 set() 静默遮蔽 -D cache"的机理链与 `NOT DEFINED` 守卫这一最小上游可提交修法，以及不可修时的依赖降级退路。

## 本 run 证据

- 未打补丁探针日志 probe-configure.log：`AddLLVM.cmake:1962` 错误块共 12 处（两簇 :420-462、:552-594），6 个 check-* 目标（check-openmp/check-libomp/check-ompt/check-libarcher/check-libomptarget/check-ompt-multiplex）各 2 处，调用栈直指 AddLLVM.cmake:2028 与 OpenMPTesting.cmake:220/243，证明 `-D` 覆盖已被回置丢弃。
- 修复：注册补丁 `0001-openmp-cmake-let-ENABLE_CHECK_TARGETS-override-work.patch`（`if(NOT DEFINED)` 守卫）。
- 权威 CI run3：带 `-DENABLE_CHECK_TARGETS=OFF` 的 configure 全绿、构建至 test_package dlopen+dlsym 通过（探针日志留档于本 run 临时目录，run 结束后以 CI 日志为准）。
