# DRAFT-stormlib-cmake-system-libs-and-sfile-eof（草稿）

- **软件**：StormLib 9.40（https://github.com/ladislav-zezula/StormLib）
- **构建系统**：CMake（C++11）+ Conan CMakeToolchain/CMakeDeps
- **平台**：HarmonyOS PC / aarch64，`clang++ 15.0.4`
- **状态**：DRAFT

## 现象

1. 消费者测试跑真实 MPQ 往返时失败：

```
FAIL: SFileReadFile failed (line 65)
```

2. 上游 `test/` 目标无法构建：`find_package(ALSA REQUIRED)`。

## 根因

1. **CMake 的双路径依赖选择**：StormLib 的 `CMakeLists.txt` 用
   `find_package(ZLIB)` / `find_package(BZip2)` 决定走系统库还是编译随包内置副本：

```cmake
find_package(ZLIB)
if (ZLIB_FOUND AND NOT STORM_USE_BUNDLED_LIBRARIES)
    set(LINK_LIBS ${LINK_LIBS} ZLIB::ZLIB)
    target_compile_definitions(${LIBRARY_NAME} PRIVATE -D__SYS_ZLIB)
else()
    set(SRC_FILES ${SRC_FILES} ${ZLIB_FILES})
endif()
```

   用 Conan 的 `CMakeDeps` 声明 `zlib`/`bzip2` 依赖即可命中"系统库"分支，
   自动定义 `__SYS_ZLIB`/`__SYS_BZLIB` 并移除内置源文件——**无需改上游代码**。

2. **上游测试目标不可用**：`test/CMakeLists.txt` 硬依赖
   `find_package(ALSA REQUIRED)`，且默认 `STORMTEST_USE_OLD_PATHS=ON` 使用 OS
   硬编码 work 路径。沙箱无音频栈 → `STORM_BUILD_TESTS=OFF`，功能覆盖移到
   test_package。

3. **API 语义陷阱**：`SFileReadFile` 在请求长度大于文件实际大小时返回 `FALSE`，
   且 `SErrGetLastError() == 1002`（`ERROR_HANDLE_EOF`）——**即使数据已全部读出**。
   错误日志表现为"读取失败"，实际只是多要了几个字节。

4. 取错误码需用 `StormPort.h` 的 `SErrGetLastError()`，不要 `#include <windows.h>`。

## 适配做法

```python
def requirements(self):
    self.requires("zlib/1.3.1.1")
    self.requires("bzip2/1.0.8.2")

def generate(self):
    tc = CMakeToolchain(self)
    tc.variables["STORM_USE_BUNDLED_LIBRARIES"] = False
    tc.variables["STORM_BUILD_TESTS"] = False   # 上游测试目标要 ALSA
    tc.variables["WITH_LIBTOMCRYPT"] = False    # 用随包 libtomcrypt
    tc.generate()

def package_info(self):
    self.cpp_info.requires = ["zlib::zlib", "bzip2::bzip2"]
```

消费者正确读法：

```c
file_size = SFileGetFileSize(hFile, NULL);
SFileReadFile(hFile, readback, file_size, &read_bytes, NULL);
```

## 验证

`conan create archives/s/stormlib/9.40`（ohos-aarch64）通过，test_package 11 项
断言全过（`StormLib version: 9.40` + `STORMLIB-CONSUMER-OK`），覆盖归档创建、
写文件（ZLIB 压缩 + 加密标志）、关闭、重开、取大小、读取、`memcmp` 逐字节比对。

## 相关

- `archives/s/stormlib/9.40/conanfile.py`
- `archives/s/stormlib/9.40/test_package/test.c`
- smpq/1.7（本包的下游消费者）
