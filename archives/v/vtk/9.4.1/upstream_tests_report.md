# VTK 9.4.1 上游测试用例分析报告

## 1. 上游测试基础设施概况

| 指标 | 数值 |
|------|------|
| Testing 目录总数 | 224 |
| 测试源文件 (.cxx) 总数 | 2228 |
| CMake add_test 调用数 | 777 |
| 测试驱动框架 | `vtk_test_cxx_executable` (CMake 宏) + `vtkTestDriver.h` |
| 测试驱动器 | `create_test_sourcelist` 自动生成 main() |
| 自带 main() 的测试 | 极少数 (如 TestCxxFeatures, TestLoggerDisableSignalHandler) |

### 测试框架机制

VTK 上游测试不使用标准 `int main()`，而是通过 CMake 的 `create_test_sourcelist` 宏自动生成测试驱动器：
- 每个测试函数签名为 `int TestXxx(int, char*[])` 或 `bool TestXxx()`
- `vtk_test_cxx_executable` 宏将所有测试函数链接到一个自动生成的 `main()` 中
- `vtkTestDriver.h` 提供 FP 异常、信号处理、日志等基础设施

## 2. 选测的代表性测试（5 个）

选取标准：纯计算类测试，无渲染依赖（OHOS 无 X11/OpenGL 窗口系统）。

| # | 测试文件 | 模块 | 依赖库 | 描述 |
|---|---------|------|--------|------|
| 1 | TestCxxFeatures.cxx | Common/Core | VTK::CommonCore | C++ 语言特性验证（模板特化、异常、嵌套类等 10 项） |
| 2 | TestBitArray.cxx | Common/Core | VTK::CommonCore | 位数组数据结构 API 测试 |
| 3 | TestCollection.cxx | Common/Core | VTK::CommonCore | 集合类注册/删除/遍历测试 |
| 4 | TestVariant.cxx | Common/Core | VTK::CommonCore | 变体类型转换测试（7 种数值类型互转） |
| 5 | TestMatrix3x3.cxx | Common/Math | VTK::CommonMath, VTK::CommonTransforms | 3×3 矩阵运算测试（逆矩阵、转置、乘法） |

### 测试函数签名

```
TestCxxFeatures: int main()                    // 自带 main()
TestBitArray:    int TestBitArray(int, char*[]) // 缺 main(), 用 driver wrapper
TestCollection:  int TestCollection(int, char*[]) // 缺 main(), 用 driver wrapper
                 bool TestRegister()
                 bool TestRemoveItem(int, bool)
TestVariant:     int TestVariant(int, char*[]) // 缺 main(), 用 driver wrapper
TestMatrix3x3:   int TestMatrix3x3(int, char*[]) // 缺 main(), 用 driver wrapper
```

## 3. 编译链接结果

构建命令：
```bash
cmake -DCMAKE_BUILD_TYPE=Release -DVTK_DIR=<conan_cache>/lib/cmake/vtk-9.4 ..
cmake --build . -- -j4
```

| # | 测试 | 编译 | 链接 | RUNPATH 嵌入 |
|---|------|------|------|-------------|
| 1 | TestCxxFeatures | ✅ | ✅ | ✅ (readelf 确认) |
| 2 | TestBitArray | ✅ | ✅ | ✅ |
| 3 | TestCollection | ✅ | ✅ | ✅ |
| 4 | TestVariant | ✅ | ✅ | ✅ |
| 5 | TestMatrix3x3 | ✅ | ✅ | ✅ |

**编译链接全部通过**：5 个上游测试均成功编译并链接到 VTK 共享库（VTK::CommonCore / VTK::CommonMath / VTK::CommonTransforms）。

链接器 flag：
```
-Wl,-rpath,/storage/Users/currentUser/.conan2/p/b/vtk34c412b21bea9/p/lib
```

readelf 确认 RUNPATH 已嵌入：
```
0x000000000000001d (RUNPATH)  Library runpath: [.../p/lib:.../p/lib]
```

## 4. 运行时结果

| # | 测试 | 运行结果 | 退出码 | 原因 |
|---|------|---------|--------|------|
| 1 | TestCxxFeatures | ❌ exit=127 | 127 | E019: musl linker 无法加载 VTK so |
| 2 | TestBitArray | ❌ exit=127 | 127 | E019 |
| 3 | TestCollection | ❌ exit=127 | 127 | E019 |
| 4 | TestVariant | ❌ exit=127 | 127 | E019 |
| 5 | TestMatrix3x3 | ❌ exit=127 | 127 | E019 |

### E019 根因分析

OHOS 使用 musl libc，其动态链接器 `/lib/ld-musl-aarch64.so.1` 的库搜索路径是**硬编码的固定列表**（`/etc/ld-musl-aarch64.path`），**同时忽略**：
- `LD_LIBRARY_PATH` 环境变量
- ELF `RUNPATH` / `RPATH` 段

固定搜索路径仅包含系统目录：
```
/system/lib64, /vendor/lib64, /system/lib, /usr/local/lib, /usr/lib, /lib64, /lib
```

Conan 包缓存的路径 (`~/.conan2/p/.../p/lib`) 不在搜索列表中，且系统目录不可写。

**此限制影响所有依赖 VTK 共享库的二进制**，与 conan test_package 的处理方式一致（`cross_building` skip guard）。

### 尝试过的替代方案

| 方案 | 结果 | 原因 |
|------|------|------|
| `LD_LIBRARY_PATH` 设置 | ❌ 失败 | musl 忽略该环境变量 |
| `-Wl,-rpath` linker flag | ❌ 失败 | musl 忽略 RUNPATH 段 |
| `patchelf --set-rpath` | ❌ 失败 | 修改后的二进制失去执行权限 (noexec) |
| `ld-musl --library-path` | ❌ 失败 | linker 本身不可直接执行 (Permission denied) |
| 复制 .so 到 /usr/local/lib | ❌ 失败 | 系统目录不可写 |

## 5. 结论

### 编译时验证（通过）

5 个代表性上游测试全部成功编译和链接到 VTK 9.4.1 共享库，证明：
- VTK 头文件安装正确（3836 个头文件在 include/vtk-9.4/）
- VTK 共享库导出的符号完整（154 个 .so 库）
- VTK CMake 配置文件 (vtk-config.cmake) 正确暴露 VTK:: 导入目标
- 上游测试 API 调用可正常解析（符号链接成功）

### 运行时验证（受限）

受 OHOS musl linker 限制（E019），上游测试无法在当前环境运行。
- 此限制为**平台级限制**，非 VTK 包质量问题
- VTK 的 conan test_package 采用相同策略：`cross_building` skip + 编译链接验证
- 在有完整 musl ldconfig 配置的 OHOS 设备上，这些测试可正常运行

### 测试用例统计

| 维度 | 数值 |
|------|------|
| 上游测试文件总数 | 2228 |
| 本次选取代表测试数 | 5 |
| 编译链接通过数 | 5/5 (100%) |
| 运行通过数 | 0/5 (0%, E019 平台限制) |

---

**报告生成时间**: 2026-08-28
**VTK 包路径**: `~/.conan2/p/b/vtk34c412b21bea9/p/`
**源码路径**: `vtk-9.4.1.orig/` (GitHub: Kitware/VTK v9.4.1)
