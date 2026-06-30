# cjson 1.7.19 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码：https://github.com/DaveGamble/cJSON/archive/refs/tags/v1.7.19.tar.gz
2. 解压到 ~/builds/cjson-1.7.19.work
3. 应用补丁：patches/0001-CMakeLists.txt.patch
4. cmake 配置：
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
         -DCMAKE_BUILD_TYPE=Release \
         -B build
   ```
5. 编译：cmake --build build -j1
6. 安装：cmake --install build --prefix /storage/Users/currentUser/usr/local

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required VERSION 3.0 鸿蒙不支持 | 鸿蒙 cmake 版本较低 | 补丁修改为 VERSION 3.5 |
| 2 | -std=c89 鸿蒙 clang 不支持 | 鸿蒙 clang 不支持 C89 标准 | 补丁修改为 -std=c99 |

## 源码修改

- patches/0001-CMakeLists.txt.patch
  - cmake_minimum_required VERSION 3.0 → 3.5
  - -std=c89 → -std=c99
  - 移除尾随空格（CMake 语法规范）

## 依赖版本

无外部依赖（纯 C 库）

## 验证结果

cjson 是库，无独立可执行文件，通过库文件验证：
```bash
# 验证库文件存在
ls ~/usr/local/lib/libcjson*
# 输出：libcjson.a, libcjson.so
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cjson-1.7.19-ohos-aarch64.tar.gz | ~50KB | 预编译包（库文件） |
| cjson-1.7.19-ohos-aarch64-debug.tar.gz | ~60KB | 调试版预编译包 |

## 注意事项

- 补丁为平台适配，无需 OHOS 守卫
- 编译简单，无特殊依赖
---

**编译结束**: 2026-05-27 20:05
**最终状态**: built
