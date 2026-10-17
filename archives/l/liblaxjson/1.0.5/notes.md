# liblaxjson 1.0.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

```bash
# 源码: /storage/Users/currentUser/builds/liblaxjson-1.0.5.work（官方 tag 1.0.5 tarball）
cd /storage/Users/currentUser/builds/liblaxjson-1.0.5.work/build
CC=clang cmake .. -DCMAKE_BUILD_TYPE=Release
make -j4
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 报 "Compatibility with CMake < 3.5 has been removed" | CMakeLists.txt 声明 `cmake_minimum_required(VERSION 2.8)`，新 CMake 已移除 <3.5 兼容 | 改为 `cmake_minimum_required(VERSION 3.5)`（纯版本声明，无行为差异） |
| 2 | example/token_list.c 编译失败：`a function declaration without a prototype is deprecated`（-Werror） | 上游自带 `-pedantic -Werror -Wall`，`int main()` 无原型声明在新 clang 触发 strict-prototypes | 改为 `int main(void)` |

## 源码修改

- CMakeLists.txt: `cmake_minimum_required(VERSION 2.8)` → `(VERSION 3.5)`
- example/token_list.c: `int main()` → `int main(void)`

## 上游测试清点与实测（R51）

- 上游测试目录: test/primitives.c（1 个源文件，注册为 ctest `DetectPrimitives`）
- 实测: `ctest --output-on-failure` → 1/1 Passed（0.03s）
- 直接运行: `./primitives_test` rc=0
- example/token_list: 从 file.json 读取（非 stdin），喂入合法 JSON 输出完整 token 流 rc=0
- 说明: 本机无 RPATH，运行时需 `LD_LIBRARY_PATH=$BUILD_DIR` 指向 liblaxjson.so

## 依赖版本

- cmake 4.1.2（需要 `cmake_minimum_required >= 3.5`）
- clang 15.0.4

## 验证结果

```bash
cd /storage/Users/currentUser/builds/liblaxjson-1.0.5.work/build
export LD_LIBRARY_PATH=$PWD
ctest --output-on-failure   # 1/1 tests passed
./primitives_test           # rc=0
```

## 注意事项

- 库为 MIT 协议（COPYING），静态库 laxjson_static + 共享库 laxjson（SOVERSION 1）
- 安装头文件 include/laxjson.h → include/，库 → lib/
- 构建产物：liblaxjson.a、liblaxjson.so.1.0.5
---

**编译结束**: 2026-09-23 00:36
**最终状态**: built
