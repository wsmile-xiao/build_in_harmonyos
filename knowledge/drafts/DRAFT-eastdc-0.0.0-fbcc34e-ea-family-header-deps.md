# DRAFT: EA 家族公开头链式依赖 + plain-name 链接 + 分配器契约

- **草稿 ID**: `DRAFT-eastdc-0.0.0-fbcc34e-ea-family-header-deps`
- **触发软件**: eastdc 0.0.0-fbcc34e（Electronic Arts EAStdC）
- **状态**: DRAFT（待主编/AI 审核提升为 E 条目）
- **姊妹条目**: DRAFT-ohos-public-header-transitive-dep（公开头链传递依赖）、
  DRAFT-conan2-cmakedeps-transitive-include-strip（CMakeDeps 传递 include）、E278（plain-name 链接）

## 问题（三类真实错误）

1. clean 源码树编译：
```
include/EAStdC/EACallback.h:81:10: fatal error: 'eathread/eathread_atomic.h' file not found
#include <eathread/eathread_atomic.h>   // Used even if EASTDC_THREADING_SUPPORTED is zero
```
以及 `'EABase/eabase.h' file not found`、`'EAAssert/eaassert.h' file not found`。

2. clean 源码树 configure：
```
CMake Error at CMakeLists.txt:16 (include): include could not find requested file: CommonCppFlags
```

3. 消费者链接（无契约实现时）：
```
ld.lld: error: undefined symbol: operator new[](unsigned long, char const*, int, unsigned int, char const*, int)
```

## 根因

EA 家族库（EABase/EAAssert/EAThread/EAStdC/EASTL/EAMain/EATest）按**链式头依赖**设计：

- EAStdC 的 public 头（EACallback.h、internal/Thread.h）**无条件** include `<eathread/...>`，
  即使功能宏 `EASTDC_THREADING_SUPPORTED=0` 仍 include（注释明示 "Used even if ... is zero"）；
  18 个源文件 include `<EAAssert/eaassert.h>`，27 处 include `<EABase/eabase.h>`。
- 上游 CMakeLists 用 **plain-name** 声明兄弟库依赖：
  `target_link_libraries(EAStdC EABase)` / `EAAssert` / `EAThread`（等价 `-l` 库名），
  没有 find_package、没有 CMake target 传播 → CMakeDeps 生成的 `eabase::eabase` 等目标不会被使用，
  clean 源码树编译时依赖头文件路径不会进入编译。
- 测试 CMake 模块（CommonCppFlags）位于 git submodule 树
  （test/packages/EASTL/scripts/CMake），官方 archive tarball **不含子模块内容**。
- EAStdC 的 internal/Config.h 声明 **user-provided** 调试 `operator new/delete`
  （六参形式：name/flags/debugFlags/file/line），库本体对象引用该符号；
  上游测试主文件（EAStdCTest.cpp）与 EATest/EAMain 提供转发实现，普通消费者链接时缺失。

## 方案

1. **兄弟库提升为 recipe 直接 requires**：EAStdC 主库 requires `eabase/0699a15` +
   `eaassert/...` + `eathread/...`（eathread 未发布时为外部依赖阻塞，按 R36 发布后恢复）。
2. **plain-name 无 target 传播 → generate() 注入 -I**：遍历
   `self.dependencies[...].cpp_info.includedirs`，拼 `-I<pkg>/<inc>` 进
   `CMAKE_CXX_FLAGS`（上游 CMakeLists 不消费 CMakeDeps target 时的通用手段）。
3. **分配器契约**：test_package/消费者侧提供 `ea_allocator_impl.cpp`
   （`extern` 六参 operator new/delete 转发 ::operator new），与上游 EAStdCTest.cpp 同款做法；
   不修改被测库源码。
4. **子模块 CMake 模块缺失**：顶层 CMakeLists 用 `if(EXISTS ".../CommonCppFlags.cmake")`
   守卫 include；库构建关闭 `EASTDC_BUILD_TESTS`；上游测试用官方镜像抓取的子模块源码本地
   验证（不进归档/PR）。
5. **CMake 4.x 前置**：`cmake_minimum_required < 3.5` 先提升到 3.5（复用 E103），否则 configure 直接失败。

## 验证（eastdc 0.0.0-fbcc34e）

- 主库 `libEAStdC.a` 编译成功（cmake + make，aarch64-ohos clang 15）
- 上游测试 **21/21 PASSED**，RETURNCODE=0（reports/upstream-test-run.log，sha256 d86bbcdb…）
- 消费者测试 5 项公开 API（CRC32/Sprintf/Memclear+IsAligned/RandomLinearCongruential/UTF8Validate）
  全部通过，exit 0
- HarmonyOS 专项测试（小端校验/端序往返/int128 乘法）ALL OK，exit 0
- clean 源码树 conan create 推进到 `eathread/eathread_atomic.h` 缺失（eathread 未发布，
  属外部依赖阻塞，恢复条件见 reports/conan-dependency-gate.md）
- R02 闭环（2026-09-18）：eaassert/0.0.0-e5e1812 与 eathread/0.0.0-f3c6c54 已发布到 ohpcd，
  conanfile.py 声明三兄弟依赖后 `conan create`（ohos-aarch64）PASS，test_package 消费者
  5 项公开 API + OHOS 专项 ALL OK，finish/W2/W3 通过；配方 package() 因上游无 install 规则
  手动镜像导出布局（copy 头/库/LICENSE），package_info 用 cpp_info.requires 传播兄弟库 include

## 边界 / 反例

- 适用：EA 家族库（EABase/EAAssert/EAThread/EAStdC/EASTL/EAMain/EATest）及其消费者；
  用 plain-name 声明依赖的老式 CMake 库。
- 反例：使用 `find_package` + 标准 CMake target 传播的库不需要 generate() -I 注入；
  release 归档含子模块 CMake 模块的库不需要 if(EXISTS) 守卫；
  主库 public 头不 include 兄弟库头（兄弟库仅测试链使用）的库不受此约束。
- 注意：eathread/eaassert 未发布是 eastdc 交付的真实依赖阻塞，草稿不替代发布动作。
