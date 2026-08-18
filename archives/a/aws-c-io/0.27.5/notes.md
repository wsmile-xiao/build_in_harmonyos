# aws-c-io 0.27.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码 `aws-c-io v0.27.5` 并解压
2. 应用两个补丁（平台检测 + 线程链接顺序）
3. 使用 Conan 工具链配置 CMake：
   ```bash
   cmake -B build \
     -DBUILD_TESTING=OFF \
     -DBYO_CRYPTO=ON \
     -DBUILD_SHARED_LIBS=ON \
     -DCMAKE_PREFIX_PATH="<dep_folders>"
   ```
4. `cmake --build build`
5. `cmake --install build`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 HarmonyOS 平台 | aws-c-io CMakeLists.txt 平台检测分支只有 Linux/Android，无 HarmonyOS | 补丁 0001：在 `elseif` 条件中添加 `CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"` |
| 2 | `Threads::Threads` 目标未定义 | `find_package(aws-c-cal)` 触发 aws-lc 的 crypto-config.cmake 引用 `Threads::Threads`，但 `find_package(Threads)` 在其后调用 | 补丁 0002：将 `find_package(Threads REQUIRED)` 提前至 `aws_use_package(aws-c-cal)` 之前 |

## 源码修改

- `patches/0001-CMakeLists-add-harmonyos-platform.patch`：在 CMakeLists.txt 平台检测 `elseif` 分支添加 HarmonyOS，复用 Linux/epoll 事件循环源码
- `patches/0002-CMakeLists-add-threads-before-cal.patch`：将 `find_package(Threads REQUIRED)` 移至 `aws_use_package(aws-c-cal)` 之前

## 依赖版本

- aws-c-common/0.14.3
- aws-c-cal/0.9.15
- aws-lc/5.4.0（aws-c-cal 的传递依赖，需直接声明以使 CMAKE_PREFIX_PATH 包含其路径）

## 验证结果

```bash
conan create . --build=missing    # PASS
cd test_package && conan test ..   # 1/1 PASS
```

## 注意事项

- 使用 `CMAKE_PREFIX_PATH` 而非 `CMakeDeps`，以保留上游 `AWS::` 目标名和 CMake 模块路径（AwsCFlags、AwsCheckHeaders 等）
- `BYO_CRYPTO=ON` 禁用 s2n-tls TLS 后端，基础 IO 功能（事件循环、socket、DNS）仍可用
- aws-lc 虽是 aws-c-cal 的传递依赖，但需在 conanfile.py 中直接声明，以便 Conan 工具链将其 lib/include 路径加入 CMAKE_LIBRARY_PATH/CMAKE_INCLUDE_PATH

---

**编译结束**: 2026-07-27 13:51
**最终状态**: built

## 最终状态

COMPLETED — aws-c-io 0.27.5 适配完成，状态: built
