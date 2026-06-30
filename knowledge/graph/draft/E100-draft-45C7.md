# E100 — CMake 交叉编译 TRY_RUN 测试失败

## 错误特征

CMake 在配置阶段检测到交叉编译时，TRY_RUN() 宏会尝试编译并运行测试程序，但目标平台的二进制无法在宿主机执行，导致配置失败。

典型错误日志：
```
CMake Error: TRY_RUN(TRY_RUN_VAR) failed to compile
-- The test executable was not built
-- cannot run test executables on this platform
CMake Error: TRY_RUN not supported in cross-compiling mode
```

## 触发条件
- 构建系统: CMake
- 阶段: configure (configuration)
- 平台: OHOS/musl 或其他非标准平台
- 条件: CMAKE_SYSTEM_NAME 与宿主机不同，触发交叉编译检测

## 根因分析

CMake 的 TRY_RUN() 宏用于检测编译器的运行时特性，流程如下：
1. 编译一个测试程序（例如检查 long double 精度）
2. 尝试运行该程序获取输出结果
3. 将结果存储到 CMake 缓存变量中

在交叉编译模式下：
- 步骤 1 可以成功（编译器能生成目标平台代码）
- 步骤 2 无法执行（目标平台二进制无法在宿主机运行）
- 步骤 3 失败，无法获取运行时结果

这是 CMake 交叉编译的固有限制，需要预先告知测试结果。

## 解决方案

### 推荐方案：创建 TryRunResults 缓存文件

**核心思路**：预先创建一个 CMake 缓存文件，设置所有 TRY_RUN 变量的值，避免实际执行测试程序。

**步骤**：

1. **收集 TRY_RUN 变量列表**
   ```bash
   # 在首次失败后，CMake 会列出所有需要的 TRY_RUN 变量
   grep "TRY_RUN" CMakeLists.txt
   ```

2. **创建 TryRunResults-ohos.cmake 文件**
   ```cmake
   # TryRunResults-ohos.cmake
   # 预设所有 TRY_RUN 变量值

   # 示例：HDF5 的 TRY_RUN 变量
   set(H5_PRINTF_LL_TEST "ll" CACHE STRING "printf long long format")
   set(HDF5_PRINTF_LL_TEST_RUN "ll" CACHE STRING "printf long long format")

   # long double 精度（musl 的 LDBL_DIG）
   set(HDF5_LONG_DOUBLE_DIG_TEST 33 CACHE STRING "long double decimal digits")
   set(HDF5_LONG_DOUBLE_DIG_TEST_RUN 33 CACHE STRING "long double decimal digits")

   # 其他测试...
   ```

3. **使用缓存文件配置**
   ```bash
   cmake -C TryRunResults-ohos.cmake \
         -DCMAKE_SYSTEM_NAME=Linux \
         -DCMAKE_BUILD_TYPE=Release \
         ..
   ```

**关键技巧**：
- 使用 `-C` 参数加载缓存文件（在 `-D` 参数之前）
- `CMAKE_SYSTEM_NAME=Linux`（而非 OHOS）避免未知平台警告
- 变量名需要与软件的 CMakeLists.txt 中的定义一致

### 回退方案：禁用交叉编译检测

如果无法创建缓存文件，可以尝试让 CMake 认为是本地编译：
```bash
cmake -DCMAKE_SYSTEM_NAME=Linux ..
```

**限制**：这会跳过一些有用的平台检测，可能导致编译问题。

### 禁止做法
- ❌ 使用 `CMAKE_SYSTEM_NAME=OHOS`（不是标准平台名，会触发更多警告）
- ❌ 手动修改 CMake 生成的配置文件（违反 R6）
- ❌ 禁用整个测试套件来绕过问题（应该只处理 TRY_RUN）

## 验证
```bash
# 检查 TRY_RUN 变量是否生效
cmake -C TryRunResults-ohos.cmake .. | grep "TRY_RUN"

# 确认配置完成
cmake --build . --target help

# 运行实际编译
make -j1
```

## 实际案例：HDF5 1.13.0

HDF5 在 OHOS/musl 平台编译时遇到 TRY_RUN 问题：

**创建的缓存文件内容**：
```cmake
# TryRunResults-ohos.cmake
set(H5_PRINTF_LL_TEST "ll")
set(HDF5_PRINTF_LL_TEST_RUN "ll")
set(HDF5_LONG_DOUBLE_DIG_TEST 33)
set(HDF5_LONG_DOUBLE_DIG_TEST_RUN 33)

# 转换测试设置为失败（使用安全默认值）
set(HDF5_ALIGNMENT_TEST_RUN "FAILED")
set(HDF5_DIRECT_VFD_TEST_RUN "FAILED")
```

**配置命令**：
```bash
cmake -C TryRunResults-ohos.cmake \
      -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_SYSTEM_NAME=Linux \
      -DCMAKE_BUILD_TYPE=Release \
      -DHDF5_BUILD_CPP_LIB=ON \
      -DHDF5_ENABLE_Z_LIB_SUPPORT=ON \
      -DZLIB_INCLUDE_DIR=/path/to/include \
      -DZLIB_LIBRARY=/path/to/libz.a \
      ..
```

**结果**：成功编译，生成完整的库和工具。

## 关联条目
- 相关: E007 (config.guess 平台检测)
- 相关: E072 (config.sub 三元组验证)
- 相关: R23 (平台检测机制优先于改生成文件)