# toml11 4.4.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码 tarball: https://github.com/ToruNiina/toml11/archive/refs/tags/v4.4.0.tar.gz
2. 解压源码
3. CMake 配置:
```bash
cmake .. -DCMAKE_BUILD_TYPE=Release -DTOML11_INSTALL=ON -DCMAKE_SYSTEM_NAME=OHOS -DCMAKE_CXX_STANDARD=11
```
4. 构建:
```bash
make -j1
```
5. 安装到 staging 目录:
```bash
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 测试编译失败: doctest.h not found | tarball 不含 git submodule (tests/extlib/doctest) | 跳过测试构建，Conan test_package 使用独立测试 |
| 2 | make -j2 失败: mkfifo Operation not permitted | HMDFS 不支持 mkfifo | 改用 make -j1 |

## 源码修改

无补丁，源码无需修改。

## 依赖版本

无外部依赖。toml11 是 header-only 库，仅需 C++11 编译器。

## 验证结果

```bash
# 烟雾测试: 编写简单程序解析 TOML 字符串
clang++ -std=c++11 -I<include-path> test_toml11.cpp -o test_toml11
./test_toml11
# 输出:
# key = value
# num = 42
```

## 注意事项

- toml11 是 header-only 库，构建产物只有头文件和 CMake 配置文件
- 上游测试依赖 doctest 和 json submodules，tarball 下载不含 submodule 内容
- Conan 配方应使用 CMake 包装器，设置 TOML11_INSTALL=ON
---

**编译结束**: 2026-08-23 00:14
**最终状态**: built
