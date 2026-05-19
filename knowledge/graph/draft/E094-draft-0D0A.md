# E094 — CMake 平台检测失败

## 错误特征

### 典型错误现象

在编译使用 CMake 构建系统的 C 库（如 json-c 0.17）时，可能会遇到以下问题：

1. **CMake 检测失败**：
   ```
   -- Looking for snprintf
   -- Looking for snprintf - not found
   -- Looking for isnan
   -- Looking for isnan - not found
   ```

2. **config.h 缺少定义**：
   ```c
   /* config.h */
   /* #undef HAVE_SNPRINTF */     // 应该是 #define HAVE_SNPRINTF 1
   /* #undef HAVE_DECL_ISNAN */   // 应该是 #define HAVE_DECL_ISNAN 1
   ```

3. **编译错误**：
   ```
   error: 'snprintf' undeclared (first use in this function)
   error: "HAVE_DECL_ISNAN" macro redefined
   ```

### 错误日志示例

```
CMake Error at CMakeLists.txt:45 (check_c_source_compiles):
  check_c_source_compiles failed for snprintf test
  
In file included from json_object.c:25:
./config.h:85: error: "HAVE_DECL_ISNAN" redefined
 #define HAVE_DECL_ISNAN 1
```

## 触发条件

- **构建系统**: CMake
- **阶段**: configuration（配置阶段）
- **平台**: OHOS（基于 musl libc）
- **典型场景**: 
  - 使用 `check_c_source_compiles()` 检测 C 函数特性
  - 使用 `check_function_exists()` 检测函数是否存在
  - 使用 `check_include_file()` 检测头文件
  - 生成的 config.h 中 `HAVE_*` 定义缺失或冲突

## 根因分析

### 问题根源

CMake 的平台检测机制（`check_c_source_compiles`, `check_function_exists` 等）在 OHOS 平台上可能失败，主要原因包括：

1. **musl libc 与 glibc 差异**：
   - OHOS 使用 musl libc，与 glibc 的实现细节不同
   - 某些函数的声明方式、宏定义方式存在差异
   - CMake 的检测代码片段可能假设 glibc 环境

2. **检测代码片段不兼容**：
   ```cmake
   check_c_source_compiles("
     #include <stdio.h>
     int main() { snprintf(NULL, 0, \"\"); return 0; }
   " HAVE_SNPRINTF)
   ```
   这个检测代码在 musl 环境下可能因编译器标志、头文件包含顺序等问题失败。

3. **头文件冲突**：
   - musl 的 `<math.h>` 定义了 `isnan` 为宏
   - CMake 检测代码可能尝试声明 `isnan` 为函数
   - 导致 "macro redefined" 错误

4. **交叉编译环境检测失败**：
   - CMake 的 try_compile 机制在交叉编译时可能误报
   - 工具链配置不完整导致检测失败

### 为什么会发生

```
┌─────────────────────────────────────────────────┐
│ CMake 检测流程                                   │
├─────────────────────────────────────────────────┤
│ 1. 生成测试代码片段                               │
│ 2. try_compile() 编译测试代码                     │
│ 3. 分析编译结果（成功/失败）                      │
│ 4. 设置 HAVE_* 变量                              │
│    ↓                                            │
│ ❌ 失败点：                                       │
│ - 测试代码片段不兼容 musl                         │
│ - 编译器标志不匹配                                │
│ - 头文件包含顺序问题                              │
│ - 宏定义冲突                                      │
└─────────────────────────────────────────────────┘
```

## 解决方案

### 推荐方案：手动添加 HAVE_* 定义

**适用场景**: CMake 检测失败，但实际函数在平台上可用

**步骤**：

1. **运行 CMake 配置**：
   ```bash
   cmake -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
   ```

2. **检查 config.h 缺失的定义**：
   ```bash
   # 检查哪些 HAVE_* 定义缺失
   grep -E "HAVE_SNPRINTF|HAVE_DECL_ISNAN" build/config.h
   ```

3. **手动添加缺失的定义**：
   ```bash
   # 方法 1：追加到 config.h
   cat >> build/config.h << 'EOF'
   
   /* Manually added for OHOS platform */
   #define HAVE_SNPRINTF 1
   #define HAVE_DECL_ISNAN 1
   #define HAVE_DECL_ISINF 1
   EOF
   ```

4. **或者创建补丁文件**：
   ```diff
   --- a/CMakeLists.txt
   +++ b/CMakeLists.txt
   @@ -50,6 +50,14 @@ check_function_exists(vsnprintf HAVE_VSNPRINTF)
    check_function_exists(snprintf HAVE_SNPRINTF)
    check_include_file("math.h" HAVE_MATH_H)
   
   +# OHOS platform fixes
   +if(NOT HAVE_SNPRINTF)
   +  set(HAVE_SNPRINTF 1 CACHE INTERNAL "Force enable snprintf on OHOS")
   +endif()
   +if(NOT HAVE_DECL_ISNAN)
   +  set(HAVE_DECL_ISNAN 1 CACHE INTERNAL "Force enable isnan on OHOS")
   +endif()
   +
    configure_file(config.h.in config.h @ONLY)
   ```

5. **重新生成配置**：
   ```bash
   cd build
   cmake ..
   ```

6. **继续编译**：
   ```bash
   make -j$(nproc) && make install DESTDIR=$TEST_PREFIX
   ```

### 补丁示例：json-c 0.17 的修复方式

**问题**：json-c 的 CMake 检测 `snprintf` 和 `isnan/isinf` 失败

**解决方案**：

1. **创建补丁文件** `0001-fix-cmake-platform-detection.patch`：
   ```diff
   diff --git a/CMakeLists.txt b/CMakeLists.txt
   index abc123..def456 100644
   --- a/CMakeLists.txt
   +++ b/CMakeLists.txt
   @@ -120,6 +120,17 @@ check_c_source_compiles(
        "${JSON_C_HAVE_SNPRINTF}"
        HAVE_SNPRINTF)
   
   +# OHOS/musl platform: override incorrect detection results
   +if(NOT HAVE_SNPRINTF)
   +  # snprintf exists in musl libc, force enable it
   +  set(HAVE_SNPRINTF 1 CACHE INTERNAL "snprintf available in musl" FORCE)
   +  message(STATUS "Overriding HAVE_SNPRINTF for OHOS/musl platform")
   +endif()
   +if(NOT HAVE_DECL_ISNAN)
   +  set(HAVE_DECL_ISNAN 1 CACHE INTERNAL "isnan available in musl" FORCE)
   +  message(STATUS "Overriding HAVE_DECL_ISNAN for OHOS/musl platform")
   +endif()
   +
    check_symbol_exists(isnan "math.h" HAVE_DECL_ISNAN)
    check_symbol_exists(isinf "math.h" HAVE_DECL_ISINF)
    
   diff --git a/config.h.in b/config.h.in
   index 123abc..456def 100644
   --- a/config.h.in
   +++ b/config.h.in
   @@ -15,6 +15,9 @@
   #define JSON_C_VERSION_PATCH @JSON_C_VERSION_PATCH@
   #define JSON_C_VERSION_NUM @JSON_C_VERSION_NUM@
   
   +/* Platform-specific overrides for OHOS */
   +#cmakedefine HAVE_SNPRINTF 1
   +#cmakedefine HAVE_DECL_ISNAN 1
   +
   /* Function availability */
   #cmakedefine HAVE_SNPRINTF
   #cmakedefine HAVE_DECL_ISNAN
   ```

2. **应用补丁**：
   ```bash
   cd $BUILD_SRC_DIR
   patch -p1 < 0001-fix-cmake-platform-detection.patch
   ```

### 替代方案：CMake Toolchain 文件修复

**适用场景**: 需要系统性解决多个项目的检测问题

**步骤**：

1. **创建 OHOS toolchain 文件** `ohos-toolchain.cmake`：
   ```cmake
   # OHOS/musl platform toolchain
   set(CMAKE_SYSTEM_NAME Linux)
   set(CMAKE_SYSTEM_PROCESSOR aarch64)
   
   # Override platform detection
   set(HAVE_SNPRINTF ON CACHE INTERNAL "")
   set(HAVE_DECL_ISNAN ON CACHE INTERNAL "")
   set(HAVE_DECL_ISINF ON CACHE INTERNAL "")
   
   # Prevent CMake from re-running checks
   set(CMAKE_C_COMPILER_WORKS ON CACHE INTERNAL "")
   set(CMAKE_CXX_COMPILER_WORKS ON CACHE INTERNAL "")
   ```

2. **使用 toolchain 配置**：
   ```bash
   cmake -B build \
     -DCMAKE_TOOLCHAIN_FILE=/path/to/ohos-toolchain.cmake \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
   ```

### 禁止做法

- ❌ **盲目修改生成的 config.h**：
  ```bash
  # 错误方式：直接 sed 替换
  sed -i 's/#undef HAVE_SNPRINTF/#define HAVE_SNPRINTF 1/' config.h
  ```
  这可能破坏其他正确的检测结果，导致编译错误。

- ❌ **修改源码假设函数存在**：
  ```c
  // 错误方式：直接在源码中假设
  #define HAVE_SNPRINTF 1  // 不要这样做
  ```
  应该在配置阶段解决，而不是硬编码到源码中。

- ❌ **忽略检测失败继续编译**：
  ```bash
  cmake ..  # 检测失败但不处理
  make      # 继续编译会导致 undefined 错误
  ```

## 验证

### 验证步骤

1. **检查 config.h 内容**：
   ```bash
   grep -E "HAVE_SNPRINTF|HAVE_DECL_ISNAN" build/config.h
   ```
   应该看到：
   ```
   #define HAVE_SNPRINTF 1
   #define HAVE_DECL_ISNAN 1
   ```

2. **验证编译通过**：
   ```bash
   cd build
   make clean
   make -j$(nproc)
   ```
   不应该有 "undeclared" 或 "macro redefined" 错误。

3. **运行测试验证功能**：
   ```bash
   make test
   # 或手动测试
   ./test_snprintf
   ./test_isnan
   ```

4. **检查生成的二进制**：
   ```bash
   nm -D build/libjson-c.so | grep snprintf
   # 应该能看到 snprintf 相关符号
   ```

### 成功标志

- ✅ config.h 包含正确的 `HAVE_*` 定义
- ✅ 编译无错误（无 "undeclared" 或 "redefined" 警告）
- ✅ 测试套件通过（或至少相关功能测试通过）
- ✅ 生成的库文件功能正常

## 影响范围

### 受影响的软件类型

1. **使用 CMake 构建的 C 库**：
   - json-c（JSON 解析库）
   - libxml2（XML 解析库）
   - curl（HTTP 客户端库）
   - openssl（加密库）
   - zlib（压缩库）
   - libevent（事件库）

2. **常见的失败检测**：
   - `check_c_source_compiles()` - 编译测试代码片段
   - `check_function_exists()` - 函数存在性检测
   - `check_symbol_exists()` - 符号存在性检测
   - `check_include_file()` - 头文件存在性检测

3. **典型的缺失定义**：
   - `HAVE_SNPRINTF` - snprintf 函数
   - `HAVE_VSNPRINTF` - vsnprintf 函数
   - `HAVE_DECL_ISNAN` - isnan 宏/函数
   - `HAVE_DECL_ISINF` - isinf 宏/函数
   - `HAVE_STRLCPY` - strlcpy 函数
   - `HAVE_STRLCAT` - strlcat 函数

### 如何判断是否受影响

编译时出现以下症状，应怀疑是此问题：

```bash
# 运行 CMake 配置，观察检测失败
cmake -B build 2>&1 | grep "not found"

# 检查 config.h
grep -E "undef HAVE_" build/config.h | head -20
# 大量的 #undef HAVE_* 可能表示检测失败

# 尝试编译，看是否有 undeclared 错误
make 2>&1 | grep "undeclared"
```

## 最佳实践

### 预防措施

1. **提前了解 OHOS 平台特性**：
   - OHOS 使用 musl libc
   - 大部分标准 C 函数都存在
   - 但实现细节可能与 glibc 不同

2. **优先使用项目提供的配置**：
   - 某些项目已有 OHOS/musl 支持
   - 查看项目的 `platform/` 或 `cmake/` 目录
   - 搜索 `__OHOS__` 或 `__MUSL__` 宏

3. **创建可复用的补丁**：
   - 为常用库准备 OHOS 平台补丁
   - 放在 `archives/{软件名}/{版本}/patches/` 目录
   - 在 `manifest.yaml` 中记录

### 相关知识条目

- **E007**: config.guess/config.sub 平台识别失败
  - 当 CMake 无法识别 OHOS 平台时可能触发
  - 需要先解决平台识别问题

- **E046**: chmod 不生效（SELinux 限制）
  - 平台限制问题，非 CMake 特有

- **E051**: 未实现的 syscall
  - 某些检测可能尝试使用未实现的 syscall

## 总结

E094 是 OHOS 平台上 CMake 构建项目的常见问题。根因是 CMake 的检测机制与 musl libc 不兼容。推荐方案是手动在 config.h 添加缺失的 `HAVE_*` 定义，或创建补丁修复 CMakeLists.txt 中的检测逻辑。

**关键要点**：
- ✅ 理解 CMake 检测失败的原因
- ✅ 使用手动定义或补丁方式修复
- ✅ 验证修复后的功能正常
- ❌ 不要盲目修改生成的配置文件
- ❌ 不要忽略检测失败继续编译