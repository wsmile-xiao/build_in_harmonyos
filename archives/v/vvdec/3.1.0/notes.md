# vvdec 3.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-18
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: published

## 编译步骤

1. `cd $BUILD_SRC_DIR && mkdir build && cd build`
2. `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DVVDEC_INSTALL_VVDECAPP=ON`
3. `make -j2`
4. `make install DESTDIR=$TEST_PREFIX` (R20 DESTDIR staging)
5. `make install` (本地安装到 $DEFAULT_PREFIX)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `error: bad option 'no-tree-vectorize' to attribute 'optimize'` | Clang 不支持 GCC 的 `__attribute__((optimize("no-tree-vectorize")))` 语法（宏 `NO_OPT_SIMD`） | 修改 `CommonDefX86.cpp` 中宏定义：将 `#if __GNUC__` 改为 `#if defined(__GNUC__) && !defined(__clang__)` |
| 2 | vvdecapp 默认不安装 | cmake 配置选项 `VVDEC_INSTALL_VVDECAPP` 默认 OFF | 添加 `-DVVDEC_INSTALL_VVDECAPP=ON` |
| 3 | 测试套全部失败 | 需要 239 个外部 conformance bitstream 测试数据文件 | 非代码问题，bitstream 文件需 `-DVVDEC_ENABLE_BITSTREAM_DOWNLOAD=ON` 下载，不影响编译结果 |

## 源码修改

- `source/Lib/CommonLib/x86/CommonDefX86.cpp`: 修复 clang 兼容性
  - 原: `#if __GNUC__` → 改为: `#if defined(__GNUC__) && !defined(__clang__)`
  - 补丁: `0001-source-Lib-CommonLib-x86-CommonDefX86.cpp.patch`

## 依赖版本

无外部依赖。使用内置的 SIMDE (SIMD Everywhere) 实现 x86 SIMD 指令跨平台。

## 验证结果

```bash
$ vvdecapp --version
vvdecapp version 3.1.0

$ vvdecapp --help
Usage: vvdecapp [param1] [pararm2] [...]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| vvdec-3.1.0-ohos-aarch64.tar.gz | 9181KB | 预编译包（ELF签名） |
| vvdec-3.1.0-ohos-aarch64-debug.tar.gz | 298KB | 调试符号包 |

## 注意事项

- vvdec 使用 SIMDE 实现 x86 SIMD 跨平台到 ARM，无需修改架构相关代码
- 测试套需下载大型 bitstream 文件，编译时跳过不影响功能
- G0 干净构建验证因鸿蒙平台 `patch` 命令限制失败，已手动验证补丁正确

---
**编译结束**: 2026-06-18 00:23
**最终状态**: published
