# eventpp 0.1.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-23
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: built

## 编译步骤

```bash
# 源码: https://github.com/wqking/eventpp/archive/v0.1.3.tar.gz
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
```

eventpp 是 header-only 库（CMake INTERFACE target），编译步骤仅安装头文件，
不产生 `.a`/`.so` 制品。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 报 "System is unknown" 警告 | 鸿蒙 OHOS 平台未被 CMake 内置识别 | conanfile.py generate() 中设置 `CMAKE_SYSTEM_NAME=Linux` (E092) |
| 2 | GitHub 下载超时 | 鸿蒙环境对 GitHub 直连不稳定 | 使用 git clone 获取源码，CI 流水线使用镜像 fallback |

## 源码修改

无补丁，eventpp 源码无需任何修改即可在鸿蒙平台编译运行。

## 依赖版本

无外部依赖。仅使用 C++11 标准库组件：
- `<functional>` `<mutex>` `<atomic>` `<condition_variable>`
- `<memory>` `<map>` `<unordered_map>` `<list>` `<cassert>`

## 验证结果

```bash
# CMake 配置
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
# → Configuring done, Generating done

# 编译安装
make install DESTDIR=$TEST_PREFIX
# → 所有头文件正确安装到 include/eventpp/

# 示例程序验证
clang++ -std=c++11 -I./include -o test_eventpp test_eventpp.cpp
./test_eventpp
# → Callback: Hello HarmonyOS 1
# → Got event 3
# → Got event 5: World
# → All tests passed!
```

三大核心组件（CallbackList、EventDispatcher、EventQueue）均在鸿蒙平台验证通过。

## 注意事项

- eventpp 是 header-only 库，`package_info()` 中 `cpp_info.libs` 应为空列表
- 上游单元测试（tests/ 目录）需要 C++17 和 GTest，CI test_package 使用自带的消费者测试（C++11）
- 版本 0.1.3 是上游最新正式发布版本（2023-09-21）
---

**编译结束**: 2026-07-23 11:15
**最终状态**: built
