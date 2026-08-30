# E321 — OHOS 小对象分配未满足 `max_align_t` 对齐

## 错误特征
在 HarmonyOS/OpenHarmony PC arm64 上运行 foonathan/memory 的默认分配器测试时，出现：

```text
REQUIRE( detail::is_aligned(node, def_alignment) )
```

设备实测 `alignof(std::max_align_t)=16`，而小尺寸 `malloc`/`operator new` 返回地址可能只按 8 字节对齐。

## 触发条件
- 构建系统：CMake/Conan
- 阶段：上游 CTest 或消费者运行测试
- 平台：OHOS、HarmonyOS、OpenHarmony hosted 实现
- 边界：零字节请求也必须返回满足最大对齐要求的可释放地址

## 根因分析
foonathan/memory 的 `heap_allocator`、`malloc_allocator` 和 `new_allocator` 都把 hosted 分配结果视为满足 `detail::max_alignment`。OpenHarmony 的 musl 系运行时不保证小对象默认分配达到本机的 16 字节最大对齐，因此上游 `default_allocator`、`heap_allocator`、`malloc_allocator` 或 `new_allocator` 测试会失败。对 size 为 0 的请求，直接调用 `posix_memalign` 还可能得到未定义的零长度分配行为，所以请求大小必须提升为至少 1。

## 解决方案

### 推荐方案
在 POSIX hosted 路径（使用标准 `__unix__` 守卫）使用 `posix_memalign(&memory, detail::max_alignment, size ? size : 1)`（头文件所在命名空间中使用 `max_alignment`），并用 `std::free` 释放；Windows 路径继续保留上游的 `malloc` 或 `operator new` 语义。配方应通过 `refresh-patch --auto` 固化该源码修改，并在原生 OHOS worker 上运行完整上游测试。

同一项目若用 `CMAKE_SYSTEM_NAME=HarmonyOS` 在原生设备上构建，CMake 仍会把显式设置系统名标记为 cross-compiling；节点大小生成工具需要额外允许 `CMAKE_HOST_SYSTEM_NAME=HarmonyOS` 且目标为 OHOS/HarmonyOS 的路径运行。

### 禁止做法
- ❌ 跳过或放宽对齐测试。
- ❌ 只把指针强制转换为更高对齐类型，或把未对齐地址向上取整后直接返回。
- ❌ 用静态链接、权限放宽或伪造测试结果掩盖运行时分配契约差异。

## 验证
```bash
cmake -S . -B build -DCMAKE_SYSTEM_NAME=HarmonyOS \
  -DFOONATHAN_MEMORY_BUILD_TESTS=ON -DFOONATHAN_MEMORY_BUILD_TOOLS=ON
cmake --build build --parallel 1
ctest --test-dir build --output-on-failure
# 结果：39/39 test cases、140870 assertions 全部通过
```

## 关联条目
- 相关：E267（CMake 对 OHOS/HarmonyOS 系统名的识别）
- 相关：E140（HarmonyOS CMake 平台分支检测）
